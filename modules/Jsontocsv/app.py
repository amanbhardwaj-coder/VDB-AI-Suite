import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="JSON to CSV Converter", layout="wide")

st.title("📄 Postman JSON → CSV Converter")

uploaded_file = st.file_uploader(
    "Upload your Postman JSON response",
    type=["json", "txt"]
)

if uploaded_file:
    try:
        data = json.load(uploaded_file)

        # Update this path if your JSON structure differs
        records = data.get("response", {}).get("body", {}).get("diamonds", [])

        if not records:
            st.error("No records found at response.body.diamonds")
        else:
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
