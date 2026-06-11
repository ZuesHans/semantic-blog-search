import hashlib
import re


def chunk_post(
    post: dict,
    chunk_size: int,
    chunk_overlap: int,
    split_heading_max_level: int = 0,
    include_heading_path: bool = True,
) -> list[dict]:
    """Split one post into chunks while keeping title and metadata."""
    sections = _split_sections(
        post.get("content", ""),
        split_heading_max_level=split_heading_max_level,
    )

    chunks = []
    for section in sections:
        chunks.extend(
            _chunk_section(
                post=post,
                section=section,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                start_index=len(chunks),
                include_heading_path=include_heading_path,
            )
        )

    return chunks


def chunk_posts(
    posts: list[dict],
    chunk_size: int,
    chunk_overlap: int,
    split_heading_max_level: int = 0,
    include_heading_path: bool = True,
) -> list[dict]:
    """Split many posts into one flat chunk list."""
    chunks = []
    for post in posts:
        chunks.extend(
            chunk_post(
                post,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                split_heading_max_level=split_heading_max_level,
                include_heading_path=include_heading_path,
            )
        )
    return chunks


def _chunk_section(
    post: dict,
    section: dict,
    chunk_size: int,
    chunk_overlap: int,
    start_index: int,
    include_heading_path: bool,
) -> list[dict]:
    paragraphs = _split_paragraphs(section.get("body", ""))
    if not paragraphs:
        paragraphs = [""]

    chunks = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        should_flush = current_parts and current_length + paragraph_length > chunk_size
        if should_flush:
            chunks.append(
                _make_chunk(
                    post=post,
                    paragraphs=current_parts,
                    chunk_index=start_index + len(chunks),
                    section=section,
                    include_heading_path=include_heading_path,
                )
            )
            current_parts = _overlap_parts(current_parts, chunk_overlap)
            current_length = sum(len(part) for part in current_parts)

        current_parts.append(paragraph)
        current_length += paragraph_length

    if current_parts:
        chunks.append(
            _make_chunk(
                post=post,
                paragraphs=current_parts,
                chunk_index=start_index + len(chunks),
                section=section,
                include_heading_path=include_heading_path,
            )
        )

    return chunks


def _split_paragraphs(content: str) -> list[str]:
    paragraphs = []
    for raw_paragraph in content.split("\n\n"):
        paragraph = raw_paragraph.strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _split_sections(content: str, split_heading_max_level: int) -> list[dict]:
    if split_heading_max_level <= 0:
        return [
            {
                "body": content.strip(),
                "heading_path": "",
                "heading_text": "",
                "heading_level": 0,
            }
        ]

    sections = []
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_heading_path = ""
    current_heading_text = ""
    current_heading_level = 0
    in_fenced_code = False

    def flush_current():
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(
                {
                    "body": body,
                    "heading_path": current_heading_path,
                    "heading_text": current_heading_text,
                    "heading_level": current_heading_level,
                }
            )

    for line in content.splitlines():
        if _is_fence_line(line):
            in_fenced_code = not in_fenced_code
            current_lines.append(line)
            continue

        heading = None if in_fenced_code else _parse_heading(line)
        if heading and heading["level"] <= split_heading_max_level:
            flush_current()
            level = heading["level"]
            text = heading["text"]
            heading_stack = [item for item in heading_stack if item[0] < level]
            heading_stack.append((level, text))
            current_heading_path = " > ".join(item[1] for item in heading_stack)
            current_heading_text = text
            current_heading_level = level
            current_lines = []
            continue

        current_lines.append(line)

    flush_current()
    if not sections:
        return [
            {
                "body": "",
                "heading_path": "",
                "heading_text": "",
                "heading_level": 0,
            }
        ]
    return sections


def _parse_heading(line: str) -> dict | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None

    level = len(match.group(1))
    text = re.sub(r"\s+#+\s*$", "", match.group(2)).strip()
    if not text:
        return None

    return {"level": level, "text": text}


def _is_fence_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _make_chunk(
    post: dict,
    paragraphs: list[str],
    chunk_index: int,
    section: dict,
    include_heading_path: bool,
) -> dict:
    body = "\n\n".join(paragraphs).strip()
    tags_text = "、".join(post.get("tags", []))
    heading_path = section.get("heading_path", "") if include_heading_path else ""
    text_parts = [
        f"文章标题：{post.get('title', '')}",
        f"标签：{tags_text}",
    ]
    if heading_path:
        text_parts.append(f"小节路径：{heading_path}")
    text_parts.append(f"正文：\n{body}")
    text = "\n".join(text_parts)
    chunk_id = _make_chunk_id(post, chunk_index)

    return {
        "chunk_id": chunk_id,
        "text": text,
        "title": post.get("title", ""),
        "url": post.get("url", ""),
        "tags": post.get("tags", []),
        "source_file": post.get("source_file", ""),
        "chunk_index": chunk_index,
        "heading_path": heading_path,
        "heading_level": section.get("heading_level", 0) if heading_path else 0,
        "heading_text": section.get("heading_text", "") if heading_path else "",
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
