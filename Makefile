.PHONY: benchmark benchmark-yolo benchmark-rtdetr benchmark-fast figures lint test

## Run the full benchmark harness (YOLOv11s vs RT-DETR-l)
benchmark:
	uv run python ml/run_benchmark.py --models yolo rtdetr

## Run benchmark for YOLO only
benchmark-yolo:
	uv run python ml/run_benchmark.py --models yolo

## Run benchmark for RT-DETR only
benchmark-rtdetr:
	uv run python ml/run_benchmark.py --models rtdetr

## Run benchmark without ONNX export
benchmark-fast:
	uv run python ml/run_benchmark.py --models yolo rtdetr --skip-onnx

## Regenerate all documentation figures from models and JSON results
figures:
	uv run python ml/figures/make_figures.py

## Lint Python code
lint:
	uv run ruff check apps/ ml/

## Run tests
test:
	uv run pytest
