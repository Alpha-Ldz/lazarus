"""Factory — sélection du détecteur par variable d'environnement."""

import os
from pathlib import Path

from .base import Detector

_DEFAULT_MODEL_PATH = str(Path(__file__).parent.parent / "models" / "best.pt")


def build_detector() -> Detector:
    """
    Construit et retourne le détecteur configuré via les variables d'environnement.

    LAZARUS_DETECTOR : identifiant du détecteur (défaut: "yolo")
    LAZARUS_MODEL_PATH : chemin vers les poids (défaut: apps/api/models/best.pt)
    """
    detector_type = os.getenv("LAZARUS_DETECTOR", "yolo")
    model_path = os.getenv("LAZARUS_MODEL_PATH", _DEFAULT_MODEL_PATH)

    if detector_type == "yolo":
        from .yolo import YoloDetector

        return YoloDetector(model_path)

    raise ValueError(
        f"Détecteur inconnu: '{detector_type}'. "
        "Valeurs acceptées: 'yolo'. "
        "Ajoutez un fichier dans apps/api/detectors/ et une entrée ici pour en ajouter un."
    )
