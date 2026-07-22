"""Implémentation RT-DETR du détecteur — même interface que YoloDetector."""

from pathlib import Path

from .yolo import _DSPCBSD_CLASSES, _UltralyticsDetector


class RtdetrDetector(_UltralyticsDetector):
    """Détecteur basé sur Ultralytics RT-DETR."""

    def __init__(self, model_path: str | Path) -> None:
        from ultralytics import RTDETR

        super().__init__()
        self._model = RTDETR(str(model_path))
        self.name = f"rtdetr-{Path(model_path).stem}"
        self._init_class_names(_DSPCBSD_CLASSES)
