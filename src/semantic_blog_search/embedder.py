from sentence_transformers import SentenceTransformer


class Embedder:
    """Small wrapper around sentence-transformers."""

    def __init__(self, model_name: str):
        # 模型第一次加载时会自动下载到本地缓存。
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts into normalized embedding vectors."""
        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return vectors.tolist()

    def get_vector_size(self) -> int:
        """Return the embedding vector size for the loaded model."""
        return int(self.model.get_sentence_embedding_dimension())
