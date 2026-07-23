"""PatchcoreDetector — interface Detector sur un modèle Anomalib exporté."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .anomaly_bbox import anomaly_map_to_detections
from .base import DetectionResult


class PatchcoreDetector:
    """Détecteur PatchCore basé sur un modèle Anomalib (ONNX ou Torch).

    Respecte l'interface Detector : name, class_names, predict().
    La logique de dessin est déléguée à detectors/annotate.py via les Detection
    retournées — aucun rendu ici.
    """

    def __init__(self, model_path: str | Path, category: str = "pcb") -> None:
        from anomalib.deploy import OpenVINOInferencer, TorchInferencer

        model_path = Path(model_path)
        self.name: str = f"patchcore-visa-{category}"
        self._category = category
        self._threshold: float | None = None

        # Charge le modèle : ONNX → TorchInferencer, .pt → TorchInferencer
        suffix = model_path.suffix.lower()
        if suffix in (".pt", ".pth"):
            self._inferencer = TorchInferencer(path=model_path)
        elif suffix == ".onnx":
            # TorchInferencer accepte aussi l'ONNX via Anomalib
            try:
                self._inferencer = TorchInferencer(path=model_path)
            except Exception:
                self._inferencer = OpenVINOInferencer(path=model_path)
        else:
            self._inferencer = TorchInferencer(path=model_path)

        # Récupère le seuil adaptatif si disponible
        model = getattr(self._inferencer, "model", None)
        if model is not None:
            for attr in ("pixel_threshold", "image_threshold", "_pixel_threshold"):
                val = getattr(model, attr, None)
                if val is not None:
                    try:
                        self._threshold = float(val.value if hasattr(val, "value") else val)
                        break
                    except Exception:
                        pass

    @property
    def class_names(self) -> list[str]:
        return ["anomaly"]

    def predict(self, image: Image.Image) -> DetectionResult:
        orig_w, orig_h = image.size

        # Inférence Anomalib
        output = self._inferencer.predict(image=np.array(image.convert("RGB")))

        # Récupère la heatmap (anomaly_map) et le seuil
        anomaly_map: np.ndarray | None = None
        for attr in ("anomaly_map", "heat_map", "heatmap"):
            candidate = getattr(output, attr, None)
            if candidate is not None:
                anomaly_map = np.array(candidate, dtype=np.float32)
                # Squeeze extra dimensions
                while anomaly_map.ndim > 2:
                    anomaly_map = anomaly_map.squeeze(0)
                break

        if anomaly_map is None:
            return DetectionResult(detections=[])

        # Détermine le seuil
        threshold = self._threshold
        if threshold is None:
            # Fallback : percentile 99 (documenté)
            threshold = float(np.percentile(anomaly_map, 99))

        detections = anomaly_map_to_detections(
            anomaly_map=anomaly_map,
            threshold=threshold,
            orig_width=orig_w,
            orig_height=orig_h,
        )
        return DetectionResult(detections=detections)
