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


def test_chunk_post_splits_on_headings_up_to_configured_level():
    post = _post(
        """
## 数据结构

概览。

### 并查集

基础。

#### 家谱

路径压缩。
"""
    )

    chunks = chunk_post(
        post,
        chunk_size=1000,
        chunk_overlap=0,
        split_heading_max_level=4,
    )

    assert [chunk["heading_path"] for chunk in chunks] == [
        "数据结构",
        "数据结构 > 并查集",
        "数据结构 > 并查集 > 家谱",
    ]
    assert "小节路径：数据结构 > 并查集 > 家谱" in chunks[2]["text"]


def test_chunk_post_does_not_split_on_level_five_by_default():
    post = _post(
        """
### 线性 DP

介绍。

#### LIS

主体。

##### 小结

仍然属于 LIS。
"""
    )

    chunks = chunk_post(
        post,
        chunk_size=1000,
        chunk_overlap=0,
        split_heading_max_level=4,
    )

    assert [chunk["heading_path"] for chunk in chunks] == [
        "线性 DP",
        "线性 DP > LIS",
    ]
    assert "##### 小结" in chunks[1]["text"]


def test_chunk_post_ignores_headings_inside_fenced_code():
    post = _post(
        """
### C++ 模板

```cpp
#include <bits/stdc++.h>
#### fake heading
```

#### 真正题目

正文。
"""
    )

    chunks = chunk_post(
        post,
        chunk_size=1000,
        chunk_overlap=0,
        split_heading_max_level=4,
    )

    assert [chunk["heading_path"] for chunk in chunks] == [
        "C++ 模板",
        "C++ 模板 > 真正题目",
    ]
    assert "fake heading" in chunks[0]["text"]


def test_chunk_post_splits_long_section_without_losing_heading_path():
    post = _post(
        """
#### 按秩合并

第一段很长很长。

第二段也很长很长。

第三段还是很长很长。
"""
    )

    chunks = chunk_post(
        post,
        chunk_size=18,
        chunk_overlap=0,
        split_heading_max_level=4,
    )

    assert len(chunks) > 1
    assert {chunk["heading_path"] for chunk in chunks} == {"按秩合并"}


def test_chunk_post_can_fall_back_to_plain_paragraph_chunking():
    post = _post(
        """
### 并查集

第一段。

#### 家谱

第二段。
"""
    )

    chunks = chunk_post(
        post,
        chunk_size=1000,
        chunk_overlap=0,
        split_heading_max_level=0,
    )

    assert len(chunks) == 1
    assert chunks[0]["heading_path"] == ""
    assert "### 并查集" in chunks[0]["text"]


def _post(content: str) -> dict:
    return {
        "title": "算法笔记",
        "url": "/posts/algo",
        "tags": ["算法"],
        "content": content.strip(),
        "source_file": "posts/algo.md",
    }
