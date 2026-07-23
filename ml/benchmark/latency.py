"""Latency profiling via the Detector interface.

Protocol (imposed by issue #30):
- batch=1 for latency measurement (real serving scenario).
- torch.cuda.synchronize() before AND after each timed iteration.
- 50 warmup iterations excluded from measurements.
- >= 200 measured iterations.
- Reports p50 / p95 / p99 / mean / std.
- Decomposes preprocess / inference / postprocess via Ultralytics predictor.speed.
- Measurements done via the Detector interface (production path), not raw Ultralytics.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image


def _sync() -> None:
    """GPU synchronize if CUDA available, no-op otherwise."""
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def _get_speed_breakdown(detector: Any) -> dict[str, float] | None:
    """Extract per-stage timing from last Ultralytics result after a predict() call.

    Ultralytics stores per-stage timing on result.speed (Results object),
    accessible via model.predictor.results[0].speed after each call.
    """
    model_obj = getattr(detector, "_model", None)
    if model_obj is None:
        return None
    predictor = getattr(model_obj, "predictor", None)
    if predictor is None:
        return None
    results = getattr(predictor, "results", None)
    if not results:
        return None
    speed = getattr(results[0], "speed", None)
    if not speed:
        return None
    return {
        "preprocess": float(speed.get("preprocess", 0.0)),
        "inference": float(speed.get("inference", 0.0)),
        "postprocess": float(speed.get("postprocess", 0.0)),
    }


def profile_latency(
    detector: Any,
    sample_image: Image.Image,
    warmup: int = 50,
    n_iters: int = 200,
    backend: str = "pytorch",
) -> dict[str, Any]:
    """Profile detector.predict() latency with proper GPU synchronization.

    Args:
        detector: Any object implementing the Detector protocol (predict method).
        sample_image: PIL image used for timing (640x640 recommended).
        warmup: Number of warmup iterations excluded from measurements.
        n_iters: Number of measured iterations.
        backend: Label for the result dict (e.g. 'pytorch', 'onnxruntime_gpu').

    Returns:
        Dict with p50/p95/p99/mean/std in ms, breakdown, throughput, and metadata.
    """
    # Warmup — excluded from measurements
    for _ in range(warmup):
        detector.predict(sample_image)
    _sync()

    times_ms: list[float] = []
    pre_list: list[float] = []
    infer_list: list[float] = []
    post_list: list[float] = []

    for _ in range(n_iters):
        _sync()
        t0 = time.perf_counter()
        detector.predict(sample_image)
        _sync()
        t1 = time.perf_counter()
        times_ms.append((t1 - t0) * 1000.0)

        breakdown = _get_speed_breakdown(detector)
        if breakdown is not None:
            pre_list.append(breakdown["preprocess"])
            infer_list.append(breakdown["inference"])
            post_list.append(breakdown["postprocess"])

    arr = np.array(times_ms)

    breakdown_means: dict[str, float]
    if pre_list:
        breakdown_means = {
            "preprocess": round(float(np.mean(pre_list)), 3),
            "inference": round(float(np.mean(infer_list)), 3),
            "postprocess": round(float(np.mean(post_list)), 3),
        }
    else:
        breakdown_means = {"preprocess": 0.0, "inference": 0.0, "postprocess": 0.0}

    return {
        "backend": backend,
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "p99_ms": round(float(np.percentile(arr, 99)), 3),
        "mean_ms": round(float(np.mean(arr)), 3),
        "std_ms": round(float(np.std(arr)), 3),
        "breakdown_ms": breakdown_means,
        "throughput_img_s": round(1000.0 / float(np.mean(arr)), 1),
        "batch_size": 1,
        "warmup_iters": warmup,
        "measured_iters": n_iters,
    }


def export_onnx_and_profile(
    detector: Any,
    sample_image: Image.Image,
    model_type: str = "yolo",
    imgsz: int = 640,
    warmup: int = 50,
    n_iters: int = 200,
) -> list[dict[str, Any]]:
    """Export detector weights to ONNX and profile the exported model.

    Returns a list of latency result dicts (one per backend tried).
    Returns [{"backend": "onnxruntime_gpu", "error": "..."}] if unavailable.
    """
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return [{"backend": "onnxruntime_gpu", "error": "onnxruntime not installed"}]

    model_obj = getattr(detector, "_model", None)
    if model_obj is None:
        return [{"backend": "onnxruntime_gpu", "error": "detector has no _model attribute"}]

    try:
        onnx_path_str = model_obj.export(format="onnx", imgsz=imgsz, simplify=True)
        onnx_path = Path(onnx_path_str)
    except Exception as exc:
        return [{"backend": "onnxruntime_gpu", "error": f"ONNX export failed: {exc}"}]

    try:
        # Load exported ONNX via the same Detector interface (Ultralytics supports .onnx)
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        if model_type == "yolo":
            from apps.api.detectors.yolo import YoloDetector

            onnx_detector: Any = YoloDetector(onnx_path)
        else:
            from apps.api.detectors.rtdetr import RtdetrDetector

            onnx_detector = RtdetrDetector(onnx_path)
    except Exception as exc:
        return [{"backend": "onnxruntime_gpu", "error": f"ONNX detector init failed: {exc}"}]

    try:
        result = profile_latency(onnx_detector, sample_image, warmup=warmup, n_iters=n_iters, backend="onnxruntime_gpu")
        return [
            {
                "backend": "onnxruntime_gpu",
                "p50_ms": result["p50_ms"],
                "mean_ms": result["mean_ms"],
                "throughput_img_s": result["throughput_img_s"],
            }
        ]
    except Exception as exc:
        return [{"backend": "onnxruntime_gpu", "error": f"ONNX profiling failed: {exc}"}]


def load_sample_image(dataset_path: Path, imgsz: int = 640) -> Image.Image:
    """Load a single sample image from the val split for timing."""
    val_images = list((dataset_path / "images" / "val").glob("*.jpg"))
    if not val_images:
        val_images = list((dataset_path / "images" / "val").glob("*.png"))
    if not val_images:
        raise FileNotFoundError(f"No images found in {dataset_path}/images/val/")
    img = Image.open(val_images[0]).convert("RGB")
    img = img.resize((imgsz, imgsz), Image.BILINEAR)
    return img
