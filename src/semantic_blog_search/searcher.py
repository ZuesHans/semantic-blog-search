import re

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
        hybrid_enabled = bool(search_config.get("hybrid_enabled", True))

        query_vector = self.embedder.encode([query])[0]
        if not hybrid_enabled:
            return self.store.search(query_vector=query_vector, top_k=final_top_k)

        candidate_limit = _candidate_limit(search_config, final_top_k)
        candidates = self.store.search_candidates(
            query_vector=query_vector,
            limit=candidate_limit,
        )
        return _rerank_hybrid(query, candidates, search_config)[:final_top_k]

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


def _candidate_limit(search_config: dict, top_k: int) -> int:
    multiplier = int(search_config.get("hybrid_candidate_multiplier", 4))
    configured_limit = int(search_config.get("hybrid_candidate_limit", 30))
    return max(top_k, min(max(top_k * multiplier, top_k), configured_limit))


def _rerank_hybrid(query: str, candidates: list[dict], search_config: dict) -> list[dict]:
    keyword_weight = float(search_config.get("hybrid_keyword_weight", 0.25))
    reranked = []
    for rank, candidate in enumerate(candidates):
        semantic_score = float(candidate.get("score", 0.0))
        keyword_score = _keyword_score(query, candidate)
        final_score = semantic_score + keyword_weight * keyword_score
        result = {
            "title": candidate.get("title", ""),
            "url": candidate.get("url", ""),
            "score": final_score,
            "snippet": candidate.get("snippet", ""),
            "source_file": candidate.get("source_file", ""),
        }
        reranked.append((final_score, semantic_score, -rank, result))

    reranked.sort(reverse=True, key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in reranked]


def _keyword_score(query: str, candidate: dict) -> float:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return 0.0

    title = _normalize_text(candidate.get("title", ""))
    tags = _normalize_text(" ".join(candidate.get("tags", [])))
    heading_path = _normalize_text(candidate.get("heading_path", ""))
    text = _normalize_text(candidate.get("text", candidate.get("snippet", "")))

    score = 0.0
    if normalized_query in title:
        score += 0.45
    if normalized_query in tags:
        score += 0.35
    if normalized_query in heading_path:
        score += 0.40
    if normalized_query in text:
        score += 0.30

    terms = _query_terms(normalized_query)
    if terms:
        score += 0.20 * _term_coverage(terms, title)
        score += 0.15 * _term_coverage(terms, tags)
        score += 0.20 * _term_coverage(terms, heading_path)
        score += 0.15 * _term_coverage(terms, text)

    grams = _char_ngrams(normalized_query, n=2)
    if grams:
        score += 0.20 * _gram_coverage(grams, title)
        score += 0.20 * _gram_coverage(grams, heading_path)
        score += 0.10 * _gram_coverage(grams, text)

    return min(score, 1.0)


def _normalize_text(value: object) -> str:
    text = str(value or "").lower()
    return re.sub(r"\s+", " ", text).strip()


def _query_terms(normalized_query: str) -> list[str]:
    terms = [term for term in re.split(r"[\s,，。；;：:、/\\|()\[\]{}<>]+", normalized_query) if term]
    if normalized_query and normalized_query not in terms:
        terms.append(normalized_query)
    return terms


def _term_coverage(terms: list[str], text: str) -> float:
    if not terms or not text:
        return 0.0
    hits = sum(1 for term in terms if term in text)
    return hits / len(terms)


def _char_ngrams(text: str, n: int) -> set[str]:
    compact = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    if len(compact) < n:
        return set()
    return {compact[index : index + n] for index in range(0, len(compact) - n + 1)}


def _gram_coverage(query_grams: set[str], text: str) -> float:
    if not query_grams or not text:
        return 0.0
    text_grams = _char_ngrams(text, n=2)
    if not text_grams:
        return 0.0
    return len(query_grams & text_grams) / len(query_grams)
