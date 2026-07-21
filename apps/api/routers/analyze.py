"""
Router pour l'analyse d'images PCB.
"""

import base64
import io
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from PIL import Image
from pydantic import BaseModel

from ..detectors.annotate import draw_detections
from ..detectors.base import Detection

router = APIRouter()


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
    detector = request.app.state.detector

    if detector is None:
        raise HTTPException(status_code=503, detail="Détecteur non chargé")

    # Vérifier le type de fichier
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Format d'image non supporté. Utilisez JPEG ou PNG.")

    # Lire l'image et convertir en PIL
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Effectuer l'inférence via l'interface Detector
    result = detector.predict(image)

    # Générer l'image annotée si demandé
    image_annotated = None
    if return_image:
        annotated = draw_detections(image, result.detections)
        buffer = io.BytesIO()
        annotated.save(buffer, format="JPEG", quality=85)
        image_annotated = base64.b64encode(buffer.getvalue()).decode()

    return AnalyzeResponse(
        success=True,
        detections=result.detections,
        image_annotated=image_annotated,
    )


@router.get("/classes")
async def get_classes(request: Request):
    """Retourne la liste des classes de défauts."""
    detector = request.app.state.detector
    if detector is None:
        raise HTTPException(status_code=503, detail="Détecteur non chargé")
    return {"classes": detector.class_names}
