import argparse
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from semantic_blog_search.api import create_app
from semantic_blog_search.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Run semantic blog search API.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    server_config = config.get("server", {})
    host = server_config.get("host", "127.0.0.1")
    port = int(server_config.get("port", 8000))

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
