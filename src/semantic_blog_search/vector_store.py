from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)


class VectorStore:
    """Read and write vectors with Qdrant local mode."""

    def __init__(self, db_path: str, collection_name: str, vector_size: int):
        self.client = QdrantClient(path=db_path)
        self.collection_name = collection_name
        self.vector_size = vector_size

    def ensure_collection(self):
        """Create the collection if it does not exist."""
        if self._collection_exists():
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    def recreate_collection(self):
        """Drop and recreate the collection for a full rebuild."""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    def upsert_chunks(
        self,
        chunks: list[dict],
        vectors: list[list[float]],
        content_hash: str | None = None,
    ):
        """Store chunk payloads and vectors in Qdrant."""
        points = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "chunk_id": chunk["chunk_id"],
                "title": chunk["title"],
                "url": chunk["url"],
                "tags": chunk["tags"],
                "source_file": chunk["source_file"],
                "snippet": _make_snippet(chunk["text"]),
                "chunk_index": chunk["chunk_index"],
            }
            if content_hash is not None:
                payload["content_hash"] = content_hash

            points.append(
                PointStruct(
                    id=_point_id_from_chunk_id(chunk["chunk_id"]),
                    vector=vector,
                    payload=payload,
                )
            )

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

    def delete_by_source_file(self, source_file: str):
        """Delete all chunks that came from one Markdown file."""
        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file),
                        )
                    ]
                )
            ),
        )

    def delete_by_chunk_ids(self, chunk_ids: list[str]):
        """Delete chunks by their stable chunk IDs."""
        if not chunk_ids:
            return

        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=[_point_id_from_chunk_id(chunk_id) for chunk_id in chunk_ids]
            ),
        )

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        """Search Qdrant and return payloads with scores."""
        self.ensure_collection()
        hits = self._search_points(query_vector, top_k)
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "title": payload.get("title", ""),
                    "url": payload.get("url", ""),
                    "score": float(hit.score),
                    "snippet": payload.get("snippet", ""),
                    "source_file": payload.get("source_file", ""),
                }
            )
        return results

    def _collection_exists(self) -> bool:
        if hasattr(self.client, "collection_exists"):
            return bool(self.client.collection_exists(self.collection_name))

        collections = self.client.get_collections().collections
        return any(item.name == self.collection_name for item in collections)

    def _search_points(self, query_vector: list[float], top_k: int):
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            return response.points

        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )


def _make_snippet(text: str, max_length: int = 180) -> str:
    snippet = text.replace("\n", " ").strip()
    if len(snippet) <= max_length:
        return snippet
    return snippet[:max_length].rstrip() + "..."


def _point_id_from_chunk_id(chunk_id: str) -> int:
    return int(chunk_id[:16], 16)
