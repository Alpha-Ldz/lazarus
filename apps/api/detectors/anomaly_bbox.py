"""Adaptateur anomaly_map → list[Detection].

Fonction pure, sans dépendance à Anomalib : prend un np.ndarray + un seuil,
retourne des Detection avec coordonnées à l'échelle de l'image d'origine.
"""

from __future__ import annotations

import numpy as np

from .base import Detection

# Surface minimale d'un blob : 0,05 % de l'aire de l'image
MIN_BLOB_AREA_RATIO: float = 0.0005


def anomaly_map_to_detections(
    anomaly_map: np.ndarray,
    threshold: float,
    orig_width: int,
    orig_height: int,
) -> list[Detection]:
    """Convert an anomaly heatmap to a list of Detection bounding boxes.

    Args:
        anomaly_map: Float array (H, W) with anomaly scores in [0, 1] or raw scores.
        threshold: Binarisation threshold. Pixels above → anomaly.
        orig_width: Width of the original image (for coordinate rescaling).
        orig_height: Height of the original image (for coordinate rescaling).

    Returns:
        List of Detection objects with bbox in original image coordinates.
    """
    import cv2

    map_h, map_w = anomaly_map.shape[:2]
    min_blob_pixels = max(1, int(MIN_BLOB_AREA_RATIO * map_h * map_w))

    # Normalise map to [0, 1] for confidence scoring
    map_min, map_max = float(anomaly_map.min()), float(anomaly_map.max())
    if map_max > map_min:
        normalised = (anomaly_map - map_min) / (map_max - map_min)
    else:
        normalised = np.zeros_like(anomaly_map, dtype=np.float32)

    # Binarise
    binary = (anomaly_map >= threshold).astype(np.uint8)

    # Connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    detections: list[Detection] = []
    scale_x = orig_width / map_w
    scale_y = orig_height / map_h

    for label_id in range(1, num_labels):  # 0 = background
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area < min_blob_pixels:
            continue

        x1_map = int(stats[label_id, cv2.CC_STAT_LEFT])
        y1_map = int(stats[label_id, cv2.CC_STAT_TOP])
        w_map = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h_map = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        x2_map = x1_map + w_map
        y2_map = y1_map + h_map

        # Max score within the blob (normalised) as confidence
        blob_mask = labels == label_id
        confidence = float(normalised[blob_mask].max())

        # Rescale to original image coordinates
        x1 = x1_map * scale_x
        y1 = y1_map * scale_y
        x2 = x2_map * scale_x
        y2 = y2_map * scale_y

        detections.append(
            Detection(
                class_id=0,
                class_name="anomaly",
                confidence=round(confidence, 4),
                bbox=[round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            )
        )

    return detections
