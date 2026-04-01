"""
Router pour le diagnostic avec Claude AI.
"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DiagnoseRequest(BaseModel):
    """Requête de diagnostic."""

    defects: list[dict]  # Liste des défauts détectés par YOLO
    context: str | None = None  # Contexte additionnel (type de PCB, etc.)


class DiagnoseResponse(BaseModel):
    """Réponse du diagnostic."""

    success: bool
    diagnosis: str
    recommendations: list[str]
    severity: str  # "low", "medium", "high", "critical"


@router.post("/", response_model=DiagnoseResponse)
async def diagnose_defects(request: DiagnoseRequest):
    """
    Génère un diagnostic détaillé des défauts PCB avec Claude.

    - **defects**: Liste des défauts détectés (class_name, confidence, bbox)
    - **context**: Informations supplémentaires sur le PCB
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY non configurée. Définissez la variable d'environnement.",
        )

    if not request.defects:
        return DiagnoseResponse(
            success=True,
            diagnosis="Aucun défaut détecté sur ce PCB.",
            recommendations=["Continuer la production normalement."],
            severity="low",
        )

    # Construire le prompt pour Claude
    defects_summary = "\n".join(
        f"- {d.get('class_name', 'unknown')}: confiance {d.get('confidence', 0):.1%}"
        for d in request.defects
    )

    context_text = f"\nContexte additionnel: {request.context}" if request.context else ""

    prompt = f"""Analysez les défauts suivants détectés sur un PCB (circuit imprimé) et fournissez un diagnostic technique.

Défauts détectés:
{defects_summary}
{context_text}

Fournissez:
1. Un diagnostic détaillé expliquant l'impact potentiel de ces défauts
2. Des recommandations d'action (réparation, rejet, inspection manuelle, etc.)
3. Un niveau de sévérité global (low, medium, high, critical)

Répondez de manière concise et technique, adaptée à un ingénieur en électronique."""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # Parser la réponse (simpliste, pourrait être amélioré)
        severity = "medium"
        if any(d.get("class_name") in ["open", "short"] for d in request.defects):
            severity = "high"
        if len(request.defects) > 5:
            severity = "critical"

        recommendations = [
            "Inspection manuelle recommandée",
            "Vérifier les connexions électriques",
            "Documenter les défauts pour analyse qualité",
        ]

        return DiagnoseResponse(
            success=True,
            diagnosis=response_text,
            recommendations=recommendations,
            severity=severity,
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Package anthropic non installé. Ajoutez-le aux dépendances.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Claude API: {str(e)}")
