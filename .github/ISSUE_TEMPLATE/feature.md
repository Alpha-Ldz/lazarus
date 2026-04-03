# Issue Template for Lazarus (Small Model Agents)

> **Principe clé** : un petit modèle (Qwen, Mistral) ne devine rien.
> Chaque issue = une checklist de micro-tâches avec des vérifications intermédiaires.
> Le modèle exécute step 1, vérifie, step 2, vérifie, etc.

---

## Format

````markdown
## feat|fix|chore: [description courte en 10 mots max]

### Contexte (3 lignes max)

[POURQUOI cette tâche existe. Quel problème elle résout.]

### Fichiers concernés

| Action | Fichier                       | Détail                  |
| ------ | ----------------------------- | ----------------------- |
| CREATE | `apps/api/services/foo.py`    | Service de calcul       |
| MODIFY | `apps/api/routers/analyze.py` | Ajouter endpoint /stats |
| MODIFY | `apps/web/src/types/index.ts` | Ajouter interface Stats |

### Dépendances à installer

```bash
# Si rien à installer, écrire: Aucune
cd apps/api && uv add httpx
cd apps/web && npm install recharts
```
````

### Steps

> IMPORTANT: Exécute les steps dans l'ordre. Après chaque step,
> lance la commande de vérification AVANT de passer au suivant.

#### Step 1/N — [Nom de l'étape]

**Fichier**: `chemin/complet/du/fichier.py`
**Action**: CREATE | MODIFY | DELETE

[Description précise de ce qu'il faut faire — pseudo-code ou code exact]

```python
# Exemple de code attendu (copier-coller ok)
from pydantic import BaseModel

class StatsResponse(BaseModel):
    total_defects: int
    by_class: dict[str, int]
```

**Vérification step 1**:

```bash
python -c "from apps.api.services.foo import StatsResponse; print('OK')"
```

---

#### Step 2/N — [Nom de l'étape]

**Fichier**: `chemin/complet/du/fichier.tsx`
**Action**: MODIFY

[...]

**Vérification step 2**:

```bash
cd apps/web && npx tsc --noEmit
```

---

### Vérification finale

```bash
# TOUTES ces commandes doivent passer sans erreur
uv run ruff check apps/
cd apps/web && npx tsc --noEmit
curl -s http://localhost:8000/api/[endpoint] | python -m json.tool
echo "✅ DONE"
```

### Acceptance Criteria

- [ ] Critère 1 (vérifiable par une commande)
- [ ] Critère 2 (vérifiable par une commande)
- [ ] Pas de régression: les endpoints existants fonctionnent toujours

### NE PAS FAIRE

- Ne pas toucher à [fichier X]
- Ne pas renommer [chose Y]
- Ne pas installer de package non listé ci-dessus

````

---

## Règles d'or pour petits modèles

### 1. Taille d'une issue = MAX 5 steps
Si tu dépasses 5 steps, découpe en 2 issues avec des dépendances.
Un petit modèle perd le fil au-delà de 5 actions.

### 2. Un step = un fichier
Ne jamais demander de modifier 2 fichiers dans le même step.
Exception : si c'est un import + son usage dans le même fichier.

### 3. Code > Prose
Privilégie le code exact à copier plutôt qu'une description en français.
Le modèle exécute mieux du code qu'il n'interprète des instructions vagues.

### 4. Vérifications intermédiaires obligatoires
Chaque step a une commande de vérification. Ça sert de checkpoint :
- Si la vérification échoue, le modèle peut corriger avant de continuer
- Si la vérification passe, le modèle sait qu'il peut avancer

### 5. Section "NE PAS FAIRE" obligatoire
Les petits modèles adorent "améliorer" le code existant.
Lister explicitement ce qu'il ne faut PAS toucher.

### 6. Pas d'ambiguïté sur les chemins
Toujours `apps/api/routers/analyze.py`, jamais `analyze.py`.

### 7. Variables d'environnement
Si la feature nécessite une env var, indiquer :
- Le nom exact
- Une valeur d'exemple
- Où la mettre (.env, export, etc.)

---

## Exemple concret

```markdown
## feat: ajouter endpoint GET /api/analyze/stats

### Contexte
On veut afficher des stats globales dans le dashboard :
nombre total de défauts analysés, répartition par classe.

### Fichiers concernés
| Action | Fichier | Détail |
|--------|---------|--------|
| MODIFY | `apps/api/routers/analyze.py` | Ajouter GET /stats |
| MODIFY | `apps/web/src/types/index.ts` | Ajouter AnalyzeStats |

### Dépendances à installer
Aucune

### Steps

#### Step 1/2 — Ajouter le type AnalyzeStats
**Fichier**: `apps/web/src/types/index.ts`
**Action**: MODIFY — ajouter à la fin du fichier

```typescript
export interface AnalyzeStats {
  total_analyses: number
  defects_by_class: Record<string, number>
  last_analysis_at: string | null
}
````

**Vérification step 1**:

```bash
cd apps/web && npx tsc --noEmit
```

#### Step 2/2 — Ajouter l'endpoint /stats

**Fichier**: `apps/api/routers/analyze.py`
**Action**: MODIFY — ajouter cette route après la route POST existante

```python
@router.get("/stats")
async def get_stats():
    """Retourne les stats d'analyse."""
    # Pour l'instant, retourner des valeurs statiques
    return {
        "total_analyses": 0,
        "defects_by_class": {},
        "last_analysis_at": None,
    }
```

**Vérification step 2**:

```bash
curl -s http://localhost:8000/api/analyze/stats | python -m json.tool
```

### Vérification finale

```bash
uv run ruff check apps/api/routers/analyze.py
cd apps/web && npx tsc --noEmit
curl -s http://localhost:8000/api/analyze/stats | python -m json.tool
# Vérifier que l'ancien endpoint marche encore
curl -s -X POST http://localhost:8000/api/analyze -F "file=@test.jpg" | python -m json.tool
echo "✅ DONE"
```

### Acceptance Criteria

- [ ] GET /api/analyze/stats retourne un JSON avec total_analyses, defects_by_class, last_analysis_at
- [ ] Le type AnalyzeStats existe dans apps/web/src/types/index.ts
- [ ] POST /api/analyze fonctionne toujours (pas de régression)

### NE PAS FAIRE

- Ne pas modifier le modèle YOLO ni son chargement
- Ne pas toucher à apps/api/main.py
- Ne pas créer de nouveau fichier

```

```
