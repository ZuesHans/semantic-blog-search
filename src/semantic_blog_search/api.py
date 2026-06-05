from fastapi import FastAPI, Header, HTTPException, Query, status

from semantic_blog_search.searcher import SearchService


def create_app(config: dict, search_service: SearchService | None = None) -> FastAPI:
    """Create the FastAPI app and load the search service once."""
    app = FastAPI(title="semantic-blog-search")
    search_service = search_service or SearchService(config)
    api_token = _load_api_token(config)

    @app.get("/health")
    def health():
        return search_service.health()

    @app.get("/search")
    def search(
        q: str = Query(..., min_length=1),
        top_k: int | None = Query(default=None, ge=1, le=50),
        authorization: str | None = Header(default=None),
    ):
        _require_bearer_token(authorization, api_token)

        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="q cannot be empty")

        return {
            "query": query,
            "results": search_service.search(query=query, top_k=top_k),
        }

    return app


def _load_api_token(config: dict) -> str:
    token = str(config.get("server", {}).get("api_token", "")).strip()
    if not token:
        raise ValueError("Missing server.api_token in config.yaml")
    if token == "change-this-token-before-deploy":
        raise ValueError("Please change server.api_token before starting the API server")
    return token


def _require_bearer_token(authorization: str | None, api_token: str):
    expected = f"Bearer {api_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
