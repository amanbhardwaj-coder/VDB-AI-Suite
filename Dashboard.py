from __future__ import annotations

from pathlib import Path

import streamlit as st

from shared.page_runner import run_tool_script
from shared.registry import TOOLS, categories, get_tool, module_exists
from shared.theme import apply_theme


st.set_page_config(
    page_title="VDB AI Suite",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def _home_page() -> None:
    tool = get_tool(st.session_state.get("active_tool", "smiling_rocks"))

    st.subheader("Tool Launcher")
    st.caption("Pick a tool from the sidebar, then open it in this app.")

    if not tool:
        st.error("Tool not found in registry.")
        return

    title_col, action_col = st.columns([4, 1])
    with title_col:
        st.subheader(f"{tool.icon} {tool.name}")
        st.caption(tool.description)
        st.caption(
            f"{tool.category} | {Path(tool.module_path).name} | {'Ready' if module_exists(tool) else 'Missing'}"
        )
    with action_col:
        st.link_button("Open repository", tool.repo_url, use_container_width=True)

    open_label = f"Open {tool.name}"
    if st.button(
        open_label,
        use_container_width=True,
        type="primary",
        disabled=tool.key not in st.session_state["tool_pages"],
    ):
        st.switch_page(st.session_state["tool_pages"][tool.key])

    if tool.key not in st.session_state["tool_pages"]:
        st.error(f"Module folder not found: `{tool.module_path}`")
        return

    st.info("This launcher opens each tool as a real Streamlit page so it works on the live deployment too.")


def _tool_page_factory(tool_key: str):
    def _page() -> None:
        run_tool_script(tool_key)

    _page.__name__ = f"{tool_key}_page"
    return _page


def _build_navigation():
    home_page = st.Page(_home_page, title="Home", icon="💎", default=True)

    tool_pages: dict[str, st.Page] = {}
    for tool in TOOLS:
        if not module_exists(tool):
            continue
        tool_pages[tool.key] = st.Page(
            _tool_page_factory(tool.key),
            title=tool.name,
            icon=tool.icon,
            url_path=tool.key,
        )

    pages = [home_page, *tool_pages.values()]
    current_page = st.navigation(pages, position="hidden")
    return current_page, home_page, tool_pages


def _sync_tool_state(current_page: st.Page, tool_pages: dict[str, st.Page]) -> None:
    if "active_tool" not in st.session_state:
        st.session_state["active_tool"] = "smiling_rocks"
    if "tool_category" not in st.session_state:
        active_tool = get_tool(st.session_state["active_tool"])
        st.session_state["tool_category"] = active_tool.category if active_tool else "All"

    tool_keys_by_path = {page.url_path: key for key, page in tool_pages.items()}
    active_key = tool_keys_by_path.get(current_page.url_path)
    if active_key:
        tool = get_tool(active_key)
        st.session_state["active_tool"] = active_key
        if tool:
            st.session_state["tool_category"] = tool.category

    st.session_state["tool_pages"] = tool_pages


def _activate_tool(tool_key: str, tool_pages: dict[str, st.Page]) -> None:
    tool = get_tool(tool_key)
    if not tool:
        return
    st.session_state["active_tool"] = tool.key
    st.session_state["tool_category"] = tool.category
    if tool.key in tool_pages:
        st.switch_page(tool_pages[tool.key])


def _sidebar(current_page: st.Page, home_page: st.Page, tool_pages: dict[str, st.Page]) -> None:
    with st.sidebar:
        st.markdown("# 💎 VDB AI Suite")
        st.caption("Choose a tool and run it in this app.")

        if current_page.url_path:
            st.markdown("---")
            if st.button("← Home", use_container_width=True):
                st.switch_page(home_page)

        st.markdown("---")
        st.caption("Tool selector")

        category_options = ["All"] + categories()
        current_category = st.session_state.get("tool_category", "All")
        if current_category not in category_options:
            current_category = "All"

        selected_category = st.selectbox("Category", category_options, index=category_options.index(current_category))
        st.session_state["tool_category"] = selected_category

        visible_tools = [
            tool
            for tool in TOOLS
            if selected_category == "All" or tool.category == selected_category
        ]

        if not visible_tools:
            st.info("No tools found in this category.")
            return

        visible_keys = [tool.key for tool in visible_tools]
        active_key = st.session_state.get("active_tool", visible_keys[0])
        if active_key not in visible_keys:
            active_key = visible_keys[0]
            st.session_state["active_tool"] = active_key

        selected_tool = st.selectbox(
            "Tool",
            visible_keys,
            index=visible_keys.index(active_key),
            format_func=lambda key: _tool_option_label(key),
        )
        st.session_state["active_tool"] = selected_tool

        selected_tool_obj = get_tool(selected_tool)
        if selected_tool_obj:
            st.caption(selected_tool_obj.description)

        open_disabled = selected_tool not in tool_pages
        if st.button("Open selected tool", use_container_width=True, type="primary", disabled=open_disabled):
            _activate_tool(selected_tool, tool_pages)

        st.markdown("---")
        st.caption("Quick launch")
        quick_cols = st.columns(2)
        with quick_cols[0]:
            if st.button("💎 SR", use_container_width=True):
                _activate_tool("smiling_rocks", tool_pages)
        with quick_cols[1]:
            if st.button("📄 Merge", use_container_width=True):
                _activate_tool("file_merge", tool_pages)


def _tool_option_label(tool_key: str) -> str:
    tool = get_tool(tool_key)
    if not tool:
        return tool_key
    status = "ready" if module_exists(tool) else "missing"
    return f"{tool.icon} {tool.name} ({status})"


def main() -> None:
    current_page, home_page, tool_pages = _build_navigation()
    _sync_tool_state(current_page, tool_pages)
    _sidebar(current_page, home_page, tool_pages)
    current_page.run()


if __name__ == "__main__":
    main()
