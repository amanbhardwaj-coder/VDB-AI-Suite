import re


def _numbers(text):
    return [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", text)]


def parse_english_rules(instructions: str):
    """
    English-to-rule parser for V3.

    Creates visible rules for:
    - metal pricing
    - variant columns
    - static/keep fields
    - separator cleanup
    - duplicate cleanup
    """

    original = instructions or ""
    text = original.lower()

    rules = {
        "pricing_rules": [],
        "normalization_rules": [],
        "variant_rules": [],
        "static_rules": [],
        "notes": []
    }

    if not text.strip():
        rules["notes"].append(
            "No English instructions were provided, so only header mapping rules were generated."
        )
        return rules

    # ------------------------------------------------------------
    # Pricing rule examples:
    # "14k metal prices should be 500 and rest should be 1000"
    # "14K should be 500, others 1000"
    # ------------------------------------------------------------
    has_14k = any(token in text for token in ["14k", "14 k", "14kt", "14 kt"])
    has_rest = any(token in text for token in ["rest", "other", "others", "default", "remaining"])
    nums = _numbers(text)

    if has_14k and len(nums) >= 2:
        rules["pricing_rules"].append(
            {
                "type": "metal_price_rule",
                "condition": {
                    "field_contains": "metal",
                    "value_contains_any": ["14k", "14 k", "14kt", "14 kt", "14kw", "14ky", "14kr"]
                },
                "price": nums[0],
                "else_price": nums[1] if has_rest or len(nums) >= 2 else None,
                "source_instruction": original
            }
        )

    # ------------------------------------------------------------
    # Variant rules:
    # "create variants only for metal and shape"
    # "expand metal, shape and head"
    # ------------------------------------------------------------
    variant_keywords = {
        "metal": "Available Metal Type",
        "metals": "Available Metal Type",
        "shape": "Supported Shape Variations",
        "shapes": "Supported Shape Variations",
        "head": "Available Head",
        "heads": "Available Head",
        "size": "Available Size",
        "sizes": "Available Size",
        "ring size": "Available Size",
        "center": "Available Center Size",
        "center size": "Available Center Size",
        "carat": "Available Center Size",
    }

    if any(word in text for word in ["variant", "variants", "expand", "expansion", "create variants"]):
        selected = []
        for key, header in variant_keywords.items():
            if key in text and header not in selected:
                selected.append(header)

        if selected:
            rules["variant_rules"].append(
                {
                    "type": "expand_selected_fields",
                    "headers": selected,
                    "source_instruction": original
                }
            )

    # ------------------------------------------------------------
    # Static field rules:
    # "keep jewelry style static"
    # "do not expand jewelry style"
    # ------------------------------------------------------------
    static_candidates = {
        "jewelry style": "Jewelry Style",
        "style": "Jewelry Style",
        "jewelry type": "Jewelry Type",
        "description": "Description",
        "collection": "Collection",
        "material": "Material",
        "color": "Color",
        "gender": "Gender",
        "notes": "Notes",
    }

    if any(word in text for word in ["static", "do not expand", "don't expand", "keep"]):
        selected = []
        for key, header in static_candidates.items():
            if key in text and header not in selected:
                selected.append(header)

        if selected:
            rules["static_rules"].append(
                {
                    "type": "keep_static",
                    "headers": selected,
                    "source_instruction": original
                }
            )

    # ------------------------------------------------------------
    # Normalization rules
    # ------------------------------------------------------------
    if any(x in text for x in ["duplicate", "duplicates", "dedupe", "de-dupe"]):
        rules["normalization_rules"].append(
            {
                "type": "remove_duplicate_tokens",
                "source_instruction": original
            }
        )

    if any(x in original for x in ["#", "|", ";"]) or "separator" in text:
        rules["normalization_rules"].append(
            {
                "type": "normalize_separators",
                "to": ",",
                "source_instruction": original
            }
        )

    if "metal" in text and any(x in text for x in ["14kw", "14ky", "14kr", "standard", "normalize"]):
        rules["normalization_rules"].append(
            {
                "type": "normalize_metal_values",
                "source_instruction": original
            }
        )

    if not any(rules[key] for key in ["pricing_rules", "normalization_rules", "variant_rules", "static_rules"]):
        rules["notes"].append(
            "Instructions were saved, but no structured rule could be inferred yet."
        )

    return rules
