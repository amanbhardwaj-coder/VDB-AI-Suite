from io import BytesIO


def apply_export_profile(df, config, profile="standard"):
    if df is None:
        return df

    if profile != "internal":
        return df.copy()

    rename_map = {}
    for item in config.get("mapping", []):
        accepted_header = str(item.get("accepted_header", "")).strip()
        internal_setter = str(item.get("internal_setter", "")).strip()
        if accepted_header and internal_setter:
            rename_map[accepted_header] = internal_setter

    return df.rename(columns=rename_map).copy()


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df):
    buffer = BytesIO()
    with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")
    return buffer.getvalue()
