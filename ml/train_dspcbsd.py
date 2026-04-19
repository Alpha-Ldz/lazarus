"""
Script d'entraînement YOLOv11 sur le dataset DsPCBSD+.

DsPCBSD+ contient 10 259 images réelles de défauts PCB industriels.
9 classes: short, spur, spurious_copper, open, mousebite,
           hole_breakout, conductor_scratch, conductor_foreign_object,
           base_material_foreign_object

Source: https://doi.org/10.6084/m9.figshare.24970329.v1
"""

from pathlib import Path

from ultralytics import YOLO

# Configuration
ML_DIR = Path(__file__).parent
DATASET_YAML = ML_DIR / "datasets" / "dspcbsd" / "dspcbsd.yaml"
IMG_SIZE = 640

CLASSES = [
    "short",               # 0 - SH
    "spur",                # 1 - SP
    "spurious_copper",     # 2 - SC
    "open",                # 3 - OP
    "mousebite",           # 4 - MB
    "hole_breakout",       # 5 - HB
    "conductor_scratch",   # 6 - CS
    "conductor_foreign_object",      # 7 - CFO
    "base_material_foreign_object",  # 8 - BMFO
]


def train_yolo(
    epochs: int = 150,
    batch: int = 16,
    model_size: str = "s",
    resume: bool = False,
    pretrained: str | None = None,
):
    """
    Entraîne un modèle YOLOv11 sur DsPCBSD+.

    Args:
        epochs: Nombre d'epochs (150 recommandé pour 10k images)
        batch: Taille du batch (16 pour RTX 5090 32GB)
        model_size: Taille du modèle YOLO (n/s/m/l/x)
        resume: Reprendre un entraînement interrompu
        pretrained: Chemin vers un .pt pour fine-tuning (ex: DeepPCB best.pt)
    """
    if not DATASET_YAML.exists():
        raise FileNotFoundError(
            f"Config dataset non trouvée : {DATASET_YAML}\n"
            "Lancez d'abord: python ml/download_dspcbsd.py"
        )

    # Charger le modèle
    if pretrained:
        print(f"Fine-tuning depuis : {pretrained}")
        model = YOLO(pretrained)
    else:
        print(f"Chargement du modèle pré-entraîné YOLOv11{model_size}...")
        model = YOLO(f"yolo11{model_size}.pt")

    print(f"Dataset : {DATASET_YAML}")
    print(f"Classes : {len(CLASSES)}")
    print(f"Epochs : {epochs}")
    print(f"Batch : {batch}")
    print(f"Image size : {IMG_SIZE}")
    print("Démarrage de l'entraînement...")

    # Entraîner
    results = model.train(
        data=str(DATASET_YAML),
        epochs=epochs,
        batch=batch,
        imgsz=IMG_SIZE,
        project=str(ML_DIR / "runs" / "detect"),
        name="dspcbsd_yolo11",
        patience=25,
        save=True,
        plots=True,
        device="0",
        # Augmentations adaptées aux images PCB industrielles
        hsv_h=0.01,      # Faible variation de teinte (PCB = couleurs fixes)
        hsv_s=0.3,        # Variation de saturation modérée
        hsv_v=0.3,        # Variation de luminosité modérée
        degrees=0,        # Pas de rotation (les PCB sont photographiées alignées)
        translate=0.1,
        scale=0.3,
        fliplr=0.5,
        flipud=0.0,       # Pas de flip vertical
        mosaic=1.0,
        mixup=0.1,
    )

    print("=" * 60)
    print("Entraînement terminé!")
    print(f"Modèle sauvegardé dans : {ML_DIR / 'runs' / 'detect' / 'dspcbsd_yolo11'}")
    print()
    print("Pour utiliser ce modèle dans l'API :")
    print("  cp ml/runs/detect/dspcbsd_yolo11/weights/best.pt apps/api/models/best.pt")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Entraînement YOLOv11 sur DsPCBSD+")
    parser.add_argument("--epochs", type=int, default=150, help="Nombre d'epochs")
    parser.add_argument("--batch", type=int, default=16, help="Taille du batch")
    parser.add_argument("--model-size", type=str, default="s", choices=["n", "s", "m", "l", "x"])
    parser.add_argument("--pretrained", type=str, default=None,
                        help="Chemin vers un modèle .pt pour fine-tuning")
    parser.add_argument("--resume", action="store_true", help="Reprendre un entraînement")

    args = parser.parse_args()

    print("=" * 60)
    print("Entraînement YOLOv11 sur DsPCBSD+")
    print("=" * 60)

    train_yolo(
        epochs=args.epochs,
        batch=args.batch,
        model_size=args.model_size,
        resume=args.resume,
        pretrained=args.pretrained,
    )


if __name__ == "__main__":
    main()
