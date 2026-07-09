import pandas as pd
from itertools import product
from core.normalizer import split_value


def is_available_column(column):
    return str(column).strip().lower().startswith("available ")


def _stock_col(df):
    for candidate in ["Master Stock Number", "Master stock", "Master Stock", "Stock Number", "SKU"]:
        if candidate in df.columns:
            return candidate
    return None


def _apply_pricing(row, config):
    pricing_rules = config.get("business_rules", {}).get("pricing_rules", [])

    if not pricing_rules:
        return row

    metal_value = ""

    for col in row.index:
        if "metal" in str(col).lower():
            metal_value = str(row[col]).lower()
            break

    for rule in pricing_rules:
        if rule.get("type") == "metal_price_rule":
            tokens = rule.get("condition", {}).get("value_contains_any", [])

            if any(str(token).lower() in metal_value for token in tokens):
                row["Price"] = rule.get("price")
            elif rule.get("else_price") is not None:
                row["Price"] = rule.get("else_price")

    return row


def expand_inventory(normalized_df, config=None):
    """
    V3 starter expansion engine.

    It expands columns whose headers start with "Available ".
    """
    if config is None:
        config = {}

    if normalized_df is None or normalized_df.empty:
        return pd.DataFrame()

    available_cols = [col for col in normalized_df.columns if is_available_column(col)]

    if not available_cols:
        out = normalized_df.copy()
        out = out.apply(lambda row: _apply_pricing(row, config), axis=1)
        return out

    output_rows = []

    master_col = _stock_col(normalized_df)

    for _, row in normalized_df.iterrows():
        option_lists = []

        for col in available_cols:
            tokens = split_value(row.get(col, ""))
            option_lists.append(tokens or [""])

        for combo in product(*option_lists):
            new_row = row.copy()

            sku_parts = []
            if master_col:
                sku_parts.append(str(row.get(master_col, "")).strip())

            for col, value in zip(available_cols, combo):
                base_col = str(col).replace("Available ", "").strip()
                new_row[base_col] = value
                sku_parts.append(value)

            if "Stock Number" not in new_row or not str(new_row.get("Stock Number", "")).strip():
                new_row["Stock Number"] = "-".join(
                    [x.replace(" ", "").replace(",", "") for x in sku_parts if str(x).strip()]
                )

            new_row = _apply_pricing(new_row, config)

            output_rows.append(dict(new_row))

    return pd.DataFrame(output_rows)
