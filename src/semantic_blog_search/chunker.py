import hashlib


def chunk_post(post: dict, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """Split one post into chunks while keeping title and metadata."""
    paragraphs = _split_paragraphs(post.get("content", ""))
    if not paragraphs:
        paragraphs = [""]

    chunks = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        should_flush = current_parts and current_length + paragraph_length > chunk_size
        if should_flush:
            chunks.append(_make_chunk(post, current_parts, len(chunks)))
            current_parts = _overlap_parts(current_parts, chunk_overlap)
            current_length = sum(len(part) for part in current_parts)

        current_parts.append(paragraph)
        current_length += paragraph_length

    if current_parts:
        chunks.append(_make_chunk(post, current_parts, len(chunks)))

    return chunks


def chunk_posts(posts: list[dict], chunk_size: int, chunk_overlap: int) -> list[dict]:
    """Split many posts into one flat chunk list."""
    chunks = []
    for post in posts:
        chunks.extend(chunk_post(post, chunk_size, chunk_overlap))
    return chunks


def _split_paragraphs(content: str) -> list[str]:
    paragraphs = []
    for raw_paragraph in content.split("\n\n"):
        paragraph = raw_paragraph.strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _make_chunk(post: dict, paragraphs: list[str], chunk_index: int) -> dict:
    body = "\n\n".join(paragraphs).strip()
    tags_text = "、".join(post.get("tags", []))
    text = f"标题：{post.get('title', '')}\n标签：{tags_text}\n正文：\n{body}"
    chunk_id = _make_chunk_id(post, chunk_index)

    return {
        "chunk_id": chunk_id,
        "text": text,
        "title": post.get("title", ""),
        "url": post.get("url", ""),
        "tags": post.get("tags", []),
        "source_file": post.get("source_file", ""),
        "chunk_index": chunk_index,
    }


def _make_chunk_id(post: dict, chunk_index: int) -> str:
    raw = f"{post.get('source_file', '')}:{chunk_index}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _overlap_parts(parts: list[str], chunk_overlap: int) -> list[str]:
    if chunk_overlap <= 0:
        return []

    kept = []
    total_length = 0
    for paragraph in reversed(parts):
        if total_length >= chunk_overlap:
            break
        kept.append(paragraph)
        total_length += len(paragraph)

    return list(reversed(kept))
