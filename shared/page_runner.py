from __future__ import annotations

import os
import runpy
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import streamlit as st

from shared.module_runner import find_entry_file
from shared.registry import get_tool, tool_is_available


@contextmanager
def _tool_context(module_dir: Path) -> Iterator[None]:
    previous_cwd = Path.cwd()
    previous_sys_path = list(sys.path)
    repo_root = Path(__file__).resolve().parent.parent

    sys.path.insert(0, str(module_dir))
    sys.path.insert(0, str(repo_root))
    os.chdir(module_dir)
    try:
        yield
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_sys_path


def run_tool_script(tool_key: str) -> None:
    tool = get_tool(tool_key)
    if not tool:
        st.error("Tool not found in registry.")
        return
    if not tool.enabled:
        st.warning(f"{tool.name} is currently disabled in the registry.")
        return
    if not tool_is_available(tool):
        st.error(f"{tool.name} is enabled but its module folder is not available.")
        return

    entry = find_entry_file(tool)
    if not entry:
        st.error(f"No Python entry file found in `{tool.module_path}`.")
        return

    entry = entry.resolve()
    with _tool_context(entry.parent):
        runpy.run_path(str(entry), run_name="__main__")
