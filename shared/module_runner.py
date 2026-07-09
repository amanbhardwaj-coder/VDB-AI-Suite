from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from shared.registry import Tool


CANDIDATE_ENTRY_FILES = [
    "app.py",
    "Dashboard.py",
    "streamlit_app.py",
    "main.py",
    "excel_merger_app.py",
    "url_checker.py",
    "Local_cleaner.py",
]


BASE_PORT = 8600


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def find_free_port(start: int = BASE_PORT, end: int = 8699) -> int:
    for port in range(start, end + 1):
        if not is_port_open(port):
            return port
    raise RuntimeError("No free Streamlit port found between 8600 and 8699.")


def find_entry_file(tool: Tool) -> Optional[Path]:
    module_dir = Path(tool.module_path)
    if not module_dir.exists():
        return None

    if tool.entry_file:
        candidate = module_dir / tool.entry_file
        if candidate.exists():
            return candidate

    for name in CANDIDATE_ENTRY_FILES:
        candidate = module_dir / name
        if candidate.exists():
            return candidate

    py_files = sorted(
        p for p in module_dir.rglob("*.py")
        if "__pycache__" not in p.parts and not p.name.startswith(".")
    )
    return py_files[0] if py_files else None


def _process_key(tool: Tool) -> str:
    return f"module_process_{tool.key}"


def _port_key(tool: Tool) -> str:
    return f"module_port_{tool.key}"


def get_running_url(tool: Tool) -> Optional[str]:
    port = st.session_state.get(_port_key(tool))
    proc = st.session_state.get(_process_key(tool))
    if port and proc and proc.poll() is None and is_port_open(int(port)):
        return f"http://localhost:{port}"
    return None


def stop_tool(tool: Tool) -> None:
    proc = st.session_state.get(_process_key(tool))
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
    st.session_state.pop(_process_key(tool), None)
    st.session_state.pop(_port_key(tool), None)


def start_tool(tool: Tool) -> str:
    existing = get_running_url(tool)
    if existing:
        return existing

    entry = find_entry_file(tool)
    if not entry:
        raise FileNotFoundError(f"No Python entry file found in {tool.module_path}")

    port = find_free_port()
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(entry),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(Path.cwd()),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    st.session_state[_process_key(tool)] = proc
    st.session_state[_port_key(tool)] = port

    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"Streamlit app exited immediately for {tool.name}.")
        if is_port_open(port):
            return f"http://localhost:{port}"
        time.sleep(0.25)

    return f"http://localhost:{port}"


def render_tool_app(tool: Tool, height: int = 850) -> None:
    entry = find_entry_file(tool)
    if entry:
        st.caption(f"Entry file detected: `{entry}`")
    else:
        st.error(f"No Python entry file found in `{tool.module_path}`.")
        return

    controls = st.columns([1, 1, 1, 4])
    with controls[0]:
        launch = st.button("▶ Run app", key=f"run_app_{tool.key}", type="primary", use_container_width=True)
    with controls[1]:
        refresh = st.button("🔄 Refresh", key=f"refresh_app_{tool.key}", use_container_width=True)
    with controls[2]:
        stop = st.button("⏹ Stop", key=f"stop_app_{tool.key}", use_container_width=True)

    if stop:
        stop_tool(tool)
        st.success("Stopped.")
        return

    url = get_running_url(tool)
    if launch or refresh or not url:
        with st.spinner(f"Starting {tool.name}..."):
            url = start_tool(tool)

    st.success(f"Running: {url}")
    st.link_button("Open in new tab", url, use_container_width=True)
    components.iframe(url, height=height, scrolling=True)
