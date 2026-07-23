# Case Study — Lazarus: PCB Defect Detection Station

## Problem

Manual inspection of printed circuit boards is slow, fatigue-prone, and non-reproducible. An experienced technician reviews roughly 40 boards per hour; high-volume lines may require throughput ten times higher. The goal was to build a system capable of automatically detecting defects, classifying them, and generating a structured repair sheet — in under two seconds per board.

## Approach

Two paradigms were benchmarked on the same dataset:

**Supervised detection** (YOLOv11s and RT-DETR-l on DsPCBSD+) — trained on 9 annotated defect classes, evaluated with standard mAP metrics. This paradigm requires a labelled dataset but returns structured bounding boxes that can be consumed directly by an LLM diagnostic step.

**Unsupervised anomaly detection** (PatchCore on VisA PCB) — no defect annotations required; the model learns the distribution of defect-free boards and flags deviations. This paradigm can be applied to any PCB type without annotation cost, but does not distinguish defect classes.

A shared `Detector` interface allows swapping models without modifying the application router.

## Evaluation Protocol

To ensure a fair comparison between the two supervised models:

- Same validation split for both models (DsPCBSD+ val, not seen during training except for early stopping).
- Identical Ultralytics hyperparameters (equal budget, no model-specific tuning).
- Identical training schedule: 150 epochs, patience=50.
- Latency measured at batch=1, 200 iterations, 50 warmup, GPU synchronised before and after each call.
- Models measured sequentially, never in parallel.

## Results

| Model | mAP@50 | mAP@50-95 | Latency p50 | Params |
|-------|--------|-----------|-------------|--------|
| YOLOv11s | **0.849** | **0.550** | **33 ms** | 9.5 M |
| RT-DETR-l | 0.818 | 0.522 | 133 ms | 33.0 M |

RT-DETR-l reached its best checkpoint at epoch 52 and plateaued. YOLOv11s converges more consistently under the available budget.

## Engineering Decision

**YOLOv11s goes to production.** The +3.1 pp mAP@50 gap, combined with 4x lower latency and 3.5x fewer parameters, represents an unambiguous cost/benefit advantage for a real-time inspection API.

**The challenger lost — and that is a valid result worth keeping.** RT-DETR-l's results were not discarded: they are fully documented in `docs/BENCHMARK.md`, including methodological caveats (shared hyperparameters, schedule potentially mismatched to transformer convergence). Dropping a challenger because it underperforms is poor MLOps practice. Negative results, properly documented, are evidence of a sound evaluation process.

## Acknowledged Limitations

- The `val` split was used for early stopping: reported metrics are slightly optimistic.
- Default Ultralytics hyperparameters are calibrated for YOLO-family architectures; RT-DETR might improve with architecture-specific tuning.
- PatchCore ran as a dry-run: no real inference metrics are available for this paradigm.
- TensorRT export, backbone freeze, and per-architecture learning rate schedules were not explored — out of budget.
