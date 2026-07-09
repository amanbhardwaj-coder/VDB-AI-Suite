from __future__ import annotations

from html import escape
from typing import Iterable

import pandas as pd
import streamlit as st

from shared.registry import Tool, module_exists


def hero(title: str, subtitle: str, badges: Iterable[str] = ()) -> None:
    badge_html = "".join(f'<span class="vdb-pill">{escape(b)}</span>' for b in badges)
    st.markdown(
        f"""
<div class="vdb-hero">
  <h1>{escape(title)}</h1>
  <p>{escape(subtitle)}</p>
  <div class="vdb-badge-row">{badge_html}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, note: str = "") -> None:
    note_html = f'<span class="vdb-muted">{escape(note)}</span>' if note else ""
    st.markdown(
        f"""
<div class="vdb-section-title">
  <h2>{escape(title)}</h2>
  {note_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def tool_card(tool: Tool) -> None:
    exists = module_exists(tool)
    status_class = "status-built-in" if tool.key == "smiling_rocks" else ("status-ready" if exists else "status-linked")
    status_text = "Local module" if exists else tool.status
    if tool.key == "smiling_rocks":
        status_text = "Adapter ready"

    st.markdown(
        f"""
<div class="vdb-card">
  <div class="vdb-card-top">
    <div class="vdb-icon">{tool.icon}</div>
    <span class="vdb-status {status_class}">{escape(status_text)}</span>
  </div>
  <h3>{escape(tool.name)}</h3>
  <p>{escape(tool.description)}</p>
  <div class="vdb-card-footer">
    <span class="vdb-pill">{escape(tool.category)}</span>
    <span class="vdb-pill">{escape(tool.module_path)}</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_grid(tools: list[Tool], cols: int = 3) -> None:
    if not tools:
        st.info("No matching tools found.")
        return
    for i in range(0, len(tools), cols):
        row = st.columns(cols)
        for col, tool in zip(row, tools[i : i + cols]):
            with col:
                tool_card(tool)
                open_label = "Open in dashboard" if tool.key == "smiling_rocks" else "Open repo"
                if tool.key == "smiling_rocks":
                    if st.button(open_label, key=f"open_{tool.key}", use_container_width=True, type="primary"):
                        st.session_state["page"] = "Tools"
                        st.session_state["active_tool"] = tool.key
                        st.rerun()
                else:
                    st.link_button(open_label, tool.repo_url, use_container_width=True)


def repo_table(tools: list[Tool]) -> None:
    rows = []
    for tool in tools:
        rows.append(
            {
                "Tool": tool.name,
                "Category": tool.category,
                "Status": "Local module found" if module_exists(tool) else tool.status,
                "Module path": tool.module_path,
                "Repo": tool.repo_url,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def empty_tool_state(tool: Tool) -> None:
    hero(
        f"{tool.icon} {tool.name}",
        "This tool is registered in the dashboard shell. The next integration step is to wrap its existing Streamlit app with a run() function and mount it here.",
        [tool.category, tool.status],
    )
    st.warning("Tool UI is not mounted yet. Use the repository link for now.")
    st.link_button("Open repository", tool.repo_url, use_container_width=True)
    st.markdown("### Integration checklist")
    st.markdown(
        f"""
1. Run `bash scripts/setup_modules.sh` to clone/update the repo into `{tool.module_path}`.
2. Open the app file in that module.
3. Wrap the existing Streamlit code inside `def run():`.
4. Add an adapter under `adapters/` and call it from `Dashboard.py`.
        """
    )


def command_block(command: str) -> None:
    st.markdown('<div class="vdb-command">', unsafe_allow_html=True)
    st.code(command, language="bash")
    st.markdown('</div>', unsafe_allow_html=True)
