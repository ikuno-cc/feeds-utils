import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.archiver import extract_single_archive_url

client = TestClient(app)

def test_extract_single_archive_url_parser():
    mock_html = """
    <html>
    <body>
        <div>
            <span>List of URLs, ordered from newer to older</span>
            <a href="https://archive.ph/H6GcX">
                <img src="/thumb/2 Aug 2026 19:10">
            </a>
            <a href="https://archive.ph/K9YzW">
                <img src="/thumb/3 Aug 2026 09:55">
            </a>
        </div>
    </body>
    </html>
    """
    shortlink = extract_single_archive_url(mock_html, "archive.ph")
    assert shortlink == "https://archive.ph/H6GcX"


def test_archive_endpoint_validation():
    response = client.post("/api/v1/archive", json={"url": "not-a-valid-url"})
    assert response.status_code == 422

    response = client.post("/api/v1/archive", json={"url": ""})
    assert response.status_code == 422


def test_archive_endpoint_structure():
    test_target = "https://www.ft.com/content/e9027253-e13c-460a-a4b1-f9047e5a6ca7"
    response = client.post("/api/v1/archive", json={"url": test_target})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_target
    assert data["archive_url"] == "https://archive.ph/H6GcX"
    assert data["status"] == "success"
    assert data["domain_used"] == "archive.ph"
    print("Archive endpoint response:", data)


def test_archive_shortcut_endpoint():
    test_target = "https://www.ft.com/content/e9027253-e13c-460a-a4b1-f9047e5a6ca7"
    response = client.post("/archive", json={"url": test_target})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_target
    assert data["archive_url"] == "https://archive.ph/H6GcX"
    assert data["status"] == "success"
    print("Archive shortcut response:", data)
