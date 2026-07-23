"""Generate benchmark_results.json and BENCHMARK.md from collected data."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark.metrics import CLASSES


def _gpu_info() -> str:
    """Return GPU name from nvidia-smi, or 'N/A'."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            timeout=5,
        )
        return out.decode().strip().splitlines()[0]
    except Exception:
        return "N/A"


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], timeout=5)
        return out.decode().strip()
    except Exception:
        return "N/A"


def _torch_version() -> str:
    try:
        import torch

        return torch.__version__
    except ImportError:
        return "N/A"


def _cuda_version() -> str:
    try:
        import torch

        return torch.version.cuda or "N/A"
    except ImportError:
        return "N/A"


def _ultralytics_version() -> str:
    try:
        import ultralytics

        return ultralytics.__version__
    except ImportError:
        return "N/A"


def _model_size_mb(weights_path: str | Path) -> float:
    p = Path(weights_path)
    if p.exists():
        return round(p.stat().st_size / (1024 * 1024), 1)
    return 0.0


def build_results_json(
    manifest: dict[str, Any],
    model_entries: list[dict[str, Any]],
    eval_split: str,
    conf_threshold: float,
    iou_threshold: float,
    imgsz: int,
) -> dict[str, Any]:
    """Assemble the full benchmark_results.json structure."""
    return {
        "meta": {
            "date": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "gpu": _gpu_info(),
            "torch": _torch_version(),
            "ultralytics": _ultralytics_version(),
            "cuda": _cuda_version(),
            "eval_split": eval_split,
            "imgsz": imgsz,
            "conf_threshold": conf_threshold,
            "iou_threshold": iou_threshold,
            "training_manifest": "ml/runs/training_manifest.json",
        },
        "models": model_entries,
    }


def build_model_entry(
    manifest_model: dict[str, Any],
    name: str,
    weights_path: str | Path,
    n_params: int,
    detection_metrics: dict[str, Any],
    latency: dict[str, Any],
    latency_exported: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a single model entry conforming to the JSON schema."""
    return {
        "name": name,
        "paradigm": "supervised_detection",
        "weights": str(weights_path),
        "params_m": round(n_params / 1_000_000, 1),
        "size_mb": _model_size_mb(weights_path),
        "detection_metrics": detection_metrics,
        "anomaly_metrics": None,  # Reserved for EPIC C (PatchCore)
        "latency": latency,
        "latency_exported": latency_exported,
    }


def save_json(results: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))


def _fmt(v: float, decimals: int = 3) -> str:
    return f"{v:.{decimals}f}"


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def generate_markdown(results: dict[str, Any], manifest: dict[str, Any]) -> str:
    meta = results["meta"]
    models = results["models"]

    lines: list[str] = []

    lines += [
        "# Benchmark Report — YOLOv11s vs RT-DETR-l on DsPCBSD+",
        "",
        f"Generated: {meta['date']}  ",
        f"Git commit: `{meta['git_commit'][:12]}`  ",
        f"GPU: {meta['gpu']}",
        "",
    ]

    # ── 1. Main comparison table ──────────────────────────────────────────────
    lines += [
        "## 1. Main Comparison Table",
        "",
    ]

    header = (
        "| Model | Paradigm | mAP50 | mAP50-95 | Precision | Recall"
        " | Latency p50 (ms) | Latency p95 (ms) | Throughput (img/s)"
        " | Params (M) | VRAM Train (GB) | Train Duration (h) |"
    )
    sep = (
        "|-------|----------|-------|----------|-----------|--------"
        "|-----------------|-----------------|-------------------"
        "|------------|-----------------|-------------------|"
    )
    lines += [header, sep]

    for m in models:
        dm = m["detection_metrics"]
        lat = m["latency"]
        ti_key = "yolo" if "yolo" in m["name"] else "rtdetr"
        ti = manifest["models"].get(ti_key, {})
        vram = ti.get("peak_vram_gb", "N/A")
        dur_s = ti.get("duration_seconds", 0)
        dur_h = f"{dur_s / 3600:.1f}" if dur_s else "N/A"
        row = (
            f"| **{m['name']}** | {m['paradigm']} "
            f"| {_fmt(dm['map50'])} | {_fmt(dm['map50_95'])} "
            f"| {_fmt(dm['precision'])} | {_fmt(dm['recall'])} "
            f"| {lat['p50_ms']} | {lat['p95_ms']} "
            f"| {lat['throughput_img_s']} "
            f"| {m['params_m']} | {vram} | {dur_h} |"
        )
        lines.append(row)

    lines.append("")

    # ── 2. Per-class table ────────────────────────────────────────────────────
    lines += [
        "## 2. Per-Class Metrics",
        "",
        "All classes from DsPCBSD+ (9 categories). Support = instances in the evaluation split.",
        "",
    ]

    cls_header = "| Class | Support |"
    cls_sep = "|-------|---------|"
    for m in models:
        cls_header += f" {m['name']} P | {m['name']} R | {m['name']} mAP50 | {m['name']} mAP50-95 |"
        cls_sep += "---|---|---|---|"
    lines += [cls_header, cls_sep]

    # Align per-class data by class name
    per_class_by_model: dict[str, dict[str, dict[str, Any]]] = {}
    for m in models:
        per_class_by_model[m["name"]] = {pc["class"]: pc for pc in m["detection_metrics"]["per_class"]}

    for cls_name in CLASSES:
        support = next(
            (pc["support"] for m in models for pc in m["detection_metrics"]["per_class"] if pc["class"] == cls_name),
            "?",
        )
        row = f"| {cls_name} | {support} |"
        for m in models:
            pc = per_class_by_model[m["name"]].get(cls_name, {})
            row += (
                f" {_fmt(pc.get('precision', 0))} "
                f"| {_fmt(pc.get('recall', 0))} "
                f"| {_fmt(pc.get('map50', 0))} "
                f"| {_fmt(pc.get('map50_95', 0))} |"
            )
        lines.append(row)

    lines.append("")

    # ── 3. Latency breakdown ──────────────────────────────────────────────────
    lines += [
        "## 3. Latency Breakdown (preprocess / inference / postprocess)",
        "",
        "Measured via the `Detector` interface (production path). batch=1.",
        "",
        "| Model | Backend | Pre (ms) | Infer (ms) | Post (ms) | p50 (ms) | p95 (ms) | p99 (ms) | std (ms) |",
        "|-------|---------|---------|-----------|----------|---------|---------|---------|---------|",
    ]
    for m in models:
        lat = m["latency"]
        bd = lat.get("breakdown_ms", {})
        lines.append(
            f"| {m['name']} | {lat['backend']} "
            f"| {bd.get('preprocess', 0)} "
            f"| {bd.get('inference', 0)} "
            f"| {bd.get('postprocess', 0)} "
            f"| {lat['p50_ms']} | {lat['p95_ms']} | {lat['p99_ms']} | {lat['std_ms']} |"
        )
    lines.append("")

    # ONNX exported backends
    for m in models:
        for exp in m.get("latency_exported", []):
            if "error" in exp:
                lines.append(f"> **ONNX ({m['name']})**: {exp['error']}")
            else:
                lines.append(
                    f"> **ONNX ({m['name']})**: p50={exp.get('p50_ms')} ms, mean={exp.get('mean_ms')} ms"
                )
    lines.append("")

    # ── 4. Protocol ───────────────────────────────────────────────────────────
    split_note = (
        "**Note:** no `test` split in dspcbsd.yaml — using `val`. "
        "Val was used for early-stopping, so metrics are slightly optimistic."
        if meta["eval_split"] == "val"
        else "dedicated test split"
    )
    warmup_iters = models[0]["latency"]["warmup_iters"] if models else 50
    measured_iters = models[0]["latency"]["measured_iters"] if models else 200

    lines += [
        "## 4. Measurement Protocol",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Evaluation split | `{meta['eval_split']}` ({split_note}) |",
        f"| Image size | {meta['imgsz']}x{meta['imgsz']} |",
        f"| Confidence threshold | {meta['conf_threshold']} |",
        f"| IoU threshold | {meta['iou_threshold']} |",
        "| Latency batch size | 1 (real serving scenario) |",
        f"| Warmup iterations | {warmup_iters} (excluded from measurements) |",
        f"| Measured iterations | {measured_iters} |",
        "| GPU synchronization | `torch.cuda.synchronize()` before AND after each iteration |",
        "| Latency measured via | `Detector.predict()` interface (production path) |",
        "| Breakdown source | `model.predictor.speed` (Ultralytics per-stage timing) |",
        "| Models measured | sequentially (never in parallel) |",
        f"| GPU at measurement | {meta['gpu']} |",
        f"| PyTorch | {meta['torch']} |",
        f"| Ultralytics | {meta['ultralytics']} |",
        f"| CUDA | {meta['cuda']} |",
        "",
        "> **Reproducibility**: detection metrics are deterministic given the same split, thresholds, and weights.",
        "> Latency measurements have natural variance (std reported); two runs should agree within ~2x std.",
        "",
    ]

    # ── 5. Limitations & honesty ──────────────────────────────────────────────
    lines += [
        "## 5. Limitations & Honesty",
        "",
        "This section is required for result credibility.",
        "",
        "- **Evaluation split**: The `val` split was used for early-stopping (patience=50) during training.",
        "  Metrics reported here are therefore slightly optimistic for both models.",
        "  A held-out `test` split does not exist in the current DsPCBSD+ download.",
        "",
        "- **Identical hyperparameters**: Ultralytics default hyperparameters are tuned for YOLO-family",
        "  architectures. Applying them unchanged to RT-DETR is the fairest equal-budget comparison,",
        "  but it mechanically advantages YOLO.",
        "",
        "- **Training schedule**: 150 epochs with patience=50 is a comfortable budget for a CNN like",
        "  YOLOv11s, and more constrained for a transformer. RT-DETR-l reached its best checkpoint at",
        "  epoch 52 then plateaued — we cannot distinguish 'true ceiling on this dataset' from 'schedule",
        "  not adapted to transformer convergence dynamics' with the available data.",
        "",
        "- **Batch size**: batch=8 was used for both models. This intentionally limits YOLO (which can",
        "  benefit from larger batches) but is also small for a transformer.",
        "",
        "- **Not explored** (out of budget): partial backbone freeze for HGNet, extended schedule,",
        "  model-specific learning rate tuning, TensorRT export.",
        "",
        "- **GPU clock state**: clocks were not explicitly locked during latency measurement. Reported",
        "  std captures this variance.",
        "",
        "**Conclusion to state precisely**: *Under equal training budget and non-specialized hyperparameters,",
        "RT-DETR-l under-performs YOLOv11s on DsPCBSD+. This is not a verdict on the architecture in",
        "absolute terms.*",
        "",
    ]

    # ── 6. Engineering decision ───────────────────────────────────────────────
    yolo_map = next((m["detection_metrics"]["map50"] for m in models if "yolo" in m["name"]), None)
    rtdetr_map = next((m["detection_metrics"]["map50"] for m in models if "rtdetr" in m["name"]), None)
    yolo_p50 = next((m["latency"]["p50_ms"] for m in models if "yolo" in m["name"]), None)
    rtdetr_p50 = next((m["latency"]["p50_ms"] for m in models if "rtdetr" in m["name"]), None)
    yolo_params = next((m["params_m"] for m in models if "yolo" in m["name"]), None)
    rtdetr_params = next((m["params_m"] for m in models if "rtdetr" in m["name"]), None)

    delta = round((yolo_map or 0) - (rtdetr_map or 0), 3)
    lines += [
        "## 6. Engineering Decision",
        "",
        "**YOLOv11s goes to production.**",
        "",
        f"YOLOv11s achieves mAP50={yolo_map} vs RT-DETR-l's {rtdetr_map} (+{delta})",
        f"at {yolo_p50} ms p50 latency vs {rtdetr_p50} ms, {yolo_params}M params vs {rtdetr_params}M.",
        "Under equal training budget and shared hyperparameters, YOLOv11s delivers better accuracy,",
        "lower latency, and 3.5x fewer parameters — an unambiguous cost/benefit advantage for a",
        "PCB inspection API where real-time throughput and deployment footprint matter.",
        "",
    ]

    return "\n".join(lines)
