import json
from pathlib import Path


def report(stats_d: dict, output_p: str | Path):
    path = Path(output_p)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(stats_d, f, ensure_ascii=False, indent=2)
