"""
Orchestrateur de benchmark YOLOv11s vs RT-DETR-l sur DsPCBSD+.

Lance les deux entraînements SÉQUENTIELLEMENT avec des hyperparamètres strictement
identiques et écrit un manifeste d'équité dans ml/runs/training_manifest.json.

Les runs sont séquentiels par conception : un seul GPU, des mesures de vitesse propres,
pas de contention sur la bande passante mémoire ni les workers DataLoader.

Usage:
    uv run python ml/run_training_benchmark.py [--only {yolo,rtdetr,both}] \\
                                                [--epochs N] [--dry-run]

Exemple smoke test (3 epochs) :
    uv run python ml/run_training_benchmark.py --only both --epochs 3
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# ── NixOS CUDA fix ────────────────────────────────────────────────────────────
# libcuda.so réside dans /run/opengl-driver/lib sur NixOS et n'est pas dans le
# search path par défaut du dynamic linker. On doit re-exec AVANT que le
# processus charge la moindre .so C (torch, ultralytics...).
_CUDA_LIB = "/run/opengl-driver/lib"
if os.path.isdir(_CUDA_LIB) and _CUDA_LIB not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{_CUDA_LIB}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    print(f"[cuda-fix] re-exec avec LD_LIBRARY_PATH += {_CUDA_LIB}", flush=True)
    os.execvp(sys.executable, [sys.executable] + sys.argv)

# Imports lourds APRÈS le fix CUDA
import torch  # noqa: E402
from ultralytics import RTDETR, YOLO  # noqa: E402

# ── Chemins ───────────────────────────────────────────────────────────────────
ML_DIR = Path(__file__).parent
DATASET_YAML = ML_DIR / "datasets" / "dspcbsd" / "dspcbsd.yaml"
RUNS_DIR = ML_DIR / "runs" / "detect"
MANIFEST_PATH = ML_DIR / "runs" / "training_manifest.json"

# ── Classes (ordre = index YOLO dans le yaml) ─────────────────────────────────
CLASSES = [
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

# ── Augmentations communes (PCB industrielles) ────────────────────────────────
# Source : train_dspcbsd.py — appliquées à l'identique aux deux modèles.
SHARED_AUGMENTATIONS: dict[str, float] = {
    "hsv_h": 0.01,   # faible variation de teinte (PCB = couleurs fixes)
    "hsv_s": 0.3,    # saturation modérée
    "hsv_v": 0.3,    # luminosité modérée
    "degrees": 0.0,  # pas de rotation (PCB photographiées alignées)
    "translate": 0.1,
    "scale": 0.3,
    "fliplr": 0.5,
    "flipud": 0.0,   # pas de flip vertical
    "mosaic": 1.0,
    "mixup": 0.1,
}

# ── Hyperparamètres communs (non négociables) ─────────────────────────────────
SHARED_HYPERPARAMS: dict[str, object] = {
    "data": str(DATASET_YAML),
    "imgsz": 640,
    "epochs": 150,        # écrasé par --epochs
    "patience": 50,
    "batch": 8,
    "seed": 42,
    "deterministic": False,  # grid_sampler_2d_backward_cuda segfault sur torch 2.11+cu130 avec deterministic=True
    "device": "0",
    "workers": 8,
    "save": True,
    "plots": True,
    **SHARED_AUGMENTATIONS,
}


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ML_DIR,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _env_info() -> dict[str, str]:
    import ultralytics

    return {
        "ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda or "N/A",
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "gpu_vram_gb": (
            str(round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1))
            if torch.cuda.is_available()
            else "N/A"
        ),
        "python": sys.version.split()[0],
    }


def _dataset_info() -> dict[str, object]:
    """Compte les images et instances par classe par split."""
    from collections import Counter

    result: dict[str, object] = {
        "yaml_path": str(DATASET_YAML),
        "yaml_sha256": _sha256(DATASET_YAML),
        "splits": {},
    }
    labels_base = DATASET_YAML.parent / "labels"
    for split in ("train", "val", "test"):
        split_dir = labels_base / split
        if not split_dir.exists():
            continue
        counter: Counter[int] = Counter()
        n_images = 0
        for lf in split_dir.glob("*.txt"):
            n_images += 1
            for line in lf.read_text().splitlines():
                if line.strip():
                    counter[int(line.split()[0])] += 1
        result["splits"][split] = {  # type: ignore[index]
            "images": n_images,
            "instances": sum(counter.values()),
            "per_class": {CLASSES[i]: counter[i] for i in range(len(CLASSES))},
        }
    return result


def _count_epochs_from_csv(run_dir: Path) -> int | None:
    """Lit results.csv pour compter les epochs réellement effectuées."""
    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        return None
    try:
        with open(csv_path) as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return None


def _extract_metrics(results: object) -> dict[str, object]:
    """Extrait métriques globales + par classe depuis un objet ultralytics val."""
    box = results.box  # type: ignore[attr-defined]
    global_metrics: dict[str, float] = {
        "mAP50": round(float(box.map50), 4),
        "mAP50-95": round(float(box.map), 4),
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
    }
    per_class: dict[str, object] = {}
    try:
        names: dict[int, str] = results.names  # type: ignore[attr-defined]
        ap50 = box.ap50
        ap = box.ap
        for idx, cls_name in names.items():
            per_class[cls_name] = {
                "mAP50": round(float(ap50[idx]), 4),
                "mAP50-95": round(float(ap[idx]), 4),
            }
    except Exception as exc:
        per_class["_extraction_error"] = str(exc)
    return {"global": global_metrics, "per_class": per_class}


def _peak_vram_gb() -> float | None:
    if not torch.cuda.is_available():
        return None
    return round(torch.cuda.max_memory_allocated(0) / 1e9, 2)


def _count_params(model: object) -> int | None:
    try:
        return sum(p.numel() for p in model.model.parameters())  # type: ignore[attr-defined]
    except Exception:
        return None


def _actual_run_dir(base_name: str, model: object) -> Path:
    """Retourne le répertoire réel du run (ultralytics peut incrémenter le nom: bench → bench2).

    Priorité :
    1. model.trainer.save_dir (exposé par ultralytics après entraînement)
    2. Répertoire le plus récent correspondant au pattern dans RUNS_DIR
    3. Fallback sur RUNS_DIR / base_name
    """
    try:
        save_dir = Path(model.trainer.save_dir)  # type: ignore[attr-defined]
        if save_dir.exists():
            return save_dir
    except Exception:
        pass
    candidates = sorted(
        RUNS_DIR.glob(f"{base_name}*/"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else RUNS_DIR / base_name


# ── Runners ───────────────────────────────────────────────────────────────────

def run_yolo(epochs: int, dry_run: bool) -> dict[str, object]:
    """Entraîne YOLOv11s et retourne l'entrée du manifeste."""
    run_name = "dspcbsd_yolo11_bench"
    base_weights = "yolo11s.pt"
    hp: dict[str, object] = {
        **SHARED_HYPERPARAMS,
        "epochs": epochs,
        "project": str(RUNS_DIR),
        "name": run_name,
    }

    if dry_run:
        print(f"[dry-run][YOLO] config:\n{json.dumps(hp, indent=2, default=str)}")
        return {"model_name": "YOLOv11s", "status": "dry-run", "hyperparams_effective": hp}

    print(f"\n{'─'*60}")
    print(f"  YOLO  base={base_weights}  run={run_name}  epochs={epochs}")
    print(f"{'─'*60}")

    model = YOLO(base_weights)
    n_params = _count_params(model)

    torch.cuda.reset_peak_memory_stats(0)
    start = time.monotonic()
    start_ts = datetime.now(UTC).isoformat()
    status = "success"
    error_msg: str | None = None

    try:
        model.train(**hp)  # type: ignore[arg-type]
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        print(f"[YOLO][ERROR] {exc}")

    end_ts = datetime.now(UTC).isoformat()
    duration = round(time.monotonic() - start, 1)
    peak_vram = _peak_vram_gb()

    run_dir = _actual_run_dir(run_name, model)
    best_pt = run_dir / "weights" / "best.pt"
    epochs_done = _count_epochs_from_csv(run_dir)
    if run_dir.name != run_name:
        print(f"[YOLO] nom incrémenté par ultralytics : {run_name!r} → {run_dir.name!r}")

    val_metrics: dict[str, object] = {}
    if best_pt.exists() and status == "success":
        print("[YOLO] Validation du best.pt pour les métriques finales...")
        try:
            val_model = YOLO(str(best_pt))
            val_results = val_model.val(
                data=str(DATASET_YAML),
                imgsz=640,
                device="0",
                workers=8,
                verbose=False,
            )
            val_metrics = _extract_metrics(val_results)
        except Exception as exc:
            val_metrics = {"_error": str(exc)}

    # Libère explicitement la VRAM avant le prochain run
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"[YOLO] status={status}  durée={duration}s  epochs={epochs_done}  peak_vram={peak_vram}GB")
    return {
        "model_name": "YOLOv11s",
        "base_weights": base_weights,
        "run_name": run_name,
        "best_pt_path": str(best_pt) if best_pt.exists() else None,
        "n_params": n_params,
        "train_start": start_ts,
        "train_end": end_ts,
        "duration_seconds": duration,
        "epochs_completed": epochs_done,
        "peak_vram_gb": peak_vram,
        "hyperparams_effective": hp,
        "metrics": val_metrics,
        "status": status,
        "error": error_msg,
    }


def run_rtdetr(epochs: int, dry_run: bool) -> dict[str, object]:
    """Entraîne RT-DETR-l et retourne l'entrée du manifeste."""
    run_name = "dspcbsd_rtdetr_bench"
    base_weights = "rtdetr-l.pt"
    hp: dict[str, object] = {
        **SHARED_HYPERPARAMS,
        "epochs": epochs,
        "project": str(RUNS_DIR),
        "name": run_name,
    }

    if dry_run:
        print(f"[dry-run][RT-DETR] config:\n{json.dumps(hp, indent=2, default=str)}")
        return {"model_name": "RT-DETR-l", "status": "dry-run", "hyperparams_effective": hp}

    print(f"\n{'─'*60}")
    print(f"  RT-DETR  base={base_weights}  run={run_name}  epochs={epochs}")
    print(f"{'─'*60}")

    model = RTDETR(base_weights)
    n_params = _count_params(model)

    torch.cuda.reset_peak_memory_stats(0)
    start = time.monotonic()
    start_ts = datetime.now(UTC).isoformat()
    status = "success"
    error_msg: str | None = None

    try:
        model.train(**hp)  # type: ignore[arg-type]
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        print(f"[RT-DETR][ERROR] {exc}")

    end_ts = datetime.now(UTC).isoformat()
    duration = round(time.monotonic() - start, 1)
    peak_vram = _peak_vram_gb()

    run_dir = _actual_run_dir(run_name, model)
    best_pt = run_dir / "weights" / "best.pt"
    epochs_done = _count_epochs_from_csv(run_dir)
    if run_dir.name != run_name:
        print(f"[RT-DETR] nom incrémenté par ultralytics : {run_name!r} → {run_dir.name!r}")

    val_metrics: dict[str, object] = {}
    if best_pt.exists() and status == "success":
        print("[RT-DETR] Validation du best.pt pour les métriques finales...")
        try:
            val_model = RTDETR(str(best_pt))
            val_results = val_model.val(
                data=str(DATASET_YAML),
                imgsz=640,
                device="0",
                workers=8,
                verbose=False,
            )
            val_metrics = _extract_metrics(val_results)
        except Exception as exc:
            val_metrics = {"_error": str(exc)}

    # Libère explicitement la VRAM
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"[RT-DETR] status={status}  durée={duration}s  epochs={epochs_done}  peak_vram={peak_vram}GB")
    return {
        "model_name": "RT-DETR-l",
        "base_weights": base_weights,
        "run_name": run_name,
        "best_pt_path": str(best_pt) if best_pt.exists() else None,
        "n_params": n_params,
        "train_start": start_ts,
        "train_end": end_ts,
        "duration_seconds": duration,
        "epochs_completed": epochs_done,
        "peak_vram_gb": peak_vram,
        "hyperparams_effective": hp,
        "metrics": val_metrics,
        "status": status,
        "error": error_msg,
    }


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark YOLOv11s vs RT-DETR-l sur DsPCBSD+",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--only",
        choices=["yolo", "rtdetr", "both"],
        default="both",
        help="Modèle(s) à entraîner",
    )
    parser.add_argument("--epochs", type=int, default=150, help="Nombre d'epochs")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche la config sans entraîner",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  Lazarus Benchmark — YOLOv11s vs RT-DETR-l  [séquentiel]")
    print(f"  epochs={args.epochs}  batch=8  imgsz=640  seed=42  device=0")
    print(f"  dry-run={args.dry_run}  only={args.only}")
    print("=" * 70)

    if not DATASET_YAML.exists():
        print(f"[ERREUR] Dataset YAML introuvable : {DATASET_YAML}")
        sys.exit(1)

    if not args.dry_run and not torch.cuda.is_available():
        print("[ERREUR] CUDA non disponible. GPU requis pour l'entraînement.")
        sys.exit(1)

    if not args.dry_run:
        # Force l'initialisation CUDA avant les runners (reset_peak_memory_stats
        # échoue si le device n'a pas encore été initialisé).
        torch.cuda.init()
        torch.cuda.set_device(0)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    model_results: dict[str, dict[str, object]] = {}

    if args.only in ("yolo", "both"):
        model_results["yolo"] = run_yolo(args.epochs, args.dry_run)
        if not args.dry_run:
            print("[main] Nettoyage VRAM entre les deux runs...")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats(0)

    if args.only in ("rtdetr", "both"):
        model_results["rtdetr"] = run_rtdetr(args.epochs, args.dry_run)

    if args.dry_run:
        print("\n[dry-run] Aucun entraînement lancé. Configuration affichée ci-dessus.")
        return

    # ── Écriture du manifeste d'équité ────────────────────────────────────────
    print("\nÉcriture du manifeste d'équité...")
    manifest: dict[str, object] = {
        "benchmark_id": f"lazarus-bench-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "training_mode": "sequential",
        "environment": _env_info(),
        "dataset": _dataset_info(),
        "shared_hyperparams": {**SHARED_HYPERPARAMS, "epochs": args.epochs},
        "models": model_results,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"Manifeste : {MANIFEST_PATH}")

    # ── Résumé terminal ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESULTATS DU BENCHMARK")
    print("=" * 70)
    for key, entry in model_results.items():
        g = entry.get("metrics", {}).get("global", {})  # type: ignore[union-attr]
        print(f"\n  [{entry.get('model_name', key)}]")
        print(f"    status      : {entry.get('status')}")
        print(f"    epochs      : {entry.get('epochs_completed')} / {args.epochs}")
        print(f"    durée       : {entry.get('duration_seconds')}s")
        print(f"    peak VRAM   : {entry.get('peak_vram_gb')} GB")
        print(f"    n_params    : {entry.get('n_params')}")
        if g:
            print(f"    mAP50       : {g.get('mAP50')}")
            print(f"    mAP50-95    : {g.get('mAP50-95')}")
            print(f"    precision   : {g.get('precision')}")
            print(f"    recall      : {g.get('recall')}")
        if entry.get("error"):
            print(f"    ERREUR      : {entry.get('error')}")

    print(f"\nManifeste complet : {MANIFEST_PATH}\n")


if __name__ == "__main__":
    main()
