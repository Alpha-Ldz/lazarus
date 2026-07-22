"""
Script d'entraînement RT-DETR sur le dataset DsPCBSD+.

RT-DETR (« DETRs Beat YOLOs », CVPR 2024) est un détecteur temps-réel basé Transformer, sans NMS.
Entraîné sur les mêmes 9 classes, même résolution que la baseline YOLOv11 — comparaison fair.

9 classes: short, spur, spurious_copper, open, mousebite,
           hole_breakout, conductor_scratch, conductor_foreign_object,
           base_material_foreign_object

Source dataset: https://doi.org/10.6084/m9.figshare.24970329.v1
"""

from pathlib import Path

from ultralytics import RTDETR

# Configuration
ML_DIR = Path(__file__).parent
DATASET_YAML = ML_DIR / "datasets" / "dspcbsd" / "dspcbsd.yaml"
IMG_SIZE = 640  # identique à la baseline YOLO — condition d'équité du benchmark


def train_rtdetr(
    epochs: int = 150,
    batch: int = 8,
    variant: str = "l",
) -> None:
    """
    Entraîne un modèle RT-DETR sur DsPCBSD+.

    Args:
        epochs: Nombre d'epochs (150 recommandé pour 10k images)
        batch: Taille du batch (8 = point de départ sûr sur 32 Go pour un transformer)
        variant: Variante du modèle RT-DETR : 'l' ou 'x' uniquement
    """
    if not DATASET_YAML.exists():
        raise FileNotFoundError(
            f"Config dataset non trouvée : {DATASET_YAML}\n"
            "Lancez d'abord: python ml/download_dspcbsd.py"
        )

    print(f"Chargement du modèle pré-entraîné RT-DETR-{variant}...")
    model = RTDETR(f"rtdetr-{variant}.pt")

    print(f"Dataset : {DATASET_YAML}")
    print(f"Epochs : {epochs}")
    print(f"Batch : {batch}")
    print(f"Image size : {IMG_SIZE}")
    print("Démarrage de l'entraînement...")

    model.train(
        data=str(DATASET_YAML),
        epochs=epochs,
        imgsz=IMG_SIZE,
        batch=batch,
        project=str(ML_DIR / "runs" / "detect"),
        name="dspcbsd_rtdetr",
        device="0",
        # Augmentations adaptées aux images PCB industrielles (identiques à train_dspcbsd.py)
        hsv_h=0.01,
        hsv_s=0.3,
        hsv_v=0.3,
        degrees=0,
        translate=0.1,
        scale=0.3,
        fliplr=0.5,
        flipud=0.0,
        mosaic=1.0,
        mixup=0.1,
    )

    print("=" * 60)
    print("Entraînement terminé!")
    print(f"Modèle sauvegardé dans : {ML_DIR / 'runs' / 'detect' / 'dspcbsd_rtdetr'}")
    print()
    print("Pour utiliser ce modèle dans l'API :")
    print("  LAZARUS_DETECTOR=rtdetr \\")
    print("  LAZARUS_MODEL_PATH=ml/runs/detect/dspcbsd_rtdetr/weights/best.pt \\")
    print("    uv run uvicorn apps.api.main:app --reload")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Entraînement RT-DETR sur DsPCBSD+")
    parser.add_argument("--epochs", type=int, default=150, help="Nombre d'epochs")
    parser.add_argument("--batch", type=int, default=8, help="Taille du batch")
    parser.add_argument(
        "--variant",
        type=str,
        default="l",
        choices=["l", "x"],
        help="Variante RT-DETR : 'l' ou 'x' (n/s/m inexistants pour RT-DETR)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Entraînement RT-DETR sur DsPCBSD+")
    print("=" * 60)

    train_rtdetr(
        epochs=args.epochs,
        batch=args.batch,
        variant=args.variant,
    )


if __name__ == "__main__":
    main()
