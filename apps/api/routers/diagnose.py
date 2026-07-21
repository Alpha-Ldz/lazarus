"""
Router pour le diagnostic PCB avec LLM configurable.
"""

from pathlib import Path

import litellm
from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.config import get_config

_PROMPT = (Path(__file__).parent.parent / "prompts" / "diagnose.txt").read_text()

router = APIRouter()

HIGH_SEVERITY = {"open", "short", "hole_breakout", "base_material_foreign_object"}

difficulty_map = {
    "short": 3, "spur": 2, "spurious_copper": 3, "open": 4, "mousebite": 2,
    "hole_breakout": 4, "conductor_scratch": 2,
    "conductor_foreign_object": 3, "base_material_foreign_object": 4,
}

cost_map = {
    "short": "10-25€", "spur": "5-10€", "spurious_copper": "10-20€", "open": "15-30€",
    "mousebite": "5-15€", "hole_breakout": "20-40€", "conductor_scratch": "5-15€",
    "conductor_foreign_object": "10-20€", "base_material_foreign_object": "20-40€",
}


class DiagnoseRequest(BaseModel):
    """Requête de diagnostic."""

    defects: list[dict] | None = None  # Ancien format (rétrocompatible)
    detections: list[dict] | None = None  # Nouveau format envoyé par le frontend
    context: str | None = None

    def get_defects(self) -> list[dict]:
        """Retourne les défauts, peu importe le nom du champ envoyé."""
        return self.detections or self.defects or []


class RepairSheetModel(BaseModel):
    """Fiche de réparation structurée."""

    component: str
    defect_type: str
    severity: str  # "low" | "medium" | "high"
    steps: list[str]
    estimated_cost: str
    difficulty: int  # 1 à 5


class DiagnoseResponse(BaseModel):
    """Réponse du diagnostic — format attendu par le frontend."""

    repair_sheet: RepairSheetModel


def _llm_repair_sheet(defects_summary: str, context_text: str) -> str | None:
    cfg = get_config()
    try:
        resp = litellm.completion(
            model=cfg["model"],
            api_base=cfg.get("base_url"),
            api_key=cfg["api_key"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            messages=[
                {"role": "system", "content": _PROMPT},
                {"role": "user", "content": f"{defects_summary}{context_text}"},
            ],
        )
        return resp.choices[0].message.content
    except Exception:
        return None  # fallback sur les steps par défaut


@router.post("/", response_model=DiagnoseResponse)
async def diagnose_defects(request: DiagnoseRequest):
    """
    Génère un diagnostic détaillé des défauts PCB avec LLM configurable.
    """
    defects = request.get_defects()

    if not defects:
        return DiagnoseResponse(
            repair_sheet=RepairSheetModel(
                component="N/A",
                defect_type="none",
                severity="low",
                steps=["Aucun défaut détecté. Continuer la production normalement."],
                estimated_cost="0€",
                difficulty=1,
            )
        )

    # Déterminer le défaut principal (plus haute confiance)
    main_defect = max(defects, key=lambda d: d.get("confidence", 0))
    defect_type = main_defect.get("class_name", "unknown")

    # Déterminer la sévérité
    severity = "medium"
    if defect_type in HIGH_SEVERITY:
        severity = "high"
    if len(defects) > 5:
        severity = "high"

    # Déterminer la difficulté et le coût estimé
    difficulty = difficulty_map.get(defect_type, 3)
    estimated_cost = cost_map.get(defect_type, "10-20€")

    # Construire les étapes de réparation par défaut
    default_steps = [
        f"Localiser le défaut de type '{defect_type}' aux coordonnées indiquées",
        "Inspecter visuellement la zone sous microscope",
        "Nettoyer la zone avec de l'isopropanol",
        "Appliquer la réparation adaptée au type de défaut",
        "Vérifier la continuité électrique après réparation",
    ]

    # Enrichir le diagnostic via le LLM configuré
    defects_summary = "\n".join(
        f"- {d.get('class_name', 'unknown')}: confiance {d.get('confidence', 0):.1%}"
        for d in defects
    )
    context_text = f"\nContexte: {request.context}" if request.context else ""
    llm_steps = _llm_repair_sheet(defects_summary, context_text)
    if llm_steps:
        steps = [s.strip() for s in llm_steps.split("\n") if s.strip()]
        if len(steps) >= 3:
            default_steps = steps[:5]

    return DiagnoseResponse(
        repair_sheet=RepairSheetModel(
            component=(
                f"PCB Zone ({main_defect.get('bbox', [0,0,0,0])[0]:.0f},"
                f" {main_defect.get('bbox', [0,0,0,0])[1]:.0f})"
            ),
            defect_type=defect_type,
            severity=severity,
            steps=default_steps,
            estimated_cost=estimated_cost,
            difficulty=difficulty,
        )
    )
