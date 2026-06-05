import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.api import create_app


class FakeSearchService:
    def health(self):
        return {
            "status": "ok",
            "collection_name": "blog_chunks",
        }

    def search(self, query, top_k=None):
        return [
            {
                "title": "Test",
                "url": "/posts/test",
                "score": 0.9,
                "snippet": query,
                "source_file": "sample.md",
            }
        ]


def test_health_does_not_require_token():
    client = TestClient(create_app(_config(), search_service=FakeSearchService()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_rejects_missing_token():
    client = TestClient(create_app(_config(), search_service=FakeSearchService()))

    response = client.get("/search", params={"q": "hello"})

    assert response.status_code == 401


def test_search_accepts_bearer_token():
    client = TestClient(create_app(_config(), search_service=FakeSearchService()))

    response = client.get(
        "/search",
        params={"q": "hello", "top_k": 3},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["snippet"] == "hello"


def test_app_requires_non_default_token():
    try:
        create_app({"server": {"api_token": "change-this-token-before-deploy"}}, search_service=FakeSearchService())
    except ValueError as error:
        assert "change server.api_token" in str(error)
    else:
        raise AssertionError("create_app should reject the default token")


def _config():
    return {
        "server": {
            "api_token": "test-token",
        }
    }
