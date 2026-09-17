---
name: commit-helper
description: Generates descriptive git commit messages from staged and unstaged changes. Use when the user asks to commit, write a commit message, or review changes before committing.
---

# Commit helper

## Workflow

1. Run in parallel:
   - `git status`
   - `git diff` (staged and unstaged)
   - `git log -5 --oneline` (match repo style)
2. Draft a 1–2 sentence message focused on **why**, not a file list.
3. Stage relevant files only; never stage secrets (`.env`, credentials, keys).
4. Commit only when the user explicitly asks.
5. Run `git status` after commit to confirm success.

## Message format

Follow recent commits in the repo. Default when no pattern exists:

```
<type>: <short summary>

<optional body explaining why>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Safety

- Never update git config.
- Never `--no-verify`, force-push, or amend unless explicitly requested and safe.
- Never commit `.env` or credential files.
