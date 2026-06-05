from tqdm import tqdm

from semantic_blog_search.chunker import chunk_posts
from semantic_blog_search.embedder import Embedder
from semantic_blog_search.parser import load_markdown_posts
from semantic_blog_search.vector_store import VectorStore


def build_index(config: dict) -> None:
    """Build a local vector index from configured Markdown posts."""
    posts_dir = config["posts_dir"]
    url_prefix = config.get("url_prefix", "/posts")

    chunk_config = config.get("chunk", {})
    chunk_size = int(chunk_config.get("chunk_size", 600))
    chunk_overlap = int(chunk_config.get("chunk_overlap", 100))

    embedding_config = config.get("embedding", {})
    model_name = embedding_config.get("model_name", "BAAI/bge-small-zh-v1.5")

    qdrant_config = config.get("qdrant", {})
    db_path = qdrant_config.get("db_path", "./data/qdrant")
    collection_name = qdrant_config.get("collection_name", "blog_chunks")

    print("Reading Markdown posts...")
    posts = load_markdown_posts(posts_dir, url_prefix=url_prefix)
    print(f"Loaded {len(posts)} post(s).")

    print("Splitting posts into chunks...")
    chunks = chunk_posts(posts, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"Created {len(chunks)} chunk(s).")

    if not chunks:
        print("No chunks were created. Nothing to index.")
        return

    print(f"Loading embedding model: {model_name}")
    embedder = Embedder(model_name)

    texts = [chunk["text"] for chunk in chunks]
    print("Encoding chunks...")
    vectors = embedder.encode(texts)
    vector_size = len(vectors[0])

    print("Writing vectors to Qdrant local mode...")
    store = VectorStore(
        db_path=db_path,
        collection_name=collection_name,
        vector_size=vector_size,
    )
    store.recreate_collection()

    batch_size = 64
    for start in tqdm(range(0, len(chunks), batch_size), desc="Upserting"):
        end = start + batch_size
        store.upsert_chunks(chunks[start:end], vectors[start:end])

    print("Index build finished.")
