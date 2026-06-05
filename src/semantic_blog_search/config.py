from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    """Read a YAML config file and return it as a dictionary."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Please copy config.example.yaml to config.yaml first."
        )

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if "posts_dir" not in config:
        raise ValueError("Missing required config item: posts_dir")

    return config
