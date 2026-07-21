"""
FastAPI backend pour Lazarus - Détection de défauts PCB.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analyze, diagnose

# Chemin vers le modèle YOLO
MODEL_PATH = Path(__file__).parent / "models" / "best.pt"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    from .detectors.factory import build_detector

    if MODEL_PATH.exists():
        try:
            app.state.detector = build_detector()
            print(f"✅ Détecteur chargé: {app.state.detector.name}")
        except Exception as exc:
            app.state.detector = None
            print(f"⚠️ Échec du chargement du détecteur: {exc}")
    else:
        app.state.detector = None
        print(f"⚠️ Modèle non trouvé: {MODEL_PATH}")
        print("   Créez un symlink ou copiez le modèle depuis ml/runs/detect/dspcbsd_yolo11/weights/best.pt")

    yield

    # Shutdown: cleanup si nécessaire
    app.state.detector = None


app = FastAPI(
    title="Lazarus API",
    description="API de détection de défauts PCB avec YOLOv11",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuration CORS pour le frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers
app.include_router(analyze.router, prefix="/api/analyze", tags=["analyze"])
app.include_router(diagnose.router, prefix="/api/diagnose", tags=["diagnose"])


@app.get("/")
async def root():
    """Endpoint racine."""
    return {
        "name": "Lazarus API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    detector = app.state.detector
    return {
        "status": "healthy",
        "detector_loaded": detector is not None,
        "detector_name": detector.name if detector is not None else None,
    }
