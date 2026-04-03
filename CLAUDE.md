# Lazarus — PCB Repair Station

## CRITICAL — Python package management

This project uses **uv**, NOT pip, NOT poetry, NOT conda.
NEVER run `pip install`, `pip3 install`, `python -m pip`, or `python setup.py`.
NEVER run `python` or `python3` directly.

Use these commands INSTEAD:
| ❌ NEVER | ✅ ALWAYS |
|----------|----------|
| `pip install X` | `uv add X` |
| `python script.py` | `uv run python script.py` |
| `python -m pytest` | `uv run pytest` |
| `python -c "..."` | `uv run python -c "..."` |
| `pip freeze` | `uv pip list` |
| `pip install -r req.txt` | `uv sync` |

## IMPORTANT — Read Before Coding

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
│   │   │   └── diagnose.py # POST /api/diagnose — LLM diagnosis
│   │   ├── models/
│   │   │   └── best.pt     # YOLOv11 weights (symlink)
│   │   └── services/       # Business logic
│   └── web/               # React + Vite + TypeScript
│       └── src/
│           ├── components/  # DropZone, PCBViewer, BoundingBox, DiagnosticPanel, ExportButton
│           ├── hooks/       # useAnalyze.ts
│           ├── config/      # index.ts — API base URL from VITE_API_BASE_URL
│           └── types/       # index.ts — ALL types go here
├── ml/                    # YOLOv11 training scripts
└── pyproject.toml         # Python deps managed by uv
```

## Commands

```bash
# Install Python deps
uv sync

# Start backend
uv run uvicorn apps.api.main:app --reload

# Start frontend
cd apps/web && npm run dev

# Add a Python dependency
uv add <package-name>

# Run any Python script
uv run python <script.py>

# Test API analyze
curl -s -X POST http://localhost:8000/api/analyze -F "file=@test.jpg" | python -m json.tool

# Test API diagnose
curl -s -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"detections":[{"class_name":"short","confidence":0.92,"bbox":[10,20,50,60]}]}' \
  | uv run python -m json.tool

# Type-check frontend
cd apps/web && npx tsc --noEmit

# Lint Python
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
type DefectClass =
  | "open"
  | "short"
  | "mousebite"
  | "spur"
  | "copper"
  | "pin-hole";

interface Detection {
  class_id: number;
  class_name: DefectClass;
  confidence: number;
  bbox: [number, number, number, number];
}

interface RepairSheet {
  component: string;
  defect_type: string;
  severity: "low" | "medium" | "high";
  steps: string[];
  estimated_cost: string;
  difficulty: number;
}
```

## Git

- Branch format: `<type>/plland/<kebab-case-name>`
- Commit format: `<type>(<scope>): <description>` — Refs #<issue>
- Types: feat, fix, docs, refactor, test, chore

## Anti-patterns — DO NOT

- Do NOT use `pip`, `pip3`, `python`, or `python3` directly — use `uv run` and `uv add`
- Do NOT create new type files — put types in `apps/web/src/types/index.ts`
- Do NOT install packages without being told to in the issue
- Do NOT modify `apps/api/main.py` unless the issue explicitly says to
- Do NOT skip verification steps — run ALL commands before saying DONE
- Do NOT refactor code unrelated to the current issue
