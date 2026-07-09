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
    "🏠 Home",
    "🧰 Tools",
    "📚 Repository Center",
    "🧭 Roadmap",
    "⚙️ Settings",
]


if "page" not in st.session_state:
    st.session_state["page"] = "🏠 Home"
if "active_tool" not in st.session_state:
    st.session_state["active_tool"] = "smiling_rocks"
if "favorites_only" not in st.session_state:
    st.session_state["favorites_only"] = False
if "tool_category" not in st.session_state:
    default_tool = get_tool(st.session_state["active_tool"])
    st.session_state["tool_category"] = default_tool.category if default_tool else "All"


def activate_tool(tool_key: str) -> None:
    tool = get_tool(tool_key)
    if not tool:
        return
    st.session_state["page"] = "🧰 Tools"
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

        if st.session_state["page"] == "🧰 Tools":
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
        local_count = sum(1 for tool in TOOLS if module_exists(tool))
        st.metric("Registered tools", len(TOOLS))
        st.metric("Local modules", local_count)
        st.caption(f"Last opened: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")


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
                activate_tool(key)
                st.rerun()

    section_title("Favorite tools", "Pinned for faster access")
    render_tool_grid(fav_tools)

    section_title("System status", "What is ready right now")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown(
            """
<div class="vdb-timeline">
  <div class="vdb-step"><b>Dashboard shell</b><span>Polished UI, navigation, search, repository center, and roadmap are ready.</span></div>
  <div class="vdb-step"><b>Modules uploaded</b><span>The dashboard detects modules under the modules/ folder.</span></div>
  <div class="vdb-step"><b>Apps runnable</b><span>Registered module apps can now be launched inside the dashboard iframe.</span></div>
</div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        command_block("streamlit run Dashboard.py")


def tools_page() -> None:
    tool = get_tool(st.session_state.get("active_tool", "smiling_rocks"))

    if not tool:
        st.error("Tool not found in registry.")
        return

    title_col, repo_col = st.columns([4, 1])
    with title_col:
        st.subheader(f"{tool.icon} {tool.name}")
        st.caption(tool.description)
        st.caption("Use the sidebar dropdown to switch tools. The embedded app below keeps the same workflow as before.")
    with repo_col:
        st.link_button("Open repository", tool.repo_url, use_container_width=True)

    info_cols = st.columns(3)
    info_cols[0].metric("Category", tool.category)
    info_cols[1].metric("Module", Path(tool.module_path).name)
    info_cols[2].metric("Status", "Ready" if module_exists(tool) else "Missing")

    if not module_exists(tool):
        st.error(f"Module folder not found: `{tool.module_path}`")
        return

    section_title("Live app", "Compact workspace with the tool selector moved into the sidebar")
    render_tool_app(tool, height=980)


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
### Phase 1 — Dashboard shell
- Polished UI and navigation
- Tool registry
- Search and filters
- Repository center
- Module detection
- Iframe app runner

### Phase 2 — Better adapters
- Smiling Rocks native integration
- File Merge native integration
- URL Checker native integration
- Excel Splitter native integration
            """
        )
    with c2:
        st.markdown(
            """
### Phase 3 — Inventory/config tools
- Inventory Tool AI
- Inventory Tool 2.0
- JSON to CSV
- Jewelry Filter Builder

### Phase 4 — Platform features
- Shared upload manager
- Download history
- Job logs
- Reusable validation utilities
            """
        )

    section_title("Current runner", "Apps are started as child Streamlit apps and embedded below the shell")
    st.code(
        """# dashboard launches each uploaded module like this
python -m streamlit run modules/<tool>/app.py --server.port <free_port>""",
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
bash scripts/setup_modules.sh
streamlit run Dashboard.py"""
    )


def main() -> None:
    sidebar()
    page = st.session_state["page"]
    if page == "🏠 Home":
        home_page()
    elif page == "🧰 Tools":
        tools_page()
    elif page == "📚 Repository Center":
        repository_page()
    elif page == "🧭 Roadmap":
        roadmap_page()
    elif page == "⚙️ Settings":
        settings_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
