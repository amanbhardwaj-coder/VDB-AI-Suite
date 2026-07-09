from __future__ import annotations

from pathlib import Path

import streamlit as st

from shared.module_runner import render_tool_app
from shared.registry import TOOLS, categories, get_tool, module_exists
from shared.theme import apply_theme
from shared.ui import section_title


st.set_page_config(
    page_title="VDB AI Suite",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


HOME_PAGE = "🏠 Home"


if "page" not in st.session_state:
    st.session_state["page"] = HOME_PAGE
if "active_tool" not in st.session_state:
    st.session_state["active_tool"] = "smiling_rocks"
if "tool_category" not in st.session_state:
    default_tool = get_tool(st.session_state["active_tool"])
    st.session_state["tool_category"] = default_tool.category if default_tool else "All"


def activate_tool(tool_key: str) -> None:
    tool = get_tool(tool_key)
    if not tool:
        return
    st.session_state["page"] = HOME_PAGE
    st.session_state["active_tool"] = tool.key
    st.session_state["tool_category"] = tool.category


def tool_option_label(tool_key: str) -> str:
    tool = get_tool(tool_key)
    if not tool:
        return tool_key
    status = "ready" if module_exists(tool) else "missing"
    return f"{tool.icon} {tool.name} ({status})"


def sidebar() -> None:
    with st.sidebar:
        st.markdown("# 💎 VDB AI Suite")
        st.caption("Choose a tool and run it below.")
        st.markdown("---")
        st.caption("Home")
        st.session_state["page"] = HOME_PAGE

        st.markdown("---")
        st.caption("Tool selector")

        category_options = ["All"] + categories()
        if st.session_state.get("tool_category") not in category_options:
            st.session_state["tool_category"] = "All"

        selected_category = st.selectbox("Category", category_options, key="tool_category")
        visible_tools = [
            tool
            for tool in TOOLS
            if selected_category == "All" or tool.category == selected_category
        ]

        if not visible_tools:
            st.info("No tools found in this category.")
        else:
            visible_keys = [tool.key for tool in visible_tools]
            if st.session_state.get("active_tool") not in visible_keys:
                st.session_state["active_tool"] = visible_keys[0]

            selected_tool = st.selectbox(
                "Tool",
                visible_keys,
                index=visible_keys.index(st.session_state["active_tool"]),
                format_func=tool_option_label,
            )
            st.session_state["active_tool"] = selected_tool

            active_tool = get_tool(selected_tool)
            if active_tool:
                st.caption(active_tool.description)

        st.markdown("---")
        st.caption("Quick launch")
        quick_cols = st.columns(2)
        with quick_cols[0]:
            if st.button("💎 SR", use_container_width=True):
                activate_tool("smiling_rocks")
                st.rerun()
        with quick_cols[1]:
            if st.button("📄 Merge", use_container_width=True):
                activate_tool("file_merge")
                st.rerun()


def home_page() -> None:
    st.subheader("Tool Launcher")
    st.caption("Select a tool from the left and it will open here.")
    render_active_tool()


def render_active_tool() -> None:
    tool = get_tool(st.session_state.get("active_tool", "smiling_rocks"))

    if not tool:
        st.error("Tool not found in registry.")
        return

    title_col, repo_col = st.columns([4, 1])
    with title_col:
        st.subheader(f"{tool.icon} {tool.name}")
        st.caption(tool.description)
        st.caption(
            f"{tool.category} | {Path(tool.module_path).name} | {'Ready' if module_exists(tool) else 'Missing'}"
        )
    with repo_col:
        st.link_button("Open repository", tool.repo_url, use_container_width=True)

    if not module_exists(tool):
        st.error(f"Module folder not found: `{tool.module_path}`")
        return

    section_title("Live app")
    render_tool_app(tool, height=980)


def main() -> None:
    sidebar()
    home_page()


if __name__ == "__main__":
    main()
