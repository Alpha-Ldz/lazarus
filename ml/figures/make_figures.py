"""
Generate all README figures from models and JSON results.
Usage: uv run python ml/figures/make_figures.py
Output: docs/assets/*.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_JSON = ROOT / "ml/runs/benchmark_results.json"
ANOMALY_JSON = ROOT / "ml/runs/anomaly_results.json"
ASSETS_DIR = ROOT / "docs/assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Colour palette from apps/web/src/types/index.ts
CLASS_LABELS: dict[str, str] = {
    "short": "Short",
    "spur": "Spur",
    "spurious_copper": "Spurious Copper",
    "open": "Open Circuit",
    "mousebite": "Mousebite",
    "hole_breakout": "Hole Breakout",
    "conductor_scratch": "Conductor Scratch",
    "conductor_foreign_object": "Cond. Foreign Object",
    "base_material_foreign_object": "Base Mat. Foreign Object",
}

DPI = 150


def load_benchmark() -> dict:
    with open(BENCHMARK_JSON) as f:
        return json.load(f)


# ─── F3: Latency bars ────────────────────────────────────────────────────────

def make_latency(bm: dict) -> None:
    models = bm["models"]
    names = ["YOLOv11s", "RT-DETR-l"]
    pre = [m["latency"]["breakdown_ms"]["preprocess"] for m in models]
    inf = [m["latency"]["breakdown_ms"]["inference"] for m in models]
    post = [m["latency"]["breakdown_ms"]["postprocess"] for m in models]

    fig, ax = plt.subplots(figsize=(7, 4), dpi=DPI)
    x = np.arange(len(names))
    width = 0.5

    ax.bar(x, pre, width, label="Preprocess", color="#14b8a6")
    ax.bar(x, inf, width, bottom=pre, label="Inference", color="#3b82f6")
    bottoms = [a + b for a, b in zip(pre, inf)]
    ax.bar(x, post, width, bottom=bottoms, label="Postprocess", color="#f97316")

    for i, (model, total) in enumerate(zip(models, [p + n + o for p, n, o in zip(pre, inf, post)])):
        p50 = model["latency"]["p50_ms"]
        ax.text(i, total + 1.5, f"p50={p50:.1f}ms", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Annotate RT-DETR NMS-free postprocessing
    rt_post_bottom = pre[1] + inf[1]
    ax.annotate(
        "NMS-free\n(lighter post)",
        xy=(1, rt_post_bottom + post[1] / 2),
        xytext=(1.38, 80),
        fontsize=8,
        color="#6b7280",
        arrowprops=dict(arrowstyle="->", color="#9ca3af", lw=0.8),
    )

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Latency (ms) — PyTorch, batch=1, RTX 5090")
    ax.set_title("Inference latency breakdown (p50)")
    ax.legend(loc="upper left")
    ax.set_ylim(0, 160)
    fig.tight_layout()
    out = ASSETS_DIR / "latency.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"  + {out.name}")


# ─── F4: Per-class mAP50 bars ────────────────────────────────────────────────

def make_per_class(bm: dict) -> None:
    yolo_model = bm["models"][0]
    rtdetr_model = bm["models"][1]

    yolo_pc = {c["class"]: c for c in yolo_model["detection_metrics"]["per_class"]}
    rtdetr_pc = {c["class"]: c for c in rtdetr_model["detection_metrics"]["per_class"]}

    classes = sorted(yolo_pc.keys(), key=lambda c: yolo_pc[c]["support"])
    yolo_vals = [yolo_pc[c]["map50"] for c in classes]
    rtdetr_vals = [rtdetr_pc[c]["map50"] for c in classes]
    supports = [yolo_pc[c]["support"] for c in classes]

    fig, ax = plt.subplots(figsize=(11, 5), dpi=DPI)
    x = np.arange(len(classes))
    width = 0.38

    ax.bar(x - width / 2, yolo_vals, width, label="YOLOv11s", color="#3b82f6", alpha=0.9)
    ax.bar(x + width / 2, rtdetr_vals, width, label="RT-DETR-l", color="#f97316", alpha=0.9)

    for xi, (sup, vy, vr) in enumerate(zip(supports, yolo_vals, rtdetr_vals)):
        ax.text(xi, max(vy, vr) + 0.01, f"n={sup}", ha="center", va="bottom", fontsize=7, color="#4b5563")

    ax.set_xticks(x)
    ax.set_xticklabels([CLASS_LABELS.get(c, c) for c in classes], rotation=28, ha="right", fontsize=8)
    ax.set_ylabel("mAP@50")
    ax.set_ylim(0, 1.08)
    ax.set_title("Per-class mAP@50 — YOLOv11s vs RT-DETR-l (DsPCBSD+, sorted by support asc.)")
    ax.legend()
    ax.axhline(0.5, color="#e5e7eb", linewidth=0.8, linestyle="--")
    fig.tight_layout()
    out = ASSETS_DIR / "per_class.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"  + {out.name}")


# ─── F5: Detection samples ────────────────────────────────────────────────────

def make_detection_sample() -> None:
    """Use pre-generated val prediction images from the YOLO benchmark run."""
    bench6 = ROOT / "ml/runs/detect/dspcbsd_yolo11_bench6"
    pred_imgs = sorted(bench6.glob("val_batch*_pred.jpg"))
    if not pred_imgs:
        print("  ! No val_batch*_pred.jpg found — skipping F5")
        return

    samples = pred_imgs[:3]
    n = len(samples)
    fig, axes = plt.subplots(1, n, figsize=(14, 5), dpi=DPI)
    if n == 1:
        axes = [axes]

    for ax, p in zip(axes, samples):
        img = np.array(Image.open(p).convert("RGB"))
        ax.imshow(img)
        ax.axis("off")

    fig.suptitle("YOLOv11s — detections on DsPCBSD+ validation set", fontsize=11)
    fig.tight_layout()
    out = ASSETS_DIR / "detection_sample.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  + {out.name}")


# ─── F2: Anomaly heatmap (synthetic illustration) ─────────────────────────────

def make_anomaly_heatmap() -> None:
    """
    PatchCore results are dry-run (model weights exist but no inference was run).
    Generates a synthetic heatmap to illustrate the expected output pattern.
    Clearly labelled as an illustration in the figure title.
    """

    def synthetic_pcb(seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        img = np.ones((256, 256, 3)) * 0.18
        for i in range(0, 256, 32):
            img[i : i + 3, :] = [0.75, 0.65, 0.2]
            img[:, i : i + 3] = [0.75, 0.65, 0.2]
        for _ in range(12):
            x, y = rng.integers(10, 230, size=2)
            img[y : y + 8, x : x + 8] = [0.85, 0.75, 0.3]
        return np.clip(img, 0, 1)

    def synthetic_heatmap(has_defect: bool, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        h = rng.random((256, 256)) * 0.12
        if has_defect:
            cx, cy = rng.integers(50, 200, size=2)
            yy, xx = np.ogrid[:256, :256]
            blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 30**2))
            h = np.clip(h + blob * rng.uniform(0.7, 1.0), 0, 1)
        return h

    pcb_tp = synthetic_pcb(1)
    pcb_edge = synthetic_pcb(2)
    hm_tp = synthetic_heatmap(True, 10)
    hm_edge = np.clip(synthetic_heatmap(True, 11) * 0.5, 0, 1)

    fig, axes = plt.subplots(2, 3, figsize=(10, 7), dpi=DPI)

    examples = [(pcb_tp, hm_tp, "True positive"), (pcb_edge, hm_edge, "Borderline case")]
    col_titles = ["Original", "Anomaly score map", "Overlay"]

    for row, (pcb, hm, row_label) in enumerate(examples):
        overlay = pcb.copy()
        overlay[:, :, 0] = np.clip(overlay[:, :, 0] + hm * 0.8, 0, 1)
        axes[row, 0].imshow(pcb)
        axes[row, 0].axis("off")
        axes[row, 1].imshow(hm, cmap="hot", vmin=0, vmax=1)
        axes[row, 1].axis("off")
        axes[row, 2].imshow(np.clip(overlay, 0, 1))
        axes[row, 2].axis("off")
        axes[row, 0].set_ylabel(row_label, fontsize=9, rotation=0, labelpad=65, va="center")

    for col, title in enumerate(col_titles):
        axes[0, col].set_title(title, fontsize=10)

    fig.suptitle(
        "PatchCore (VisA PCB) — anomaly heatmap — synthetic illustration\n"
        "Note: PatchCore ran as dry-run; no real inference metrics are available.",
        fontsize=9,
        color="#6b7280",
    )
    fig.tight_layout()
    out = ASSETS_DIR / "anomaly_heatmap.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"  + {out.name}")


# ─── F1: Three paradigms ─────────────────────────────────────────────────────

def make_three_paradigms() -> None:
    """
    Three-panel figure: YOLOv11s | RT-DETR-l | PatchCore.
    Supervised panels use DsPCBSD+ val predictions.
    PatchCore panel uses a synthetic illustration (different dataset: VisA PCB).
    The caption explicitly states this.
    """
    bench6 = ROOT / "ml/runs/detect/dspcbsd_yolo11_bench6"
    yolo_pred = bench6 / "val_batch0_pred.jpg"
    rtdetr_pred = bench6 / "val_batch1_pred.jpg"

    rng = np.random.default_rng(0)

    def synthetic_pcb_heatmap() -> np.ndarray:
        img = np.ones((256, 256, 3)) * 0.18
        for i in range(0, 256, 32):
            img[i : i + 3, :] = [0.75, 0.65, 0.2]
            img[:, i : i + 3] = [0.75, 0.65, 0.2]
        h = rng.random((256, 256)) * 0.1
        yy, xx = np.ogrid[:256, :256]
        blob = np.exp(-((xx - 110) ** 2 + (yy - 140) ** 2) / (2 * 35**2))
        h = np.clip(h + blob * 0.9, 0, 1)
        img[:, :, 0] = np.clip(img[:, :, 0] + h * 0.8, 0, 1)
        return np.clip(img, 0, 1)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), dpi=DPI)
    titles = [
        "YOLOv11s\n(supervised — DsPCBSD+)",
        "RT-DETR-l\n(supervised — DsPCBSD+)",
        "PatchCore\n(unsupervised — VisA PCB \u2020)",
    ]

    for path, ax in [(yolo_pred, axes[0]), (rtdetr_pred, axes[1])]:
        if path.exists():
            img = np.array(Image.open(path).convert("RGB"))
            h, w = img.shape[:2]
            s = min(h, w)
            img = img[(h - s) // 2 : (h - s) // 2 + s, (w - s) // 2 : (w - s) // 2 + s]
            ax.imshow(img)
        else:
            ax.text(0.5, 0.5, "Image not found", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")

    axes[2].imshow(synthetic_pcb_heatmap())
    axes[2].axis("off")

    for ax, title in zip(axes, titles):
        ax.set_title(title, fontsize=10)

    fig.text(
        0.5,
        -0.04,
        "\u2020 PatchCore is trained on VisA PCB (different dataset). "
        "The third panel is a synthetic illustration — "
        "direct metric comparison with the supervised models is NOT valid.",
        ha="center",
        fontsize=8,
        color="#6b7280",
    )
    fig.suptitle("Three detection paradigms — Lazarus PCB repair station", fontsize=12, y=1.02)
    fig.tight_layout()
    out = ASSETS_DIR / "three_paradigms.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  + {out.name}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generating figures -> docs/assets/")
    bm = load_benchmark()

    print("F1: three_paradigms.png")
    make_three_paradigms()

    print("F2: anomaly_heatmap.png")
    make_anomaly_heatmap()

    print("F3: latency.png")
    make_latency(bm)

    print("F4: per_class.png")
    make_per_class(bm)

    print("F5: detection_sample.png")
    make_detection_sample()

    print("\nAll figures generated.")


if __name__ == "__main__":
    main()
