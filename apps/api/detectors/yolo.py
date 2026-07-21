"""Implémentation YOLO du détecteur — encapsule tout le spécifique Ultralytics."""

from pathlib import Path

from PIL import Image

from .base import Detection, DetectionResult

# Classes DsPCBSD+ (9 catégories de défauts PCB industriels)
# Ref: https://doi.org/10.1038/s41597-024-03656-8
_DSPCBSD_CLASSES = [
    "short",
    "spur",
    "spurious_copper",
    "open",
    "mousebite",
    "hole_breakout",
    "conductor_scratch",
    "conductor_foreign_object",
    "base_material_foreign_object",
]


class YoloDetector:
    """Détecteur basé sur Ultralytics YOLO."""

    def __init__(self, model_path: str | Path) -> None:
        from ultralytics import YOLO

        self._model = YOLO(str(model_path))
        self.name: str = f"yolo-{Path(model_path).stem}"
        # Récupère les noms de classes depuis le modèle si disponibles
        if hasattr(self._model, "names") and self._model.names:
            self._class_names: list[str] = [
                self._model.names[i] for i in sorted(self._model.names)
            ]
        else:
            self._class_names = _DSPCBSD_CLASSES

    @property
    def class_names(self) -> list[str]:
        return self._class_names

    def predict(self, image: Image.Image) -> DetectionResult:
        results = self._model(image, verbose=False)
        detections: list[Detection] = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                class_name = (
                    self._class_names[cls_id]
                    if cls_id < len(self._class_names)
                    else str(cls_id)
                )
                detections.append(
                    Detection(
                        class_id=cls_id,
                        class_name=class_name,
                        confidence=float(box.conf[0]),
                        bbox=box.xyxy[0].tolist(),
                    )
                )
        return DetectionResult(detections=detections)
