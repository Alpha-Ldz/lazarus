"""Interface commune pour tous les détecteurs."""

from typing import Annotated, Protocol, runtime_checkable

from PIL import Image
from pydantic import BaseModel, Field, field_validator


class Detection(BaseModel):
    """Une détection normalisée, indépendante du modèle sous-jacent."""

    class_id: int
    class_name: str  # str (pas un Enum figé) — un futur détecteur peut renvoyer "anomaly"
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    bbox: list[float]  # [x1, y1, x2, y2] en pixels

    @field_validator("bbox")
    @classmethod
    def bbox_must_have_four_elements(cls, v: list[float]) -> list[float]:
        if len(v) != 4:
            raise ValueError(f"bbox must have exactly 4 elements, got {len(v)}")
        return v


class DetectionResult(BaseModel):
    detections: list[Detection]


@runtime_checkable
class Detector(Protocol):
    """Interface que tout détecteur (YOLO, RT-DETR, PatchCore...) doit respecter."""

    name: str  # identifiant lisible, ex. "yolo11s-dspcbsd"

    @property
    def class_names(self) -> list[str]: ...

    def predict(self, image: Image.Image) -> DetectionResult: ...
