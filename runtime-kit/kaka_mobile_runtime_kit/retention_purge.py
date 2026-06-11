from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


SCHEMA_VERSION = "kaka.runtime_retention_purge_receipt.v1"
SURFACE = "hermes_openclaw_runtime_retention_purge"


def build_runtime_retention_purge_receipt(
    *,
    runtime: str,
    policy: Mapping[str, int],
    now_iso: str,
    dry_run: bool = True,
    store: Any | None = None,
    memory_assets: MutableMapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    now = _parse_utc(now_iso)
    normalized_policy = {
        "input_assets_days": int(policy["input_assets_days"]),
        "output_assets_days": int(policy["output_assets_days"]),
        "task_history_days": int(policy["task_history_days"]),
    }
    input_cutoff = _format_utc(now - timedelta(days=normalized_policy["input_assets_days"]))
    output_cutoff = _format_utc(now - timedelta(days=normalized_policy["output_assets_days"]))
    task_cutoff = _format_utc(now - timedelta(days=normalized_policy["task_history_days"]))

    eligible_input_asset_ids: list[str] = []
    eligible_output_asset_ids: list[str] = []
    deleted_input_asset_ids: list[str] = []
    deleted_output_asset_ids: list[str] = []
    untracked_asset_ids: list[str] = []
    asset_purge_status = "skipped_missing_asset_timestamps"
    asset_source_evaluated = False
    if store is not None and hasattr(store, "purge_assets"):
        asset_source_evaluated = True
        asset_receipt = store.purge_assets(input_cutoff, output_cutoff, dry_run=dry_run)
        _append_unique(eligible_input_asset_ids, asset_receipt.eligible_input_asset_ids)
        _append_unique(eligible_output_asset_ids, asset_receipt.eligible_output_asset_ids)
        _append_unique(deleted_input_asset_ids, asset_receipt.deleted_input_asset_ids)
        _append_unique(deleted_output_asset_ids, asset_receipt.deleted_output_asset_ids)
        _append_unique(untracked_asset_ids, asset_receipt.untracked_asset_ids)

    if memory_assets is not None:
        asset_source_evaluated = True
        input_cutoff_dt = _parse_utc(input_cutoff)
        output_cutoff_dt = _parse_utc(output_cutoff)
        for asset_id, asset in sorted(memory_assets.items()):
            kind = _asset_retention_kind(asset_id, asset)
            created_at = _asset_created_at(asset)
            if kind not in {"input", "output"} or created_at is None:
                _append_unique(untracked_asset_ids, [asset_id])
                continue
            if kind == "input" and created_at < input_cutoff_dt:
                _append_unique(eligible_input_asset_ids, [asset_id])
            if kind == "output" and created_at < output_cutoff_dt:
                _append_unique(eligible_output_asset_ids, [asset_id])
        if not dry_run:
            for asset_id in eligible_input_asset_ids:
                if memory_assets.pop(asset_id, None) is not None:
                    _append_unique(deleted_input_asset_ids, [asset_id])
            for asset_id in eligible_output_asset_ids:
                if memory_assets.pop(asset_id, None) is not None:
                    _append_unique(deleted_output_asset_ids, [asset_id])

    if asset_source_evaluated:
        if untracked_asset_ids:
            asset_purge_status = (
                "partial_missing_asset_timestamps"
                if eligible_input_asset_ids or eligible_output_asset_ids
                else "skipped_missing_asset_timestamps"
            )
        else:
            asset_purge_status = "complete"

    eligible_task_ids: list[str] = []
    eligible_task_event_ids: list[str] = []
    deleted_task_ids: list[str] = []
    deleted_task_event_ids: list[str] = []
    preserved_active_task_ids: list[str] = []
    if store is not None and hasattr(store, "purge_task_history"):
        task_receipt = store.purge_task_history(task_cutoff, dry_run=dry_run)
        eligible_task_ids = list(task_receipt.deleted_task_ids)
        eligible_task_event_ids = list(task_receipt.deleted_task_event_ids)
        if not dry_run:
            deleted_task_ids = list(task_receipt.deleted_task_ids)
            deleted_task_event_ids = list(task_receipt.deleted_task_event_ids)
        preserved_active_task_ids = list(task_receipt.preserved_active_task_ids)

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "mode": "dry_run" if dry_run else "apply",
        "applied": not dry_run,
        "generated_at": _format_utc(now),
        "policy": normalized_policy,
        "cutoffs": {
            "input_assets_before": input_cutoff,
            "output_assets_before": output_cutoff,
            "task_history_before": task_cutoff,
        },
        "eligible": {
            "input_asset_ids": eligible_input_asset_ids,
            "output_asset_ids": eligible_output_asset_ids,
            "task_ids": eligible_task_ids,
            "task_event_ids": eligible_task_event_ids,
        },
        "deleted": {
            "input_asset_ids": deleted_input_asset_ids,
            "output_asset_ids": deleted_output_asset_ids,
            "task_ids": deleted_task_ids,
            "task_event_ids": deleted_task_event_ids,
        },
        "preserved": {
            "active_task_ids": preserved_active_task_ids,
            "untracked_asset_ids": untracked_asset_ids,
            "asset_purge_status": asset_purge_status,
        },
        "recall_untouched": True,
        "safety": {
            "runtime_side_only": True,
            "phone_api_path": "/mobile/v1",
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_mobile_bridge_purge_endpoint": True,
            "no_automatic_cleanup": True,
            "no_recall_purge": True,
        },
    }


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def _asset_retention_kind(asset_id: str, asset: Mapping[str, Any]) -> str:
    raw_kind = str(asset.get("retention_kind") or asset.get("role") or "").strip().lower()
    if raw_kind in {"input", "output"}:
        return raw_kind
    if asset_id.startswith("asset_result_"):
        return "output"
    if asset_id.startswith("asset_"):
        return "input"
    return ""


def _asset_created_at(asset: Mapping[str, Any]) -> datetime | None:
    raw_created_at = str(asset.get("retention_created_at") or asset.get("created_at") or "").strip()
    if not raw_created_at:
        return None
    try:
        return _parse_utc(raw_created_at)
    except ValueError:
        return None
