"""
Router pour le diagnostic PCB avec LLM configurable.
"""

import json
from pathlib import Path
from typing import Literal

import litellm
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from ..config import get_config

router = APIRouter()

# Charger le prompt système
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "diagnose.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()


class Detection(BaseModel):
    """Une détection YOLO."""

    class_: str = Field(..., alias="class")
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


class ImageSize(BaseModel):
    """Dimensions de l'image."""

    width: int
    height: int


class DiagnoseRequest(BaseModel):
    """Requête de diagnostic."""

    detections: list[Detection]
    image_size: ImageSize


class RepairSheet(BaseModel):
    """Fiche de réparation structurée."""

    component: str
    defect_type: str
    severity: Literal["low", "medium", "high"]
    steps: list[str]
    estimated_cost: str
    difficulty: int = Field(..., ge=1, le=5)


class DiagnoseResponse(BaseModel):
    """Réponse du diagnostic."""

    repair_sheet: RepairSheet


@router.post("/", response_model=DiagnoseResponse)
async def diagnose_defects(request: DiagnoseRequest):
    """
    Génère une fiche de réparation pour les défauts PCB détectés.

    - **detections**: Liste des défauts YOLO (class, confidence, bbox)
    - **image_size**: Dimensions de l'image analysée
    """
    # Validation : liste vide
    if not request.detections:
        raise HTTPException(status_code=422, detail="Empty detections list")

    # Charger la configuration LLM
    try:
        config = get_config()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Configuration error: {e}")

    # Construire le prompt utilisateur
    detections_text = "\n".join(
        f"- Class: {d.class_}, Confidence: {d.confidence:.2%}, BBox: {d.bbox}"
        for d in request.detections
    )

    user_prompt = f"""Image dimensions: {request.image_size.width}x{request.image_size.height}

Detected defects:
{detections_text}

Provide a repair sheet for the most critical defect."""

    # Appeler le LLM via LiteLLM
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Construire les paramètres pour LiteLLM
        llm_params = {
            "model": config["model"],
            "messages": messages,
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
        }

        # Ajouter api_key et base_url si définis
        if config.get("api_key"):
            llm_params["api_key"] = config["api_key"]
        if config.get("base_url"):
            llm_params["base_url"] = config["base_url"]

        llm_response = await litellm.acompletion(**llm_params)
        llm_text = llm_response.choices[0].message.content.strip()
    except Exception as e:
        # Ne jamais logger l'api_key
        error_msg = str(e)
        if config.get("api_key") in error_msg:
            error_msg = error_msg.replace(config["api_key"], "***")
        raise HTTPException(status_code=500, detail=f"LLM error: {error_msg}")

    # Parser le JSON
    try:
        repair_data = json.loads(llm_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Malformed LLM JSON response: {e}",
        )

    # Valider avec Pydantic
    try:
        repair_sheet = RepairSheet(**repair_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid repair sheet structure: {e}",
        )

    return DiagnoseResponse(repair_sheet=repair_sheet)
