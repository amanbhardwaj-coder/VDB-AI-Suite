from pathlib import Path
import pandas as pd
import re


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def load_header_knowledge(header_dir: Path):
    """
    Loads accepted header CSVs.

    Expected columns:
    - Setter name
    - Header variations

    UI uses accepted_header.
    Internal setter remains hidden.
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
            if not variations:
                continue

            accepted_header = variations[0]

            knowledge.append(
                {
                    "source_file": file.name,
                    "setter": setter,
                    "accepted_header": accepted_header,
                    "variations": variations,
                    "norm_variations": [norm(x) for x in variations],
                }
            )

    return knowledge
