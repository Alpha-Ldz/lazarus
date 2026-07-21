"""Détecteurs de défauts PCB — package public."""

from .base import Detection, DetectionResult, Detector
from .factory import build_detector

__all__ = ["Detection", "DetectionResult", "Detector", "build_detector"]
