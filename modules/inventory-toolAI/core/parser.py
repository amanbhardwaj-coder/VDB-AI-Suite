import pandas as pd


def read_uploaded_file(uploaded):
    file_name = uploaded.name.lower()

    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        df = pd.read_excel(uploaded, dtype=str, keep_default_na=False)
        meta = {"file_name": uploaded.name, "file_type": "excel"}
        return df, meta

    df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    meta = {"file_name": uploaded.name, "file_type": "csv"}
    return df, meta
