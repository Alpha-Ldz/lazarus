# Model Cards

---

## YOLOv11s — DsPCBSD+

**Role:** Primary production detector (EPIC A default).

| Property | Value |
|----------|-------|
| Architecture | YOLOv11s (Ultralytics 8.4.33) |
| Dataset | DsPCBSD+ — 10 259 images, 9 defect classes, CC BY 4.0 |
| Training split | train / early-stop on val (patience=50, 150 epochs) |
| Image size | 640 × 640 |
| Parameters | 9.5 M |
| Weights file | `ml/runs/detect/dspcbsd_yolo11_bench6/weights/best.pt` (18 MB) |

**Metrics (DsPCBSD+ val):**

| mAP@50 | mAP@50-95 | Precision | Recall | Latency p50 | Throughput |
|--------|-----------|-----------|--------|-------------|------------|
| 0.849 | 0.550 | 0.821 | 0.815 | 33 ms (PyTorch) · 27 ms (ONNX) | 30 img/s |

**Weakest classes:** `conductor_foreign_object` (mAP50=0.707), `conductor_scratch` (0.771) — both have fewer training examples relative to their visual variability.

**Intended use:** Real-time inspection of PCB images via the `/api/analyze` endpoint. Results are passed to an LLM for repair-sheet generation.

**Known limits:**
- Trained and evaluated on the same split (val used for early stopping) → metrics are slightly optimistic.
- Not evaluated on PCB types outside DsPCBSD+.
- Confidence threshold 0.25; lower threshold reduces false negatives at the cost of more false positives.

---

## RT-DETR-l — DsPCBSD+ (challenger)

**Role:** Benchmarked challenger. Integrated via `RtdetrDetector`; selectable at runtime.

| Property | Value |
|----------|-------|
| Architecture | RT-DETR-l (Ultralytics 8.4.33, NMS-free transformer) |
| Dataset | DsPCBSD+ — same split as YOLOv11s |
| Training | 150 epochs, patience=50, identical hyperparameters to YOLOv11s |
| Image size | 640 × 640 |
| Parameters | 33.0 M |
| Weights file | `ml/runs/detect/dspcbsd_rtdetr_bench5/weights/best.pt` (63 MB) |

**Metrics (DsPCBSD+ val):**

| mAP@50 | mAP@50-95 | Precision | Recall | Latency p50 | Throughput |
|--------|-----------|-----------|--------|-------------|------------|
| 0.818 | 0.522 | 0.832 | 0.778 | 133 ms (PyTorch) · 98 ms (ONNX) | 7.5 img/s |

**Result vs YOLOv11s:** −3.1 pp mAP@50, 4× slower, 3.5× more parameters.

**Weakest class:** `conductor_scratch` (mAP50=0.661, −11 pp vs YOLOv11s).

**Intended use:** Available as a swappable alternative for scenarios where higher precision at lower throughput is acceptable, or for further architecture-specific tuning.

**Known limits:**
- Best checkpoint reached at epoch 52; plateau suggests the 150-epoch budget or default hyperparameters may not be optimal for this transformer on this dataset.
- Postprocessing is NMS-free (architectural advantage), but inference dominates latency regardless.
- Same evaluation-split caveat as YOLOv11s.

---

## PatchCore — VisA PCB

**Role:** Unsupervised anomaly detector (EPIC C). No defect labels required.

| Property | Value |
|----------|-------|
| Architecture | PatchCore (Anomalib) |
| Dataset | VisA PCB — pcb1, pcb2, pcb3, pcb4 categories |
| Training paradigm | Fit on defect-free images only (no annotations) |
| Resolution | 256 × 256 (Anomalib default) |
| Weights | `ml/runs/patchcore/pcb{1..4}/weights/torch/model.pt` |

**Metrics:** Not available — model ran as dry-run (no inference executed). See `ml/runs/anomaly_results.json`.

**Dataset note:** VisA PCB is a **different dataset** from DsPCBSD+. Direct metric comparison between PatchCore and the supervised models is not valid.

**Intended use:** Inspection scenarios where labelled defect data is unavailable. Returns a pixel-level anomaly score map rather than bounding boxes with class labels. Suitable for new PCB types where annotation cost is prohibitive.

**Known limits:**
- No real inference metrics available at this stage.
- Does not distinguish defect classes — reports "anomaly" only.
- Resolution mismatch with supervised models (256 vs 640) — not comparable at the image level.
- Integration in the `Detector` interface is structural only; the anomaly score must be thresholded to produce a binary detection result.
