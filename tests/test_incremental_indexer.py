import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.incremental_indexer import (
    load_manifest,
    save_manifest,
    sync_index_with_services,
)


class FakeEmbedder:
    def encode(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeStore:
    def __init__(self):
        self.upserts = []
        self.deleted_sources = []
        self.deleted_chunk_ids = []

    def ensure_collection(self):
        pass

    def delete_by_source_file(self, source_file):
        self.deleted_sources.append(source_file)

    def delete_by_chunk_ids(self, chunk_ids):
        self.deleted_chunk_ids.extend(chunk_ids)

    def upsert_chunks(self, chunks, vectors, content_hash=None):
        self.upserts.append(
            {
                "chunks": chunks,
                "vectors": vectors,
                "content_hash": content_hash,
            }
        )


def test_sync_index_skips_unchanged_file(tmp_path):
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    post_path = posts_dir / "sample.md"
    post_path.write_text("---\ntitle: Test\n---\n\nhello", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    first_store = FakeStore()
    config = _config(posts_dir)
    sync_index_with_services(config, FakeEmbedder(), first_store, str(manifest_path))

    second_store = FakeStore()
    summary = sync_index_with_services(config, FakeEmbedder(), second_store, str(manifest_path))

    assert summary["skipped"] == 1
    assert second_store.upserts == []


def test_sync_index_reindexes_changed_file(tmp_path):
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    post_path = posts_dir / "sample.md"
    post_path.write_text("---\ntitle: Test\n---\n\nhello", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    config = _config(posts_dir)
    sync_index_with_services(config, FakeEmbedder(), FakeStore(), str(manifest_path))

    post_path.write_text("---\ntitle: Test\n---\n\nhello changed", encoding="utf-8")
    store = FakeStore()
    summary = sync_index_with_services(config, FakeEmbedder(), store, str(manifest_path))

    assert summary["changed"] == 1
    assert store.deleted_sources == [str(post_path)]
    assert len(store.upserts) == 1


def test_sync_index_deletes_removed_file(tmp_path):
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    removed_path = posts_dir / "removed.md"
    manifest_path = tmp_path / "manifest.json"
    save_manifest(
        str(manifest_path),
        {
            "version": 1,
            "posts": {
                str(removed_path): {
                    "source_file": str(removed_path),
                    "content_hash": "old",
                    "chunk_ids": ["abc123"],
                    "indexed_at": "2026-06-06T00:00:00+00:00",
                }
            },
        },
    )

    store = FakeStore()
    summary = sync_index_with_services(_config(posts_dir), FakeEmbedder(), store, str(manifest_path))
    manifest = load_manifest(str(manifest_path))

    assert summary["deleted"] == 1
    assert store.deleted_chunk_ids == ["abc123"]
    assert manifest["posts"] == {}


def _config(posts_dir):
    return {
        "posts_dir": str(posts_dir),
        "url_prefix": "/posts",
        "chunk": {
            "chunk_size": 600,
            "chunk_overlap": 100,
        },
    }
