from __future__ import annotations

import json
from datetime import datetime, timezone

from kaka_mobile_runtime_kit.runtime_store import (
    RuntimeRecallItem,
    RuntimeTaskEvent,
    RuntimeTaskRecord,
    SQLiteRuntimeStore,
)
from kaka_mobile_runtime_kit.recall_search import RecallSearchResult


def _iso(value: str) -> str:
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def test_recall_items_persist_across_reopened_store(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Remember Chinese summaries.",
            created_at=_iso("2026-06-05T09:30:00Z"),
            source_task_id="task_123",
            source_surface="inbox",
        ),
        index_ids=["embedding_recall_0001"],
    )

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()

    items = reopened.list_recall(query="Chinese", limit=10)
    assert [item.item_id for item in items] == ["recall_0001"]
    assert items[0].summary == "Remember Chinese summaries."
    assert items[0].source_task_id == "task_123"
    assert reopened.export_recall()["items"][0]["provenance"]["source_task_id"] == "task_123"


def test_recall_export_includes_artifact_policy_without_index_leakage(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Remember Chinese summaries.",
            created_at=_iso("2026-06-05T09:30:00Z"),
            source_task_id="task_123",
            metadata={
                "runtime_store_path": str(db_path),
                "raw_embeddings": [0.1, 0.2],
            },
        ),
        index_ids=["embedding_recall_0001"],
    )

    exported = store.export_recall()
    rendered_items = json.dumps(exported["items"], ensure_ascii=False, sort_keys=True)

    assert exported["schema_version"] == "kaka.recall_export.v1"
    assert exported["format"] == "json"
    assert exported["artifact_policy"]["item_fields"] == [
        "item_id",
        "summary",
        "created_at",
        "provenance",
    ]
    assert "embedding_recall_0001" not in rendered_items
    assert str(db_path) not in rendered_items
    assert "raw_embeddings" not in rendered_items


def test_semantic_recall_search_ranks_summary_matches(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Answer launch summaries in Chinese.",
            created_at=_iso("2026-06-05T09:30:00Z"),
            source_task_id="task_123",
        ),
        index_ids=["embedding_recall_0001"],
    )
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0002",
            summary="Track unrelated grocery errands.",
            created_at=_iso("2026-06-05T09:31:00Z"),
            source_task_id="task_456",
        ),
        index_ids=["embedding_recall_0002"],
    )

    results = store.search_recall_semantic("launch summary language", limit=5)

    assert [result["item"]["item_id"] for result in results] == ["recall_0001"]
    assert results[0]["score"] > 0
    assert "launch" in results[0]["match_reason"].lower()
    assert "embedding_recall_0001" not in json.dumps(results, sort_keys=True)


def test_semantic_recall_search_delegates_to_injected_provider(tmp_path):
    class FakeRecallSearchProvider:
        provider_mode = "provider_backed"

        def __init__(self):
            self.calls = []

        def search(self, query, items, limit):
            self.calls.append(
                {
                    "query": query,
                    "item_ids": [item.item_id for item in items],
                    "limit": limit,
                }
            )
            return [
                RecallSearchResult(
                    item=items[0],
                    score=0.42,
                    match_reason="Matched fake provider.",
                    provider_mode=self.provider_mode,
                )
            ]

    provider = FakeRecallSearchProvider()
    store = SQLiteRuntimeStore(tmp_path / "kaka-runtime.sqlite3", recall_search_provider=provider)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Answer launch summaries in Chinese.",
            created_at=_iso("2026-06-05T09:30:00Z"),
        ),
        index_ids=["embedding_recall_0001"],
    )

    results = store.search_recall_semantic("provider query", limit=3)

    assert provider.calls == [
        {
            "query": "provider query",
            "item_ids": ["recall_0001"],
            "limit": 3,
        }
    ]
    assert results == [
        {
            "item": {
                "item_id": "recall_0001",
                "summary": "Answer launch summaries in Chinese.",
                "created_at": "2026-06-05T09:30:00Z",
                "provenance": {},
            },
            "score": 0.42,
            "match_reason": "Matched fake provider.",
        }
    ]


def test_runtime_assets_persist_across_reopened_store_without_metadata_leakage(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.upsert_asset(
        RuntimeAssetRecord(
            asset_id="asset_input_1",
            role="input",
            created_at=_iso("2026-06-01T00:00:00Z"),
            filename="source.png",
            mime_type="image/png",
            size_bytes=8,
            sha256="abc123",
            body=b"PNGDATA!",
            metadata={"source": "share_extension", "runtime_store_path": str(db_path)},
        )
    )

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()
    asset = reopened.get_asset("asset_input_1")

    assert asset is not None
    assert asset.asset_id == "asset_input_1"
    assert asset.role == "input"
    assert asset.created_at == "2026-06-01T00:00:00Z"
    assert asset.filename == "source.png"
    assert asset.mime_type == "image/png"
    assert asset.size_bytes == 8
    assert asset.sha256 == "abc123"
    assert asset.body == b"PNGDATA!"
    assert asset.metadata["source"] == "share_extension"


def test_runtime_asset_purge_deletes_only_old_input_and_output_assets(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_keep",
            summary="Keep Recall untouched.",
            created_at=_iso("2026-06-01T00:00:00Z"),
        )
    )
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_keep",
            title="Keep active task",
            status="running",
            updated_at="2026-05-01T00:00:00Z",
        )
    )
    for record in [
        RuntimeAssetRecord(
            asset_id="asset_old_input",
            role="input",
            created_at="2026-05-01T00:00:00Z",
            filename="old-input.png",
            mime_type="image/png",
            size_bytes=9,
            sha256="oldinput",
            body=b"old-input",
        ),
        RuntimeAssetRecord(
            asset_id="asset_recent_input",
            role="input",
            created_at="2026-06-06T00:00:00Z",
            filename="recent-input.png",
            mime_type="image/png",
            size_bytes=12,
            sha256="recentinput",
            body=b"recent-input",
        ),
        RuntimeAssetRecord(
            asset_id="asset_result_old_output",
            role="output",
            created_at="2026-05-01T00:00:00Z",
            filename="old-output.png",
            mime_type="image/png",
            size_bytes=10,
            sha256="oldoutput",
            body=b"old-output",
        ),
    ]:
        store.upsert_asset(record)

    dry_run = store.purge_assets(
        input_cutoff_iso="2026-05-31T00:00:00Z",
        output_cutoff_iso="2026-05-08T00:00:00Z",
        dry_run=True,
    )

    assert dry_run.eligible_input_asset_ids == ["asset_old_input"]
    assert dry_run.eligible_output_asset_ids == ["asset_result_old_output"]
    assert dry_run.deleted_input_asset_ids == []
    assert dry_run.deleted_output_asset_ids == []
    assert store.get_asset("asset_old_input") is not None

    applied = store.purge_assets(
        input_cutoff_iso="2026-05-31T00:00:00Z",
        output_cutoff_iso="2026-05-08T00:00:00Z",
        dry_run=False,
    )

    assert applied.deleted_input_asset_ids == ["asset_old_input"]
    assert applied.deleted_output_asset_ids == ["asset_result_old_output"]
    assert store.get_asset("asset_old_input") is None
    assert store.get_asset("asset_result_old_output") is None
    assert store.get_asset("asset_recent_input") is not None
    assert [item.item_id for item in store.list_recall()] == ["recall_keep"]
    assert store.get_task("task_keep") is not None


def test_runtime_asset_purge_treats_invalid_created_at_as_untracked(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord

    store = SQLiteRuntimeStore(tmp_path / "kaka-runtime.sqlite3")
    store.initialize()
    for record in [
        RuntimeAssetRecord(
            asset_id="asset_bad_oldish_input",
            role="input",
            created_at="0000-bad",
            filename="bad-oldish.png",
            mime_type="image/png",
            size_bytes=3,
            sha256="badoldish",
            body=b"bad",
        ),
        RuntimeAssetRecord(
            asset_id="asset_bad_text_input",
            role="input",
            created_at="not-a-date",
            filename="bad-text.png",
            mime_type="image/png",
            size_bytes=3,
            sha256="badtext",
            body=b"bad",
        ),
    ]:
        store.upsert_asset(record)

    receipt = store.purge_assets(
        input_cutoff_iso="2026-05-31T00:00:00Z",
        output_cutoff_iso="2026-05-08T00:00:00Z",
        dry_run=False,
    )

    assert receipt.eligible_input_asset_ids == []
    assert receipt.deleted_input_asset_ids == []
    assert receipt.untracked_asset_ids == ["asset_bad_oldish_input", "asset_bad_text_input"]
    assert store.get_asset("asset_bad_oldish_input") is not None
    assert store.get_asset("asset_bad_text_input") is not None


def test_recall_delete_returns_content_and_index_receipts(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0002",
            summary="Forget this item.",
            created_at=_iso("2026-06-05T09:31:00Z"),
        ),
        index_ids=["embedding_recall_0002", "lexical_recall_0002"],
    )

    receipt = store.delete_recall("recall_0002")

    assert receipt.status == "forgotten"
    assert receipt.deleted_item_ids == ["recall_0002"]
    assert receipt.deleted_index_ids == ["embedding_recall_0002", "lexical_recall_0002"]
    assert store.list_recall() == []


def test_recall_delete_by_source_requires_all_provenance_fields_to_match(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Delete this exact inbox item.",
            created_at=_iso("2026-06-05T09:31:00Z"),
            source_task_id="task_123",
            source_inbox_item_id="12345678-1234-1234-1234-1234567890AB",
        ),
        index_ids=["embedding_recall_0001"],
    )
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_0002",
            summary="Keep the other inbox item.",
            created_at=_iso("2026-06-05T09:32:00Z"),
            source_task_id="task_123",
            source_inbox_item_id="12345678-1234-1234-1234-1234567890AC",
        ),
        index_ids=["embedding_recall_0002"],
    )

    receipt = store.delete_recall_by_source(
        source_task_id="task_123",
        source_inbox_item_id="12345678-1234-1234-1234-1234567890AB",
    )

    assert receipt.deleted_item_ids == ["recall_0001"]
    assert receipt.deleted_index_ids == ["embedding_recall_0001"]
    assert [item.item_id for item in store.list_recall()] == ["recall_0002"]
    assert store.list_recall()[0].to_mobile_bridge()["provenance"]["source_inbox_item_id"].endswith("90AC")


def test_runtime_tasks_and_events_persist_across_reopened_store(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_0001",
            title="Summarize shared PDF",
            status="waiting_for_approval",
            updated_at=_iso("2026-06-05T09:32:00Z"),
            detail="Needs approval before reading the file.",
            approval_required=True,
        )
    )
    store.append_task_event(
        RuntimeTaskEvent(
            event_id="event_0001",
            task_id="task_0001",
            type="approval_requested",
            message="Approve PDF summary.",
            created_at=_iso("2026-06-05T09:32:01Z"),
        )
    )

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()

    tasks = reopened.list_tasks()
    task = reopened.get_task("task_0001")
    events = reopened.list_task_events("task_0001")
    assert [task.task_id for task in tasks] == ["task_0001"]
    assert task is not None
    assert task.title == "Summarize shared PDF"
    assert tasks[0].approval_required is True
    assert [event.event_id for event in events] == ["event_0001"]
    assert events[0].type == "approval_requested"


def test_task_history_purge_dry_run_reports_terminal_tasks_without_deleting(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_old_done",
            title="Old completed task",
            status="completed",
            updated_at=_iso("2026-05-01T00:00:00Z"),
        )
    )
    store.append_task_event(
        RuntimeTaskEvent(
            event_id="event_old_done",
            task_id="task_old_done",
            type="completed",
            message="Done.",
            created_at=_iso("2026-05-01T00:00:01Z"),
        )
    )
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_active_old",
            title="Old active task",
            status="running",
            updated_at=_iso("2026-05-01T00:00:00Z"),
        )
    )

    receipt = store.purge_task_history(
        cutoff_iso=_iso("2026-06-01T00:00:00Z"),
        dry_run=True,
    )

    assert receipt.status == "dry_run"
    assert receipt.deleted_task_ids == ["task_old_done"]
    assert receipt.deleted_task_event_ids == ["event_old_done"]
    assert receipt.preserved_active_task_ids == ["task_active_old"]
    assert store.get_task("task_old_done") is not None
    assert store.list_task_events("task_old_done")[0].event_id == "event_old_done"


def test_task_history_purge_apply_deletes_terminal_tasks_and_is_idempotent(tmp_path):
    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    for status in ("completed", "failed", "cancelled"):
        task_id = f"task_old_{status}"
        store.upsert_task(
            RuntimeTaskRecord(
                task_id=task_id,
                title=f"Old {status}",
                status=status,
                updated_at=_iso("2026-05-01T00:00:00Z"),
            )
        )
        store.append_task_event(
            RuntimeTaskEvent(
                event_id=f"event_old_{status}",
                task_id=task_id,
                type=status,
                message=status,
                created_at=_iso("2026-05-01T00:00:01Z"),
            )
        )
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_recent_done",
            title="Recent completed task",
            status="completed",
            updated_at=_iso("2026-06-06T00:00:00Z"),
        )
    )
    store.remember_recall(
        RuntimeRecallItem(
            item_id="recall_keep",
            summary="Retention purge must not delete Recall.",
            created_at=_iso("2026-05-01T00:00:00Z"),
        ),
        index_ids=["embedding_recall_keep"],
    )

    receipt = store.purge_task_history(
        cutoff_iso=_iso("2026-06-01T00:00:00Z"),
        dry_run=False,
    )
    second = store.purge_task_history(
        cutoff_iso=_iso("2026-06-01T00:00:00Z"),
        dry_run=False,
    )

    assert receipt.status == "applied"
    assert receipt.deleted_task_ids == [
        "task_old_cancelled",
        "task_old_completed",
        "task_old_failed",
    ]
    assert receipt.deleted_task_event_ids == [
        "event_old_cancelled",
        "event_old_completed",
        "event_old_failed",
    ]
    assert store.get_task("task_old_completed") is None
    assert store.get_task("task_recent_done") is not None
    assert [item.item_id for item in store.list_recall(limit=None)] == ["recall_keep"]
    assert second.deleted_task_ids == []
    assert second.deleted_task_event_ids == []
