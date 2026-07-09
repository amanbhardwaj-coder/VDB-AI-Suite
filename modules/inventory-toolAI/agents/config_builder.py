import json
from datetime import datetime
import pandas as pd


def save_config(config, path):
    path.parent.mkdir(parents=True, exist_ok=True)

    config["generated_at"] = datetime.utcnow().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _clean_value(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in {"nan", "none", "nat"}:
        return ""

    return value


def _join_unique_values(values):
    output = []

    for value in values:
        value = _clean_value(value)

        if not value:
            continue

        split_value = (
            str(value)
            .replace("#", ",")
            .replace("|", ",")
            .replace(";", ",")
        )

        for part in split_value.split(","):
            part = part.strip()

            if part and part not in output:
                output.append(part)

    return ",".join(output)


def _get_item_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def create_normalized_file(df, config):
    """
    Create a normalized input dataframe without ever creating duplicate
    dataframe columns.

    Important:
    We do NOT use df.rename() first, because if multiple vendor columns map to
    the same accepted header, pandas creates duplicate column names and then
    df["column"] can return a DataFrame instead of a Series.

    Instead, we build the normalized dataframe column-by-column.
    """

    if df is None:
        return pd.DataFrame()

    source_df = df.copy()

    mapping_rows = config.get("mapping", [])

    target_to_sources = {}
    mapped_sources = set()

    for item in mapping_rows:

        vendor_column = _get_item_value(
            item,
            "vendor_column",
            "Vendor Column",
        )

        accepted_header = _get_item_value(
            item,
            "accepted_header",
            "Accepted Header",
        )

        if not vendor_column or not accepted_header:
            continue

        if vendor_column not in source_df.columns:
            continue

        target_to_sources.setdefault(accepted_header, []).append(vendor_column)
        mapped_sources.add(vendor_column)


    normalized_data = {}

    # First add mapped columns, merging many source columns into one accepted header
    for accepted_header, source_columns in target_to_sources.items():

        if len(source_columns) == 1:
            source_col = source_columns[0]
            normalized_data[accepted_header] = source_df[source_col].apply(_clean_value)
        else:
            merged_values = []
            for _, row in source_df[source_columns].iterrows():
                merged_values.append(_join_unique_values([row[col] for col in source_columns]))

            normalized_data[accepted_header] = merged_values


    # Preserve unmapped columns with original names so user does not lose data
    for source_col in source_df.columns:
        if source_col not in mapped_sources and source_col not in normalized_data:
            normalized_data[source_col] = source_df[source_col].apply(_clean_value)


    normalized = pd.DataFrame(normalized_data)

    normalized.columns = [
        str(col).strip()
        for col in normalized.columns
    ]

    # Final absolute safety: combine any duplicate columns that somehow remain
    if normalized.columns.duplicated().any():
        final_data = {}

        for col_index, col_name in enumerate(normalized.columns):
            series = normalized.iloc[:, col_index].apply(_clean_value)

            if col_name not in final_data:
                final_data[col_name] = series
            else:
                combined = []
                existing = final_data[col_name]

                for old, new in zip(existing.tolist(), series.tolist()):
                    combined.append(_join_unique_values([old, new]))

                final_data[col_name] = pd.Series(combined)

        normalized = pd.DataFrame(final_data)

    return normalized
