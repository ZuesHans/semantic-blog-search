from pathlib import Path
from typing import Any

import frontmatter


def load_markdown_posts(posts_dir: str, url_prefix: str = "/posts") -> list[dict]:
    """Scan a directory and parse all Markdown posts."""
    root = Path(posts_dir).expanduser()
    if not root.exists():
        raise FileNotFoundError(
            f"posts_dir does not exist: {root}. "
            "Please edit posts_dir in config.yaml."
        )
    if not root.is_dir():
        raise NotADirectoryError(f"posts_dir is not a directory: {root}")

    posts = []
    for markdown_file in sorted(root.rglob("*.md")):
        posts.append(parse_markdown_file(markdown_file, url_prefix))

    return posts


def parse_markdown_file(markdown_file: str | Path, url_prefix: str = "/posts") -> dict:
    """Parse one Markdown file into the post dictionary used by the indexer."""
    markdown_file = Path(markdown_file)
    parsed = frontmatter.load(markdown_file, encoding="utf-8")
    metadata = parsed.metadata

    slug = _metadata_text(metadata.get("slug")) or markdown_file.stem
    title = _metadata_text(metadata.get("title")) or markdown_file.stem
    tags = _normalize_tags(metadata.get("tags"))
    date = _metadata_text(metadata.get("date"))

    return {
        "title": title,
        "date": date,
        "tags": tags,
        "slug": slug,
        "url": _build_url(url_prefix, slug),
        "content": parsed.content.strip(),
        "source_file": str(markdown_file),
    }


def _metadata_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _build_url(url_prefix: str, slug: str) -> str:
    prefix = (url_prefix or "").strip()
    if not prefix:
        return f"/{slug}"
    return f"{prefix.rstrip('/')}/{slug}"
