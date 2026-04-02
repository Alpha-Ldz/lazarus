# Review PR Comments

Récupère les commentaires d'une PR, applique les modifications demandées, et répond aux commentaires.

## Arguments

- `$ARGUMENTS` : Numéro de la PR GitHub (ex: 42)

## Instructions

### 1. Récupérer les commentaires de review

Utilise l'API GitHub pour récupérer les commentaires :

```bash
gh api repos/:owner/:repo/pulls/$ARGUMENTS/comments
```

Pour chaque commentaire, note :
- `id` : identifiant du commentaire (pour répondre)
- `path` : fichier concerné
- `line` : ligne concernée
- `body` : contenu du commentaire
- `diff_hunk` : contexte du code

### 2. Analyser les demandes

Pour chaque commentaire :
1. Comprends la demande de modification
2. Localise le code concerné
3. Planifie les changements nécessaires

### 3. Appliquer les modifications

Pour chaque demande :
1. Modifie le code selon la demande
2. Vérifie que le code compile (`npm run build`, `uv run pytest`, etc.)
3. Crée un commit descriptif référençant la PR

Format du commit :
```
fix(scope): description de la correction

Répond au commentaire de review sur <fichier>

Refs #<numéro-pr>
```

### 4. Push les modifications

```bash
git push
```

### 5. Répondre aux commentaires

Ajoute un commentaire à la PR résumant les modifications :

```bash
gh pr comment $ARGUMENTS --body "<description des modifications>"
```

Le message de réponse doit :
- Référencer le commentaire original (ex: "Re: configuration API")
- Confirmer que la modification a été faite
- Mentionner le hash du commit
- Décrire brièvement les changements avec un extrait de code si pertinent
