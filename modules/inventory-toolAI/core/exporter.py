from io import BytesIO


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df):
    buffer = BytesIO()
    with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")
    return buffer.getvalue()
