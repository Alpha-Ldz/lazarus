# Workflow Lazarus — Guide de bonnes pratiques

## Architecture du workflow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Toi (human) │     │ Claude Opus  │     │ Qwen/Mistral    │
│  + Claude    │────▶│ /write-issue │────▶│ /implement #42  │
│  (planif)    │     │ (rédaction)  │     │ (exécution)     │
└─────────────┘     └──────────────┘     └─────────────────┘
       ▲                                          │
       │                                          │
       └──────── review PR ◀──────────────────────┘
```

**Toi + Claude Opus** : planification, architecture, rédaction d'issues
**Petit modèle** : exécution mécanique step-by-step

---

## Fichiers livrés

| Fichier | Où le placer | Rôle |
|---------|-------------|------|
| `CLAUDE.md` | `lazarus/CLAUDE.md` (racine du projet) | Contexte projet pour tous les agents |
| `ISSUE_TEMPLATE.md` | `lazarus/.github/ISSUE_TEMPLATE/feature.md` | Template GitHub Issues |
| `.claude/skills/implement/SKILL.md` | `lazarus/.claude/skills/implement/SKILL.md` | Skill d'implémentation |
| `.claude/skills/write-issue/SKILL.md` | `lazarus/.claude/skills/write-issue/SKILL.md` | Skill de rédaction d'issues |

---

## Setup Claude Code + modèle local

### Option 1 : Ollama (le plus simple)
```bash
# Installer le modèle
ollama pull qwen3-coder

# Lancer Claude Code avec le modèle local
ANTHROPIC_BASE_URL=http://localhost:11434 \
ANTHROPIC_MODEL=qwen3-coder \
claude --dangerously-skip-permissions
```

### Option 2 : llama.cpp (meilleure perf sur RTX 5090)
```bash
# Servir le modèle
./llama-server -m qwen3-coder-Q4_K_M.gguf \
  -c 32768 \       # contexte 32K minimum
  -ngl 99 \        # tout sur GPU
  --port 8001

# Lancer Claude Code
ANTHROPIC_BASE_URL=http://localhost:8001 \
ANTHROPIC_API_KEY=dummy \
claude
```

### Paramètres critiques pour petits modèles
- **Contexte**: minimum 25K tokens, idéal 32K
- **Temperature**: 0.1-0.3 pour du code (pas 0.7 !)
- **Quantization**: Q4_K_M minimum, Q5_K_M si tu as la VRAM

---

## Tips anti-boucle / anti-arrêt

### 1. Le signal de fin
Toujours terminer les issues par `echo "✅ DONE"`.
Les petits modèles ont besoin d'un signal explicite de complétion.

### 2. Vérifications intermédiaires = checkpoints de sauvegarde
Chaque step a une commande de vérification. Si elle échoue,
le modèle peut corriger. Si elle passe, il avance.
Sans ça, le modèle tourne en rond sans savoir où il en est.

### 3. Un step = un fichier = un commit
Le modèle ne peut pas "tenir en tête" des changements
dans 3 fichiers simultanément. Un à la fois.

### 4. La section "NE PAS FAIRE"
Les petits modèles adorent "améliorer" le code qu'ils voient.
Lister ce qu'il ne faut PAS toucher les cadre.

### 5. Compact régulièrement
À 50% de contexte, faire `/compact` manuellement.
À 90%+, le modèle hallucine. Faire `/clear` et relancer.

### 6. La technique "Ralph Wiggum"
Si le modèle s'arrête avant la fin, relancer en boucle :
```bash
# Boucle bash externe
while ! grep -q "DONE" /tmp/claude-output.log; do
  claude -m qwen3-coder -p "Continue implementing issue #42. \
    Check git log for what's already done. \
    Resume from where you left off. \
    When ALL steps are done, run echo '✅ DONE'"
done
```

### 7. Issues de max 5 steps
Au-delà, le modèle perd le fil. Découper en sous-issues
avec des dépendances : "Issue #43 depends on #42".

---

## Workflow quotidien recommandé

1. **Planifier** (toi + Claude Opus sur claude.ai)
   - Décrire la feature en langage naturel
   - Utiliser `/write-issue` pour générer l'issue formatée
   - Relire, ajuster, poster sur GitHub

2. **Exécuter** (Qwen via Claude Code)
   ```bash
   claude -m qwen3-coder
   > /implement 42
   ```

3. **Review** (toi)
   - `gh pr view --web`
   - Vérifier les changements
   - Merger ou demander des corrections

4. **Itérer**
   - Si la PR a des problèmes : créer une issue fix
   - Pas de ping-pong infini avec le modèle

---

## Ressources communauté

- [Unsloth — Claude Code + Local LLMs](https://unsloth.ai/docs/basics/claude-code)
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
- [FlorianBruniaux/claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide)
- [abhishekray07/claude-md-templates](https://github.com/abhishekray07/claude-md-templates)
- [Ralph Wiggum Loop technique](https://antran.app/blogs/2026/ralph_wiggum/)
- [Addy Osmani — LLM Coding Workflow 2026](https://addyosmani.com/blog/ai-coding-workflow/)
