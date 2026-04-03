---
name: implement
description: "Implement a GitHub issue step-by-step with verification checkpoints. Designed for small local models (Qwen, Mistral) that need explicit guidance."
argument-hint: "<issue-number>"
---

# Implement Issue $ARGUMENTS

You are implementing a GitHub issue. Follow this procedure EXACTLY.
Do NOT skip steps. Do NOT improvise.

## Phase 1 — Read the issue

```bash
gh issue view $ARGUMENTS
```

Read the output carefully. Identify:

1. The list of files to CREATE or MODIFY
2. The numbered steps
3. The verification commands for each step
4. The "NE pas faire" section

## Phase 2 — Setup branch

```bash
git checkout main
git pull origin main
```

Determine branch name from the issue title:

- `enhancement` or `feature` label → `feature/plland/<kebab-case>`
- `bug` or `fix` label → `fix/plland/<kebab-case>`
- Default → `feature/plland/<kebab-case>`

```bash
git checkout -b <branch-name>
```

## Phase 3 — Execute steps ONE BY ONE

For EACH step in the issue:

1. Read the step instructions
2. Make the changes to the SINGLE file specified
3. Run the verification command for that step
4. If verification FAILS: fix the error, re-run verification
5. If verification PASSES: commit with message `<type>(<scope>): <step-description> — Refs #$ARGUMENTS`
6. Move to the next step

CRITICAL RULES:

- ONE step at a time. Do NOT batch multiple steps.
- ONE file per step. Do NOT edit multiple files in one step.
- ALWAYS run the verification command before moving on.
- If you are UNSURE about something, re-read the issue. Do NOT guess.

## Phase 4 — Final verification

Run ALL commands from the "Vérification finale" section of the issue.
Every command must pass.

```bash
# Typical final checks
uv run ruff check apps/
cd apps/web && npx tsc --noEmit
```

## Phase 5 — Create PR

```bash
git push -u origin <branch-name>
gh pr create \
  --title "$(gh issue view $ARGUMENTS --json title -q .title)" \
  --body "## Changes
$(git log --oneline main..HEAD | sed 's/^/- /')

## Verification
All verification commands from issue #$ARGUMENTS pass.

Closes #$ARGUMENTS

🤖 Generated with Claude Code"
```

## Phase 6 — Signal completion

```bash
echo "✅ DONE — PR created for issue #$ARGUMENTS"
```

## REMINDERS

- Do NOT modify files not listed in the issue
- Do NOT install packages not listed in the issue
- Do NOT refactor code unrelated to the issue
- If a verification fails after 3 attempts, STOP and explain the error
