import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_archive_endpoint_validation():
    # Test invalid URL format
    response = client.post("/api/v1/archive", json={"url": "not-a-valid-url"})
    assert response.status_code == 422

    # Test empty URL
    response = client.post("/api/v1/archive", json={"url": ""})
    assert response.status_code == 422


def test_archive_endpoint_structure():
    test_target = "https://www.ft.com/content/e9027253-e13c-460a-a4b1-f9047e5a6ca7"
    response = client.post("/api/v1/archive", json={"url": test_target})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_target
    assert "archive_url" in data
    assert "status" in data
    assert "domain_used" in data
    print("Archive endpoint response:", data)


def test_archive_shortcut_endpoint():
    test_target = "https://www.ft.com/content/e9027253-e13c-460a-a4b1-f9047e5a6ca7"
    response = client.post("/archive", json={"url": test_target})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_target
    assert data["archive_url"].startswith("http")
    print("Archive shortcut response:", data)
