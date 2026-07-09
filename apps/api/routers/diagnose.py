"""
Router pour le diagnostic PCB avec LLM configurable.
"""

import litellm
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_config

router = APIRouter()


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


@router.post("/", response_model=DiagnoseResponse)
async def diagnose_defects(request: DiagnoseRequest):
    """
    Génère un diagnostic détaillé des défauts PCB via LLM (Ollama/Qwen par défaut).
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
    if defect_type in ("open", "short"):
        severity = "high"
    if len(defects) > 5:
        severity = "high"

    # Déterminer la difficulté et le coût estimé
    difficulty_map = {"open": 4, "short": 3, "mousebite": 2, "spur": 2, "copper": 3, "pin-hole": 1}
    difficulty = difficulty_map.get(defect_type, 3)

    cost_map = {"open": "15-30€", "short": "10-25€", "mousebite": "5-15€", "spur": "5-10€", "copper": "10-20€", "pin-hole": "5-10€"}
    estimated_cost = cost_map.get(defect_type, "10-20€")

    # Construire les étapes de réparation par défaut
    default_steps = [
        f"Localiser le défaut de type '{defect_type}' aux coordonnées indiquées",
        "Inspecter visuellement la zone sous microscope",
        "Nettoyer la zone avec de l'isopropanol",
        "Appliquer la réparation adaptée au type de défaut",
        "Vérifier la continuité électrique après réparation",
    ]

    # Utiliser LiteLLM avec la config (Ollama/Qwen par défaut)
    try:
        config = get_config()
        defects_summary = "\n".join(
            f"- {d.get('class_name', 'unknown')}: confiance {d.get('confidence', 0):.1%}"
            for d in defects
        )
        context_text = f"\nContexte: {request.context}" if request.context else ""

        prompt = f"""Défauts PCB détectés:
{defects_summary}{context_text}

Donne exactement 5 étapes de réparation concrètes et courtes (une phrase chacune).
Réponds UNIQUEMENT avec les 5 étapes, une par ligne, sans numérotation."""

        llm_params = {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
        }
        if config.get("api_key"):
            llm_params["api_key"] = config["api_key"]
        if config.get("base_url"):
            llm_params["base_url"] = config["base_url"]

        response = await litellm.acompletion(**llm_params)
        steps_text = response.choices[0].message.content.strip()
        steps = [s.strip() for s in steps_text.split("\n") if s.strip()]
        if len(steps) >= 3:
            default_steps = steps[:5]
    except Exception:
        pass  # Fallback sur les étapes par défaut

    return DiagnoseResponse(
        repair_sheet=RepairSheetModel(
            component=f"PCB Zone ({main_defect.get('bbox', [0,0,0,0])[0]:.0f}, {main_defect.get('bbox', [0,0,0,0])[1]:.0f})",
            defect_type=defect_type,
            severity=severity,
            steps=default_steps,
            estimated_cost=estimated_cost,
            difficulty=difficulty,
        )
    )
