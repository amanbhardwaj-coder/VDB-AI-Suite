#!/usr/bin/env python3
"""VDB AI Suite dashboard.

Run locally:
    streamlit run Dashboard.py

This dashboard keeps the Smiling Rocks converter inside this repo and gives
quick launch cards for the other public automation repos.
"""

from __future__ import annotations

import importlib
import io
import re
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd
import streamlit as st
from shared.constants import VDB_LOGO_URL


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="VDB Tools",
    page_icon=VDB_LOGO_URL,
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .main > div { padding-top: 1.4rem; }
        .vdb-hero {
            padding: 1.6rem 1.8rem;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(47, 105, 255, .14), rgba(168, 85, 247, .12));
            border: 1px solid rgba(120, 120, 160, .22);
            margin-bottom: 1.1rem;
        }
        .vdb-hero h1 { margin: 0; font-size: 2.25rem; line-height: 1.1; }
        .vdb-hero p { margin: .55rem 0 0 0; opacity: .78; font-size: 1rem; }
        .tool-card {
            padding: 1.05rem 1.1rem;
            border: 1px solid rgba(120, 120, 160, .22);
            border-radius: 18px;
            background: rgba(255, 255, 255, .035);
            min-height: 142px;
            margin-bottom: 1rem;
        }
        .tool-card h3 { margin: 0 0 .35rem 0; font-size: 1.05rem; }
        .tool-card p { margin: 0 0 .75rem 0; opacity: .75; font-size: .9rem; }
        .tool-pill {
            display: inline-block;
            padding: .18rem .52rem;
            border-radius: 999px;
            background: rgba(47, 105, 255, .14);
            border: 1px solid rgba(47, 105, 255, .22);
            font-size: .75rem;
            margin-right: .25rem;
        }
        .small-muted { opacity: .68; font-size: .86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Tool registry
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ToolLink:
    name: str
    category: str
    description: str
    repo_url: str
    status: str = "Repo"


TOOLS = [
    ToolLink(
        "Smiling Rocks Converter",
        "Inventory",
        "MFG pricing workbook to VDB CSV converter with image URL mapping.",
        "https://github.com/amanbhardwaj-coder/Smiling_Rocks",
        "Built in",
    ),
    ToolLink(
        "Inventory Tool AI",
        "Inventory",
        "AI-assisted inventory normalization and VDB-format output builder.",
        "https://github.com/amanbhardwaj-coder/inventory-toolAI",
    ),
    ToolLink(
        "Inventory Tool 2.0",
        "Inventory",
        "Inventory expansion workflow for jewelry variations and output fields.",
        "https://github.com/amanbhardwaj-coder/inventory-tool2.0",
    ),
    ToolLink(
        "Inventory Tool",
        "Inventory",
        "Earlier inventory conversion utility.",
        "https://github.com/amanbhardwaj-coder/inventory-tool",
    ),
    ToolLink(
        "File Merge",
        "Excel",
        "Merge CSV/XLSX files and align matching columns into one output.",
        "https://github.com/amanbhardwaj-coder/file_merge",
    ),
    ToolLink(
        "Excel Splitter",
        "Excel",
        "Split large Excel files into smaller files for upload or review.",
        "https://github.com/amanbhardwaj-coder/Excelsplitter",
    ),
    ToolLink(
        "URL Checker",
        "Images",
        "Check image/video/file URLs and report working or broken links.",
        "https://github.com/amanbhardwaj-coder/URL_Checker",
    ),
    ToolLink(
        "JSON to CSV",
        "JSON",
        "Convert JSON payload/config data into CSV format.",
        "https://github.com/amanbhardwaj-coder/Jsontocsv",
    ),
    ToolLink(
        "Jewelry Filter Creation",
        "JSON",
        "Create jewelry filter/dependency configuration payloads.",
        "https://github.com/amanbhardwaj-coder/Jewelry_filter_creation",
    ),
    ToolLink(
        "JL",
        "Jewelry",
        "Jewelry-specific helper utility.",
        "https://github.com/amanbhardwaj-coder/JL",
    ),
]


# -----------------------------------------------------------------------------
# Safe import of the existing app.py conversion core
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_smiling_core():
    """Import app.py without letting its standalone Streamlit UI auto-render.

    app.py currently renders its UI whenever it detects a Streamlit runtime.
    For this dashboard we only need its conversion functions, so we temporarily
    make get_script_run_ctx() return None during import.
    """
    try:
        import streamlit.runtime.scriptrunner as scriptrunner

        original_get_ctx = scriptrunner.get_script_run_ctx
        scriptrunner.get_script_run_ctx = lambda: None
        try:
            return importlib.import_module("app")
        finally:
            scriptrunner.get_script_run_ctx = original_get_ctx
    except Exception as exc:  # pragma: no cover - surfaced in UI
        return exc


# -----------------------------------------------------------------------------
# Shared UI helpers
# -----------------------------------------------------------------------------
def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="vdb-hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_card(tool: ToolLink) -> None:
    st.markdown(
        f"""
        <div class="tool-card">
            <h3>{tool.name}</h3>
            <p>{tool.description}</p>
            <span class="tool-pill">{tool.category}</span>
            <span class="tool-pill">{tool.status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.link_button("Open repo", tool.repo_url, use_container_width=True)


def render_status_table() -> None:
    df = pd.DataFrame(
        [
            {
                "Tool": t.name,
                "Category": t.category,
                "Status": t.status,
                "Repo": t.repo_url,
            }
            for t in TOOLS
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# Built-in Smiling Rocks converter page
# -----------------------------------------------------------------------------
def smiling_rocks_converter() -> None:
    core = _load_smiling_core()
    if isinstance(core, Exception):
        st.error(f"Could not load Smiling Rocks converter core: {core}")
        return

    hero(
        "💎 Smiling Rocks Converter",
        "Upload MFG pricing files, optionally upload the image filename list, and download the VDB-ready CSV.",
    )

    with st.sidebar:
        st.subheader("Converter settings")
        collection = st.text_input(
            "Collection / Config Field 13",
            value=getattr(core, "DEFAULT_COLLECTION", "Essential"),
            help="Example: Essential, Smiling Brides, Fashion.",
        ).strip() or getattr(core, "DEFAULT_COLLECTION", "Essential")

        st.markdown("---")
        remark_map = getattr(core, "REMARK_MAP", {})
        st.caption(f"Mapped remarks: {len(remark_map)}")
        with st.expander("View remark map"):
            if remark_map:
                rm_df = pd.DataFrame(
                    [(k, v[0], v[1], v[2]) for k, v in remark_map.items()],
                    columns=["MFG Remark", "Sub-Cat rule", "Config Field 14", "Jewelry Style"],
                ).sort_values("MFG Remark").reset_index(drop=True)
                st.dataframe(rm_df, use_container_width=True, hide_index=True)
            else:
                st.info("No remark map found.")

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("1. MFG file(s)")
        mfg_files = st.file_uploader(
            "Client quotation workbook (.xlsx). Multiple files allowed.",
            type=["xlsx"],
            accept_multiple_files=True,
            key="dashboard_mfg_files",
        )
    with col_r:
        st.subheader("2. Image list")
        img_file = st.file_uploader(
            "Single-column CSV of image filenames, for example SRR-00023WHT_W1.jpg.",
            type=["csv"],
            accept_multiple_files=False,
            key="dashboard_img_file",
        )

    run = st.button(
        "Convert to VDB CSV",
        type="primary",
        disabled=not mfg_files,
        use_container_width=True,
    )

    if not mfg_files:
        st.info("Upload at least one MFG .xlsx file to enable conversion.")

    if run:
        image_map, img_stats = {}, {"accepted": 0, "skipped": 0, "skip_samples": {}}
        if img_file is not None:
            try:
                image_map, img_stats = core.load_image_map(io.BytesIO(img_file.getvalue()))
            except Exception as exc:
                st.error(f"Could not read the image list: {exc}")
                st.stop()

        try:
            inputs = [io.BytesIO(f.getvalue()) for f in mfg_files]
            with st.spinner("Parsing MFG sheets and building VDB rows..."):
                df, unknown = core.convert(inputs, image_map, collection=collection)
        except Exception as exc:
            st.error(f"Conversion failed: {exc}")
            st.stop()

        st.session_state["sr_result_df"] = df
        st.session_state["sr_unknown"] = sorted(unknown)
        st.session_state["sr_img_stats"] = img_stats
        st.session_state["sr_img_used"] = img_file is not None
        st.session_state["sr_collection"] = collection

    if "sr_result_df" not in st.session_state:
        return

    df = st.session_state["sr_result_df"]
    unknown = st.session_state["sr_unknown"]
    img_stats = st.session_state["sr_img_stats"]
    img_used = st.session_state["sr_img_used"]
    coll_used = st.session_state["sr_collection"]

    st.markdown("---")
    st.subheader("Results")

    unique_styles = df["Stock Number"].str.replace(r"-..K[WYR]$", "", regex=True).nunique() if "Stock Number" in df else 0
    rows_with_img = (df["Image Url 1"] != "").sum() if "Image Url 1" in df else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Unique styles", f"{unique_styles:,}")
    c3.metric(
        "Rows with image",
        f"{rows_with_img:,} / {len(df):,}",
        delta=f"{(rows_with_img / len(df) * 100):.1f}%" if len(df) else None,
        delta_color="off",
    )
    c4.metric(
        "Image codes accepted",
        f"{img_stats['accepted']:,}" if img_used else "—",
        delta=f"{img_stats['skipped']:,} skipped" if img_used else None,
        delta_color="off",
    )

    if unknown:
        with st.expander(f"⚠️ {len(unknown)} unmapped MFG remark(s)", expanded=True):
            st.write(
                "These remarks were defaulted in Config Field 14 / Jewelry Style. "
                "Add them to REMARK_MAP in app.py when you want fixed mapping."
            )
            st.code("\n".join(unknown))

    if img_used and img_stats.get("skip_samples"):
        with st.expander(f"Skipped image-list entries: {img_stats['skipped']}"):
            top = sorted(img_stats["skip_samples"].items())[:25]
            st.code("\n".join(f"{code!r:14}  {fn}" for code, fn in top))

    st.markdown("**Preview** — first 100 rows")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    fname_slug = re.sub(r"[^A-Za-z0-9_-]+", "_", coll_used) or "VDB"
    st.download_button(
        "⬇️ Download VDB CSV",
        data=csv_bytes,
        file_name=f"VDB_{fname_slug}_Output.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )


# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------
def home_page() -> None:
    hero(
        "🚀 VDB AI Suite",
        "One dashboard for inventory conversion, Excel utilities, URL checks, JSON tools, and jewelry automation helpers.",
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total tools", len(TOOLS))
    m2.metric("Built-in tools", 1)
    m3.metric("Categories", len(set(t.category for t in TOOLS)))
    m4.metric("Repos linked", len(TOOLS))

    st.markdown("### Quick launch")
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("💎 Open Smiling Rocks Converter", use_container_width=True, type="primary"):
            st.session_state["selected_page"] = "💎 Smiling Rocks Converter"
            st.rerun()
    with q2:
        st.link_button("📄 Open File Merge repo", "https://github.com/amanbhardwaj-coder/file_merge", use_container_width=True)
    with q3:
        st.link_button("🖼 Open URL Checker repo", "https://github.com/amanbhardwaj-coder/URL_Checker", use_container_width=True)

    st.markdown("### Tool library")
    selected_category = st.selectbox(
        "Filter by category",
        ["All"] + sorted(set(t.category for t in TOOLS)),
        index=0,
    )
    filtered = [t for t in TOOLS if selected_category == "All" or t.category == selected_category]

    for i in range(0, len(filtered), 3):
        cols = st.columns(3)
        for col, tool in zip(cols, filtered[i : i + 3]):
            with col:
                render_tool_card(tool)


def repository_page() -> None:
    hero("📚 Repository Center", "All connected automation repositories in one view.")
    render_status_table()

    st.markdown("### Next integration step")
    st.info(
        "Right now, Smiling Rocks is built into this dashboard. The other tools are linked as repos. "
        "To make them run inside this same dashboard, add each repo as a module/submodule and expose a run() function in its Streamlit app."
    )

    st.code(
        """git submodule add https://github.com/amanbhardwaj-coder/file_merge modules/file_merge
git submodule add https://github.com/amanbhardwaj-coder/URL_Checker modules/URL_Checker
git submodule add https://github.com/amanbhardwaj-coder/inventory-toolAI modules/inventory-toolAI""",
        language="bash",
    )


def about_page() -> None:
    hero("⚙️ Dashboard Notes", "How to run and extend the VDB AI Suite.")
    st.markdown(
        """
        **Run this dashboard**

        ```bash
        streamlit run Dashboard.py
        ```

        **Current setup**

        - Smiling Rocks converter runs directly inside the dashboard.
        - Other automation apps are available as launch cards.
        - No extra Python dependency was added beyond the existing Streamlit, pandas, and openpyxl stack.

        **To fully combine another Streamlit repo**

        1. Add that repo under `modules/<tool_name>`.
        2. Wrap its existing Streamlit code in a `run()` function.
        3. Import and call that `run()` function from this dashboard.
        """
    )


# -----------------------------------------------------------------------------
# Main router
# -----------------------------------------------------------------------------
def main() -> None:
    pages: dict[str, Callable[[], None]] = {
        "🏠 Home": home_page,
        "💎 Smiling Rocks Converter": smiling_rocks_converter,
        "📚 Repository Center": repository_page,
        "⚙️ Dashboard Notes": about_page,
    }

    if "selected_page" not in st.session_state:
        st.session_state["selected_page"] = "🏠 Home"

    with st.sidebar:
        st.title("VDB AI Suite")
        selected = st.radio(
            "Navigation",
            list(pages.keys()),
            index=list(pages.keys()).index(st.session_state["selected_page"]),
        )
        st.session_state["selected_page"] = selected
        st.markdown("---")
        st.caption("Built-in: Smiling Rocks Converter")
        st.caption("Linked repos: Inventory, Excel, URL, JSON, Jewelry tools")

    pages[st.session_state["selected_page"]]()


if __name__ == "__main__":
    main()
