import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.parser import read_uploaded_file
from core.normalizer import normalize_input_dataframe
from core.validator import build_qa_report
from core.expander import expand_inventory
from core.exporter import to_csv_bytes, to_excel_bytes
from agents.ai_analyzer import AIInventoryAnalyzer
from agents.rule_parser import parse_english_rules
from agents.header_knowledge import load_header_knowledge
from agents.config_store import save_generated_config


APP_TITLE = "AI Inventory Studio"
HEADER_DIR = Path("configs/headers")
GENERATED_DIR = Path("generated")


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

st.markdown(
    """
Upload any vendor inventory file, tell the AI what you want in English, review the mapping,
then create the normalized and expanded inventory.
"""
)

if "source_df" not in st.session_state:
    st.session_state["source_df"] = None
if "analysis_config" not in st.session_state:
    st.session_state["analysis_config"] = None
if "normalized_df" not in st.session_state:
    st.session_state["normalized_df"] = None
if "expanded_df" not in st.session_state:
    st.session_state["expanded_df"] = None
if "qa_report" not in st.session_state:
    st.session_state["qa_report"] = None


def safe_preview(df, rows=20):
    if df is None or df.empty:
        st.info("No data to preview.")
        return

    preview = df.head(rows).copy()
    preview.columns = [str(c).strip() for c in preview.columns]
    preview = preview.loc[:, ~preview.columns.duplicated()]
    st.dataframe(preview, use_container_width=True)


def mapping_editor(config):
    rows = []
    for item in config.get("mapping", []):
        rows.append(
            {
                "Vendor Column": item.get("vendor_column", ""),
                "Accepted Header": item.get("accepted_header", ""),
                "Role": item.get("role", "static"),
                "Expand": bool(item.get("expand", False)),
                "Confidence": item.get("confidence", 0),
            }
        )

    edited = st.data_editor(
        pd.DataFrame(rows),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Role": st.column_config.SelectboxColumn(
                "Role",
                options=["static", "variant", "ignore"],
            ),
            "Expand": st.column_config.CheckboxColumn("Expand"),
        },
    )

    config["mapping"] = [
        {
            "vendor_column": row.get("Vendor Column", ""),
            "accepted_header": row.get("Accepted Header", ""),
            "role": row.get("Role", "static"),
            "expand": bool(row.get("Expand", False)),
            "confidence": row.get("Confidence", 0),
        }
        for row in edited.to_dict("records")
    ]

    return config


with st.sidebar:
    st.header("Workflow")
    st.write("1. Upload")
    st.write("2. AI Analyze")
    st.write("3. Review")
    st.write("4. Create Inventory")
    st.write("5. Download")

    st.divider()
    st.header("Options")
    create_expanded = st.toggle("Create expanded inventory", value=True)
    preserve_unmapped = st.toggle("Preserve unmapped columns", value=True)
    run_qa = st.toggle("Run QA report", value=True)


uploaded = st.file_uploader("Upload vendor inventory", type=["csv", "xlsx", "xls"])

instructions = st.text_area(
    "AI Instructions",
    height=180,
    placeholder=(
        "Example:\\n"
        "- Convert metal values into Available Metal Type\\n"
        "- Create variants only for metal, shape, and head\\n"
        "- Keep Jewelry Style static\\n"
        "- 14K metal price should be 500 and the rest should be 1000\\n"
        "- Use description to identify jewelry type"
    ),
)

if uploaded:
    try:
        df, file_meta = read_uploaded_file(uploaded)
        st.session_state["source_df"] = df
        st.success(f"Loaded {uploaded.name}: {len(df):,} rows, {len(df.columns):,} columns")
        st.subheader("Source Preview")
        safe_preview(df, 10)
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        st.stop()

    if st.button("🤖 Analyze with AI", type="primary"):
        knowledge = load_header_knowledge(HEADER_DIR)
        business_rules = parse_english_rules(instructions)

        analyzer = AIInventoryAnalyzer(knowledge)
        config = analyzer.analyze(
            df=df,
            file_name=uploaded.name,
            instructions=instructions,
            business_rules=business_rules,
        )

        st.session_state["analysis_config"] = config
        st.session_state["normalized_df"] = None
        st.session_state["expanded_df"] = None
        st.session_state["qa_report"] = None


if st.session_state["analysis_config"]:
    st.divider()
    st.subheader("AI Analysis Summary")

    config = st.session_state["analysis_config"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Detected Type", config.get("inventory_type", "unknown"))
    col2.metric("Columns Mapped", sum(1 for x in config.get("mapping", []) if x.get("accepted_header")))
    col3.metric("Low Confidence", sum(1 for x in config.get("mapping", []) if float(x.get("confidence", 0)) < 0.8))

    if config.get("warnings"):
        with st.expander("Warnings", expanded=True):
            for warning in config["warnings"]:
                st.warning(warning)

    st.subheader("Review Mapping")
    config = mapping_editor(config)
    st.session_state["analysis_config"] = config

    with st.expander("Generated Rules JSON", expanded=False):
        st.json(config.get("business_rules", {}))

    if st.button("🚀 Create Inventory", type="primary"):
        source_df = st.session_state["source_df"]

        normalized_df = normalize_input_dataframe(
            source_df,
            config,
            preserve_unmapped=preserve_unmapped,
        )

        st.session_state["normalized_df"] = normalized_df

        if create_expanded:
            expanded_df = expand_inventory(
                normalized_df,
                config=config,
            )
        else:
            expanded_df = normalized_df.copy()

        st.session_state["expanded_df"] = expanded_df

        if run_qa:
            st.session_state["qa_report"] = build_qa_report(
                source_df=source_df,
                normalized_df=normalized_df,
                output_df=expanded_df,
                config=config,
            )

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        save_generated_config(config, GENERATED_DIR / "mapping_config.json")

        normalized_df.to_csv(GENERATED_DIR / "normalized_input.csv", index=False)
        expanded_df.to_csv(GENERATED_DIR / "expanded_inventory.csv", index=False)

        st.success("Inventory created.")


if st.session_state["normalized_df"] is not None:
    st.divider()
    st.subheader("Normalized Input Preview")
    safe_preview(st.session_state["normalized_df"], 20)

    st.download_button(
        "Download normalized_input.csv",
        to_csv_bytes(st.session_state["normalized_df"]),
        "normalized_input.csv",
        "text/csv",
    )

if st.session_state["expanded_df"] is not None:
    st.subheader("Expanded Inventory Preview")
    safe_preview(st.session_state["expanded_df"], 20)

    st.download_button(
        "Download expanded_inventory.csv",
        to_csv_bytes(st.session_state["expanded_df"]),
        "expanded_inventory.csv",
        "text/csv",
    )

    st.download_button(
        "Download expanded_inventory.xlsx",
        to_excel_bytes(st.session_state["expanded_df"]),
        "expanded_inventory.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if st.session_state["qa_report"] is not None:
    st.subheader("QA Report")
    qa = st.session_state["qa_report"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Source Rows", qa.get("source_rows", 0))
    col2.metric("Output Rows", qa.get("output_rows", 0))
    col3.metric("Duplicate SKUs", qa.get("duplicate_skus", 0))
    col4.metric("Missing Master Stock", qa.get("missing_master_stock", 0))

    if qa.get("warnings"):
        with st.expander("QA Warnings", expanded=True):
            for warning in qa["warnings"]:
                st.warning(warning)

    st.download_button(
        "Download qa_report.json",
        json.dumps(qa, indent=2).encode("utf-8"),
        "qa_report.json",
        "application/json",
    )

if st.session_state["analysis_config"] is not None:
    st.download_button(
        "Download mapping_config.json",
        json.dumps(st.session_state["analysis_config"], indent=2).encode("utf-8"),
        "mapping_config.json",
        "application/json",
    )
