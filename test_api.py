"""
VisionMate AI — Basic API Tests
Run with:  python -m pytest tests/ -v
"""

import io
import sys
import os
import pytest

# Make sure parent dir is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "version" in data


# ── Home page ─────────────────────────────────────────────────────────────────

def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"VisionMate" in r.data


# ── No image supplied ─────────────────────────────────────────────────────────

def test_detect_no_image(client):
    r = client.post("/api/detect")
    assert r.status_code in (400, 500)
    data = r.get_json()
    assert data["success"] is False


def test_read_text_no_image(client):
    r = client.post("/api/read-text")
    assert r.status_code in (400, 500)
    data = r.get_json()
    assert data["success"] is False


def test_medicine_no_image(client):
    r = client.post("/api/identify-medicine")
    assert r.status_code in (400, 500)
    data = r.get_json()
    assert data["success"] is False


def test_bus_no_image(client):
    r = client.post("/api/identify-bus")
    assert r.status_code in (400, 500)
    data = r.get_json()
    assert data["success"] is False


# ── Bad file type ─────────────────────────────────────────────────────────────

def test_detect_bad_filetype(client):
    fake_file = (io.BytesIO(b"not an image"), "test.txt")
    r = client.post(
        "/api/detect",
        data={"image": fake_file},
        content_type="multipart/form-data",
    )
    assert r.status_code in (400, 500)
    data = r.get_json()
    assert data["success"] is False


# ── With a minimal valid PNG ───────────────────────────────────────────────────
# A 1x1 white PNG (smallest valid PNG)
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_detect_tiny_image(client):
    fake_file = (io.BytesIO(TINY_PNG), "tiny.png")
    r = client.post(
        "/api/detect",
        data={"image": fake_file},
        content_type="multipart/form-data",
    )
    # Should succeed (models may or may not detect anything, but no crash)
    data = r.get_json()
    assert "success" in data


def test_read_text_tiny_image(client):
    fake_file = (io.BytesIO(TINY_PNG), "tiny.png")
    r = client.post(
        "/api/read-text",
        data={"image": fake_file},
        content_type="multipart/form-data",
    )
    data = r.get_json()
    assert "success" in data


def test_medicine_tiny_image(client):
    fake_file = (io.BytesIO(TINY_PNG), "tiny.png")
    r = client.post(
        "/api/identify-medicine",
        data={"image": fake_file},
        content_type="multipart/form-data",
    )
    data = r.get_json()
    assert "success" in data
    if data["success"]:
        assert "safety" in data   # safety notice must always be present


def test_bus_tiny_image(client):
    fake_file = (io.BytesIO(TINY_PNG), "tiny.png")
    r = client.post(
        "/api/identify-bus",
        data={"image": fake_file},
        content_type="multipart/form-data",
    )
    data = r.get_json()
    assert "success" in data
    if data["success"]:
        assert "disclaimer" in data   # disclaimer must always be present
