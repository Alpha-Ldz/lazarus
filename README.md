# Lazarus

Système de détection et diagnostic de défauts sur circuits imprimés (PCB) utilisant YOLOv11 et Claude AI.

## Architecture

Ce projet est organisé en monorepo avec trois composants principaux :

```
lazarus/
├── apps/
│   ├── api/          # Backend FastAPI
│   │   ├── routers/  # Endpoints API (analyze, diagnose)
│   │   └── models/   # Modèle YOLO (symlink)
│   └── web/          # Frontend React + TypeScript
│       └── src/      # Composants React
├── ml/               # Pipeline ML
│   ├── data/         # Dataset DsPCBSD+
│   ├── datasets/     # Datasets YOLO formatés
│   ├── runs/         # Résultats d'entraînement
│   ├── notebooks/    # Notebooks Jupyter
│   ├── train.py      # Script d'entraînement YOLOv11
│   └── test.py       # Script de test
└── packages/         # Packages partagés (si nécessaire)
```

### Stack Technique

**Backend (apps/api/)**
- FastAPI 0.115+ avec Uvicorn
- Python 3.13+
- YOLOv11 (Ultralytics) pour la détection de défauts
- Anthropic Claude API pour le diagnostic intelligent
- Pillow pour le traitement d'images

**Frontend (apps/web/)**
- React 19 avec TypeScript
- Vite pour le build et le dev server
- TailwindCSS 4 pour le styling
- Konva/React-Konva pour l'annotation d'images
- jsPDF pour l'export de rapports
- React Dropzone pour l'upload de fichiers

**ML Pipeline (ml/)**
- YOLOv11 (Ultralytics)
- PyTorch 2.11+
- OpenCV pour le traitement d'images
- Dataset DsPCBSD+ (10 259 images réelles, 9 classes, CC BY 4.0) — [DOI: 10.1038/s41597-024-03656-8](https://doi.org/10.1038/s41597-024-03656-8)
  - Classes : short, spur, spurious_copper, open, mousebite, hole_breakout, conductor_scratch, conductor_foreign_object, base_material_foreign_object

### Gestion des dépendances

- **Python** : `uv` (modern Python package manager)
- **Node.js** : `npm`

## Démarrage rapide

### 1. Backend FastAPI

```bash
# Installer les dépendances Python
uv sync

# Créer le symlink vers le modèle YOLO entraîné
ln -s ../../../ml/runs/detect/dspcbsd_yolo11/weights/best.pt apps/api/models/best.pt

# Démarrer le serveur API
uv run uvicorn apps.api.main:app --reload
```

L'API sera disponible sur `http://localhost:8000`

### 2. Frontend React

```bash
# Aller dans le dossier web
cd apps/web

# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm run dev
```

Le frontend sera disponible sur `http://localhost:5173`

### 3. Entraînement ML (optionnel)

```bash
# Installer les dépendances ML
uv sync --extra ml

# Télécharger le dataset DsPCBSD+
uv run python ml/download_dspcbsd.py

# Lancer l'entraînement YOLOv11
uv run python ml/train_dspcbsd.py
```

### Modèles supportés (à venir)

- YOLOv11 (détection en temps réel)
- RT-DETR (détection haute précision)
- PatchCore (détection d'anomalies sans supervision)

## Endpoints API

### Analyse d'image
- **POST** `/api/analyze` - Upload d'une image PCB pour détection YOLO
  - Input: Fichier image (multipart/form-data)
  - Output: Liste des défauts détectés avec bounding boxes et scores

### Diagnostic IA
- **POST** `/api/diagnose` - Diagnostic détaillé par Claude AI
  - Input: Liste de défauts détectés
  - Output: Analyse textuelle et recommandations

### Health Check
- **GET** `/health` - Vérification de l'état de l'API
  - Output: Status et présence du modèle YOLO

### Documentation interactive
- **GET** `/docs` - Interface Swagger UI
- **GET** `/redoc` - Documentation ReDoc

## Workflow

1. **Upload** : L'utilisateur upload une image PCB via le frontend
2. **Détection** : L'API utilise YOLOv11 pour détecter les défauts
3. **Annotation** : Le frontend affiche les détections avec bounding boxes
4. **Diagnostic** : Claude AI analyse les défauts et génère un rapport
5. **Export** : Génération d'un rapport PDF avec les résultats
