import json
import re
from pathlib import Path

import pandas as pd


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _build_item(*, setter, accepted_header, variations, source_file):
    unique_variations = []
    seen = set()

    for variation in variations:
        cleaned = str(variation).strip()
        if not cleaned:
            continue

        normalized = norm(cleaned)
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        unique_variations.append(cleaned)

    if not setter or not accepted_header or not unique_variations:
        return None

    return {
        "source_file": source_file,
        "setter": setter,
        "accepted_header": accepted_header,
        "variations": unique_variations,
        "norm_variations": [norm(x) for x in unique_variations],
    }


def _load_learned_knowledge(knowledge_file: Path):
    if not knowledge_file.exists():
        return []

    try:
        payload = json.loads(knowledge_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    items = payload if isinstance(payload, list) else payload.get("items", [])
    learned = []

    for item in items:
        knowledge_item = _build_item(
            setter=str(item.get("setter", "")).strip(),
            accepted_header=str(item.get("accepted_header", "")).strip(),
            variations=item.get("variations", []),
            source_file=str(item.get("source_file", "learned_headers.json")).strip() or "learned_headers.json",
        )
        if knowledge_item:
            learned.append(knowledge_item)

    return learned


def load_header_knowledge(header_dir: Path):
    """
    Loads accepted header CSVs and learned mappings saved from prior runs.

    Expected CSV columns:
    - Setter name
    - Header variations
    """
    knowledge = []

    if not header_dir.exists():
        return knowledge

    for file in header_dir.glob("*.csv"):
        try:
            df = pd.read_csv(file, dtype=str, keep_default_na=False)
        except Exception:
            continue

        for _, row in df.iterrows():
            setter = str(row.get("Setter name", "")).strip()
            raw_variations = str(row.get("Header variations", "")).strip()

            if not setter or not raw_variations:
                continue

            variations = [x.strip() for x in raw_variations.split(",") if x.strip()]
            accepted_header = variations[0] if variations else ""

            knowledge_item = _build_item(
                setter=setter,
                accepted_header=accepted_header,
                variations=variations,
                source_file=file.name,
            )
            if knowledge_item:
                knowledge.append(knowledge_item)

    knowledge.extend(_load_learned_knowledge(header_dir.parent / "knowledge" / "learned_headers.json"))

    return knowledge
