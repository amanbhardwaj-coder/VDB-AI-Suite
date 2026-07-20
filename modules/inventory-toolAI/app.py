import json
from pathlib import Path

import pandas as pd
import streamlit as st

from agents.ai_analyzer import AIInventoryAnalyzer
from agents.config_store import (
    ensure_runtime_dirs,
    hydrate_knowledge_file,
    load_run_history,
    save_generated_config,
    save_run_artifacts,
    store_learned_mappings,
)
from agents.header_knowledge import load_header_knowledge
from agents.openai_helper import InventoryOpenAIAgent, load_openai_settings
from agents.rule_parser import parse_english_rules
from agents.supabase_backend import SupabaseBackend, load_supabase_settings
from core.expander import expand_inventory
from core.exporter import apply_export_profile, to_csv_bytes, to_excel_bytes
from core.normalizer import normalize_input_dataframe
from core.parser import read_uploaded_file
from core.validator import build_qa_report


APP_TITLE = "AI Inventory Studio"
MODULE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = MODULE_DIR / "configs"
HEADER_DIR = CONFIG_DIR / "headers"
GENERATED_DIR = CONFIG_DIR / "generated"
KNOWLEDGE_FILE = CONFIG_DIR / "knowledge" / "learned_headers.json"
RUN_INDEX_FILE = CONFIG_DIR / "history" / "runs_index.json"
SUPABASE_SETTINGS = load_supabase_settings(dict(st.secrets) if hasattr(st, "secrets") else {})
SUPABASE_BACKEND = SupabaseBackend(SUPABASE_SETTINGS)
OPENAI_SETTINGS = load_openai_settings(dict(st.secrets) if hasattr(st, "secrets") else {})
OPENAI_AGENT = InventoryOpenAIAgent(OPENAI_SETTINGS)


def _init_state():
    defaults = {
        "source_df": None,
        "file_meta": None,
        "analysis_config": None,
        "normalized_df": None,
        "expanded_df": None,
        "export_df": None,
        "qa_report": None,
        "latest_run_meta": None,
        "supabase_sync_enabled": SUPABASE_BACKEND.is_configured,
        "supabase_status": None,
        "supabase_hydrated": False,
        "supabase_test_result": None,
        "openai_status": None,
        "openai_requirements_result": None,
        "openai_mapping_result": None,
        "user_instructions": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def safe_preview(df, rows=20):
    if df is None or df.empty:
        st.info("No data to preview.")
        return

    preview = df.head(rows).copy()
    preview.columns = [str(column).strip() for column in preview.columns]
    preview = preview.loc[:, ~preview.columns.duplicated()]
    st.dataframe(preview, use_container_width=True)


def mapping_editor(config):
    original_mapping = config.get("mapping", [])
    rows = [
        {
            "Vendor Column": item.get("vendor_column", ""),
            "Accepted Header": item.get("accepted_header", ""),
            "Role": item.get("role", "static"),
            "Expand": bool(item.get("expand", False)),
            "Confidence": item.get("confidence", 0),
        }
        for item in original_mapping
    ]

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

    updated_mapping = []
    for original, row in zip(original_mapping, edited.to_dict("records")):
        item = dict(original)
        item["vendor_column"] = row.get("Vendor Column", "")
        item["accepted_header"] = row.get("Accepted Header", "")
        item["role"] = row.get("Role", "static")
        item["expand"] = bool(row.get("Expand", False))
        item["confidence"] = row.get("Confidence", 0)
        updated_mapping.append(item)

    config["mapping"] = updated_mapping
    return config


def _accepted_header_options(config):
    output = []
    seen = set()

    for item in config.get("mapping", []):
        accepted_header = str(item.get("accepted_header", "")).strip()
        if accepted_header and accepted_header not in seen:
            seen.add(accepted_header)
            output.append(accepted_header)

    return output


def _suggested_variant_headers(config):
    output = []
    seen = set()

    for item in config.get("mapping", []):
        accepted_header = str(item.get("accepted_header", "")).strip()
        if not accepted_header or accepted_header in seen:
            continue

        if (
            bool(item.get("expand", False))
            or str(item.get("role", "")).lower() == "variant"
            or accepted_header.lower().startswith("available ")
        ):
            seen.add(accepted_header)
            output.append(accepted_header)

    return output


def _apply_variant_preferences(config, variant_headers, static_headers):
    variant_headers = {str(value).strip() for value in variant_headers if str(value).strip()}
    static_headers = {str(value).strip() for value in static_headers if str(value).strip()}

    for item in config.get("mapping", []):
        accepted_header = str(item.get("accepted_header", "")).strip()
        if not accepted_header:
            continue

        if accepted_header in variant_headers:
            item["role"] = "variant"
            item["expand"] = True
        elif accepted_header in static_headers:
            item["role"] = "static"
            item["expand"] = False

    return config


def _parse_manual_variation_lines(text):
    manual_values = {}

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue

        header, values = line.split(":", 1)
        header = header.strip()
        serialized_values = ",".join(part.strip() for part in values.split(",") if part.strip())

        if header and serialized_values:
            manual_values[header] = serialized_values

    return manual_values


def _apply_manual_variations(df, manual_values):
    if df is None or df.empty or not manual_values:
        return df

    updated = df.copy()

    for header, value in manual_values.items():
        if header in updated.columns:
            updated[header] = updated[header].apply(lambda current: current if str(current).strip() else value)
        else:
            updated[header] = value

    return updated


def _set_supabase_status(message):
    st.session_state["supabase_status"] = message


def _set_openai_status(message):
    st.session_state["openai_status"] = message


def _active_supabase_backend():
    if SUPABASE_BACKEND.is_configured and st.session_state.get("supabase_sync_enabled"):
        return SUPABASE_BACKEND
    return None


def _test_supabase_connection():
    result = SUPABASE_BACKEND.check_connection()
    st.session_state["supabase_test_result"] = result
    if result.get("ok"):
        _set_supabase_status("Supabase connection test passed.")
    else:
        _set_supabase_status(f"Supabase connection test failed: {result.get('message', 'Unknown error')}")


def _refresh_knowledge_from_supabase():
    result = hydrate_knowledge_file(KNOWLEDGE_FILE, SUPABASE_BACKEND)
    if result.get("ok"):
        _set_supabase_status("Knowledge cache refreshed from Supabase.")
    else:
        _set_supabase_status(f"Knowledge refresh failed: {result.get('message', 'Unknown error')}")


def _push_knowledge_to_supabase():
    if st.session_state.get("analysis_config"):
        store_learned_mappings(st.session_state["analysis_config"], KNOWLEDGE_FILE, supabase_backend=SUPABASE_BACKEND)
        _set_supabase_status("Current learned mappings pushed to Supabase.")
        return

    if KNOWLEDGE_FILE.exists():
        try:
            payload = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            _set_supabase_status(f"Could not read local knowledge file: {exc}")
            return

        upload_result = SUPABASE_BACKEND.upload_bytes(
            "knowledge/learned_headers.json",
            json.dumps(payload, indent=2).encode("utf-8"),
            "application/json",
        )
        if upload_result.get("ok"):
            SUPABASE_BACKEND.upsert_rows(
                SUPABASE_BACKEND.settings.knowledge_table,
                payload if isinstance(payload, list) else [],
                on_conflict="accepted_header",
            )
            _set_supabase_status("Local knowledge file pushed to Supabase.")
        else:
            _set_supabase_status(f"Knowledge push failed: {upload_result.get('message', 'Unknown error')}")
        return

    _set_supabase_status("No local knowledge file is available yet.")


def _openai_sample_rows(df, rows=5):
    if df is None or df.empty:
        return []
    return df.head(rows).fillna("").to_dict("records")


def _accepted_headers_from_knowledge(knowledge):
    headers = []
    seen = set()
    for item in knowledge:
        accepted = str(item.get("accepted_header", "")).strip()
        if accepted and accepted not in seen:
            seen.add(accepted)
            headers.append(accepted)
    return headers


def _apply_openai_mapping_updates(config, mapping_result):
    updates = {
        str(item.get("vendor_column", "")).strip(): item
        for item in mapping_result.get("mapping_updates", [])
        if str(item.get("vendor_column", "")).strip()
    }

    recommended_variants = {
        str(item).strip() for item in mapping_result.get("recommended_variant_headers", []) if str(item).strip()
    }
    recommended_static = {
        str(item).strip() for item in mapping_result.get("recommended_static_headers", []) if str(item).strip()
    }

    for item in config.get("mapping", []):
        vendor_column = str(item.get("vendor_column", "")).strip()
        accepted_header = str(item.get("accepted_header", "")).strip()

        if vendor_column in updates:
            update = updates[vendor_column]
            item["accepted_header"] = str(update.get("accepted_header", accepted_header)).strip()
            item["role"] = str(update.get("role", item.get("role", "static"))).strip()
            item["expand"] = bool(update.get("expand", item.get("expand", False)))

        accepted_header = str(item.get("accepted_header", "")).strip()
        if accepted_header in recommended_variants:
            item["role"] = "variant"
            item["expand"] = True
        elif accepted_header in recommended_static:
            item["role"] = "static"
            item["expand"] = False

    warnings = list(config.get("warnings", []))
    for warning in mapping_result.get("warnings", []):
        if warning not in warnings:
            warnings.append(warning)
    config["warnings"] = warnings

    if mapping_result.get("inventory_type"):
        config["inventory_type"] = mapping_result["inventory_type"]

    return config


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

st.markdown(
    """
Upload any vendor inventory file, tell the AI what you want in English, review the mapping,
then create the normalized and expanded inventory.
"""
)

ensure_runtime_dirs(CONFIG_DIR)
_init_state()
if SUPABASE_BACKEND.is_configured and not st.session_state.get("supabase_hydrated"):
    hydration_result = hydrate_knowledge_file(KNOWLEDGE_FILE, SUPABASE_BACKEND)
    if hydration_result.get("ok"):
        st.session_state["supabase_status"] = "Knowledge cache refreshed from Supabase."
    st.session_state["supabase_hydrated"] = True

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
    export_profile = st.selectbox(
        "Output format",
        options=["standard", "internal"],
        format_func=lambda value: "Standard file format" if value == "standard" else "Internal tool format",
    )
    save_learning = st.toggle("Save learning and source artifacts", value=True)
    sync_to_supabase = st.toggle(
        "Sync to Supabase",
        value=st.session_state.get("supabase_sync_enabled", SUPABASE_BACKEND.is_configured),
        disabled=not SUPABASE_BACKEND.is_configured,
        help="Uploads client files, run metadata, and learned header knowledge to Supabase when configured.",
    )
    st.session_state["supabase_sync_enabled"] = sync_to_supabase

    st.divider()
    st.subheader("Storage")
    if SUPABASE_BACKEND.is_configured:
        st.success(f"Supabase ready: `{SUPABASE_SETTINGS.storage_bucket}`")
    else:
        st.caption("Supabase not configured. Local storage only.")
    if st.session_state.get("supabase_status"):
        st.caption(st.session_state["supabase_status"])

    st.divider()
    st.subheader("OpenAI")
    if OPENAI_AGENT.is_configured:
        st.success(f"OpenAI ready: `{OPENAI_SETTINGS.model}`")
    else:
        st.caption("OpenAI not configured. Add `OPENAI_API_KEY` in Streamlit secrets to enable requirement gathering and mapping fixes.")
    if st.session_state.get("openai_status"):
        st.caption(st.session_state["openai_status"])

    with st.expander("Supabase Admin", expanded=False):
        st.caption(f"URL: `{SUPABASE_SETTINGS.url or 'Not set'}`")
        st.caption(f"Bucket: `{SUPABASE_SETTINGS.storage_bucket}`")
        st.caption(f"Runs table: `{SUPABASE_SETTINGS.runs_table}`")
        st.caption(f"Knowledge table: `{SUPABASE_SETTINGS.knowledge_table}`")

        col1, col2 = st.columns(2)
        col1.button(
            "Test Connection",
            disabled=not SUPABASE_BACKEND.is_configured,
            on_click=_test_supabase_connection,
            use_container_width=True,
        )
        col2.button(
            "Refresh Knowledge",
            disabled=not SUPABASE_BACKEND.is_configured,
            on_click=_refresh_knowledge_from_supabase,
            use_container_width=True,
        )
        st.button(
            "Push Knowledge",
            disabled=not SUPABASE_BACKEND.is_configured,
            on_click=_push_knowledge_to_supabase,
            use_container_width=True,
        )

        test_result = st.session_state.get("supabase_test_result")
        if test_result:
            if test_result.get("ok"):
                st.success(test_result.get("message", "Connected"))
            else:
                st.error(test_result.get("message", "Connection failed"))

    recent_runs = load_run_history(
        RUN_INDEX_FILE,
        limit=5,
        supabase_backend=_active_supabase_backend(),
    )
    if recent_runs:
        st.divider()
        st.caption("Recent saved runs")
        for item in recent_runs:
            st.caption(f"{item.get('file_name', 'Unknown file')} -> {item.get('inventory_type', 'unknown')}")


uploaded = st.file_uploader("Upload vendor inventory", type=["csv", "tsv", "txt", "xlsx", "xls", "xlsm"])

instructions = st.text_area(
    "AI Instructions",
    height=180,
    key="user_instructions",
    placeholder=(
        "Example:\n"
        "- Convert metal values into Available Metal Type\n"
        "- Create variants only for metal, shape, and head\n"
        "- Keep Jewelry Style static\n"
        "- 14K metal price should be 500 and the rest should be 1000\n"
        "- Use description to identify jewelry type"
    ),
)

if uploaded:
    try:
        df, file_meta = read_uploaded_file(uploaded)
        st.session_state["source_df"] = df
        st.session_state["file_meta"] = file_meta
        st.success(f"Loaded {uploaded.name}: {len(df):,} rows, {len(df.columns):,} columns")
        st.subheader("Source Preview")
        safe_preview(df, 10)
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        st.stop()

    if st.button("Analyze with AI", type="primary"):
        knowledge = load_header_knowledge(HEADER_DIR)
        business_rules = parse_english_rules(st.session_state.get("user_instructions", ""))

        analyzer = AIInventoryAnalyzer(knowledge)
        config = analyzer.analyze(
            df=df,
            file_name=uploaded.name,
            instructions=st.session_state.get("user_instructions", ""),
            business_rules=business_rules,
        )

        st.session_state["analysis_config"] = config
        st.session_state["normalized_df"] = None
        st.session_state["expanded_df"] = None
        st.session_state["export_df"] = None
        st.session_state["qa_report"] = None
        st.session_state["latest_run_meta"] = None
        st.session_state["openai_mapping_result"] = None

    if OPENAI_AGENT.is_configured:
        with st.expander("OpenAI Copilot", expanded=False):
            st.caption("Use OpenAI to gather missing requirements before normalization.")
            if st.button("Gather Requirements with OpenAI", use_container_width=True):
                knowledge = load_header_knowledge(HEADER_DIR)
                accepted_headers = _accepted_headers_from_knowledge(knowledge)
                result = OPENAI_AGENT.gather_requirements(
                    file_name=uploaded.name,
                    columns=[str(column) for column in df.columns],
                    sample_rows=_openai_sample_rows(df),
                    accepted_headers=accepted_headers,
                    instructions=st.session_state.get("user_instructions", ""),
                )
                st.session_state["openai_requirements_result"] = result
                if result.get("ok"):
                    _set_openai_status("OpenAI requirement gathering completed.")
                else:
                    _set_openai_status(f"OpenAI requirement gathering failed: {result.get('message', 'Unknown error')}")

            requirements_result = st.session_state.get("openai_requirements_result")
            if requirements_result:
                if requirements_result.get("ok"):
                    data = requirements_result["data"]
                    st.write(data.get("summary", ""))
                    if data.get("missing_information"):
                        st.warning("Missing information: " + ", ".join(data["missing_information"]))
                    if data.get("follow_up_questions"):
                        st.markdown("**Follow-up questions**")
                        for item in data["follow_up_questions"]:
                            st.write(f"- {item.get('question')} ({item.get('reason')})")
                    if data.get("suggested_instructions"):
                        st.markdown("**Suggested instructions**")
                        st.code(data["suggested_instructions"])
                else:
                    st.error(requirements_result.get("message", "OpenAI request failed."))


if st.session_state["analysis_config"]:
    st.divider()
    st.subheader("AI Analysis Summary")

    config = st.session_state["analysis_config"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Detected Type", config.get("inventory_type", "unknown"))
    col2.metric("Columns Mapped", sum(1 for item in config.get("mapping", []) if item.get("accepted_header")))
    col3.metric("Low Confidence", sum(1 for item in config.get("mapping", []) if float(item.get("confidence", 0)) < 0.8))

    if config.get("warnings"):
        with st.expander("Warnings", expanded=True):
            for warning in config["warnings"]:
                st.warning(warning)

    st.subheader("Review Mapping")
    config = mapping_editor(config)
    st.session_state["analysis_config"] = config

    unmapped_columns = [item.get("vendor_column") for item in config.get("mapping", []) if not item.get("accepted_header")]
    if unmapped_columns:
        st.info(
            "These source columns still need attention: "
            + ", ".join(str(column) for column in unmapped_columns[:12])
            + ("..." if len(unmapped_columns) > 12 else "")
        )

    accepted_options = _accepted_header_options(config)
    default_variants = _suggested_variant_headers(config)

    st.subheader("Variation Setup")
    selected_variants = st.multiselect(
        "Which accepted headers should create variations?",
        options=accepted_options,
        default=default_variants,
        help="Use this when the client file is missing a ready-made variation column or when you want to force expansion.",
    )
    static_defaults = [header for header in accepted_options if header not in selected_variants]
    selected_static = st.multiselect(
        "Which accepted headers should stay static?",
        options=accepted_options,
        default=static_defaults[: min(len(static_defaults), 6)],
    )

    manual_variation_text = st.text_area(
        "Optional manual variation input",
        height=120,
        placeholder=(
            "Add values only when the source file does not provide them.\n"
            "Example:\n"
            "Available Metal Type: 14K White, 14K Yellow, Platinum\n"
            "Supported Shape Variations: Round, Oval"
        ),
    )

    with st.expander("Generated Rules JSON", expanded=False):
        st.json(config.get("business_rules", {}))

    if OPENAI_AGENT.is_configured:
        with st.expander("OpenAI Mapping Fixer", expanded=False):
            if st.button("Suggest Mapping Fixes with OpenAI", use_container_width=True):
                knowledge = load_header_knowledge(HEADER_DIR)
                accepted_headers = _accepted_headers_from_knowledge(knowledge)
                result = OPENAI_AGENT.fix_mapping(
                    file_name=config.get("file_name", "inventory.csv"),
                    instructions=st.session_state.get("user_instructions", ""),
                    mapping=config.get("mapping", []),
                    accepted_headers=accepted_headers,
                    sample_rows=_openai_sample_rows(st.session_state.get("source_df")),
                )
                st.session_state["openai_mapping_result"] = result
                if result.get("ok"):
                    _set_openai_status("OpenAI mapping suggestions are ready.")
                else:
                    _set_openai_status(f"OpenAI mapping fixer failed: {result.get('message', 'Unknown error')}")

            mapping_result = st.session_state.get("openai_mapping_result")
            if mapping_result:
                if mapping_result.get("ok"):
                    data = mapping_result["data"]
                    st.write(data.get("summary", ""))
                    if data.get("warnings"):
                        for warning in data["warnings"]:
                            st.warning(warning)
                    if data.get("mapping_updates"):
                        st.dataframe(pd.DataFrame(data["mapping_updates"]), use_container_width=True)
                    if st.button("Apply OpenAI Mapping Suggestions", use_container_width=True):
                        updated = _apply_openai_mapping_updates(config, data)
                        st.session_state["analysis_config"] = updated
                        _set_openai_status("Applied OpenAI mapping suggestions to the current config.")
                        st.rerun()
                else:
                    st.error(mapping_result.get("message", "OpenAI request failed."))

    if st.button("Create Inventory", type="primary"):
        config = _apply_variant_preferences(config, selected_variants, selected_static)
        st.session_state["analysis_config"] = config

        source_df = st.session_state["source_df"]
        manual_variations = _parse_manual_variation_lines(manual_variation_text)

        normalized_df = normalize_input_dataframe(
            source_df,
            config,
            preserve_unmapped=preserve_unmapped,
        )
        normalized_df = _apply_manual_variations(normalized_df, manual_variations)
        st.session_state["normalized_df"] = normalized_df

        if create_expanded:
            expanded_df = expand_inventory(normalized_df, config=config)
        else:
            expanded_df = normalized_df.copy()

        export_df = apply_export_profile(expanded_df, config, profile=export_profile)

        st.session_state["expanded_df"] = expanded_df
        st.session_state["export_df"] = export_df

        if run_qa:
            st.session_state["qa_report"] = build_qa_report(
                source_df=source_df,
                normalized_df=normalized_df,
                output_df=expanded_df,
                config=config,
            )
        else:
            st.session_state["qa_report"] = None

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        save_generated_config(config, GENERATED_DIR / "mapping_config.json")
        normalized_df.to_csv(GENERATED_DIR / "normalized_input.csv", index=False)
        export_df.to_csv(GENERATED_DIR / "expanded_inventory.csv", index=False)

        if save_learning:
            active_backend = _active_supabase_backend()
            store_learned_mappings(config, KNOWLEDGE_FILE, supabase_backend=active_backend)
            run_meta, _ = save_run_artifacts(
                base_dir=CONFIG_DIR,
                file_name=uploaded.name,
                file_meta={
                    **(st.session_state.get("file_meta") or {}),
                    "openai_model": OPENAI_SETTINGS.model if OPENAI_AGENT.is_configured else "",
                },
                config=config,
                normalized_df=normalized_df,
                expanded_df=export_df,
                qa_report=st.session_state["qa_report"],
                uploaded_file=uploaded,
                export_profile=export_profile,
                supabase_backend=active_backend,
            )
            st.session_state["latest_run_meta"] = run_meta
            if active_backend and run_meta.get("sync_status") == "synced":
                st.session_state["supabase_status"] = "Latest run synced to Supabase."
            elif active_backend and run_meta.get("sync_errors"):
                st.session_state["supabase_status"] = "Supabase sync completed with errors."

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

if st.session_state["export_df"] is not None:
    st.subheader("Expanded Inventory Preview")
    safe_preview(st.session_state["export_df"], 20)

    st.download_button(
        "Download expanded_inventory.csv",
        to_csv_bytes(st.session_state["export_df"]),
        "expanded_inventory.csv",
        "text/csv",
    )

    st.download_button(
        "Download expanded_inventory.xlsx",
        to_excel_bytes(st.session_state["export_df"]),
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

if st.session_state["latest_run_meta"] is not None:
    st.caption(
        f"Saved reusable run data for {st.session_state['latest_run_meta'].get('file_name')} "
        f"at {st.session_state['latest_run_meta'].get('saved_at')}."
    )
    if st.session_state["latest_run_meta"].get("sync_status"):
        st.caption(f"Supabase sync: {st.session_state['latest_run_meta'].get('sync_status')}")
