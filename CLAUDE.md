# Lazarus — PCB Repair Station

## IMPORTANT — Read First

You are working on a monorepo with a Python backend and a React frontend.
NEVER modify files outside the scope of the current issue.
ALWAYS run the verification commands listed in the issue before stopping.
When you finish ALL steps, write: `echo "✅ DONE"`.

## Project Structure

```
lazarus/
├── apps/
│   ├── api/               # FastAPI backend (Python 3.13, uv)
│   │   ├── main.py        # App entrypoint + CORS + lifespan
│   │   ├── routers/
│   │   │   ├── analyze.py  # POST /api/analyze — YOLO detection
│   │   │   └── diagnose.py # POST /api/diagnose — Claude diagnosis
│   │   ├── models/
│   │   │   └── best.pt     # YOLOv11 weights (symlink)
│   │   └── services/       # Business logic
│   └── web/               # React + Vite + TypeScript
│       └── src/
│           ├── components/  # DropZone, PCBViewer, BoundingBox, DiagnosticPanel, ExportButton
│           ├── hooks/       # useAnalyze.ts
│           └── types/       # index.ts — ALL types go here
├── ml/                    # YOLOv11 training scripts
└── pyproject.toml
```

## Commands

```bash
# Backend
cd apps/api && uv run uvicorn apps.api.main:app --reload

# Frontend
cd apps/web && npm run dev

# Test API analyze
curl -s -X POST http://localhost:8000/api/analyze -F "file=@test.jpg" | python -m json.tool

# Test API diagnose
curl -s -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"defects":[{"class_name":"short","confidence":0.92,"bbox":[10,20,50,60]}]}' \
  | python -m json.tool

# Type-check frontend
cd apps/web && npx tsc --noEmit

# Lint
uv run ruff check apps/
```

## Code Style

- Python: type hints on ALL functions, ruff for formatting, Pydantic models for request/response
- TypeScript: strict mode, no `any`, all interfaces in `apps/web/src/types/index.ts`
- React: functional components only, hooks in `apps/web/src/hooks/`
- Imports: use `@/` alias for `apps/web/src/`
- Prefer `async/await` over `.then()`

## Shared Types (source of truth)

```typescript
// apps/web/src/types/index.ts
interface Detection {
  class_name: string; // "short" | "open_circuit" | "mousebite" | "spur" | "spurious_copper" | "pin_hole"
  confidence: number; // 0 to 1
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

interface AnalyzeResponse {
  detections: Detection[];
  image_size: { width: number; height: number };
}

interface RepairSheet {
  component: string;
  defect_type: string;
  severity: "low" | "medium" | "high";
  steps: string[];
  estimated_cost: string;
  difficulty: number; // 1 to 5
}
```

## Git

- Branch format: `<type>/plland/<kebab-case-name>`
- Commit format: `<type>(<scope>): <description>` — Refs #<issue>
- Types: feat, fix, docs, refactor, test, chore

## Anti-patterns — DO NOT

- Do NOT create new type files — put types in `apps/web/src/types/index.ts`
- Do NOT install packages without being told to in the issue
- Do NOT modify `apps/api/main.py` unless the issue explicitly says to
- Do NOT skip verification steps — run ALL commands before saying DONE
- Do NOT refactor code unrelated to the current issue
