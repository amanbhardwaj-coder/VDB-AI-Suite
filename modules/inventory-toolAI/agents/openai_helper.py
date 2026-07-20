import json
import os
from dataclasses import dataclass
from typing import Any

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
class OpenAISettings:
    api_key: str = ""
    model: str = "gpt-5"
    base_url: str = "https://api.openai.com/v1"
    enabled: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.api_key and self.base_url)


def load_openai_settings(secrets: dict[str, Any] | None = None) -> OpenAISettings:
    section = _pick(secrets, "openai", "inventory_ai_openai") if isinstance(secrets, dict) else None
    section = section if isinstance(section, dict) else {}

    api_key = _pick(section, "api_key", "OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    model = _pick(section, "model", "OPENAI_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5")
    base_url = _pick(section, "base_url", "OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    enabled_raw = _pick(section, "enabled", "OPENAI_ENABLED")
    enabled = str(enabled_raw).lower() in {"1", "true", "yes", "on"} if enabled_raw is not None else bool(api_key)

    return OpenAISettings(
        api_key=str(api_key).strip(),
        model=str(model).strip() or "gpt-5",
        base_url=str(base_url).rstrip("/"),
        enabled=enabled,
    )


class InventoryOpenAIAgent:
    def __init__(self, settings: OpenAISettings, timeout: int = 60):
        self.settings = settings
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return self.settings.is_configured

    def _extract_text(self, payload: dict[str, Any]) -> str:
        if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
            return payload["output_text"]

        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text

        return ""

    def _call_json(self, *, schema_name: str, schema: dict[str, Any], system_prompt: str, user_payload: dict[str, Any]):
        if not self.is_configured:
            return {"ok": False, "message": "OpenAI is not configured."}

        body = {
            "model": self.settings.model,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(user_payload, indent=2)}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }

        response = requests.post(
            f"{self.settings.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.timeout,
        )

        if not response.ok:
            return {"ok": False, "message": response.text}

        raw = response.json()
        text = self._extract_text(raw)

        if not text.strip():
            return {"ok": False, "message": "OpenAI returned an empty response."}

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            return {"ok": False, "message": f"Could not parse OpenAI JSON output: {exc}", "raw_text": text}

        return {"ok": True, "data": parsed, "raw": raw}

    def gather_requirements(self, *, file_name: str, columns: list[str], sample_rows: list[dict[str, Any]], accepted_headers: list[str], instructions: str):
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "suggested_instructions": {"type": "string"},
                "recommended_variant_headers": {"type": "array", "items": {"type": "string"}},
                "recommended_static_headers": {"type": "array", "items": {"type": "string"}},
                "missing_information": {"type": "array", "items": {"type": "string"}},
                "follow_up_questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["question", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "summary",
                "suggested_instructions",
                "recommended_variant_headers",
                "recommended_static_headers",
                "missing_information",
                "follow_up_questions",
            ],
            "additionalProperties": False,
        }

        system_prompt = (
            "You help prepare jewelry and inventory normalization requirements. "
            "Review the input columns, sample rows, and user instructions. "
            "Identify missing requirements, ask concise follow-up questions, and recommend which accepted headers should be variant vs static. "
            "Only recommend headers from the accepted_headers list when possible."
        )

        return self._call_json(
            schema_name="inventory_requirements",
            schema=schema,
            system_prompt=system_prompt,
            user_payload={
                "file_name": file_name,
                "columns": columns,
                "sample_rows": sample_rows,
                "accepted_headers": accepted_headers,
                "instructions": instructions,
            },
        )

    def fix_mapping(
        self,
        *,
        file_name: str,
        instructions: str,
        mapping: list[dict[str, Any]],
        accepted_headers: list[str],
        sample_rows: list[dict[str, Any]],
    ):
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "inventory_type": {"type": "string"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "recommended_variant_headers": {"type": "array", "items": {"type": "string"}},
                "recommended_static_headers": {"type": "array", "items": {"type": "string"}},
                "mapping_updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "vendor_column": {"type": "string"},
                            "accepted_header": {"type": "string"},
                            "role": {"type": "string"},
                            "expand": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["vendor_column", "accepted_header", "role", "expand", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "summary",
                "inventory_type",
                "warnings",
                "recommended_variant_headers",
                "recommended_static_headers",
                "mapping_updates",
            ],
            "additionalProperties": False,
        }

        system_prompt = (
            "You fix inventory column mapping suggestions. "
            "Use the accepted header list as the target vocabulary, prefer conservative corrections, and avoid inventing fields outside the accepted_headers list. "
            "Return only updates for columns that should change."
        )

        return self._call_json(
            schema_name="inventory_mapping_fix",
            schema=schema,
            system_prompt=system_prompt,
            user_payload={
                "file_name": file_name,
                "instructions": instructions,
                "accepted_headers": accepted_headers,
                "mapping": mapping,
                "sample_rows": sample_rows,
            },
        )
