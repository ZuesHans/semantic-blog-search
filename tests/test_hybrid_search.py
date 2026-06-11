import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.searcher import _rerank_hybrid


def test_hybrid_rerank_boosts_exact_keyword_match():
    candidates = [
        {
            "title": "线段树懒标记",
            "url": "/posts/segment-tree",
            "score": 0.81,
            "snippet": "区间修改需要 pushdown。",
            "source_file": "segment-tree.md",
            "text": "标题：线段树懒标记\n正文：区间修改需要 pushdown。",
            "tags": ["线段树"],
        },
        {
            "title": "并查集",
            "url": "/posts/dsu",
            "score": 0.80,
            "snippet": "按秩合并可以减少树高。",
            "source_file": "dsu.md",
            "text": "标题：并查集\n标签：数据结构\n正文：按秩合并可以减少树高。",
            "tags": ["数据结构", "并查集"],
        },
    ]

    results = _rerank_hybrid(
        query="按秩合并",
        candidates=candidates,
        search_config={"hybrid_keyword_weight": 0.25},
    )

    assert results[0]["title"] == "并查集"
    assert results[0]["score"] > results[1]["score"]


def test_hybrid_rerank_keeps_api_shape():
    candidates = [
        {
            "title": "并查集",
            "url": "/posts/dsu",
            "score": 0.8,
            "snippet": "按秩合并可以减少树高。",
            "source_file": "dsu.md",
            "text": "按秩合并可以减少树高。",
            "tags": ["并查集"],
            "chunk_id": "internal",
        }
    ]

    results = _rerank_hybrid("按秩合并", candidates, {})

    assert set(results[0]) == {"title", "url", "score", "snippet", "source_file"}


def test_hybrid_rerank_boosts_heading_path_match():
    candidates = [
        {
            "title": "数据结构",
            "url": "/posts/data-structure",
            "score": 0.82,
            "snippet": "这里记录一道题。",
            "source_file": "data.md",
            "text": "这里记录一道题。",
            "tags": ["数据结构"],
            "heading_path": "数据结构 > 并查集 > 家谱",
        },
        {
            "title": "图论",
            "url": "/posts/graph",
            "score": 0.83,
            "snippet": "这里记录另一道题。",
            "source_file": "graph.md",
            "text": "这里记录另一道题。",
            "tags": ["图论"],
            "heading_path": "图论 > 最短路 > 模板",
        },
    ]

    results = _rerank_hybrid(
        query="家谱",
        candidates=candidates,
        search_config={"hybrid_keyword_weight": 0.25},
    )

    assert results[0]["title"] == "数据结构"
