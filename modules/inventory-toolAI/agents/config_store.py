import json
from datetime import datetime
from pathlib import Path


def save_generated_config(config, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    config = dict(config)
    config["saved_at"] = datetime.utcnow().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return path
