# lazarus

# Backend FastAPI

uv sync  
ln -s ../../../ml/runs/detect/deeppcb_yolo11/weights/best.pt apps/api/models/best.pt  
uv run uvicorn apps.api.main:app --reload

# ML training

uv sync --extra ml  
uv run python ml/train.py

# Frontend React (à initialiser)

cd apps/web && npm install && npm run dev

Endpoints API :

- POST /api/analyze - Upload image PCB → détections YOLO
- POST /api/diagnose - Liste de défauts → diagnostic Claude
- GET /health - Health check
