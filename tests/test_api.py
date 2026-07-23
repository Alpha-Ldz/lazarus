"""Tests for FastAPI endpoints — no real model required."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.main import app


@pytest.fixture()
def client() -> TestClient:
    """TestClient with no detector loaded (simulates CI environment)."""
    with TestClient(app, raise_server_exceptions=True) as c:
        # Force detector to None to test degraded behaviour
        app.state.detector = None
        yield c


class TestHealth:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_exposes_detector_state(self, client: TestClient) -> None:
        response = client.get("/health")
        body = response.json()
        assert "detector_loaded" in body
        assert body["detector_loaded"] is False


class TestAnalyzeWithoutDetector:
    def _make_image_bytes(self) -> bytes:
        img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_analyze_returns_503_when_no_detector(self, client: TestClient) -> None:
        image_bytes = self._make_image_bytes()
        response = client.post(
            "/api/analyze/",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert response.status_code == 503
