import pandas as pd


def read_uploaded_file(uploaded):
    file_name = uploaded.name.lower()

    if file_name.endswith((".xlsx", ".xls", ".xlsm")):
        df = pd.read_excel(uploaded, dtype=str, keep_default_na=False)
        meta = {"file_name": uploaded.name, "file_type": "excel"}
        return df, meta

    if file_name.endswith(".tsv"):
        df = pd.read_csv(uploaded, sep="\t", dtype=str, keep_default_na=False)
        meta = {"file_name": uploaded.name, "file_type": "tsv"}
        return df, meta

    if file_name.endswith((".csv", ".txt")):
        df = pd.read_csv(uploaded, sep=None, engine="python", dtype=str, keep_default_na=False)
        meta = {"file_name": uploaded.name, "file_type": "delimited"}
        return df, meta

    raise ValueError("Unsupported file type. Please upload CSV, TSV, TXT, XLS, XLSX, or XLSM.")
