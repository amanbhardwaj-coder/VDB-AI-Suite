from __future__ import annotations

import streamlit as st

from shared.page_runner import run_tool_script
from shared.registry import TOOLS, get_tool, module_exists
from shared.theme import apply_theme
from shared.constants import VDB_LOGO_URL

st.set_page_config(
    page_title="VDB tools",
    page_icon=VDB_LOGO_URL,
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def _home_page() -> None:
    st.subheader("Open a tool")
    st.caption("Select a tool from the sidebar and it will open here automatically.")
    st.caption(f"{len(st.session_state['tool_pages'])} tools are available in this workspace.")


def _tool_page_factory(tool_key: str):
    def _page() -> None:
        run_tool_script(tool_key)

    _page.__name__ = f"{tool_key}_page"
    return _page


def _build_navigation():
    home_page = st.Page(_home_page, title="Home", default=True)

    tool_pages: dict[str, st.Page] = {}
    for tool in TOOLS:
        if not module_exists(tool):
            continue
        tool_pages[tool.key] = st.Page(
            _tool_page_factory(tool.key),
            title=tool.name,
            url_path=tool.key,
        )

    pages = [home_page, *tool_pages.values()]
    current_page = st.navigation(pages, position="hidden")
    return current_page, tool_pages


def _sync_tool_state(current_page: st.Page, tool_pages: dict[str, st.Page]) -> None:
    if "active_tool" not in st.session_state:
        st.session_state["active_tool"] = None

    tool_keys_by_path = {page.url_path: key for key, page in tool_pages.items()}
    active_key = tool_keys_by_path.get(current_page.url_path)
    if active_key:
        st.session_state["active_tool"] = active_key

    st.session_state["tool_pages"] = tool_pages


def _activate_tool(tool_key: str, tool_pages: dict[str, st.Page]) -> None:
    tool = get_tool(tool_key)
    if not tool:
        return
    st.session_state["active_tool"] = tool.key
    if tool.key in tool_pages:
        st.switch_page(tool_pages[tool.key])


def _sidebar(current_page: st.Page, tool_pages: dict[str, st.Page]) -> None:
    with st.sidebar:
        st.markdown(
            f"""
<div class="vdb-sidebar-brand" style="display:flex; flex-direction:column; align-items:center; gap:0.65rem; margin-bottom:0.35rem;">
  <img src="{VDB_LOGO_URL}" alt="VDB logo" style="width:5rem; height:5rem;" />
  <div style="font-size:1.55rem; font-weight:700; line-height:1;">VDB tools</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Choose a tool and run it in this app.")

        st.markdown("---")

        visible_tools = TOOLS
        visible_keys = [tool.key for tool in visible_tools]
        active_key = st.session_state.get("active_tool")
        tool_keys_by_path = {page.url_path: key for key, page in tool_pages.items()}
        selected_index = None
        if active_key in visible_keys and current_page.url_path in tool_keys_by_path:
            selected_index = visible_keys.index(active_key)

        selected_tool = st.selectbox(
            "Tool",
            visible_keys,
            index=selected_index,
            placeholder="Select a tool",
            format_func=lambda key: _tool_option_label(key),
        )

        selected_tool_obj = get_tool(selected_tool) if selected_tool else None
        if selected_tool_obj:
            st.caption(selected_tool_obj.description)

        if selected_tool and selected_tool != active_key:
            st.session_state["active_tool"] = selected_tool
            _activate_tool(selected_tool, tool_pages)
        elif selected_tool:
            st.session_state["active_tool"] = selected_tool


def _tool_option_label(tool_key: str) -> str:
    tool = get_tool(tool_key)
    if not tool:
        return tool_key
    return tool.name


def main() -> None:
    current_page, tool_pages = _build_navigation()
    _sync_tool_state(current_page, tool_pages)
    _sidebar(current_page, tool_pages)
    current_page.run()


if __name__ == "__main__":
    main()
