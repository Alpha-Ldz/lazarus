# Étude de cas — Lazarus : station de détection de défauts PCB

## Problème

La détection manuelle de défauts sur cartes électroniques (PCB) est lente, sujette à la fatigue et non reproductible. Un technicien expérimenté inspecte environ 40 cartes par heure ; une ligne à fort volume peut exiger une cadence dix fois supérieure. L'objectif était de construire un système capable de détecter automatiquement les défauts, de les classer et de générer une fiche de réparation structurée — le tout en moins de deux secondes par carte.

## Approche

Deux paradigmes ont été mis en compétition sur le même jeu de données :

**Détection supervisée** (YOLOv11s et RT-DETR-l sur DsPCBSD+) — entraînement sur 9 classes de défauts annotées, évaluation standard avec métriques mAP. Ce paradigme suppose un jeu de données labellisé, mais retourne des boîtes englobantes structurées exploitables directement par un LLM.

**Détection d'anomalies non supervisée** (PatchCore sur VisA PCB) — aucune annotation de défaut requise ; le modèle apprend la distribution des cartes saines et détecte les écarts. Ce paradigme est applicable à n'importe quel type de PCB sans coût d'annotation, mais ne distingue pas les classes de défauts.

Une interface commune (`Detector`) permet de permuter les modèles sans modifier le routeur applicatif.

## Protocole d'évaluation

Pour garantir l'équité de la comparaison supervisée :

- Même split de validation pour les deux modèles (DsPCBSD+ val, non utilisé pendant l'entraînement sauf pour l'arrêt anticipé).
- Hyperparamètres Ultralytics identiques (budget égal, aucune optimisation spécifique à un modèle).
- Budget d'entraînement identique : 150 époques, patience=50.
- Mesure de latence : batch=1, 200 itérations, 50 de chauffe, synchronisation GPU avant et après chaque mesure.
- Modèles mesurés séquentiellement (jamais en parallèle).

## Résultats

| Modèle | mAP@50 | mAP@50-95 | Latence p50 | Params |
|--------|--------|-----------|-------------|--------|
| YOLOv11s | **0.849** | **0.550** | **33 ms** | 9.5 M |
| RT-DETR-l | 0.818 | 0.522 | 133 ms | 33.0 M |

RT-DETR-l a atteint son meilleur point à l'époque 52 puis a stagné. YOLOv11s converge plus régulièrement avec le budget disponible.

## Décision d'ingénieur

**YOLOv11s part en production.** L'écart de +3,1 pp mAP@50, associé à une latence 4 fois inférieure et 3,5 fois moins de paramètres, constitue un avantage coût/bénéfice non ambigu pour une API d'inspection en temps réel.

**Le challenger a perdu — et c'est un résultat valide.** Les résultats de RT-DETR-l n'ont pas été masqués : ils sont documentés intégralement dans `docs/BENCHMARK.md` avec les nuances méthodologiques (hyperparamètres partagés, schedule peut-être inadapté aux transformers). Retirer un challenger parce qu'il perd serait une mauvaise pratique MLOps.

## Limites reconnues

- Le split `val` a servi à l'arrêt anticipé : les métriques sont légèrement optimistes.
- Les hyperparamètres par défaut d'Ultralytics sont calibrés pour les architectures YOLO ; RT-DETR pourrait s'améliorer avec un réglage spécifique.
- PatchCore a tourné en dry-run : aucune métrique réelle n'est disponible pour ce paradigme.
- Pas de TensorRT, pas de backbone freeze, pas de LR spécifique par architecture — hors budget.
