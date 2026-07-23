"""Tests for anomaly_bbox coordinate scaling and blob filtering."""

from __future__ import annotations

import numpy as np
import pytest

from apps.api.detectors.anomaly_bbox import MIN_BLOB_AREA_RATIO, anomaly_map_to_detections


def _blank_map(h: int, w: int) -> np.ndarray:
    return np.zeros((h, w), dtype=np.float32)


class TestCoordinateScaling:
    """The bug most likely in this module: coordinates must scale to original image size."""

    def test_full_image_blob_scales_to_orig_size(self) -> None:
        """A blob covering the entire heatmap should cover the entire original image."""
        map_h, map_w = 256, 256
        orig_w, orig_h = 1280, 720

        anomaly_map = np.ones((map_h, map_w), dtype=np.float32)
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=orig_w, orig_height=orig_h)

        assert len(detections) == 1
        det = detections[0]
        assert det.bbox[0] == pytest.approx(0.0)
        assert det.bbox[1] == pytest.approx(0.0)
        assert det.bbox[2] == pytest.approx(float(orig_w))
        assert det.bbox[3] == pytest.approx(float(orig_h))

    def test_half_image_blob_scales_correctly(self) -> None:
        """A blob in the top-left quadrant of the heatmap should map to top-left of orig image."""
        map_h, map_w = 256, 256
        orig_w, orig_h = 640, 480

        anomaly_map = _blank_map(map_h, map_w)
        # Fill top-left quadrant
        anomaly_map[: map_h // 2, : map_w // 2] = 1.0
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=orig_w, orig_height=orig_h)

        assert len(detections) == 1
        det = detections[0]
        assert det.bbox[0] == pytest.approx(0.0)
        assert det.bbox[1] == pytest.approx(0.0)
        assert det.bbox[2] == pytest.approx(orig_w / 2, rel=0.01)
        assert det.bbox[3] == pytest.approx(orig_h / 2, rel=0.01)

    def test_non_square_orig_scales_independently_per_axis(self) -> None:
        """x and y scales must be computed independently."""
        map_h, map_w = 256, 256
        orig_w, orig_h = 1920, 480  # 4:1 aspect ratio

        anomaly_map = _blank_map(map_h, map_w)
        # Single pixel blob at center
        cx, cy = map_w // 2, map_h // 2
        anomaly_map[cy, cx] = 1.0  # will be filtered unless area ≥ min

        # Use a 32×32 blob at center to ensure it passes the area filter
        r = 16
        anomaly_map[cy - r : cy + r, cx - r : cx + r] = 1.0
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=orig_w, orig_height=orig_h)

        assert len(detections) == 1
        det = detections[0]
        # x scale = 1920/256 = 7.5, y scale = 480/256 = 1.875
        expected_x1 = (cx - r) * (orig_w / map_w)
        expected_y1 = (cy - r) * (orig_h / map_h)
        expected_x2 = (cx + r) * (orig_w / map_w)
        expected_y2 = (cy + r) * (orig_h / map_h)
        assert det.bbox[0] == pytest.approx(expected_x1, rel=0.02)
        assert det.bbox[1] == pytest.approx(expected_y1, rel=0.02)
        assert det.bbox[2] == pytest.approx(expected_x2, rel=0.02)
        assert det.bbox[3] == pytest.approx(expected_y2, rel=0.02)

    def test_identity_scale_when_map_equals_orig(self) -> None:
        """When map size == original image size, coordinates must not change."""
        size = 256
        anomaly_map = _blank_map(size, size)
        anomaly_map[10:50, 20:80] = 1.0

        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=size, orig_height=size)
        assert len(detections) == 1
        det = detections[0]
        assert det.bbox[0] == pytest.approx(20.0, rel=0.01)
        assert det.bbox[1] == pytest.approx(10.0, rel=0.01)
        assert det.bbox[2] == pytest.approx(80.0, rel=0.01)
        assert det.bbox[3] == pytest.approx(50.0, rel=0.01)


class TestBlobFiltering:
    def test_tiny_blob_filtered_out(self) -> None:
        """A single pixel blob (< MIN_BLOB_AREA_RATIO of image area) should be filtered."""
        anomaly_map = _blank_map(256, 256)
        anomaly_map[128, 128] = 1.0  # single pixel, way below threshold
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=256, orig_height=256)
        assert detections == []

    def test_large_blob_kept(self) -> None:
        """A blob covering 10% of image should pass the filter."""
        map_h, map_w = 256, 256
        anomaly_map = _blank_map(map_h, map_w)
        # 64×64 = 4096 pixels, 4096/(256*256) = 6.25% > 0.05%
        anomaly_map[96:160, 96:160] = 1.0
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=map_w, orig_height=map_h)
        assert len(detections) == 1

    def test_multiple_blobs(self) -> None:
        """Two separate large blobs should produce two detections."""
        anomaly_map = _blank_map(256, 256)
        anomaly_map[10:50, 10:50] = 1.0
        anomaly_map[180:230, 180:230] = 1.0
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=256, orig_height=256)
        assert len(detections) == 2


class TestConfidence:
    def test_class_name_is_anomaly(self) -> None:
        anomaly_map = np.ones((256, 256), dtype=np.float32)
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.5, orig_width=256, orig_height=256)
        assert len(detections) == 1
        assert detections[0].class_name == "anomaly"
        assert detections[0].class_id == 0

    def test_confidence_in_unit_interval(self) -> None:
        anomaly_map = np.random.default_rng(42).random((256, 256)).astype(np.float32)
        detections = anomaly_map_to_detections(anomaly_map, threshold=0.3, orig_width=512, orig_height=512)
        for det in detections:
            assert 0.0 <= det.confidence <= 1.0
