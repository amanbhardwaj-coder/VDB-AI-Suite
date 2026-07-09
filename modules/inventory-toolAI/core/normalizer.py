import pandas as pd


def clean_value(value):
    if value is None:
        return ""

    value = str(value).strip()
    if value.lower() in {"nan", "none", "nat"}:
        return ""

    return value


def split_value(value):
    value = clean_value(value)
    value = value.replace("#", ",").replace("|", ",").replace(";", ",")
    return [x.strip() for x in value.split(",") if x.strip()]


def join_unique(values):
    output = []

    for value in values:
        for part in split_value(value):
            if part not in output:
                output.append(part)

    return ",".join(output)


def normalize_input_dataframe(df, config, preserve_unmapped=True):
    """
    Builds normalized dataframe from scratch.

    This avoids duplicate pandas columns entirely.
    """
    if df is None:
        return pd.DataFrame()

    mapping = config.get("mapping", [])

    target_to_sources = {}
    mapped_sources = set()
    ignored_sources = set()

    for item in mapping:
        vendor_col = str(item.get("vendor_column", "")).strip()
        accepted_header = str(item.get("accepted_header", "")).strip()
        role = str(item.get("role", "static")).strip().lower()

        if not vendor_col or vendor_col not in df.columns:
            continue

        if role == "ignore":
            ignored_sources.add(vendor_col)
            continue

        if not accepted_header:
            continue

        target_to_sources.setdefault(accepted_header, []).append(vendor_col)
        mapped_sources.add(vendor_col)

    normalized_data = {}

    for accepted_header, source_columns in target_to_sources.items():
        if len(source_columns) == 1:
            source = source_columns[0]
            normalized_data[accepted_header] = df[source].apply(clean_value)
        else:
            values = []
            for _, row in df[source_columns].iterrows():
                values.append(join_unique([row[col] for col in source_columns]))
            normalized_data[accepted_header] = values

    if preserve_unmapped:
        for col in df.columns:
            if col not in mapped_sources and col not in ignored_sources and col not in normalized_data:
                normalized_data[col] = df[col].apply(clean_value)

    normalized = pd.DataFrame(normalized_data)

    normalized.columns = [str(c).strip() for c in normalized.columns]

    # absolute duplicate protection
    if normalized.columns.duplicated().any():
        final = {}
        for idx, col in enumerate(normalized.columns):
            series = normalized.iloc[:, idx].apply(clean_value)
            if col not in final:
                final[col] = series
            else:
                final[col] = [
                    join_unique([old, new])
                    for old, new in zip(final[col], series)
                ]
        normalized = pd.DataFrame(final)

    return normalized
