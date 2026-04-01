"""
Router pour l'analyse d'images PCB avec YOLO.
"""

import base64
import io
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

router = APIRouter()

CLASSES = ["open", "short", "mousebite", "spur", "copper", "pin-hole"]


class Detection(BaseModel):
    """Représente une détection de défaut."""

    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


class AnalyzeResponse(BaseModel):
    """Réponse de l'analyse."""

    success: bool
    detections: list[Detection]
    image_annotated: str | None = None  # Base64 encoded image


@router.post("/", response_model=AnalyzeResponse)
async def analyze_image(
    request: Request,
    file: Annotated[UploadFile, File(description="Image PCB à analyser")],
    return_image: bool = True,
):
    """
    Analyse une image PCB et retourne les défauts détectés.

    - **file**: Image PCB (JPEG, PNG)
    - **return_image**: Si True, retourne l'image annotée en base64
    """
    model = request.app.state.yolo_model

    if model is None:
        raise HTTPException(status_code=503, detail="Modèle YOLO non chargé")

    # Vérifier le type de fichier
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Format d'image non supporté. Utilisez JPEG ou PNG.")

    # Lire l'image
    contents = await file.read()

    # Effectuer l'inférence
    results = model(contents, verbose=False)

    detections = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=CLASSES[cls_id],
                    confidence=float(box.conf[0]),
                    bbox=box.xyxy[0].tolist(),
                )
            )

    # Générer l'image annotée si demandé
    image_annotated = None
    if return_image and results:
        # Obtenir l'image avec les annotations
        annotated = results[0].plot()

        # Convertir en base64
        from PIL import Image

        img = Image.fromarray(annotated[..., ::-1])  # BGR to RGB
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_annotated = base64.b64encode(buffer.getvalue()).decode()

    return AnalyzeResponse(
        success=True,
        detections=detections,
        image_annotated=image_annotated,
    )


@router.get("/classes")
async def get_classes():
    """Retourne la liste des classes de défauts."""
    return {"classes": CLASSES}
