import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.chunker import chunk_post


def test_chunk_post_returns_non_empty_chunks():
    post = {
        "title": "线段树懒标记入门",
        "url": "/posts/segment-tree-lazy-tag",
        "tags": ["数据结构", "线段树"],
        "content": "第一段内容。\n\n第二段内容解释 pushdown。",
        "source_file": "examples/posts/sample.md",
    }

    chunks = chunk_post(post, chunk_size=50, chunk_overlap=10)

    assert chunks
    for chunk in chunks:
        assert chunk["chunk_id"]
        assert chunk["title"]
        assert chunk["url"]
        assert chunk["text"]
