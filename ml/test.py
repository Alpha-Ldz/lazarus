"""
Script de test pour le modèle YOLOv11 entraîné sur DsPCBSD+.
"""

import argparse
from pathlib import Path

from ultralytics import YOLO

# Configuration par défaut
ML_DIR = Path(__file__).parent
DEFAULT_MODEL = ML_DIR / "runs" / "detect" / "dspcbsd_yolo11" / "weights" / "best.pt"
DEFAULT_DATA = ML_DIR / "datasets" / "dspcbsd" / "dspcbsd.yaml"
SAMPLE_IMAGE = ML_DIR / "data" / "DeepPCB" / "PCBData" / "group00041" / "00041" / "00041000_test.jpg"

CLASSES = [
    "short", "spur", "spurious_copper", "open", "mousebite",
    "hole_breakout", "conductor_scratch", "conductor_foreign_object",
    "base_material_foreign_object",
]


def validate(model_path: Path, data_path: Path):
    """Exécute la validation sur le dataset de test."""
    print("=" * 60)
    print("Validation du modèle sur le dataset de test")
    print("=" * 60)

    model = YOLO(str(model_path))
    results = model.val(data=str(data_path))

    print("\n📊 Résultats de validation:")
    print(f"  mAP50:      {results.box.map50:.4f}")
    print(f"  mAP50-95:   {results.box.map:.4f}")
    print(f"  Précision:  {results.box.mp:.4f}")
    print(f"  Rappel:     {results.box.mr:.4f}")

    print("\n📋 mAP50 par classe:")
    for i, ap in enumerate(results.box.ap50):
        print(f"  {CLASSES[i]:12s}: {ap:.4f}")

    return results


def predict_single(model_path: Path, image_path: Path, save: bool = True, show: bool = False):
    """Exécute l'inférence sur une seule image."""
    print("=" * 60)
    print(f"Inférence sur: {image_path.name}")
    print("=" * 60)

    model = YOLO(str(model_path))
    results = model(str(image_path), save=save, show=show)

    for r in results:
        boxes = r.boxes
        print(f"\n🔍 {len(boxes)} défaut(s) détecté(s):")

        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            print(f"  - {CLASSES[cls_id]:12s} (conf: {conf:.2f}) @ [{xyxy[0]:.0f}, {xyxy[1]:.0f}, {xyxy[2]:.0f}, {xyxy[3]:.0f}]")

    if save:
        print(f"\n💾 Résultat sauvegardé dans: runs/detect/predict/")

    return results


def predict_batch(model_path: Path, source_dir: Path, save: bool = True):
    """Exécute l'inférence sur un dossier d'images."""
    print("=" * 60)
    print(f"Inférence batch sur: {source_dir}")
    print("=" * 60)

    model = YOLO(str(model_path))

    # Trouver toutes les images _test.jpg
    images = list(source_dir.glob("**/*_test.jpg"))
    if not images:
        images = list(source_dir.glob("**/*.jpg"))

    print(f"📁 {len(images)} images trouvées")

    results = model(images, save=save, stream=True)

    total_detections = 0
    class_counts = {c: 0 for c in CLASSES}

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            class_counts[CLASSES[cls_id]] += 1
            total_detections += 1

    print(f"\n📊 Statistiques:")
    print(f"  Total détections: {total_detections}")
    print(f"\n  Par classe:")
    for cls_name, count in class_counts.items():
        print(f"    {cls_name:12s}: {count}")

    if save:
        print(f"\n💾 Résultats sauvegardés dans: runs/detect/predict/")


def export_model(model_path: Path, format: str = "onnx"):
    """Exporte le modèle vers un autre format."""
    print("=" * 60)
    print(f"Export du modèle vers {format.upper()}")
    print("=" * 60)

    model = YOLO(str(model_path))
    exported_path = model.export(format=format)

    print(f"✅ Modèle exporté: {exported_path}")
    return exported_path


def main():
    parser = argparse.ArgumentParser(description="Test du modèle YOLOv11 DsPCBSD+")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Chemin vers le modèle .pt")

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # Commande: validate
    val_parser = subparsers.add_parser("val", help="Validation sur le dataset de test")
    val_parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Fichier YAML du dataset")

    # Commande: predict
    pred_parser = subparsers.add_parser("predict", help="Inférence sur image(s)")
    pred_parser.add_argument("source", type=Path, nargs="?", default=SAMPLE_IMAGE, help="Image ou dossier")
    pred_parser.add_argument("--no-save", action="store_true", help="Ne pas sauvegarder les résultats")
    pred_parser.add_argument("--show", action="store_true", help="Afficher les résultats")

    # Commande: export
    export_parser = subparsers.add_parser("export", help="Exporter le modèle")
    export_parser.add_argument("--format", default="onnx", choices=["onnx", "torchscript", "tflite", "engine"],
                               help="Format d'export")

    args = parser.parse_args()

    # Vérifier que le modèle existe
    if not args.model.exists():
        print(f"❌ Modèle non trouvé: {args.model}")
        print("   Avez-vous lancé l'entraînement avec yolov_training.py ?")
        return

    if args.command == "val":
        validate(args.model, args.data)
    elif args.command == "predict":
        if args.source.is_dir():
            predict_batch(args.model, args.source, save=not args.no_save)
        else:
            predict_single(args.model, args.source, save=not args.no_save, show=args.show)
    elif args.command == "export":
        export_model(args.model, args.format)
    else:
        # Par défaut: validation + une prédiction exemple
        print("Usage: python yolov_test.py [--model MODEL] {val,predict,export}")
        print("\nExemples:")
        print("  python yolov_test.py val                    # Validation sur test set")
        print("  python yolov_test.py predict image.jpg      # Inférence sur une image")
        print("  python yolov_test.py predict data/images/   # Inférence sur un dossier")
        print("  python yolov_test.py export --format onnx   # Export ONNX")


if __name__ == "__main__":
    main()
