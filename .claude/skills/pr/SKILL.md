---
name: pr
description: Open a GitHub pull request for this repo with the gh CLI. Runs ruff and pytest before pushing, makes sure the PR links to an open issue (creates one if none exists), opens the PR, then launches the haiku pr-check-monitor to watch CI and fix any failures. Use when the user asks to open, create, or submit a PR (/pr).
---

# Open a Pull Request

Open a PR for the current branch with `gh`. Every PR must link to an open issue, so the PR shows up under that issue. Run the checks locally first, then watch CI after.

If `gh` is not on PATH, use `/opt/homebrew/bin/gh`. The repo is `hyperjumptech/agentic-mediapulse` on `github.com`.

## Steps

### 1. Look at the change

```bash
git status
git diff
git log --oneline -n 10
```

The base branch is the repo default (`main`). Review the change with `git diff main...HEAD`.

### 2. Run the checks (must pass before pushing)

```bash
conda run -n agentic-mediapulse ruff check .
conda run -n agentic-mediapulse ruff format --check .
conda run -n agentic-mediapulse python -m pytest
```

Fix anything that fails and re-run until all three are clean. Do not push hoping CI will catch it.

### 3. Push the branch

If you are on `main`, create a feature branch first (`git switch -c <type>/<short-name>`, e.g. `feat/email-retry`). Commit pending changes, then:

```bash
git push -u origin HEAD
```

### 4. Make sure a linked issue exists

A PR with no issue is not allowed. Find one, or create one.

```bash
gh issue list --repo hyperjumptech/agentic-mediapulse --state open --limit 20
```

- If an open issue matches the work, use its number.
- If none matches, create one (write the body to a temp file so nothing lands in the repo):

```bash
ISSUE_FILE="$(mktemp "${TMPDIR:-/tmp}/gh-issue.XXXXXX")"
trap 'rm -f "$ISSUE_FILE"' EXIT
cat <<'EOF' >"$ISSUE_FILE"
## Summary

What the change does and why.

## Acceptance criteria

- [ ] The outcome a reviewer can check.

## Notes

Anything useful for context.
EOF
gh issue create --repo hyperjumptech/agentic-mediapulse -t "Concise issue title" --body-file "$ISSUE_FILE"
```

Capture the number and confirm it is open:

```bash
ISSUE_NUM="$(gh issue view <number-or-url> --repo hyperjumptech/agentic-mediapulse --json number -q .number)"
gh issue view "$ISSUE_NUM" --repo hyperjumptech/agentic-mediapulse --json state -q .state   # must print OPEN
```

### 5. Open the PR

Write the body to a temp file, then create the PR. Keep the prose plain and human: no em dashes, no semicolons, no filler.

```bash
BODY_FILE="$(mktemp "${TMPDIR:-/tmp}/gh-pr.XXXXXX")"
trap 'rm -f "$BODY_FILE"' EXIT
cat <<'EOF' >"$BODY_FILE"
## Summary

1-3 sentences on what changed and why.

## Related issues

Closes #<ISSUE_NUM>

## Changes

- The important change a reviewer should check.
- Smaller follow-ups.

## How to test

1. The command(s) to run.
2. The expected result.
EOF
gh pr create --repo hyperjumptech/agentic-mediapulse --base main \
  --title "Verb-first title, no trailing period" --body-file "$BODY_FILE"
```

Use `Closes #N` when the PR finishes the issue, or `Refs #N` to link without closing. Capture the PR number:

```bash
PR_NUM="$(gh pr view --repo hyperjumptech/agentic-mediapulse --json number -q .number)"
PR_URL="$(gh pr view --repo hyperjumptech/agentic-mediapulse --json url -q .url)"
```

### 6. Watch CI and fix failures

Launch the **pr-check-monitor** subagent (Task tool, `run_in_background: true`) so CI is watched while you finish up. It runs on haiku, fixes any failing check, and pushes the fix.

Prompt:

```text
Watch CI for PR #<PR_NUM> in hyperjumptech/agentic-mediapulse (<PR_URL>).
Run until all checks pass or 30 minutes elapse.
If a check fails, read the failing logs, fix the cause, re-run ruff and pytest locally, commit, push, and keep watching until green.
Report the final status and what you changed.
```

Skip the monitor only if the user says not to watch CI.

### 7. Report

Give the PR URL, the linked issue, and a one-line test note. Say the monitor is watching CI in the background.
