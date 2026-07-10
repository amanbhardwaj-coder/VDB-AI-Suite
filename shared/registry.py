from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Tool:
    key: str
    name: str
    category: str
    icon: str
    description: str
    repo_url: str
    module_path: str
    status: str
    enabled: bool = True
    favorite: bool = False
    entry_file: Optional[str] = None


TOOLS: list[Tool] = [
    Tool(
        key="smiling_rocks",
        name="Smiling Rocks Converter",
        category="Inventory",
        icon="",
        description="Convert Smiling Rocks MFG pricing workbooks into VDB-ready CSV with image mapping support.",
        repo_url="https://github.com/amanbhardwaj-coder/Smiling_Rocks",
        module_path="modules/Smiling_Rocks",
        entry_file="app.py",
        status="Adapter ready",
        enabled=True,
        favorite=True,
    ),
    Tool(
        key="inventory_ai",
        name="Inventory Tool AI",
        category="Inventory",
        icon="",
        description="AI-assisted inventory normalization and VDB output preparation.",
        repo_url="https://github.com/amanbhardwaj-coder/inventory-toolAI",
        module_path="modules/inventory-toolAI",
        status="Module pending",
        enabled=True,
        favorite=True,
    ),
    Tool(
        key="inventory_2",
        name="Inventory Tool 2.0",
        category="Inventory",
        icon="",
        description="Inventory expansion workflow for jewelry variations, metals, shapes, and pricing output.",
        repo_url="https://github.com/amanbhardwaj-coder/inventory-tool2.0",
        module_path="modules/inventory-tool2.0",
        status="Module pending",
        enabled=True,
    ),
    Tool(
        key="inventory_old",
        name="Inventory Tool",
        category="Inventory",
        icon="",
        description="Earlier inventory conversion utility kept available for legacy workflows.",
        repo_url="https://github.com/amanbhardwaj-coder/inventory-tool",
        module_path="modules/inventory-tool",
        status="Module pending",
        enabled=False,
    ),
    Tool(
        key="file_merge",
        name="File Merge",
        category="Excel",
        icon="",
        description="Merge CSV/XLSX files, align duplicate columns, preview the first rows, and download one output.",
        repo_url="https://github.com/amanbhardwaj-coder/file_merge",
        module_path="modules/file_merge",
        status="Module pending",
        enabled=False,
        favorite=True,
    ),
    Tool(
        key="excel_splitter",
        name="Excel Splitter",
        category="Excel",
        icon="",
        description="Split large Excel files into smaller chunks for uploads, review, or batch processing.",
        repo_url="https://github.com/amanbhardwaj-coder/Excelsplitter",
        module_path="modules/Excelsplitter",
        status="Module pending",
        enabled=False,
    ),
    Tool(
        key="url_checker",
        name="URL Checker",
        category="Images",
        icon="",
        description="Check image, video, and file URLs, then report working and broken links.",
        repo_url="https://github.com/amanbhardwaj-coder/URL_Checker",
        module_path="modules/URL_Checker",
        status="Module pending",
        enabled=True,
        favorite=True,
    ),
    Tool(
        key="json_to_csv",
        name="JSON to CSV",
        category="Config",
        icon="",
        description="Convert JSON payloads and config data into CSV output for easier QA and edits.",
        repo_url="https://github.com/amanbhardwaj-coder/Jsontocsv",
        module_path="modules/Jsontocsv",
        status="Module pending",
        enabled=True,
    ),
    Tool(
        key="jewelry_filter",
        name="Jewelry Filter Builder",
        category="Config",
        icon="",
        description="Build jewelry filters and dependency payloads for VDB configuration workflows.",
        repo_url="https://github.com/amanbhardwaj-coder/Jewelry_filter_creation",
        module_path="modules/Jewelry_filter_creation",
        status="Module pending",
        enabled=True,
        favorite=True,
    ),
    Tool(
        key="jl",
        name="JL Tool",
        category="Jewelry",
        icon="",
        description="Jewelry-specific helper utility for client workflows.",
        repo_url="https://github.com/amanbhardwaj-coder/JL",
        module_path="modules/JL",
        status="Module pending",
        enabled=True,
    ),
]


def categories() -> list[str]:
    return sorted({tool.category for tool in enabled_tools()})


def get_tool(key: str) -> Tool | None:
    return next((tool for tool in TOOLS if tool.key == key), None)


def enabled_tools() -> list[Tool]:
    return [tool for tool in TOOLS if tool.enabled]


def tool_is_available(tool: Tool) -> bool:
    return tool.enabled and module_exists(tool)


def available_tools() -> list[Tool]:
    return [tool for tool in TOOLS if tool_is_available(tool)]


def module_exists(tool: Tool) -> bool:
    return Path(tool.module_path).exists()
