"""Interface commune pour tous les détecteurs."""

from typing import Protocol, runtime_checkable

from PIL import Image
from pydantic import BaseModel


class Detection(BaseModel):
    """Une détection normalisée, indépendante du modèle sous-jacent."""

    class_id: int
    class_name: str  # str (pas un Enum figé) — un futur détecteur peut renvoyer "anomaly"
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2] en pixels


class DetectionResult(BaseModel):
    detections: list[Detection]


@runtime_checkable
class Detector(Protocol):
    """Interface que tout détecteur (YOLO, RT-DETR, PatchCore...) doit respecter."""

    name: str  # identifiant lisible, ex. "yolo11s-dspcbsd"

    @property
    def class_names(self) -> list[str]: ...

    def predict(self, image: Image.Image) -> DetectionResult: ...
