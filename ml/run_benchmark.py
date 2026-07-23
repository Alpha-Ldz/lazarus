"""Benchmark orchestrator — YOLOv11s vs RT-DETR-l on DsPCBSD+.

Usage:
    uv run python ml/run_benchmark.py
    uv run python ml/run_benchmark.py --models yolo rtdetr
    uv run python ml/run_benchmark.py --models yolo --skip-onnx
    uv run python ml/run_benchmark.py --warmup 50 --iters 200

Produces:
    ml/runs/benchmark_results.json
    docs/BENCHMARK.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Ensure project root is in sys.path so apps.api.detectors is importable
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Ensure ml/ is in sys.path so `from benchmark.xxx import ...` works
_ML_DIR = Path(__file__).parent
sys.path.insert(0, str(_ML_DIR))

from benchmark.latency import export_onnx_and_profile, load_sample_image, profile_latency  # noqa: E402
from benchmark.metrics import eval_detection  # noqa: E402
from benchmark.report import build_model_entry, build_results_json, generate_markdown, save_json  # noqa: E402

MANIFEST_PATH = _ML_DIR / "runs" / "training_manifest.json"
OUTPUT_JSON = _ML_DIR / "runs" / "benchmark_results.json"
OUTPUT_MD = _PROJECT_ROOT / "docs" / "BENCHMARK.md"

DATASET_YAML = _ML_DIR / "datasets" / "dspcbsd" / "dspcbsd.yaml"
DATASET_ROOT = _ML_DIR / "datasets" / "dspcbsd"

CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.5
IMGSZ = 640


def _print_gpu_state() -> None:
    """Print nvidia-smi state at benchmark start (for reproducibility notes)."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,clocks.gr,clocks.mem,power.draw",
             "--format=csv,noheader"],
            timeout=5,
        )
        print(f"[GPU state] {out.decode().strip()}")
    except Exception:
        print("[GPU state] nvidia-smi unavailable")


def benchmark_model(
    name: str,
    weights_path: Path,
    model_type: str,
    n_params: int,
    sample_image,  # PIL Image
    manifest_model: dict,
    warmup: int,
    n_iters: int,
    skip_onnx: bool,
) -> dict:
    """Run full benchmark for one model: metrics + latency + ONNX export."""
    print(f"\n{'='*60}")
    print(f"  Benchmarking: {name}")
    print(f"  Weights: {weights_path}")
    print(f"{'='*60}")

    # ── Detection metrics via Ultralytics val() ───────────────────────────────
    print("  [1/3] Running detection metrics (val)...")
    detection_metrics, split_used = eval_detection(
        weights_path=weights_path,
        data_yaml=DATASET_YAML,
        model_type=model_type,
        imgsz=IMGSZ,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
    )
    print(f"        mAP50={detection_metrics['map50']}  mAP50-95={detection_metrics['map50_95']}")
    print(f"        Split used: {split_used}")

    # ── Build Detector via production interface ───────────────────────────────
    print("  [2/3] Loading Detector for latency profiling...")
    if model_type == "yolo":
        from apps.api.detectors.yolo import YoloDetector

        detector = YoloDetector(weights_path)
    else:
        from apps.api.detectors.rtdetr import RtdetrDetector

        detector = RtdetrDetector(weights_path)

    # ── Latency profiling (pytorch backend) ──────────────────────────────────
    print(f"  [2/3] Latency profiling ({warmup} warmup + {n_iters} measured iters)...")
    latency = profile_latency(
        detector=detector,
        sample_image=sample_image,
        warmup=warmup,
        n_iters=n_iters,
        backend="pytorch",
    )
    print(
        f"        p50={latency['p50_ms']} ms  p95={latency['p95_ms']} ms  "
        f"p99={latency['p99_ms']} ms  throughput={latency['throughput_img_s']} img/s"
    )
    breakdown = latency.get("breakdown_ms", {})
    print(
        f"        breakdown: pre={breakdown.get('preprocess')} ms  "
        f"infer={breakdown.get('inference')} ms  "
        f"post={breakdown.get('postprocess')} ms"
    )

    # ── ONNX export + profiling ───────────────────────────────────────────────
    latency_exported: list[dict] = []
    if not skip_onnx:
        print("  [3/3] ONNX export + profiling...")
        latency_exported = export_onnx_and_profile(
            detector=detector,
            sample_image=sample_image,
            model_type=model_type,
            imgsz=IMGSZ,
            warmup=warmup,
            n_iters=n_iters,
        )
        for exp in latency_exported:
            if "error" in exp:
                print(f"        ONNX ({exp['backend']}): {exp['error']}")
            else:
                print(f"        ONNX ({exp['backend']}): p50={exp.get('p50_ms')} ms")
    else:
        print("  [3/3] ONNX skipped (--skip-onnx)")
        latency_exported = [{"backend": "onnxruntime_gpu", "error": "skipped via --skip-onnx"}]

    return build_model_entry(
        manifest_model=manifest_model,
        name=name,
        weights_path=weights_path,
        n_params=n_params,
        detection_metrics=detection_metrics,
        latency=latency,
        latency_exported=latency_exported,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Lazarus benchmark: YOLOv11s vs RT-DETR-l")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["yolo", "rtdetr"],
        default=["yolo", "rtdetr"],
        help="Which models to benchmark (default: both)",
    )
    parser.add_argument("--warmup", type=int, default=50, help="Warmup iterations (default: 50)")
    parser.add_argument("--iters", type=int, default=200, help="Measured iterations (default: 200)")
    parser.add_argument("--skip-onnx", action="store_true", help="Skip ONNX export and profiling")
    args = parser.parse_args()

    # Load training manifest
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Training manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    manifest = json.loads(MANIFEST_PATH.read_text())

    print("\nLazarus Benchmark Harness")
    print(f"Models to benchmark: {args.models}")
    print(f"Protocol: warmup={args.warmup}, iters={args.iters}, conf={CONF_THRESHOLD}, iou={IOU_THRESHOLD}")
    _print_gpu_state()

    # Load one sample image for latency timing
    sample_image = load_sample_image(DATASET_ROOT, imgsz=IMGSZ)
    print(f"\nSample image for latency: {DATASET_ROOT}/images/val/*.jpg (resized to {IMGSZ}x{IMGSZ})")

    # Model configurations
    model_configs = {
        "yolo": {
            "name": "yolo11s-dspcbsd",
            "weights_path": Path(manifest["models"]["yolo"]["best_pt_path"]),
            "model_type": "yolo",
            "n_params": manifest["models"]["yolo"]["n_params"],
            "manifest_model": manifest["models"]["yolo"],
        },
        "rtdetr": {
            "name": "rtdetr-l-dspcbsd",
            "weights_path": Path(manifest["models"]["rtdetr"]["best_pt_path"]),
            "model_type": "rtdetr",
            "n_params": manifest["models"]["rtdetr"]["n_params"],
            "manifest_model": manifest["models"]["rtdetr"],
        },
    }

    model_entries: list[dict] = []
    eval_split_used = "val"

    for model_key in args.models:
        cfg = model_configs[model_key]
        if not cfg["weights_path"].exists():
            print(f"WARNING: weights not found: {cfg['weights_path']}", file=sys.stderr)
            continue

        entry = benchmark_model(
            name=cfg["name"],
            weights_path=cfg["weights_path"],
            model_type=cfg["model_type"],
            n_params=cfg["n_params"],
            sample_image=sample_image,
            manifest_model=cfg["manifest_model"],
            warmup=args.warmup,
            n_iters=args.iters,
            skip_onnx=args.skip_onnx,
        )
        model_entries.append(entry)

    if not model_entries:
        print("ERROR: No models were benchmarked. Check weights paths.", file=sys.stderr)
        sys.exit(1)

    # Build and save JSON results
    results = build_results_json(
        manifest=manifest,
        model_entries=model_entries,
        eval_split=eval_split_used,
        conf_threshold=CONF_THRESHOLD,
        iou_threshold=IOU_THRESHOLD,
        imgsz=IMGSZ,
    )
    save_json(results, OUTPUT_JSON)
    print(f"\n[JSON] Saved: {OUTPUT_JSON}")

    # Generate and save Markdown report
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    md_content = generate_markdown(results, manifest)
    OUTPUT_MD.write_text(md_content)
    print(f"[MD]   Saved: {OUTPUT_MD}")

    print("\nDone.")


if __name__ == "__main__":
    main()
