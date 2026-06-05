from semantic_blog_search.embedder import Embedder
from semantic_blog_search.vector_store import VectorStore


class SearchService:
    """Reusable search service that keeps the embedding model in memory."""

    def __init__(self, config: dict):
        self.config = config

        embedding_config = config.get("embedding", {})
        model_name = embedding_config.get("model_name", "BAAI/bge-small-zh-v1.5")
        self.embedder = Embedder(model_name)

        qdrant_config = config.get("qdrant", {})
        self.collection_name = qdrant_config.get("collection_name", "blog_chunks")
        self.store = VectorStore(
            db_path=qdrant_config.get("db_path", "./data/qdrant"),
            collection_name=self.collection_name,
            vector_size=self.embedder.get_vector_size(),
        )
        self.store.ensure_collection()

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """Search indexed blog chunks with a natural language query."""
        search_config = self.config.get("search", {})
        final_top_k = int(top_k or search_config.get("top_k", 5))

        query_vector = self.embedder.encode([query])[0]
        return self.store.search(query_vector=query_vector, top_k=final_top_k)

    def health(self) -> dict:
        """Return a small health payload for the API server."""
        return {
            "status": "ok",
            "collection_name": self.collection_name,
        }


def search(config: dict, query: str, top_k: int | None = None) -> list[dict]:
    """Convenience function for one-off command line searches."""
    service = SearchService(config)
    return service.search(query=query, top_k=top_k)
