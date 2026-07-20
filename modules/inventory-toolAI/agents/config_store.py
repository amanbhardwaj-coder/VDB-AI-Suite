import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _utc_now():
    return datetime.now(timezone.utc)


def _timestamp():
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str):
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in str(value))
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed[:80] or "inventory"


def save_generated_config(config, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(config)
    payload["saved_at"] = _utc_now().isoformat()

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    return path


def _json_bytes(payload):
    return json.dumps(payload, indent=2).encode("utf-8")


def ensure_runtime_dirs(base_dir: Path):
    paths = {
        "generated": base_dir / "generated",
        "history": base_dir / "history",
        "runs": base_dir / "history" / "runs",
        "uploads": base_dir / "uploads",
        "knowledge": base_dir / "knowledge",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def create_run_dir(base_dir: Path, file_name: str):
    runtime = ensure_runtime_dirs(base_dir)
    run_id = f"{_timestamp()}_{_slugify(file_name)}"
    run_dir = runtime["runs"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_id, run_dir, runtime


def save_uploaded_input(uploaded_file, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    uploaded_file.seek(0)
    with destination.open("wb") as handle:
        shutil.copyfileobj(uploaded_file, handle)
    uploaded_file.seek(0)
    return destination


def save_run_artifacts(
    *,
    base_dir: Path,
    file_name: str,
    file_meta: dict,
    config: dict,
    normalized_df=None,
    expanded_df=None,
    qa_report=None,
    uploaded_file=None,
    export_profile: str = "standard",
    supabase_backend=None,
):
    run_id, run_dir, runtime = create_run_dir(base_dir, file_name)

    run_meta = {
        "run_id": run_id,
        "saved_at": _utc_now().isoformat(),
        "file_name": file_name,
        "file_meta": file_meta,
        "inventory_type": config.get("inventory_type"),
        "source_rows": config.get("source_rows"),
        "source_columns": config.get("source_columns"),
        "export_profile": export_profile,
        "warnings": config.get("warnings", []),
    }

    local_files = {}

    if uploaded_file is not None:
        stored_source = runtime["uploads"] / run_id / Path(file_name).name
        save_uploaded_input(uploaded_file, stored_source)
        run_meta["stored_source"] = str(stored_source)
        local_files["source"] = stored_source

    mapping_path = run_dir / "mapping_config.json"
    save_generated_config(config, mapping_path)
    local_files["mapping_config"] = mapping_path

    if normalized_df is not None:
        normalized_path = run_dir / "normalized_input.csv"
        normalized_df.to_csv(normalized_path, index=False)
        local_files["normalized_input"] = normalized_path

    if expanded_df is not None:
        expanded_path = run_dir / "expanded_inventory.csv"
        expanded_df.to_csv(expanded_path, index=False)
        local_files["expanded_inventory"] = expanded_path

    if qa_report is not None:
        qa_path = run_dir / "qa_report.json"
        with qa_path.open("w", encoding="utf-8") as handle:
            json.dump(qa_report, handle, indent=2)
        local_files["qa_report"] = qa_path

    run_meta_path = run_dir / "run_meta.json"
    with run_meta_path.open("w", encoding="utf-8") as handle:
        json.dump(run_meta, handle, indent=2)
    local_files["run_meta"] = run_meta_path

    index_path = runtime["history"] / "runs_index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = []
    else:
        index = []

    index.insert(0, run_meta)
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index[:100], handle, indent=2)

    if supabase_backend and getattr(supabase_backend, "is_configured", False):
        remote_paths = {}
        upload_errors = []

        for label, local_path in local_files.items():
            remote_path = f"runs/{run_id}/{local_path.name}"
            upload_result = supabase_backend.upload_file(local_path, remote_path)
            if upload_result.get("ok"):
                remote_paths[label] = remote_path
            else:
                upload_errors.append(f"{label}: {upload_result.get('message', 'upload failed')}")

        remote_meta = dict(run_meta)
        remote_meta["remote_paths"] = remote_paths
        remote_meta["sync_status"] = "error" if upload_errors else "synced"
        if upload_errors:
            remote_meta["sync_errors"] = upload_errors

        sync_result = supabase_backend.upsert_rows(
            supabase_backend.settings.runs_table,
            [remote_meta],
            on_conflict="run_id",
        )

        if not sync_result.get("ok"):
            remote_meta["sync_status"] = "error"
            remote_meta.setdefault("sync_errors", []).append(sync_result.get("message", "metadata upsert failed"))

        run_meta.update(
            {
                "remote_paths": remote_meta.get("remote_paths", {}),
                "sync_status": remote_meta.get("sync_status", "pending"),
                "sync_errors": remote_meta.get("sync_errors", []),
            }
        )

    return run_meta, run_dir


def store_learned_mappings(config: dict, knowledge_file: Path, supabase_backend=None):
    knowledge_file.parent.mkdir(parents=True, exist_ok=True)

    if knowledge_file.exists():
        try:
            existing = json.loads(knowledge_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    else:
        existing = []

    items = existing if isinstance(existing, list) else existing.get("items", [])
    by_header = {}

    for item in items:
        accepted_header = str(item.get("accepted_header", "")).strip()
        if not accepted_header:
            continue

        by_header[accepted_header.lower()] = {
            "accepted_header": accepted_header,
            "setter": str(item.get("setter", "")).strip(),
            "variations": list(item.get("variations", [])),
            "source_file": str(item.get("source_file", "learned_headers.json")).strip() or "learned_headers.json",
            "updated_at": item.get("updated_at"),
        }

    for item in config.get("mapping", []):
        accepted_header = str(item.get("accepted_header", "")).strip()
        vendor_column = str(item.get("vendor_column", "")).strip()
        internal_setter = str(item.get("internal_setter", "")).strip()

        if not accepted_header or not vendor_column:
            continue

        learned_item = by_header.setdefault(
            accepted_header.lower(),
            {
                "accepted_header": accepted_header,
                "setter": internal_setter,
                "variations": [],
                "source_file": "learned_headers.json",
                "updated_at": None,
            },
        )

        if internal_setter and not learned_item.get("setter"):
            learned_item["setter"] = internal_setter

        if vendor_column not in learned_item["variations"]:
            learned_item["variations"].append(vendor_column)

        learned_item["updated_at"] = _utc_now().isoformat()

    payload = sorted(by_header.values(), key=lambda item: item["accepted_header"].lower())
    with knowledge_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    if supabase_backend and getattr(supabase_backend, "is_configured", False):
        supabase_backend.upload_bytes(
            "knowledge/learned_headers.json",
            _json_bytes(payload),
            "application/json",
        )
        supabase_backend.upsert_rows(
            supabase_backend.settings.knowledge_table,
            payload,
            on_conflict="accepted_header",
        )

    return knowledge_file


def load_run_history(history_file: Path, limit: int = 10, supabase_backend=None):
    if supabase_backend and getattr(supabase_backend, "is_configured", False):
        result = supabase_backend.fetch_rows(
            supabase_backend.settings.runs_table,
            order="saved_at.desc",
            limit=limit,
        )
        if result.get("ok"):
            rows = result.get("rows", [])
            if isinstance(rows, list):
                return rows

    if not history_file.exists():
        return []

    try:
        history = json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(history, list):
        return []

    return history[:limit]


def hydrate_knowledge_file(knowledge_file: Path, supabase_backend=None):
    if not supabase_backend or not getattr(supabase_backend, "is_configured", False):
        return {"ok": False, "message": "Supabase not configured"}

    result = supabase_backend.download_bytes("knowledge/learned_headers.json")
    if not result.get("ok"):
        return result

    knowledge_file.parent.mkdir(parents=True, exist_ok=True)
    knowledge_file.write_bytes(result["content"])
    return {"ok": True, "path": str(knowledge_file)}
