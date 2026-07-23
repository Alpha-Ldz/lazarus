"""Detection metrics via Ultralytics val(): mAP global + per-class."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 9 DsPCBSD+ classes in canonical order (matching dataset yaml index 0-8)
CLASSES: list[str] = [
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

# Instance counts per class in the val split (no test split in dspcbsd.yaml).
# Verified by counting labels/val/*.txt annotation files.
CLASS_SUPPORT_VAL: dict[str, int] = {
    "short": 169,
    "spur": 929,
    "spurious_copper": 285,
    "open": 338,
    "mousebite": 546,
    "hole_breakout": 608,
    "conductor_scratch": 448,
    "conductor_foreign_object": 423,
    "base_material_foreign_object": 346,
}


def eval_detection(
    weights_path: str | Path,
    data_yaml: str | Path,
    model_type: str = "yolo",
    imgsz: int = 640,
    conf: float = 0.25,
    iou: float = 0.5,
) -> tuple[dict[str, Any], str]:
    """Run Ultralytics val() and return (metrics_dict, eval_split_used).

    Attempts the 'test' split first; falls back to 'val' if test is absent.
    Returns the split actually used so the caller can record it in the report.
    """
    if model_type == "yolo":
        from ultralytics import YOLO

        model = YOLO(str(weights_path))
    else:
        from ultralytics import RTDETR

        model = RTDETR(str(weights_path))

    # Attempt test split; dspcbsd.yaml has no test key so we fall back to val.
    split_used = "val"
    try:
        results = model.val(
            data=str(data_yaml),
            imgsz=imgsz,
            conf=conf,
            iou=iou,
            split="test",
            verbose=False,
        )
        split_used = "test"
    except Exception:
        results = model.val(
            data=str(data_yaml),
            imgsz=imgsz,
            conf=conf,
            iou=iou,
            split="val",
            verbose=False,
        )

    box = results.box

    per_class: list[dict[str, Any]] = []
    for i, cls_name in enumerate(CLASSES):
        per_class.append(
            {
                "class": cls_name,
                "support": CLASS_SUPPORT_VAL.get(cls_name, 0),
                "precision": round(float(box.p[i]), 4) if i < len(box.p) else 0.0,
                "recall": round(float(box.r[i]), 4) if i < len(box.r) else 0.0,
                "map50": round(float(box.ap50[i]), 4) if i < len(box.ap50) else 0.0,
                "map50_95": round(float(box.ap[i]), 4) if i < len(box.ap) else 0.0,
            }
        )

    metrics: dict[str, Any] = {
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
        "per_class": per_class,
    }
    return metrics, split_used
