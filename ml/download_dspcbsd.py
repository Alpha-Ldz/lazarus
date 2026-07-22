"""
Télécharge le dataset DsPCBSD+ depuis Figshare.

DsPCBSD+ contient 10 259 images avec 20 276 annotations de défauts PCB.
9 classes: SH, SP, SC, OP, MB, HB, CS, CFO, BMFO
Format: YOLO natif (images/ et labels/ avec split train/val)

Source: https://doi.org/10.6084/m9.figshare.24970329.v1
Paper: https://doi.org/10.1038/s41597-024-03656-8
Licence: CC BY 4.0
"""

import zipfile
from pathlib import Path

ML_DIR = Path(__file__).parent
DATA_DIR = ML_DIR / "data" / "DsPCBSD+"
DATASET_DIR = ML_DIR / "datasets" / "dspcbsd"

# URL Figshare — à mettre à jour si le fichier change de version
# Le dataset est distribué en un seul zip via Figshare
FIGSHARE_DOI = "10.6084/m9.figshare.24970329.v1"
# Note: Figshare ne permet pas le téléchargement direct via URL simple
# Il faut télécharger manuellement depuis la page du DOI ou utiliser l'API Figshare
FIGSHARE_PAGE = "https://doi.org/10.6084/m9.figshare.24970329.v1"


def download_dataset():
    """Télécharge le dataset depuis Figshare."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "dspcbsd_plus.zip"

    if zip_path.exists() and zip_path.stat().st_size > 1024:
        print(f"✅ Archive déjà présente : {zip_path}")
    else:
        print("⚠️  Téléchargement manuel requis:")
        print(f"   1. Visitez : {FIGSHARE_PAGE}")
        print("   2. Téléchargez le fichier ZIP du dataset")
        print(f"   3. Placez-le dans : {zip_path}")
        print("   4. Relancez ce script")
        print()
        print("   Ou utilisez wget/curl avec l'URL directe du fichier sur Figshare")
        import sys
        sys.exit(1)

    return zip_path


def extract_dataset(zip_path: Path):
    """Extrait l'archive et vérifie la structure."""
    print(f"📦 Extraction de {zip_path}...")

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(DATA_DIR)

    # Vérifier que la structure YOLO existe
    # Le dataset contient Data_YOLO/images/{train,val} et Data_YOLO/labels/{train,val}
    yolo_dir = None
    for candidate in [
        DATA_DIR / "Data_YOLO",
        DATA_DIR / "DsPCBSD+" / "Data_YOLO",
    ]:
        if candidate.exists():
            yolo_dir = candidate
            break

    if yolo_dir is None:
        # Chercher récursivement
        for p in DATA_DIR.rglob("Data_YOLO"):
            yolo_dir = p
            break

    if yolo_dir is None:
        raise FileNotFoundError(
            "Dossier Data_YOLO non trouvé après extraction. "
            "Vérifiez la structure du zip téléchargé."
        )

    print(f"✅ Dossier YOLO trouvé : {yolo_dir}")

    # Vérifier les sous-dossiers attendus
    for split in ["train", "val"]:
        img_dir = yolo_dir / "images" / split
        lbl_dir = yolo_dir / "labels" / split
        if not img_dir.exists():
            raise FileNotFoundError(f"Dossier manquant : {img_dir}")
        if not lbl_dir.exists():
            raise FileNotFoundError(f"Dossier manquant : {lbl_dir}")

        img_count = len(list(img_dir.glob("*")))
        lbl_count = len(list(lbl_dir.glob("*.txt")))
        print(f"   {split}: {img_count} images, {lbl_count} labels")

    return yolo_dir


def create_symlinks(yolo_dir: Path):
    """Crée les symlinks pour que YOLO trouve les données."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val"]:
        for folder in ["images", "labels"]:
            src = yolo_dir / folder / split
            dst = DATASET_DIR / folder / split
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(src.resolve())
            print(f"   🔗 {dst} -> {src}")


def verify_dataset():
    """Vérifie l'intégrité du dataset préparé."""
    print("\n🔍 Vérification finale...")

    total_images = 0
    total_labels = 0

    for split in ["train", "val"]:
        img_dir = DATASET_DIR / "images" / split
        lbl_dir = DATASET_DIR / "labels" / split

        imgs = list(img_dir.glob("*"))
        lbls = list(lbl_dir.glob("*.txt"))

        total_images += len(imgs)
        total_labels += len(lbls)

        # Vérifier qu'il n'y a pas d'images sans labels
        img_stems = {p.stem for p in imgs}
        lbl_stems = {p.stem for p in lbls}
        orphan_imgs = img_stems - lbl_stems
        if orphan_imgs:
            print(f"   ⚠️  {split}: {len(orphan_imgs)} images sans labels")

    print("\n📊 Dataset prêt:")
    print(f"   Total images: {total_images}")
    print(f"   Total labels: {total_labels}")
    print("   Attendu: ~10 259 images, ~10 259 labels")

    if total_images < 9000:
        print("   ⚠️  Nombre d'images inférieur à l'attendu — vérifiez l'extraction")
    else:
        print("   ✅ Dataset complet")


def main():
    print("=" * 60)
    print("Téléchargement et préparation du dataset DsPCBSD+")
    print("=" * 60)

    zip_path = download_dataset()
    yolo_dir = extract_dataset(zip_path)
    create_symlinks(yolo_dir)
    verify_dataset()

    print("\n🎯 Pour lancer l'entraînement :")
    print("   python ml/train_dspcbsd.py")


if __name__ == "__main__":
    main()
