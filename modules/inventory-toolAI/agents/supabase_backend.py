import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


def _pick(mapping: dict[str, Any] | None, *keys: str):
    if not mapping:
        return None

    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value

    return None


@dataclass
class SupabaseSettings:
    url: str = ""
    service_role_key: str = ""
    storage_bucket: str = "inventory-ai"
    runs_table: str = "inventory_ai_runs"
    knowledge_table: str = "inventory_ai_learned_headers"
    enabled: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.url and self.service_role_key and self.storage_bucket)


def load_supabase_settings(secrets: dict[str, Any] | None = None) -> SupabaseSettings:
    section = _pick(secrets, "inventory_ai_supabase", "supabase") if isinstance(secrets, dict) else None
    section = section if isinstance(section, dict) else {}

    url = _pick(section, "url", "SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
    service_role_key = (
        _pick(section, "service_role_key", "key", "SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )
    storage_bucket = (
        _pick(section, "storage_bucket", "bucket", "SUPABASE_STORAGE_BUCKET")
        or os.getenv("SUPABASE_STORAGE_BUCKET", "inventory-ai")
    )
    runs_table = (
        _pick(section, "runs_table", "SUPABASE_RUNS_TABLE")
        or os.getenv("SUPABASE_RUNS_TABLE", "inventory_ai_runs")
    )
    knowledge_table = (
        _pick(section, "knowledge_table", "SUPABASE_KNOWLEDGE_TABLE")
        or os.getenv("SUPABASE_KNOWLEDGE_TABLE", "inventory_ai_learned_headers")
    )
    enabled_raw = _pick(section, "enabled", "SUPABASE_ENABLED")
    enabled = str(enabled_raw).lower() in {"1", "true", "yes", "on"} if enabled_raw is not None else bool(url and service_role_key)

    return SupabaseSettings(
        url=str(url).rstrip("/"),
        service_role_key=str(service_role_key),
        storage_bucket=str(storage_bucket),
        runs_table=str(runs_table),
        knowledge_table=str(knowledge_table),
        enabled=enabled,
    )


class SupabaseBackend:
    def __init__(self, settings: SupabaseSettings, timeout: int = 30):
        self.settings = settings
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return self.settings.is_configured

    def _headers(self, content_type: str | None = None, extra: dict[str, str] | None = None):
        headers = {
            "apikey": self.settings.service_role_key,
            "Authorization": f"Bearer {self.settings.service_role_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if extra:
            headers.update(extra)
        return headers

    def upload_bytes(self, remote_path: str, payload: bytes, content_type: str = "application/octet-stream"):
        if not self.is_configured:
            return {"ok": False, "message": "Supabase is not configured."}

        url = f"{self.settings.url}/storage/v1/object/{self.settings.storage_bucket}/{remote_path.lstrip('/')}"
        response = requests.post(
            url,
            headers=self._headers(content_type, {"x-upsert": "true"}),
            data=payload,
            timeout=self.timeout,
        )

        if not response.ok:
            return {"ok": False, "message": response.text}

        return {"ok": True, "path": remote_path}

    def upload_file(self, local_path: Path, remote_path: str, content_type: str | None = None):
        guessed = content_type or mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        return self.upload_bytes(remote_path, local_path.read_bytes(), guessed)

    def download_bytes(self, remote_path: str):
        if not self.is_configured:
            return {"ok": False, "message": "Supabase is not configured."}

        url = f"{self.settings.url}/storage/v1/object/{self.settings.storage_bucket}/{remote_path.lstrip('/')}"
        response = requests.get(url, headers=self._headers(), timeout=self.timeout)
        if response.status_code == 404:
            return {"ok": False, "message": "Not found", "status_code": 404}
        if not response.ok:
            return {"ok": False, "message": response.text, "status_code": response.status_code}
        return {"ok": True, "content": response.content}

    def upsert_rows(self, table: str, rows: list[dict[str, Any]], on_conflict: str | None = None):
        if not self.is_configured:
            return {"ok": False, "message": "Supabase is not configured."}
        if not rows:
            return {"ok": True, "count": 0}

        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.settings.url}/rest/v1/{table}{query}"
        headers = self._headers(
            "application/json",
            {"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        response = requests.post(url, headers=headers, data=json.dumps(rows), timeout=self.timeout)

        if not response.ok:
            return {"ok": False, "message": response.text}

        return {"ok": True, "count": len(rows)}

    def fetch_rows(self, table: str, *, select: str = "*", order: str | None = None, limit: int | None = None):
        if not self.is_configured:
            return {"ok": False, "message": "Supabase is not configured."}

        params = {"select": select}
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)

        url = f"{self.settings.url}/rest/v1/{table}?{urlencode(params)}"
        response = requests.get(url, headers=self._headers(), timeout=self.timeout)

        if not response.ok:
            return {"ok": False, "message": response.text}

        return {"ok": True, "rows": response.json()}

    def check_connection(self):
        if not self.is_configured:
            return {"ok": False, "message": "Supabase settings are incomplete."}

        result = self.fetch_rows(self.settings.runs_table, select="run_id", limit=1)
        if result.get("ok"):
            return {"ok": True, "message": "Connected"}

        return result
