"""
Script d'entraînement YOLOv11 sur le dataset DeepPCB.

DeepPCB contient 1500 paires d'images pour la détection de défauts PCB.
6 classes de défauts: open, short, mousebite, spur, copper, pin-hole
"""

import shutil
from pathlib import Path

import yaml
from ultralytics import YOLO

# Configuration
ML_DIR = Path(__file__).parent
DATA_ROOT = ML_DIR / "data" / "DeepPCB"
PCBDATA_DIR = DATA_ROOT / "PCBData"
OUTPUT_DIR = ML_DIR / "datasets" / "deeppcb_yolo"
IMG_SIZE = 640

# Classes DeepPCB (index 0-based pour YOLO, DeepPCB utilise 1-6)
CLASSES = ["open", "short", "mousebite", "spur", "copper", "pin-hole"]


def convert_deeppcb_to_yolo(annotation_path: Path, img_width: int = 640, img_height: int = 640) -> list[str]:
    """
    Convertit une annotation DeepPCB vers le format YOLO.

    Format DeepPCB: x1 y1 x2 y2 class_id (1-indexed)
    Format YOLO: class_id center_x center_y width height (normalized, 0-indexed)
    """
    yolo_annotations = []

    if not annotation_path.exists():
        return yolo_annotations

    with open(annotation_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 5:
                continue

            x1, y1, x2, y2, class_id = map(int, parts)

            # Convertir class_id de 1-indexed à 0-indexed
            class_id = class_id - 1

            # Calculer le centre et les dimensions normalisées
            center_x = ((x1 + x2) / 2) / img_width
            center_y = ((y1 + y2) / 2) / img_height
            width = (x2 - x1) / img_width
            height = (y2 - y1) / img_height

            # Clamp les valeurs entre 0 et 1
            center_x = max(0, min(1, center_x))
            center_y = max(0, min(1, center_y))
            width = max(0, min(1, width))
            height = max(0, min(1, height))

            yolo_annotations.append(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}")

    return yolo_annotations


def prepare_dataset():
    """Prépare le dataset au format YOLO."""
    print("Préparation du dataset YOLO...")

    # Créer la structure de dossiers
    for split in ["train", "val"]:
        (OUTPUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    # Lire les fichiers de split
    trainval_file = PCBDATA_DIR / "trainval.txt"
    test_file = PCBDATA_DIR / "test.txt"

    train_count = 0
    val_count = 0

    # Traiter le set d'entraînement
    if trainval_file.exists():
        with open(trainval_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 2:
                    continue

                img_rel_path, ann_rel_path = parts

                # Construire les chemins réels
                # Le fichier liste "group.../XXXXX.jpg" mais le fichier réel est "XXXXX_test.jpg"
                img_path_parts = img_rel_path.replace(".jpg", "_test.jpg")
                img_path = PCBDATA_DIR / img_path_parts
                ann_path = PCBDATA_DIR / ann_rel_path

                if not img_path.exists():
                    continue

                # Générer un nom de fichier unique
                img_name = img_path.stem
                dest_img = OUTPUT_DIR / "images" / "train" / f"{img_name}.jpg"
                dest_label = OUTPUT_DIR / "labels" / "train" / f"{img_name}.txt"

                # Copier l'image
                shutil.copy2(img_path, dest_img)

                # Convertir et sauvegarder les annotations
                yolo_annotations = convert_deeppcb_to_yolo(ann_path)
                with open(dest_label, "w") as lf:
                    lf.write("\n".join(yolo_annotations))

                train_count += 1

    # Traiter le set de validation/test
    if test_file.exists():
        with open(test_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 2:
                    continue

                img_rel_path, ann_rel_path = parts

                img_path_parts = img_rel_path.replace(".jpg", "_test.jpg")
                img_path = PCBDATA_DIR / img_path_parts
                ann_path = PCBDATA_DIR / ann_rel_path

                if not img_path.exists():
                    continue

                img_name = img_path.stem
                dest_img = OUTPUT_DIR / "images" / "val" / f"{img_name}.jpg"
                dest_label = OUTPUT_DIR / "labels" / "val" / f"{img_name}.txt"

                shutil.copy2(img_path, dest_img)

                yolo_annotations = convert_deeppcb_to_yolo(ann_path)
                with open(dest_label, "w") as lf:
                    lf.write("\n".join(yolo_annotations))

                val_count += 1

    print(f"Dataset préparé: {train_count} images train, {val_count} images val")
    return train_count, val_count


def create_yaml_config():
    """Crée le fichier de configuration YAML pour YOLO."""
    config = {
        "path": str(OUTPUT_DIR.absolute()),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(CLASSES)},
    }

    yaml_path = OUTPUT_DIR / "deeppcb.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"Configuration YAML créée: {yaml_path}")
    return yaml_path


def train_yolo(yaml_path: Path, epochs: int = 100, batch: int = 16, model_size: str = "n"):
    """
    Entraîne un modèle YOLOv11 sur le dataset DeepPCB.

    Args:
        yaml_path: Chemin vers le fichier de configuration du dataset
        epochs: Nombre d'epochs d'entraînement
        batch: Taille du batch
        model_size: Taille du modèle (n=nano, s=small, m=medium, l=large, x=xlarge)
    """
    print(f"Chargement du modèle YOLOv11{model_size}...")

    # Charger le modèle pré-entraîné YOLOv11
    model = YOLO(f"yolo11{model_size}.pt")

    print("Démarrage de l'entraînement...")

    # Entraîner le modèle
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        batch=batch,
        imgsz=IMG_SIZE,
        project=str(ML_DIR / "runs" / "detect"),
        name="deeppcb_yolo11",
        patience=20,  # Early stopping
        save=True,
        plots=True,
        device="0",  # GPU 0, utiliser "cpu" si pas de GPU
    )

    print("Entraînement terminé!")
    return results


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("Entraînement YOLOv11 sur DeepPCB")
    print("=" * 60)

    # Vérifier que les données existent
    if not PCBDATA_DIR.exists():
        raise FileNotFoundError(f"Dossier de données non trouvé: {PCBDATA_DIR}")

    # Préparer le dataset
    train_count, val_count = prepare_dataset()

    if train_count == 0:
        raise ValueError("Aucune image d'entraînement trouvée!")

    # Créer la configuration YAML
    yaml_path = create_yaml_config()

    # Entraîner le modèle
    # Utiliser model_size="s" pour un bon compromis vitesse/précision
    # Augmenter à "m" ou "l" pour plus de précision si vous avez un GPU puissant
    train_yolo(yaml_path, epochs=100, batch=16, model_size="s")


if __name__ == "__main__":
    main()
