import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from tqdm import tqdm

from semantic_blog_search.chunker import chunk_post
from semantic_blog_search.embedder import Embedder
from semantic_blog_search.parser import parse_markdown_file
from semantic_blog_search.vector_store import VectorStore


class SupportsVectorStore(Protocol):
    def ensure_collection(self): ...

    def delete_by_source_file(self, source_file: str): ...

    def delete_by_chunk_ids(self, chunk_ids: list[str]): ...

    def upsert_chunks(
        self,
        chunks: list[dict],
        vectors: list[list[float]],
        content_hash: str | None = None,
    ): ...


class SupportsEmbedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def sync_index(config: dict) -> dict:
    """Incrementally sync Markdown posts into Qdrant."""
    posts_dir = Path(config["posts_dir"]).expanduser()
    if not posts_dir.exists():
        raise FileNotFoundError(
            f"posts_dir does not exist: {posts_dir}. "
            "Please edit posts_dir in config.yaml."
        )

    embedding_config = config.get("embedding", {})
    model_name = embedding_config.get("model_name", "BAAI/bge-small-zh-v1.5")
    embedder = Embedder(model_name)

    qdrant_config = config.get("qdrant", {})
    store = VectorStore(
        db_path=qdrant_config.get("db_path", "./data/qdrant"),
        collection_name=qdrant_config.get("collection_name", "blog_chunks"),
        vector_size=embedder.get_vector_size(),
    )

    index_config = config.get("index", {})
    manifest_path = index_config.get("manifest_path", "./data/index_manifest.json")

    return sync_index_with_services(
        config=config,
        embedder=embedder,
        store=store,
        manifest_path=manifest_path,
    )


def sync_index_with_services(
    config: dict,
    embedder: SupportsEmbedder,
    store: SupportsVectorStore,
    manifest_path: str,
) -> dict:
    """Sync index with injected services so the behavior is easy to test."""
    posts_dir = Path(config["posts_dir"]).expanduser()
    url_prefix = config.get("url_prefix", "/posts")

    chunk_config = config.get("chunk", {})
    chunk_size = int(chunk_config.get("chunk_size", 700))
    chunk_overlap = int(chunk_config.get("chunk_overlap", 120))
    split_heading_max_level = int(chunk_config.get("split_heading_max_level", 4) or 0)
    include_heading_path = bool(chunk_config.get("include_heading_path", True))

    manifest = load_manifest(manifest_path)
    known_files = set(manifest.get("posts", {}).keys())
    current_files = {
        str(path): path
        for path in sorted(posts_dir.rglob("*.md"))
    }

    summary = {
        "added": 0,
        "changed": 0,
        "deleted": 0,
        "skipped": 0,
        "total_current": len(current_files),
    }

    store.ensure_collection()

    for source_file in sorted(known_files - set(current_files.keys())):
        old_entry = manifest["posts"].pop(source_file)
        chunk_ids = old_entry.get("chunk_ids", [])
        store.delete_by_chunk_ids(chunk_ids)
        summary["deleted"] += 1

    for source_file, markdown_path in tqdm(
        current_files.items(),
        desc="Syncing posts",
    ):
        content_hash = calculate_file_hash(markdown_path)
        old_entry = manifest["posts"].get(source_file)

        if old_entry and old_entry.get("content_hash") == content_hash:
            summary["skipped"] += 1
            continue

        if old_entry:
            store.delete_by_source_file(source_file)
            summary["changed"] += 1
        else:
            summary["added"] += 1

        post = parse_markdown_file(markdown_path, url_prefix=url_prefix)
        chunks = chunk_post(
            post,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            split_heading_max_level=split_heading_max_level,
            include_heading_path=include_heading_path,
        )
        vectors = embedder.encode([chunk["text"] for chunk in chunks])
        store.upsert_chunks(chunks, vectors, content_hash=content_hash)

        manifest["posts"][source_file] = {
            "source_file": source_file,
            "content_hash": content_hash,
            "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

    save_manifest(manifest_path, manifest)
    return summary


def load_manifest(path: str) -> dict:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {"version": 1, "posts": {}}

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    manifest.setdefault("version", 1)
    manifest.setdefault("posts", {})
    return manifest


def save_manifest(path: str, manifest: dict):
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)


def calculate_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
