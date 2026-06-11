from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


SCHEMA_VERSION = "kaka.host_shell_pilot_evidence_manifest.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_evidence_manifest"
P3_4_COMPLETION_OWNER = "external_host_shell"

ARTIFACT_SPECS = {
    "preflight": {
        "id": "preflight_json",
        "required": True,
        "schema_version": "kaka.host_shell_pilot_preflight.v1",
        "surface": "hermes_openclaw_host_shell_pilot_preflight",
        "default_filename": "preflight.json",
    },
    "conformance": {
        "id": "conformance_json",
        "required": True,
        "schema_version": "kaka.host_private_adapter_conformance.v1",
        "surface": "hermes_openclaw_host_private_adapter_conformance",
        "default_filename": "conformance.json",
    },
    "receipt": {
        "id": "receipt_json",
        "required": True,
        "schema_version": "kaka.host_shell_pilot_receipt.v1",
        "surface": "hermes_openclaw_external_host_shell_pilot",
        "default_filename": "pilot-receipt.json",
    },
    "handoff": {
        "id": "handoff_json",
        "required": True,
        "schema_version": "kaka.host_shell_pilot_handoff.v1",
        "surface": "hermes_openclaw_host_shell_pilot_handoff",
        "default_filename": "handoff.json",
    },
    "artifact_review": {
        "id": "artifact_review_json",
        "required": True,
        "schema_version": "kaka.host_shell_pilot_artifact_review.v1",
        "surface": "hermes_openclaw_host_shell_pilot_artifact_review",
        "default_filename": "artifact-review.json",
    },
    "request": {
        "id": "request_json",
        "required": False,
        "schema_version": "kaka.host_shell_pilot_request.v1",
        "surface": "hermes_openclaw_host_shell_pilot_request",
        "default_filename": "request.json",
    },
    "runbook": {
        "id": "runbook_json",
        "required": False,
        "schema_version": "kaka.host_shell_pilot_runbook.v1",
        "surface": "hermes_openclaw_host_shell_pilot_runbook",
        "default_filename": "runbook.json",
    },
}

REQUIRED_KEYS = ("preflight", "conformance", "receipt", "handoff", "artifact_review")
OPTIONAL_KEYS = ("request", "runbook")


def build_host_shell_pilot_evidence_manifest(
    *,
    runtime: str,
    package_id: str = "",
    created_at: str = "",
    archive_filename: str = "",
    artifact_paths: Mapping[str, str] | None = None,
    max_artifact_bytes: int = 1_048_576,
) -> Mapping[str, object]:
    paths = artifact_paths or {}
    artifacts = [
        _artifact_summary(
            key,
            path=str(paths.get(key, "")),
            runtime=runtime,
            max_artifact_bytes=max_artifact_bytes,
        )
        for key in REQUIRED_KEYS
    ]
    artifacts.extend(
        _artifact_summary(
            key,
            path=str(paths.get(key, "")),
            runtime=runtime,
            max_artifact_bytes=max_artifact_bytes,
        )
        for key in OPTIONAL_KEYS
        if str(paths.get(key, "")).strip()
    )
    artifact_review = _load_json_file(str(paths.get("artifact_review", "")), max_artifact_bytes)
    artifact_review_summary = _artifact_review_summary(artifact_review)
    blocking_reasons = _blocking_reasons(artifacts, artifact_review_summary)
    all_required_present = not any(
        artifact["required"] is True and artifact["blocking_reason"] for artifact in artifacts
    )
    no_artifact_blocking_reasons = not any(
        artifact["blocking_reason"] for artifact in artifacts
    )
    artifact_review_ready = artifact_review_summary["can_submit_to_external_review"] is True
    ready = all_required_present and no_artifact_blocking_reasons and artifact_review_ready
    if ready:
        status = "ready_for_archive"
    elif all_required_present:
        status = "blocked_artifact_review"
    else:
        status = "blocked_missing_artifacts"
    resolved_package_id = package_id.strip() or f"P3.4-{runtime}-pilot-evidence"
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ok": ready,
        "manifest_status": status,
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": P3_4_COMPLETION_OWNER,
        "package": {
            "id": resolved_package_id,
            "created_at": created_at.strip(),
            "archive_filename": archive_filename.strip()
            or f"kaka-p3.4-{runtime}-pilot-evidence.zip",
            "archive_creation": "external",
        },
        "artifacts": artifacts,
        "artifact_review_summary": artifact_review_summary,
        "archive_gates": {
            "all_required_artifacts_present": all_required_present,
            "artifact_review_ready": artifact_review_ready,
            "can_create_external_archive": ready,
            "can_mark_p3_4_complete": False,
            "blocking_reasons": blocking_reasons,
        },
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
            "does_not_submit_handoff": True,
            "does_not_mutate_host_state": True,
            "does_not_create_archive_by_default": True,
            "hashes_local_artifact_files_only": True,
        },
    }


def artifact_paths_from_root(
    artifact_root: str,
    *,
    preflight_json: str = "",
    conformance_json: str = "",
    receipt_json: str = "",
    handoff_json: str = "",
    artifact_review_json: str = "",
    request_json: str = "",
    runbook_json: str = "",
) -> Mapping[str, str]:
    root = Path(artifact_root or ".")
    explicit = {
        "preflight": preflight_json,
        "conformance": conformance_json,
        "receipt": receipt_json,
        "handoff": handoff_json,
        "artifact_review": artifact_review_json,
        "request": request_json,
        "runbook": runbook_json,
    }
    resolved = {}
    for key, spec in ARTIFACT_SPECS.items():
        value = explicit[key]
        if value:
            resolved[key] = value
        elif spec["required"]:
            resolved[key] = str(root / str(spec["default_filename"]))
    return resolved


def _artifact_summary(
    key: str,
    *,
    path: str,
    runtime: str,
    max_artifact_bytes: int,
) -> Mapping[str, object]:
    spec = ARTIFACT_SPECS[key]
    artifact_id = str(spec["id"])
    base = {
        "id": artifact_id,
        "required": bool(spec["required"]),
        "path": path,
        "loaded": False,
        "schema_version": "",
        "surface": "",
        "runtime": "",
        "ok": False,
        "byte_size": 0,
        "sha256": "",
        "blocking_reason": "",
    }
    if not path.strip():
        return {
            **base,
            "blocking_reason": f"missing_artifact:{key}" if spec["required"] else "",
        }
    file_path = Path(path)
    try:
        byte_size = file_path.stat().st_size
    except OSError:
        return {
            **base,
            "blocking_reason": f"missing_artifact:{key}" if spec["required"] else "",
        }
    if byte_size > max_artifact_bytes:
        return {
            **base,
            "byte_size": byte_size,
            "blocking_reason": f"artifact_too_large:{key}",
        }
    payload = _load_json_file(path, max_artifact_bytes)
    if payload is None:
        return {
            **base,
            "byte_size": byte_size,
            "sha256": _sha256(file_path),
            "blocking_reason": f"invalid_json:{key}",
        }
    schema_version = str(payload.get("schema_version", ""))
    surface = str(payload.get("surface", ""))
    artifact_runtime = str(payload.get("runtime", ""))
    schema_valid = (
        schema_version == spec["schema_version"]
        and surface == spec["surface"]
        and artifact_runtime == runtime
    )
    artifact_ok = payload.get("ok") is True
    if not schema_valid:
        blocking_reason = f"invalid_schema:{key}"
    elif not artifact_ok:
        blocking_reason = f"artifact_not_ok:{key}"
    else:
        blocking_reason = ""
    return {
        **base,
        "loaded": True,
        "schema_version": schema_version,
        "surface": surface,
        "runtime": artifact_runtime,
        "ok": artifact_ok,
        "byte_size": byte_size,
        "sha256": _sha256(file_path),
        "blocking_reason": blocking_reason,
    }


def _load_json_file(path: str, max_artifact_bytes: int) -> Mapping[str, object] | None:
    if not path.strip():
        return None
    file_path = Path(path)
    try:
        if file_path.stat().st_size > max_artifact_bytes:
            return None
        payload = json.loads(file_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _artifact_review_summary(artifact_review: Mapping[str, object] | None) -> Mapping[str, object]:
    if artifact_review is None:
        return {
            "provided": False,
            "review_status": "missing",
            "can_submit_to_external_review": False,
            "can_mark_p3_4_complete": False,
        }
    release_review = _object_field(artifact_review, "release_review")
    return {
        "provided": True,
        "review_status": str(artifact_review.get("review_status", "")),
        "can_submit_to_external_review": release_review.get("can_submit_to_external_review")
        is True,
        "can_mark_p3_4_complete": False,
    }


def _blocking_reasons(
    artifacts: list[Mapping[str, object]],
    artifact_review_summary: Mapping[str, object],
) -> list[str]:
    reasons = [
        str(artifact["blocking_reason"])
        for artifact in artifacts
        if artifact["blocking_reason"]
    ]
    if artifact_review_summary["can_submit_to_external_review"] is not True:
        reasons.append("artifact_review_not_ready")
    return reasons


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object_field(value: object, field: str) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        child = value.get(field, {})
        if isinstance(child, Mapping):
            return child
    return {}
