---
name: implement
description: "Implement a GitHub issue step-by-step with verification checkpoints. Designed for small local models (Qwen, Mistral) that need explicit guidance."
argument-hint: "<issue-number>"
---

# STOP. READ THIS FIRST.

You are NOT explaining code. You are NOT answering questions.
You are IMPLEMENTING a GitHub issue by WRITING CODE and RUNNING COMMANDS.

Your job:

1. Read the issue
2. Create a branch
3. Edit files exactly as described in the issue steps
4. Run verification commands after each step
5. Commit and push
6. Create a PR

DO NOT analyze or summarize code.
DO NOT ask the user questions.
DO NOT stop until you have written `echo "✅ DONE"`.

If you are unsure, re-read the issue. The issue contains ALL the information you need.

---

## NOW: Implement issue #$ARGUMENTS

### Phase 1 — Read the issue

Run this command NOW:

```bash
gh issue view $ARGUMENTS
```

From the output, identify:

- The STEPS (numbered)
- The FILES to create or modify
- The VERIFICATION COMMANDS for each step

### Phase 2 — Create a branch

Run these commands NOW:

```bash
git checkout main
git pull origin main
git checkout -b feature/plland/issue-$ARGUMENTS
```

### Phase 3 — Execute steps ONE BY ONE

RULES:

- Execute step 1 FIRST. Do NOT read ahead.
- After each step, run its verification command.
- If verification FAILS: fix and retry (max 3 attempts).
- If verification PASSES: commit and move to next step.
- Commit message format: `feat(scope): description — Refs #$ARGUMENTS`

START WITH STEP 1 NOW. Do NOT plan. Do NOT summarize. WRITE CODE.

### Phase 4 — After ALL steps are done

```bash
# Final verification
cd apps/web && npx tsc --noEmit
uv run ruff check apps/

# Push and create PR
git push -u origin feature/plland/issue-$ARGUMENTS
gh pr create \
  --title "$(gh issue view $ARGUMENTS --json title -q .title)" \
  --body "Closes #$ARGUMENTS

$(git log --oneline main..HEAD | sed 's/^/- /')

🤖 Generated with Claude Code"

echo "✅ DONE"
```

## REMINDERS

- Do NOT explain code. WRITE code.
- Do NOT ask questions. READ the issue.
- Do NOT stop early. Finish ALL steps.
- Do NOT modify files not listed in the issue.
