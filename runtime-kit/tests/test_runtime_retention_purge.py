from __future__ import annotations

import json

from kaka_mobile_runtime_kit.retention_purge import build_runtime_retention_purge_receipt
from kaka_mobile_runtime_kit.runtime_store import RuntimeTaskRecord, SQLiteRuntimeStore


def test_retention_purge_receipt_is_runtime_side_and_phone_api_unchanged():
    receipt = build_runtime_retention_purge_receipt(
        runtime="hermes",
        policy={
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        now_iso="2026-06-07T00:00:00Z",
        dry_run=True,
    )

    assert receipt["schema_version"] == "kaka.runtime_retention_purge_receipt.v1"
    assert receipt["surface"] == "hermes_openclaw_runtime_retention_purge"
    assert receipt["mode"] == "dry_run"
    assert receipt["applied"] is False
    assert receipt["safety"] == {
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "phone_settings_owner": False,
        "no_mobile_bridge_purge_endpoint": True,
        "no_automatic_cleanup": True,
        "no_recall_purge": True,
    }
    assert receipt["recall_untouched"] is True
    assert receipt["cutoffs"] == {
        "input_assets_before": "2026-05-31T00:00:00Z",
        "output_assets_before": "2026-05-08T00:00:00Z",
        "task_history_before": "2026-05-08T00:00:00Z",
    }
    assert receipt["eligible"]["task_ids"] == []
    assert receipt["deleted"]["task_ids"] == []
    assert receipt["preserved"]["asset_purge_status"] == "skipped_missing_asset_timestamps"
    rendered = json.dumps(receipt, sort_keys=True)
    for forbidden in (
        "runtime_store_path",
        "sqlite",
        "provider_endpoint",
        "bearer",
        "mobile_token",
        "tls_private_key_path",
        "raw_logs",
        "hidden_prompt",
        "embedding",
    ):
        assert forbidden not in rendered.lower()


def test_retention_purge_receipt_skips_assets_without_reliable_timestamps_and_applies_task_store(tmp_path):
    store = SQLiteRuntimeStore(tmp_path / "kaka-runtime.sqlite3")
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_old_done",
            title="Old task",
            status="completed",
            updated_at="2026-05-01T00:00:00Z",
        )
    )
    assets = {
        "asset_old_input": {
            "bytes": b"input",
            "mime_type": "text/plain",
            "size_bytes": 5,
        },
        "asset_result_old_output": {
            "bytes": b"output",
            "mime_type": "text/plain",
            "size_bytes": 6,
        },
    }

    receipt = build_runtime_retention_purge_receipt(
        runtime="openclaw",
        policy={
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        now_iso="2026-06-07T00:00:00Z",
        dry_run=False,
        store=store,
        memory_assets=assets,
    )

    assert receipt["mode"] == "apply"
    assert receipt["applied"] is True
    assert receipt["eligible"]["task_ids"] == ["task_old_done"]
    assert receipt["deleted"]["task_ids"] == ["task_old_done"]
    assert receipt["deleted"]["input_asset_ids"] == []
    assert receipt["deleted"]["output_asset_ids"] == []
    assert receipt["preserved"]["asset_purge_status"] == "skipped_missing_asset_timestamps"
    assert receipt["preserved"]["untracked_asset_ids"] == [
        "asset_old_input",
        "asset_result_old_output",
    ]
    assert sorted(assets) == ["asset_old_input", "asset_result_old_output"]
    assert store.get_task("task_old_done") is None


def test_retention_purge_receipt_deletes_timestamped_input_and_output_assets_without_leaking_bytes():
    assets = {
        "asset_old_input": {
            "role": "input",
            "created_at": "2026-05-01T00:00:00Z",
            "bytes": b"old-input",
            "mime_type": "image/png",
        },
        "asset_recent_input": {
            "role": "input",
            "created_at": "2026-06-06T00:00:00Z",
            "bytes": b"recent-input",
            "mime_type": "image/png",
        },
        "asset_result_old_output": {
            "role": "output",
            "created_at": "2026-05-01T00:00:00Z",
            "bytes": b"old-output",
            "mime_type": "image/png",
        },
        "asset_untimestamped": {
            "role": "input",
            "bytes": b"unknown-age",
            "mime_type": "image/png",
        },
    }

    dry_run = build_runtime_retention_purge_receipt(
        runtime="hermes",
        policy={
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        now_iso="2026-06-07T00:00:00Z",
        dry_run=True,
        memory_assets=assets,
    )

    assert dry_run["eligible"]["input_asset_ids"] == ["asset_old_input"]
    assert dry_run["eligible"]["output_asset_ids"] == ["asset_result_old_output"]
    assert dry_run["deleted"]["input_asset_ids"] == []
    assert dry_run["deleted"]["output_asset_ids"] == []
    assert dry_run["preserved"]["asset_purge_status"] == "partial_missing_asset_timestamps"
    assert dry_run["preserved"]["untracked_asset_ids"] == ["asset_untimestamped"]
    assert sorted(assets) == [
        "asset_old_input",
        "asset_recent_input",
        "asset_result_old_output",
        "asset_untimestamped",
    ]

    apply_receipt = build_runtime_retention_purge_receipt(
        runtime="hermes",
        policy={
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        now_iso="2026-06-07T00:00:00Z",
        dry_run=False,
        memory_assets=assets,
    )

    assert apply_receipt["eligible"]["input_asset_ids"] == ["asset_old_input"]
    assert apply_receipt["eligible"]["output_asset_ids"] == ["asset_result_old_output"]
    assert apply_receipt["deleted"]["input_asset_ids"] == ["asset_old_input"]
    assert apply_receipt["deleted"]["output_asset_ids"] == ["asset_result_old_output"]
    assert apply_receipt["preserved"]["asset_purge_status"] == "partial_missing_asset_timestamps"
    assert apply_receipt["preserved"]["untracked_asset_ids"] == ["asset_untimestamped"]
    assert sorted(assets) == ["asset_recent_input", "asset_untimestamped"]

    rendered = json.dumps(apply_receipt, sort_keys=True).lower()
    for forbidden in (
        "old-input",
        "old-output",
        "recent-input",
        "unknown-age",
        "runtime_store_path",
        "sqlite",
        "provider_endpoint",
        "bearer",
        "mobile_token",
        "raw_asset_bytes",
    ):
        assert forbidden not in rendered


def test_retention_purge_receipt_deletes_store_backed_assets_without_memory_assets_or_leaks(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.upsert_asset(
        RuntimeAssetRecord(
            asset_id="asset_old_input",
            role="input",
            created_at="2026-05-01T00:00:00Z",
            filename="old-input.png",
            mime_type="image/png",
            size_bytes=9,
            sha256="oldinput",
            body=b"old-input-bytes",
            metadata={"runtime_store_path": str(db_path), "raw_asset_bytes": "old-input-bytes"},
        )
    )
    store.upsert_asset(
        RuntimeAssetRecord(
            asset_id="asset_result_old_output",
            role="output",
            created_at="2026-05-01T00:00:00Z",
            filename="old-output.png",
            mime_type="image/png",
            size_bytes=10,
            sha256="oldoutput",
            body=b"old-output-bytes",
            metadata={"provider_endpoint": "http://127.0.0.1/private"},
        )
    )

    receipt = build_runtime_retention_purge_receipt(
        runtime="hermes",
        policy={
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        now_iso="2026-06-07T00:00:00Z",
        dry_run=False,
        store=store,
    )

    assert receipt["deleted"]["input_asset_ids"] == ["asset_old_input"]
    assert receipt["deleted"]["output_asset_ids"] == ["asset_result_old_output"]
    assert receipt["preserved"]["asset_purge_status"] == "complete"
    assert receipt["preserved"]["untracked_asset_ids"] == []
    assert store.get_asset("asset_old_input") is None
    assert store.get_asset("asset_result_old_output") is None

    rendered = json.dumps(receipt, sort_keys=True).lower()
    for forbidden in (
        "old-input-bytes",
        "old-output-bytes",
        str(db_path).lower(),
        "runtime_store_path",
        "provider_endpoint",
        "sqlite",
        "raw_asset_bytes",
    ):
        assert forbidden not in rendered
