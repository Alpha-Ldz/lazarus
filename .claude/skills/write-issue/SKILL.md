---
name: write-issue
description: "Write a GitHub issue formatted for implementation by a small local model (Qwen, Mistral). Produces step-by-step issues with verification checkpoints."
argument-hint: "<description of what you want to build>"
---

# Write Issue for Small Model Agent

The user wants: $ARGUMENTS

You must produce a GitHub issue that a small LLM (Qwen 35B, Mistral) can implement
without ambiguity. Small models CANNOT guess intent — everything must be explicit.

## Step 1 — Understand the codebase

Read the relevant files to understand the current state:

```bash
# Always read these first
cat CLAUDE.md
cat apps/web/src/types/index.ts
```

Then read files related to the requested feature:

- If backend: `cat apps/api/routers/*.py` and `cat apps/api/main.py`
- If frontend: `ls apps/web/src/components/` and read relevant components
- If both: read both sides

## Step 2 — Plan the implementation

Break the feature into steps following these rules:

1. **MAX 5 steps per issue** — if more, split into multiple issues
2. **1 step = 1 file** — never modify 2 files in one step
3. **Types first** — always start with TypeScript types or Pydantic models
4. **Backend before frontend** — API endpoints before UI
5. **Each step has a verification command** — a bash command that proves the step worked

## Step 3 — Write the issue

Use this EXACT format:

````markdown
## <type>: <description courte — 10 mots max>

### Contexte

[3 lignes max. Pourquoi cette feature existe.]

### Fichiers concernés

| Action        | Fichier          | Détail      |
| ------------- | ---------------- | ----------- |
| CREATE/MODIFY | `chemin/complet` | description |

### Dépendances à installer

[Commandes exactes ou "Aucune"]

### Steps

#### Step 1/N — [nom]

**Fichier**: `chemin/complet`
**Action**: CREATE | MODIFY

[Code exact à écrire ou à ajouter]

**Vérification step 1**:

```bash
[commande qui prouve que ça marche]
```
````

[...repeat for each step...]

### Vérification finale

```bash
[toutes les commandes de vérif]
echo "✅ DONE"
```

### Acceptance Criteria

- [ ] [critère vérifiable]

### NE PAS FAIRE

- [piège à éviter]

````

## Step 4 — Create the issue on GitHub

```bash
gh issue create \
  --title "<type>: <description>" \
  --body "$(cat /tmp/issue-body.md)" \
  --label "<enhancement|bug|chore>"
````

## Quality checklist before posting

- [ ] Every file path is absolute from project root
- [ ] Every step has a verification command
- [ ] Code blocks have language tags (python, typescript, bash)
- [ ] "NE pas faire" section is present
- [ ] No step touches more than 1 file
- [ ] Max 5 steps total
- [ ] Types/models are defined BEFORE they are used
