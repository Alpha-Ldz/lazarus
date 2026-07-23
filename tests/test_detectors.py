"""Tests for detector factory and Detection contract."""

from __future__ import annotations

import os

import pytest

from apps.api.detectors.base import Detection


class TestDetectionModel:
    """Detection Pydantic model validates and rejects correctly."""

    def test_valid_detection(self) -> None:
        det = Detection(class_id=0, class_name="short", confidence=0.85, bbox=[10.0, 20.0, 50.0, 60.0])
        assert det.confidence == pytest.approx(0.85)
        assert len(det.bbox) == 4

    def test_rejects_confidence_above_one(self) -> None:
        with pytest.raises(Exception):
            Detection(class_id=0, class_name="short", confidence=1.5, bbox=[0, 0, 10, 10])

    def test_rejects_negative_confidence(self) -> None:
        with pytest.raises(Exception):
            Detection(class_id=0, class_name="short", confidence=-0.1, bbox=[0, 0, 10, 10])


class TestBuildDetectorUnknownType:
    def test_unknown_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="inconnu"):
            original = os.environ.get("LAZARUS_DETECTOR")
            os.environ["LAZARUS_DETECTOR"] = "does_not_exist"
            try:
                from apps.api.detectors.factory import build_detector

                build_detector()
            finally:
                if original is None:
                    os.environ.pop("LAZARUS_DETECTOR", None)
                else:
                    os.environ["LAZARUS_DETECTOR"] = original


@pytest.mark.requires_weights
class TestBuildDetectorWithWeights:
    """These tests require model weights — skipped in CI."""

    def test_yolo_returns_detector(self) -> None:
        from apps.api.detectors.base import Detector
        from apps.api.detectors.factory import build_detector

        detector = build_detector()
        assert isinstance(detector, Detector)

    def test_rtdetr_returns_detector(self) -> None:
        import os

        from apps.api.detectors.base import Detector
        from apps.api.detectors.factory import build_detector

        os.environ["LAZARUS_DETECTOR"] = "rtdetr"
        try:
            detector = build_detector()
            assert isinstance(detector, Detector)
        finally:
            os.environ.pop("LAZARUS_DETECTOR", None)
