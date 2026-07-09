import re
from agents.header_knowledge import norm


VARIANT_HINTS = [
    "available",
    "metal",
    "shape",
    "size",
    "head",
    "center",
    "stone",
    "ring mm",
    "ring size",
]

STATIC_HINTS = [
    "description",
    "jewelry type",
    "jewelry style",
    "style",
    "collection",
    "gender",
    "color",
    "material",
    "short title",
    "notes",
]


def _score_match(column, variation):
    c = norm(column)
    v = norm(variation)

    if not c or not v:
        return 0

    if c == v:
        return 1.0

    if c in v or v in c:
        return 0.82

    c_tokens = set(re.findall(r"[a-z0-9]+", str(column).lower()))
    v_tokens = set(re.findall(r"[a-z0-9]+", str(variation).lower()))

    if not c_tokens or not v_tokens:
        return 0

    overlap = len(c_tokens & v_tokens) / max(len(c_tokens), len(v_tokens))

    if overlap >= 0.5:
        return round(0.55 + overlap * 0.25, 2)

    return 0


def _infer_role(column, accepted_header):
    text = f"{column} {accepted_header}".lower()

    if any(x in text for x in STATIC_HINTS):
        return "static", False

    if any(x in text for x in VARIANT_HINTS):
        return "variant", True

    return "static", False


def _detect_inventory_type(columns):
    joined = " ".join(str(x).lower() for x in columns)

    jewelry_score = sum(x in joined for x in ["jewelry", "style", "metal", "ring", "head", "setting"])
    diamond_score = sum(x in joined for x in ["diamond", "carat", "clarity", "certificate", "lab"])
    gemstone_score = sum(x in joined for x in ["gemstone", "gem", "species", "variety"])

    scores = {
        "jewelry": jewelry_score,
        "diamond": diamond_score,
        "gemstone": gemstone_score,
    }

    return max(scores, key=scores.get) if max(scores.values()) > 0 else "unknown"


def _apply_business_rules_to_mapping(mapping, business_rules):
    variant_headers = set()
    static_headers = set()

    for rule in business_rules.get("variant_rules", []):
        for header in rule.get("headers", []):
            variant_headers.add(str(header).strip().lower())

    for rule in business_rules.get("static_rules", []):
        for header in rule.get("headers", []):
            static_headers.add(str(header).strip().lower())

    for item in mapping:
        accepted = str(item.get("accepted_header", "")).strip().lower()

        if accepted in variant_headers:
            item["role"] = "variant"
            item["expand"] = True

        if accepted in static_headers:
            item["role"] = "static"
            item["expand"] = False

    return mapping


class AIInventoryAnalyzer:
    """
    Deterministic AI-style analyzer for V3 foundation.
    """

    def __init__(self, header_knowledge):
        self.header_knowledge = header_knowledge


    def match_column(self, column):
        best = {
            "vendor_column": column,
            "accepted_header": "",
            "internal_setter": "",
            "confidence": 0,
            "source_file": "",
        }

        for item in self.header_knowledge:
            for variation in item.get("variations", []):
                score = _score_match(column, variation)

                if score > best["confidence"]:
                    best = {
                        "vendor_column": column,
                        "accepted_header": item.get("accepted_header", ""),
                        "internal_setter": item.get("setter", ""),
                        "confidence": score,
                        "source_file": item.get("source_file", ""),
                    }

        role, expand = _infer_role(column, best.get("accepted_header", ""))

        best["role"] = role
        best["expand"] = expand

        return best


    def analyze(self, df, file_name, instructions="", business_rules=None):
        columns = list(df.columns)
        business_rules = business_rules or {}

        mapping = [self.match_column(col) for col in columns]

        warnings = []
        for item in mapping:
            if not item.get("accepted_header"):
                warnings.append(f"No accepted header found for: {item.get('vendor_column')}")
            elif float(item.get("confidence", 0)) < 0.8:
                warnings.append(
                    f"Low confidence mapping: {item.get('vendor_column')} -> {item.get('accepted_header')} ({item.get('confidence')})"
                )

        for item in mapping:
            if str(item.get("vendor_column", "")).lower().startswith("available "):
                item["role"] = "variant"
                item["expand"] = True

        mapping = _apply_business_rules_to_mapping(mapping, business_rules)

        return {
            "version": "v3.1",
            "file_name": file_name,
            "source_rows": len(df),
            "source_columns": len(columns),
            "inventory_type": _detect_inventory_type(columns),
            "instructions": instructions,
            "business_rules": business_rules,
            "mapping": mapping,
            "warnings": warnings,
        }
