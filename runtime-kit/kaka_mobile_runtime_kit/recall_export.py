from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


RECALL_EXPORT_SCHEMA_VERSION = "kaka.recall_export.v1"
RECALL_EXPORT_ITEM_FIELDS = ("item_id", "summary", "created_at", "provenance")
RECALL_EXPORT_PROVENANCE_FIELDS = (
    "source_task_id",
    "source_inbox_item_id",
    "source_surface",
)
RECALL_EXPORT_FORBIDDEN_FIELDS = (
    "raw_embeddings",
    "embeddings",
    "retrieval_index_rows",
    "provider_keys",
    "provider_endpoints",
    "bearer_tokens",
    "mobile_tokens",
    "runtime_store_path",
    "sqlite_path",
    "hidden_prompts",
    "raw_provider_responses",
    "unrelated_task_logs",
)


def build_recall_export_artifact(
    items: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": RECALL_EXPORT_SCHEMA_VERSION,
        "format": "json",
        "generated_at": generated_at,
        "artifact_policy": build_recall_export_artifact_policy(),
        "items": [sanitize_recall_export_item(item) for item in items],
    }


def build_recall_export_artifact_policy() -> dict[str, Any]:
    return {
        "classification": "user_recall_export",
        "artifact_kind": "recall_export_json",
        "runtime_owned_source": True,
        "database_dump": False,
        "phone_safe": True,
        "item_fields": list(RECALL_EXPORT_ITEM_FIELDS),
        "provenance_fields": list(RECALL_EXPORT_PROVENANCE_FIELDS),
        "forbidden_fields": list(RECALL_EXPORT_FORBIDDEN_FIELDS),
    }


def sanitize_recall_export_item(item: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for field in RECALL_EXPORT_ITEM_FIELDS:
        if field == "provenance":
            provenance = item.get("provenance")
            sanitized["provenance"] = sanitize_recall_export_provenance(
                provenance if isinstance(provenance, Mapping) else {}
            )
            continue
        value = item.get(field)
        if value is not None:
            sanitized[field] = str(value)
    if "provenance" not in sanitized:
        sanitized["provenance"] = {}
    return sanitized


def sanitize_recall_export_provenance(provenance: Mapping[str, Any]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for field in RECALL_EXPORT_PROVENANCE_FIELDS:
        value = provenance.get(field)
        if value is not None and str(value):
            sanitized[field] = str(value)
    return sanitized
