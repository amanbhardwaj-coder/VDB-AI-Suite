import streamlit as st
from shared.constants import VDB_LOGO_URL
import pandas as pd
import json
from typing import Any

st.set_page_config(page_title="JSON to CSV Converter", page_icon=VDB_LOGO_URL, layout="wide")

st.title("Postman JSON → CSV Converter")


def _find_records(payload: Any) -> tuple[list[dict[str, Any]], str | None]:
    candidate_paths = [
        ("response", "body", "diamonds"),
        ("response", "body", "gemstones"),
        ("response", "body", "data"),
        ("response", "body", "items"),
        ("response", "body", "results"),
        ("body", "diamonds"),
        ("body", "gemstones"),
        ("body", "data"),
        ("body", "items"),
        ("body", "results"),
        ("diamonds",),
        ("gemstones",),
        ("data",),
        ("items",),
        ("results",),
    ]

    def from_path(obj: Any, path: tuple[str, ...]) -> Any:
        current = obj
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    for path in candidate_paths:
        value = from_path(payload, path)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value, ".".join(path)

    def walk(obj: Any, path: str = "root") -> tuple[list[dict[str, Any]], str | None]:
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                return obj, path
            for index, item in enumerate(obj):
                records, found_path = walk(item, f"{path}[{index}]")
                if records:
                    return records, found_path
        elif isinstance(obj, dict):
            for key, value in obj.items():
                records, found_path = walk(value, f"{path}.{key}")
                if records:
                    return records, found_path
        return [], None

    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload, "root"

    return walk(payload)

uploaded_file = st.file_uploader(
    "Upload your Postman JSON response",
    type=["json", "txt"]
)

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        records, records_path = _find_records(data)

        if not records:
            st.error(
                "No list of objects was found in this JSON file. "
                "Supported shapes include `response.body.diamonds`, "
                "`response.body.gemstones`, `data`, `items`, and similar arrays."
            )
        else:
            if records_path:
                st.info(f"Detected records at `{records_path}`")
            df = pd.json_normalize(records)

            st.success(
                f"Successfully converted {len(df):,} rows and {len(df.columns)} columns"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Rows", f"{len(df):,}")

            with col2:
                st.metric("Columns", len(df.columns))

            st.subheader("Preview")
            st.dataframe(df.head(20), use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="converted.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
