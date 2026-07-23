"""Fit PatchCore sur les 4 catégories VisA PCB et exporte les modèles.

Usage:
    uv run python ml/train_patchcore.py                        # toutes catégories
    uv run python ml/train_patchcore.py --categories pcb1      # une seule
    uv run python ml/train_patchcore.py --dry-run              # validation sans fit
    uv run python ml/train_patchcore.py --skip-download        # suppose dataset présent

Écrit : ml/runs/anomaly_results.json (ne modifie PAS benchmark_results.json)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# ── Constantes ──────────────────────────────────────────────────────────────

ALL_CATEGORIES = ["pcb1", "pcb2", "pcb3", "pcb4"]
DATASET_ROOT = Path("ml/datasets/visa")
OUTPUT_DIR = Path("ml/runs")
RESULTS_FILE = OUTPUT_DIR / "anomaly_results.json"
BENCHMARK_FILE = OUTPUT_DIR / "benchmark_results.json"

# VisA fait ~3 Go — vérifier avant de tenter le download
MIN_FREE_DISK_GB = 10.0


# ── Helpers ─────────────────────────────────────────────────────────────────


def _gpu_info() -> str:
    try:
        import subprocess

        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            timeout=5,
        )
        return out.decode().strip().splitlines()[0]
    except Exception:
        return "N/A"


def _git_commit() -> str:
    try:
        import subprocess

        out = subprocess.check_output(["git", "rev-parse", "HEAD"], timeout=5)
        return out.decode().strip()
    except Exception:
        return "N/A"


def _check_disk_space(path: Path = Path("."), min_gb: float = MIN_FREE_DISK_GB) -> None:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    if free_gb < min_gb:
        print(
            f"[ERROR] Espace disque insuffisant : {free_gb:.1f} Go libres, "
            f"{min_gb} Go requis pour le dataset VisA.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"[INFO] Espace disque OK : {free_gb:.1f} Go libres.")


def _assert_benchmark_intact() -> None:
    """Vérifie que benchmark_results.json existe et n'a pas été modifié."""
    if not BENCHMARK_FILE.exists():
        print(
            f"[ERROR] {BENCHMARK_FILE} introuvable. "
            "Ce script enrichit le benchmark existant — il ne le remplace pas. "
            "Exécutez d'abord EPIC D (run_benchmark.py).",
            file=sys.stderr,
        )
        sys.exit(1)


def _extract_metrics(results: list[dict]) -> dict[str, float | None]:
    """Extrait AUROC image, AUROC pixel et AU-PRO depuis les résultats Anomalib."""
    metrics: dict[str, float | None] = {
        "image_auroc": None,
        "pixel_auroc": None,
        "au_pro": None,
    }
    for entry in results:
        for key, val in entry.items():
            k = key.lower()
            if "image_auroc" in k or k == "auroc":
                metrics["image_auroc"] = round(float(val), 4)
            elif "pixel_auroc" in k:
                metrics["pixel_auroc"] = round(float(val), 4)
            elif "au_pro" in k or "aupro" in k:
                metrics["au_pro"] = round(float(val), 4)
    return metrics


# ── Fit par catégorie ────────────────────────────────────────────────────────


def fit_category(
    category: str,
    skip_download: bool,
    dry_run: bool,
) -> dict:
    """Fit PatchCore sur une catégorie VisA et retourne les résultats."""
    import warnings

    warnings.filterwarnings("ignore")

    print(f"\n{'='*60}")
    print(f"[INFO] Catégorie : {category}")
    print(f"{'='*60}")

    t_start = time.monotonic()

    try:
        from anomalib.data import Visa
        from anomalib.deploy import ExportType
        from anomalib.engine import Engine
        from anomalib.models import Patchcore

        # Dossier d'export pour cette catégorie
        export_dir = OUTPUT_DIR / "patchcore" / category

        if dry_run:
            print(f"[DRY-RUN] Catégorie {category} — skip fit/export.")
            return {
                "category": category,
                "status": "dry_run",
                "metrics": {},
                "fit_duration_s": 0,
                "export_path": str(export_dir / "weights" / "torch" / "model.pt"),
                "n_train_images": "N/A",
                "n_test_images": "N/A",
                "memory_bank_size": "N/A",
            }

        # Datamodule VisA — auto-download sauf si skip_download
        print(f"[INFO] Chargement du datamodule VisA ({category})…")
        datamodule = Visa(
            root=str(DATASET_ROOT),
            category=category,
        )

        if not skip_download:
            _check_disk_space()
        else:
            if not (DATASET_ROOT / category).exists():
                print(
                    f"[ERROR] --skip-download spécifié mais {DATASET_ROOT / category} introuvable.",
                    file=sys.stderr,
                )
                raise FileNotFoundError(f"Dataset manquant : {DATASET_ROOT / category}")

        model = Patchcore()
        engine = Engine(
            default_root_dir=str(export_dir),
        )

        print(f"[INFO] Fit PatchCore sur {category}…")
        engine.fit(datamodule=datamodule, model=model)

        fit_duration = time.monotonic() - t_start
        if fit_duration > 3600:
            print(
                f"[WARNING] Fit en {fit_duration:.0f}s — c'est anormalement long pour PatchCore "
                "(normalement < 1 min/catégorie). Vérifiez la config GPU.",
                file=sys.stderr,
            )

        print(f"[INFO] Test sur {category}…")
        test_results = engine.test(datamodule=datamodule, model=model)

        metrics = _extract_metrics(test_results if isinstance(test_results, list) else [test_results or {}])

        print(f"[INFO] Export ONNX pour {category}…")
        try:
            engine.export(model=model, export_type=ExportType.TORCH, export_root=str(export_dir))
        except Exception as e_exp:
            print(f"[WARNING] Export TORCH échoué : {e_exp}. Tentative ONNX…")
            try:
                engine.export(model=model, export_type=ExportType.ONNX, export_root=str(export_dir))
            except Exception as e_onnx:
                print(f"[WARNING] Export ONNX échoué aussi : {e_onnx}. Continuer sans export.")

        # Taille de la banque mémoire
        memory_bank_size: int | str = "N/A"
        try:
            mb = model.model.memory_bank  # type: ignore[attr-defined]
            memory_bank_size = int(mb.shape[0]) if hasattr(mb, "shape") else "N/A"
        except Exception:
            pass

        # Nombre d'images
        n_train: int | str = "N/A"
        n_test: int | str = "N/A"
        try:
            datamodule.setup("fit")
            n_train = len(datamodule.train_data)  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            datamodule.setup("test")
            n_test = len(datamodule.test_data)  # type: ignore[arg-type]
        except Exception:
            pass

        # Seuil adaptatif
        threshold_value: float | str = "N/A"
        try:
            thresh = getattr(model, "pixel_threshold", None) or getattr(model, "image_threshold", None)
            if thresh is not None:
                threshold_value = round(float(thresh.value if hasattr(thresh, "value") else thresh), 4)
        except Exception:
            pass

        result = {
            "category": category,
            "status": "success",
            "metrics": metrics,
            "fit_duration_s": round(fit_duration, 1),
            "memory_bank_size": memory_bank_size,
            "n_train_images": n_train,
            "n_test_images": n_test,
            "adaptive_threshold": threshold_value,
            "export_path": str(export_dir),
        }
        print(
            f"[INFO] {category} OK — AUROC image={metrics.get('image_auroc')}, "
            f"pixel={metrics.get('pixel_auroc')}, AU-PRO={metrics.get('au_pro')}, "
            f"fit={fit_duration:.1f}s"
        )
        return result

    except Exception as exc:
        duration = time.monotonic() - t_start
        print(f"[ERROR] Catégorie {category} échouée : {exc}", file=sys.stderr)
        return {
            "category": category,
            "status": "failed",
            "error": str(exc),
            "fit_duration_s": round(duration, 1),
            "metrics": {},
        }


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit PatchCore sur VisA PCB.")
    parser.add_argument(
        "--categories",
        type=str,
        default=",".join(ALL_CATEGORIES),
        help="Catégories à traiter, séparées par des virgules (défaut: toutes).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Ne pas télécharger VisA — suppose le dataset présent dans ml/datasets/visa/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validation de la config sans fit réel.",
    )
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    invalid = [c for c in categories if c not in ALL_CATEGORIES]
    if invalid:
        print(f"[ERROR] Catégories inconnues : {invalid}. Valeurs acceptées : {ALL_CATEGORIES}", file=sys.stderr)
        sys.exit(1)

    # Vérifier que le benchmark supervisé existe (ce script enrichit, ne remplace pas)
    _assert_benchmark_intact()

    print(f"[INFO] Catégories à traiter : {categories}")
    print(f"[INFO] Dry-run : {args.dry_run}")
    print(f"[INFO] Skip download : {args.skip_download}")

    if not args.dry_run and not args.skip_download:
        _check_disk_space()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results_by_category: list[dict] = []
    for category in categories:
        cat_result = fit_category(category, skip_download=args.skip_download, dry_run=args.dry_run)
        results_by_category.append(cat_result)

    anomaly_results = {
        "meta": {
            "date": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "gpu": _gpu_info(),
            "model": "PatchCore",
            "dataset": "VisA",
            "resolution": "256x256 (Anomalib default — NOT comparable to 640x640 supervised models)",
            "paradigm": "unsupervised_anomaly_detection",
            "categories_requested": categories,
        },
        "categories": results_by_category,
    }

    RESULTS_FILE.write_text(json.dumps(anomaly_results, indent=2, ensure_ascii=False))
    print(f"\n[INFO] Résultats écrits dans {RESULTS_FILE}")

    # Afficher un résumé
    ok = [r for r in results_by_category if r["status"] == "success"]
    failed = [r for r in results_by_category if r["status"] == "failed"]
    print(f"\n[SUMMARY] {len(ok)}/{len(categories)} catégories OK, {len(failed)} échouées.")
    if failed:
        for f in failed:
            print(f"  - {f['category']}: {f.get('error', '?')}")
    if not args.dry_run:
        print("\n[INFO] Vérification que benchmark_results.json n'a pas été modifié…")
        if BENCHMARK_FILE.exists():
            print("[OK] benchmark_results.json intact.")


if __name__ == "__main__":
    main()
