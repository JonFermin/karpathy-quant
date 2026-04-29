#!/usr/bin/env python3
"""
PostToolUse hook: open a GitHub PR after a successful `git push`.

Wired up in .claude/settings.local.json on the PostToolUse:Bash event.
Reads the standard Claude Code hook JSON from stdin, fast-paths out for
anything that isn't a successful `git push`, and only opens a PR when:

  - the pushed branch is not master / main / HEAD,
  - the branch is ahead of origin/master,
  - and no open PR already exists for that head.

PR title/body come from `gh pr create --fill` (auto-populated from the
commits between master and the branch tip), so the hook needs no template.
Failures (no gh, no remote, network blip) are swallowed silently — never
break the loop on a side-effect hook.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys


SKIP_BRANCHES = {"master", "main", "HEAD", ""}


def _silent() -> None:
    sys.exit(0)


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, "", ""


def _parse_pushed_branch(cmd: str, repo: str) -> str:
    """Best-effort extraction of the branch name from the `git push` invocation.

    Falls back to the current HEAD's short name if the command is a bare
    `git push` (no remote/branch args). Strips `<local>:<remote>` mappings
    by keeping the LOCAL side, since we open a PR against the remote-named
    branch which `gh` resolves from the local checkout.
    """
    match = re.search(r"\bgit\s+push\b([^|;&\n]*)", cmd)
    if match:
        tail = match.group(1).strip().split()
        non_flag = [t for t in tail if not t.startswith("-")]
        if len(non_flag) >= 2:
            spec = non_flag[1]
            return spec.split(":", 1)[-1]
    rc, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    return out if rc == 0 else ""


def main() -> None:
    raw = sys.stdin.read()
    if not raw:
        _silent()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        _silent()

    if payload.get("tool_name") != "Bash":
        _silent()

    cmd = (payload.get("tool_input") or {}).get("command", "")
    if "git push" not in cmd:
        _silent()

    response = payload.get("tool_response") or {}
    # Different harness versions have used `exit_code`, `exitCode`, or none at
    # all (success implied). Treat missing-but-no-stderr-error as success.
    exit_code = response.get("exit_code", response.get("exitCode", 0))
    if exit_code not in (0, "0"):
        _silent()

    if shutil.which("gh") is None or shutil.which("git") is None:
        _silent()

    repo = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    rc, root, _ = _run(["git", "rev-parse", "--show-toplevel"], cwd=repo)
    if rc != 0:
        _silent()
    repo = root

    branch = _parse_pushed_branch(cmd, repo)
    if branch in SKIP_BRANCHES:
        _silent()

    # Refuse to PR a branch that has no commits over master (prevents the
    # "no commits between master and X" gh error from polluting the loop).
    rc, ahead, _ = _run(
        ["git", "rev-list", "--count", f"origin/master..origin/{branch}"],
        cwd=repo,
    )
    if rc != 0 or not ahead.isdigit() or int(ahead) == 0:
        _silent()

    rc, count, _ = _run(
        ["gh", "pr", "list", "--head", branch, "--state", "open",
         "--json", "number", "--jq", "length"],
        cwd=repo,
    )
    if rc == 0 and count.strip() not in ("", "0"):
        _silent()

    rc, url, err = _run(
        ["gh", "pr", "create", "--base", "master", "--head", branch, "--fill"],
        cwd=repo,
    )
    if rc == 0 and url:
        # Stderr is surfaced to the user via the hook's transcript line.
        print(f"auto-pr: opened {url}", file=sys.stderr)
    elif err:
        print(f"auto-pr: skipped ({err.splitlines()[-1] if err else 'unknown'})", file=sys.stderr)


if __name__ == "__main__":
    main()
