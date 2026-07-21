"""Rendu générique boîtes → image (PIL, sans dépendance modèle)."""

from PIL import Image, ImageDraw, ImageFont

from .base import Detection

# Palette de couleurs pour les classes (cycle si > 10 classes)
_COLORS = [
    "#FF3838",
    "#FF9D97",
    "#FF701F",
    "#FFB21D",
    "#CFD231",
    "#48F90A",
    "#92CC17",
    "#3DDB86",
    "#1A9334",
    "#00D4BB",
]


def draw_detections(image: Image.Image, detections: list[Detection]) -> Image.Image:
    """
    Dessine les boîtes et labels sur une copie de l'image PIL.

    Retourne une nouvelle image RGB annotée.
    """
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    for det in detections:
        x1, y1, x2, y2 = det.bbox
        color = _COLORS[det.class_id % len(_COLORS)]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        label = f"{det.class_name} {det.confidence:.2f}"
        # Background for label
        text_bbox = draw.textbbox((x1, y1), label, font=font)
        draw.rectangle(text_bbox, fill=color)
        draw.text((x1, y1), label, fill="white", font=font)

    return img
