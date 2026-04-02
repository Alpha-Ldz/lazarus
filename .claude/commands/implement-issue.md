# Implement GitHub Issue

Implémente une issue GitHub de manière structurée avec des commits atomiques.

## Arguments

- `$ARGUMENTS` : Numéro de l'issue GitHub (ex: 42)

## Instructions

### 1. Lire l'issue GitHub

Utilise `gh issue view $ARGUMENTS` pour récupérer les détails de l'issue :
- Titre
- Description
- Labels (pour déterminer le type : feature, fix, doc, chore, refactor, test)

### 2. Déterminer le type de branche

Analyse les labels de l'issue pour choisir le préfixe :
- `enhancement`, `feature` → `feature/`
- `bug`, `fix` → `fix/`
- `documentation` → `doc/`
- `refactor` → `refactor/`
- `test` → `test/`
- Par défaut → `feature/`

### 3. Créer la branche

Crée une branche avec le format : `<type>/plland/<nom-descriptif>`

Le nom descriptif doit être :
- En kebab-case
- Court mais explicite (max 50 caractères)
- Basé sur le titre de l'issue

Exemple : `feature/plland/add-user-authentication`

Commandes :
```bash
git checkout main
git pull origin main
git checkout -b <nom-de-la-branche>
```

### 4. Analyser et planifier l'implémentation

Avant de coder :
1. Analyse les critères d'acceptation de l'issue
2. Décompose en étapes atomiques et testables
3. Présente le plan à l'utilisateur pour validation

### 5. Implémenter étape par étape

Pour chaque étape du plan :
1. Implémente les changements nécessaires
2. Vérifie que le code fonctionne (tests, lint, etc.)
3. Crée un commit avec un message descriptif

Format des commits :
```
<type>(<scope>): <description courte>

<description détaillée si nécessaire>

Refs #<numéro-issue>
```

Types de commit : feat, fix, docs, refactor, test, chore

### 6. Résumé final

Une fois terminé :
1. Affiche un résumé des commits créés avec `git log --oneline main..HEAD`
2. Affiche la structure des fichiers créés/modifiés

### 7. Créer la Pull Request

Crée automatiquement une PR avec `gh pr create` :

```bash
git push -u origin <nom-de-la-branche>
gh pr create --title "<titre-issue>" --body "$(cat <<'EOF'
## Summary
<liste des changements principaux en bullet points>

## Test plan
<checklist de tests à effectuer>

Closes #<numéro-issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

La PR doit :
- Avoir un titre clair reprenant celui de l'issue
- Contenir un résumé des changements
- Inclure un plan de test
- Référencer l'issue avec `Closes #<numéro>`
