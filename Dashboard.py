from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from shared.module_runner import render_tool_app
from shared.registry import TOOLS, categories, get_tool, module_exists
from shared.theme import apply_theme
from shared.ui import command_block, hero, render_tool_grid, repo_table, section_title


st.set_page_config(
    page_title="VDB AI Suite",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


PAGE_OPTIONS = [
    "🚀 Run Tool",
    "🏠 Home",
    "📚 Repository Center",
    "🧭 Roadmap",
    "⚙️ Settings",
]


if "page" not in st.session_state:
    st.session_state["page"] = "🚀 Run Tool"
if "active_tool" not in st.session_state:
    st.session_state["active_tool"] = "smiling_rocks"
if "favorites_only" not in st.session_state:
    st.session_state["favorites_only"] = False


def sidebar() -> None:
    with st.sidebar:
        st.markdown("# 💎 VDB AI Suite")
        st.caption("Internal automation dashboard")
        st.markdown("---")

        selected = st.radio(
            "Navigation",
            PAGE_OPTIONS,
            index=PAGE_OPTIONS.index(st.session_state["page"]) if st.session_state["page"] in PAGE_OPTIONS else 0,
            label_visibility="collapsed",
        )
        st.session_state["page"] = selected

        st.markdown("---")
        st.caption("Select tool")
        tool_keys = [tool.key for tool in TOOLS]
        selected_tool = st.selectbox(
            "Tool",
            tool_keys,
            index=tool_keys.index(st.session_state.get("active_tool", "smiling_rocks")) if st.session_state.get("active_tool") in tool_keys else 0,
            format_func=lambda key: get_tool(key).name if get_tool(key) else key,
            label_visibility="collapsed",
        )
        if selected_tool != st.session_state.get("active_tool"):
            st.session_state["active_tool"] = selected_tool
            st.session_state["page"] = "🚀 Run Tool"
            st.rerun()

        selected_tool_obj = get_tool(st.session_state["active_tool"])
        if selected_tool_obj:
            if module_exists(selected_tool_obj):
                st.success("Module found")
            else:
                st.error("Module missing")
            st.caption(f"Path: `{selected_tool_obj.module_path}`")

        st.markdown("---")
        st.caption("Quick launch")
        quick_cols = st.columns(2)
        with quick_cols[0]:
            if st.button("💎 SR", use_container_width=True):
                st.session_state["page"] = "🚀 Run Tool"
                st.session_state["active_tool"] = "smiling_rocks"
                st.rerun()
        with quick_cols[1]:
            if st.button("📄 Merge", use_container_width=True):
                st.session_state["page"] = "🚀 Run Tool"
                st.session_state["active_tool"] = "file_merge"
                st.rerun()

        st.markdown("---")
        local_count = sum(1 for tool in TOOLS if module_exists(tool))
        st.metric("Registered tools", len(TOOLS))
        st.metric("Local modules", local_count)
        st.caption(f"Last opened: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")


def run_tool_page() -> None:
    tool = get_tool(st.session_state.get("active_tool", "smiling_rocks"))
    if not tool:
        st.error("Selected tool not found in registry.")
        return

    top = st.columns([1.4, 1])
    with top[0]:
        st.markdown(f"## {tool.icon} {tool.name}")
        st.caption(tool.description)
    with top[1]:
        st.markdown("#### Tool status")
        st.write("✅ Local module found" if module_exists(tool) else "❌ Module folder missing")

    if not module_exists(tool):
        st.error(f"Module folder not found: `{tool.module_path}`")
        st.info("Make sure the uploaded module folder name matches the path in `shared/registry.py`.")
        st.link_button("Open repository", tool.repo_url, use_container_width=True)
        return

    # This is the important part: the selected app runs below and behaves like its old standalone Streamlit app.
    render_tool_app(tool, height=950)


def home_page() -> None:
    local_count = sum(1 for tool in TOOLS if module_exists(tool))
    fav_tools = [tool for tool in TOOLS if tool.favorite]

    hero(
        "VDB AI Suite",
        "A single command center for inventory conversion, Excel utilities, URL checks, JSON helpers, jewelry configuration, and client-specific automation tools.",
        ["Streamlit", "Automation", "VDB workflows", "Modular tools"],
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tools", len(TOOLS))
    c2.metric("Categories", len(categories()))
    c3.metric("Local modules", f"{local_count}/{len(TOOLS)}")
    c4.metric("Favorites", len(fav_tools))

    section_title("Quick actions", "Start from the tools you use most")
    q1, q2, q3, q4 = st.columns(4)
    quick_actions = [
        ("💎 Smiling Rocks", "smiling_rocks"),
        ("📦 Inventory AI", "inventory_ai"),
        ("📄 File Merge", "file_merge"),
        ("🖼️ URL Checker", "url_checker"),
    ]
    for col, (label, key) in zip([q1, q2, q3, q4], quick_actions):
        with col:
            if st.button(label, key=f"quick_{key}", use_container_width=True, type="primary" if key == "smiling_rocks" else "secondary"):
                st.session_state["page"] = "🚀 Run Tool"
                st.session_state["active_tool"] = key
                st.rerun()

    section_title("Favorite tools", "Pinned for faster access")
    render_tool_grid(fav_tools)

    section_title("System status", "What is ready right now")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown(
            """
<div class="vdb-timeline">
  <div class="vdb-step"><b>Sidebar dropdown</b><span>Select any tool from the sidebar and run it directly.</span></div>
  <div class="vdb-step"><b>Modules uploaded</b><span>The dashboard detects modules under the modules/ folder.</span></div>
  <div class="vdb-step"><b>Standalone behavior</b><span>Each selected app is started as its own Streamlit app and embedded inside the dashboard.</span></div>
</div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        command_block("streamlit run Dashboard.py")


def repository_page() -> None:
    hero(
        "Repository Center",
        "All registered automation repositories, local module paths, and current integration states in one table.",
        ["Modules", "GitHub", "Status"],
    )
    repo_table(TOOLS)

    section_title("Module setup", "Run this locally after cloning the dashboard repo")
    command_block("bash scripts/setup_modules.sh")

    section_title("Expected module folders", "The dashboard checks these paths at runtime")
    for tool in TOOLS:
        icon = "✅" if module_exists(tool) else "⭕"
        st.write(f"{icon} `{tool.module_path}` — {tool.name}")


def roadmap_page() -> None:
    hero(
        "Roadmap",
        "A practical build path to turn this from a launcher into a full internal automation platform.",
        ["Phase plan", "Adapters", "Shared components"],
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
### Current — Standalone app runner
- Sidebar dropdown selects the tool
- Selected app starts on its own Streamlit port
- App is embedded in the dashboard
- Existing app behavior is preserved

### Next — Native adapters
- Remove iframe nesting
- One shared sidebar
- Shared upload/download manager
            """
        )
    with c2:
        st.markdown(
            """
### Priority integrations
- Smiling Rocks Converter
- File Merge
- URL Checker
- Excel Splitter
- Inventory Tool AI
- Jewelry Filter Builder
            """
        )

    section_title("Current runner", "Apps are started as child Streamlit apps and embedded below the shell")
    st.code(
        """python -m streamlit run modules/<tool>/app.py --server.port <free_port>""",
        language="bash",
    )


def settings_page() -> None:
    hero(
        "Settings",
        "Dashboard-level preferences and setup notes.",
        ["Theme", "Runtime", "Modules"],
    )

    st.markdown("### Runtime")
    st.write(f"Working directory: `{Path.cwd()}`")
    st.write(f"Registered tools: `{len(TOOLS)}`")
    st.write(f"Local modules detected: `{sum(1 for tool in TOOLS if module_exists(tool))}`")

    st.markdown("### Recommended local commands")
    command_block(
        """python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run Dashboard.py"""
    )


def main() -> None:
    sidebar()
    page = st.session_state["page"]
    if page == "🚀 Run Tool":
        run_tool_page()
    elif page == "🏠 Home":
        home_page()
    elif page == "📚 Repository Center":
        repository_page()
    elif page == "🧭 Roadmap":
        roadmap_page()
    elif page == "⚙️ Settings":
        settings_page()
    else:
        run_tool_page()


if __name__ == "__main__":
    main()
