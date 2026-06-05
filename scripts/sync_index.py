import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.config import load_config
from semantic_blog_search.incremental_indexer import sync_index


def main():
    parser = argparse.ArgumentParser(description="Incrementally sync blog index.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        summary = sync_index(config)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print("Incremental index sync finished.")
    print(f"Current Markdown files: {summary['total_current']}")
    print(f"Added: {summary['added']}")
    print(f"Changed: {summary['changed']}")
    print(f"Deleted: {summary['deleted']}")
    print(f"Skipped: {summary['skipped']}")


if __name__ == "__main__":
    main()
