from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.recall_export import build_recall_export_artifact


PACKAGING_DIR = Path("runtime-kit/packaging")


FORBIDDEN_EXPORT_FIELDS = (
    "raw_embeddings",
    "retrieval_index_rows",
    "runtime_store_path",
    "provider_keys",
    "bearer_tokens",
    "hidden_prompts",
    "raw_provider_responses",
)


def test_recall_export_artifact_policy_sanitizes_items_and_validates_schema() -> None:
    artifact = build_recall_export_artifact(
        items=[
            {
                "item_id": "recall_0001",
                "summary": "Remember Chinese summaries.",
                "created_at": "2026-06-05T00:00:00Z",
                "provenance": {
                    "source_task_id": "task_123",
                    "source_surface": "inbox",
                    "runtime_store_path": "/private/store.sqlite3",
                },
                "raw_embeddings": [0.1, 0.2],
                "retrieval_index_rows": [{"index_id": "embedding_recall_0001"}],
            }
        ],
        generated_at="2026-06-05T10:00:00Z",
    )

    assert artifact["schema_version"] == "kaka.recall_export.v1"
    assert artifact["artifact_policy"]["classification"] == "user_recall_export"
    assert artifact["artifact_policy"]["database_dump"] is False
    assert artifact["artifact_policy"]["item_fields"] == [
        "item_id",
        "summary",
        "created_at",
        "provenance",
    ]
    assert set(artifact["items"][0]) == {
        "item_id",
        "summary",
        "created_at",
        "provenance",
    }
    assert set(artifact["items"][0]["provenance"]) == {
        "source_task_id",
        "source_surface",
    }

    rendered = json.dumps(artifact["items"], ensure_ascii=False, sort_keys=True)
    for field in FORBIDDEN_EXPORT_FIELDS:
        assert field not in rendered

    schema = json.loads((PACKAGING_DIR / "recall-export.schema.json").read_text())
    validator = Draft202012Validator(schema)
    validator.validate(artifact)

    leaked = json.loads(json.dumps(artifact))
    leaked["items"][0]["raw_embeddings"] = [0.1, 0.2]
    assert not validator.is_valid(leaked)


def test_recall_export_artifact_policy_rejects_database_dump_fields() -> None:
    artifact = build_recall_export_artifact(
        items=[
            {
                "item_id": "recall_0002",
                "summary": "Keep export user-readable.",
                "created_at": "2026-06-05T00:00:00Z",
                "provenance": {"source_inbox_item_id": "inbox_123"},
            }
        ],
        generated_at="2026-06-05T10:00:00Z",
    )
    schema = json.loads((PACKAGING_DIR / "recall-export.schema.json").read_text())
    validator = Draft202012Validator(schema)

    database_dump = json.loads(json.dumps(artifact))
    database_dump["artifact_policy"]["database_dump"] = True

    assert not validator.is_valid(database_dump)
