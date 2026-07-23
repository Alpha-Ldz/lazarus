# Benchmark Report — YOLOv11s vs RT-DETR-l on DsPCBSD+

Generated: 2026-07-23T09:10:52.264034+00:00  
Git commit: `3d39702f3a16`  
GPU: NVIDIA GeForce RTX 5090

## 1. Main Comparison Table

| Model | Paradigm | mAP50 | mAP50-95 | Precision | Recall | Latency p50 (ms) | Latency p95 (ms) | Throughput (img/s) | Params (M) | VRAM Train (GB) | Train Duration (h) |
|-------|----------|-------|----------|-----------|--------|-----------------|-----------------|-------------------|------------|-----------------|-------------------|
| **yolo11s-dspcbsd** | supervised_detection | 0.849 | 0.550 | 0.821 | 0.815 | 33.22 | 33.7 | 30.1 | 9.5 | 2.19 | 1.2 |
| **rtdetr-l-dspcbsd** | supervised_detection | 0.818 | 0.522 | 0.832 | 0.778 | 133.035 | 134.032 | 7.5 | 33.0 | 6.66 | 3.4 |

## 2. Per-Class Metrics

All classes from DsPCBSD+ (9 categories). Support = instances in the evaluation split.

| Class | Support | yolo11s-dspcbsd P | yolo11s-dspcbsd R | yolo11s-dspcbsd mAP50 | yolo11s-dspcbsd mAP50-95 | rtdetr-l-dspcbsd P | rtdetr-l-dspcbsd R | rtdetr-l-dspcbsd mAP50 | rtdetr-l-dspcbsd mAP50-95 |
|-------|---------|---|---|---|---|---|---|---|---|
| short | 169 | 0.860 | 0.852 | 0.900 | 0.617 | 0.805 | 0.817 | 0.829 | 0.558 |
| spur | 929 | 0.822 | 0.796 | 0.847 | 0.433 | 0.840 | 0.743 | 0.827 | 0.417 |
| spurious_copper | 285 | 0.780 | 0.803 | 0.845 | 0.557 | 0.829 | 0.786 | 0.816 | 0.555 |
| open | 338 | 0.829 | 0.876 | 0.897 | 0.586 | 0.843 | 0.843 | 0.866 | 0.550 |
| mousebite | 546 | 0.839 | 0.780 | 0.814 | 0.435 | 0.868 | 0.756 | 0.828 | 0.446 |
| hole_breakout | 608 | 0.939 | 0.951 | 0.975 | 0.843 | 0.872 | 0.960 | 0.970 | 0.828 |
| conductor_scratch | 448 | 0.749 | 0.732 | 0.771 | 0.524 | 0.776 | 0.596 | 0.661 | 0.410 |
| conductor_foreign_object | 423 | 0.737 | 0.661 | 0.707 | 0.443 | 0.781 | 0.629 | 0.695 | 0.440 |
| base_material_foreign_object | 346 | 0.833 | 0.884 | 0.887 | 0.515 | 0.871 | 0.870 | 0.870 | 0.498 |

## 3. Latency Breakdown (preprocess / inference / postprocess)

Measured via the `Detector` interface (production path). batch=1.

| Model | Backend | Pre (ms) | Infer (ms) | Post (ms) | p50 (ms) | p95 (ms) | p99 (ms) | std (ms) |
|-------|---------|---------|-----------|----------|---------|---------|---------|---------|
| yolo11s-dspcbsd | pytorch | 0.485 | 31.065 | 0.204 | 33.22 | 33.7 | 34.346 | 0.268 |
| rtdetr-l-dspcbsd | pytorch | 0.453 | 130.931 | 0.166 | 133.035 | 134.032 | 134.869 | 0.546 |

> **ONNX (yolo11s-dspcbsd)**: p50=27.494 ms, mean=27.747 ms
> **ONNX (rtdetr-l-dspcbsd)**: p50=98.115 ms, mean=98.095 ms

## 4. Measurement Protocol

| Parameter | Value |
|-----------|-------|
| Evaluation split | `val` (**Note:** no `test` split in dspcbsd.yaml — using `val`. Val was used for early-stopping, so metrics are slightly optimistic.) |
| Image size | 640x640 |
| Confidence threshold | 0.25 |
| IoU threshold | 0.5 |
| Latency batch size | 1 (real serving scenario) |
| Warmup iterations | 50 (excluded from measurements) |
| Measured iterations | 200 |
| GPU synchronization | `torch.cuda.synchronize()` before AND after each iteration |
| Latency measured via | `Detector.predict()` interface (production path) |
| Breakdown source | `model.predictor.speed` (Ultralytics per-stage timing) |
| Models measured | sequentially (never in parallel) |
| GPU at measurement | NVIDIA GeForce RTX 5090 |
| PyTorch | 2.11.0+cu130 |
| Ultralytics | 8.4.33 |
| CUDA | 13.0 |

> **Reproducibility**: detection metrics are deterministic given the same split, thresholds, and weights.
> Latency measurements have natural variance (std reported); two runs should agree within ~2x std.

## 5. Limitations & Honesty

This section is required for result credibility.

- **Evaluation split**: The `val` split was used for early-stopping (patience=50) during training.
  Metrics reported here are therefore slightly optimistic for both models.
  A held-out `test` split does not exist in the current DsPCBSD+ download.

- **Identical hyperparameters**: Ultralytics default hyperparameters are tuned for YOLO-family
  architectures. Applying them unchanged to RT-DETR is the fairest equal-budget comparison,
  but it mechanically advantages YOLO.

- **Training schedule**: 150 epochs with patience=50 is a comfortable budget for a CNN like
  YOLOv11s, and more constrained for a transformer. RT-DETR-l reached its best checkpoint at
  epoch 52 then plateaued — we cannot distinguish 'true ceiling on this dataset' from 'schedule
  not adapted to transformer convergence dynamics' with the available data.

- **Batch size**: batch=8 was used for both models. This intentionally limits YOLO (which can
  benefit from larger batches) but is also small for a transformer.

- **Not explored** (out of budget): partial backbone freeze for HGNet, extended schedule,
  model-specific learning rate tuning, TensorRT export.

- **GPU clock state**: clocks were not explicitly locked during latency measurement. Reported
  std captures this variance.

**Conclusion to state precisely**: *Under equal training budget and non-specialized hyperparameters,
RT-DETR-l under-performs YOLOv11s on DsPCBSD+. This is not a verdict on the architecture in
absolute terms.*

## 6. Engineering Decision

**YOLOv11s goes to production.**

YOLOv11s achieves mAP50=0.8493 vs RT-DETR-l's 0.8179 (+0.031)
at 33.22 ms p50 latency vs 133.035 ms, 9.5M params vs 33.0M.
Under equal training budget and shared hyperparameters, YOLOv11s delivers better accuracy,
lower latency, and 3.5x fewer parameters — an unambiguous cost/benefit advantage for a
PCB inspection API where real-time throughput and deployment footprint matter.
