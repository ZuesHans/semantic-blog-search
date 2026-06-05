import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.config import load_config
from semantic_blog_search.searcher import search


def main():
    parser = argparse.ArgumentParser(description="Search indexed blog chunks.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of results.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        results = search(config, args.query, top_k=args.top_k)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Query: {args.query}\n")
    if not results:
        print("No results found. Please make sure the index has been built.")
        return

    for index, result in enumerate(results, start=1):
        print(f"[{index}] {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Score: {result['score']:.4f}")
        print(f"Source: {result['source_file']}")
        print(f"Snippet: {result['snippet']}")
        print()


if __name__ == "__main__":
    main()
