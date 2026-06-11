from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


SCHEMA_VERSION = "kaka.host_shell_pilot_artifact_review.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_artifact_review"
P3_4_COMPLETION_OWNER = "external_host_shell"

ARTIFACT_SPECS = {
    "preflight": {
        "schema_version": "kaka.host_shell_pilot_preflight.v1",
        "surface": "hermes_openclaw_host_shell_pilot_preflight",
        "status_field": "status",
    },
    "conformance": {
        "schema_version": "kaka.host_private_adapter_conformance.v1",
        "surface": "hermes_openclaw_host_private_adapter_conformance",
        "status_field": "",
    },
    "receipt": {
        "schema_version": "kaka.host_shell_pilot_receipt.v1",
        "surface": "hermes_openclaw_external_host_shell_pilot",
        "status_field": "status",
    },
    "handoff": {
        "schema_version": "kaka.host_shell_pilot_handoff.v1",
        "surface": "hermes_openclaw_host_shell_pilot_handoff",
        "status_field": "handoff_status",
    },
}


def build_host_shell_pilot_artifact_review(
    *,
    runtime: str,
    preflight: Mapping[str, object] | None,
    conformance: Mapping[str, object] | None,
    receipt: Mapping[str, object] | None,
    handoff: Mapping[str, object] | None,
    artifact_paths: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    paths = artifact_paths or {}
    artifacts = {
        "preflight": _artifact_summary("preflight", preflight, paths.get("preflight", "")),
        "conformance": _artifact_summary("conformance", conformance, paths.get("conformance", "")),
        "receipt": _artifact_summary("receipt", receipt, paths.get("receipt", "")),
        "handoff": _artifact_summary("handoff", handoff, paths.get("handoff", "")),
    }
    consistency = _artifact_consistency(
        runtime=runtime,
        preflight=preflight,
        conformance=conformance,
        receipt=receipt,
        handoff=handoff,
    )
    blocking_reasons = _blocking_reasons(
        artifacts=artifacts,
        consistency=consistency,
        preflight=preflight,
        conformance=conformance,
        receipt=receipt,
        handoff=handoff,
    )
    ready_for_external_review = not blocking_reasons
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ok": ready_for_external_review,
        "review_status": "ready_for_external_review"
        if ready_for_external_review
        else "blocked",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": P3_4_COMPLETION_OWNER,
        "artifacts": artifacts,
        "artifact_consistency": consistency,
        "release_review": {
            "can_submit_to_external_review": ready_for_external_review,
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
            "does_not_mutate_host_state": True,
        },
    }


def build_host_shell_pilot_artifact_review_from_paths(
    *,
    runtime: str,
    preflight_path: str,
    conformance_path: str,
    receipt_path: str,
    handoff_path: str,
) -> Mapping[str, object]:
    paths = {
        "preflight": preflight_path,
        "conformance": conformance_path,
        "receipt": receipt_path,
        "handoff": handoff_path,
    }
    loaded = {key: _load_json_file(path) for key, path in paths.items()}
    return build_host_shell_pilot_artifact_review(
        runtime=runtime,
        preflight=loaded["preflight"],
        conformance=loaded["conformance"],
        receipt=loaded["receipt"],
        handoff=loaded["handoff"],
        artifact_paths=paths,
    )


def _load_json_file(path: str) -> Mapping[str, object] | None:
    if not path.strip():
        return None
    try:
        payload = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _artifact_summary(
    artifact_id: str,
    artifact: Mapping[str, object] | None,
    path: str,
) -> Mapping[str, object]:
    if artifact is None:
        return {
            "required": True,
            "path": path,
            "loaded": False,
            "schema_valid": False,
            "schema_errors": [f"missing_artifact:{artifact_id}"],
            "schema_version": "",
            "runtime": "",
            "ok": False,
            "status": "missing",
            "summary": {},
            "blocking_reason": f"missing_artifact:{artifact_id}",
        }
    schema_errors = _schema_errors(artifact_id, artifact)
    schema_version = str(artifact.get("schema_version", ""))
    return {
        "required": True,
        "path": path,
        "loaded": True,
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "schema_version": schema_version,
        "runtime": str(artifact.get("runtime", "")),
        "ok": artifact.get("ok") is True,
        "status": _artifact_status(artifact_id, artifact),
        "summary": _object_field(artifact, "summary") if artifact_id == "conformance" else {},
        "blocking_reason": ""
        if not schema_errors
        else f"invalid_schema:{artifact_id}",
    }


def _schema_errors(artifact_id: str, artifact: Mapping[str, object]) -> list[str]:
    spec = ARTIFACT_SPECS[artifact_id]
    errors: list[str] = []
    if artifact.get("schema_version") != spec["schema_version"]:
        errors.append("schema_version")
    if artifact.get("surface") != spec["surface"]:
        errors.append("surface")
    if artifact.get("runtime") not in ("hermes", "openclaw"):
        errors.append("runtime")
    if "ok" not in artifact:
        errors.append("ok")
    status_field = str(spec["status_field"])
    if status_field and status_field not in artifact:
        errors.append(status_field)
    if artifact_id == "conformance" and "summary" not in artifact:
        errors.append("summary")
    if artifact_id == "receipt" and "release_readiness" not in artifact:
        errors.append("release_readiness")
    if artifact_id == "handoff" and "release_handoff" not in artifact:
        errors.append("release_handoff")
    return errors


def _artifact_status(artifact_id: str, artifact: Mapping[str, object]) -> str:
    if artifact_id == "preflight":
        return str(artifact.get("status", ""))
    if artifact_id == "handoff":
        return str(artifact.get("handoff_status", ""))
    if artifact_id == "receipt":
        return str(artifact.get("status", ""))
    return "passed" if artifact.get("ok") is True else "failed"


def _artifact_consistency(
    *,
    runtime: str,
    preflight: Mapping[str, object] | None,
    conformance: Mapping[str, object] | None,
    receipt: Mapping[str, object] | None,
    handoff: Mapping[str, object] | None,
) -> Mapping[str, object]:
    loaded = [item for item in (preflight, conformance, receipt, handoff) if item is not None]
    runtime_match = bool(loaded) and all(item.get("runtime") == runtime for item in loaded)
    receipt_conformance = _object_field(receipt, "conformance")
    handoff_receipt = _object_field(handoff, "pilot_receipt")
    handoff_audit_refs = _object_field(handoff, "audit_refs")
    return {
        "runtime_match": runtime_match,
        "preflight_allows_conformance": bool(preflight)
        and preflight.get("status") == "ready_for_conformance"
        and preflight.get("ok") is True,
        "conformance_passed": bool(conformance) and conformance.get("ok") is True,
        "conformance_embedded_in_receipt": _summary_matches(
            _object_field(conformance, "summary"),
            _object_field(receipt_conformance, "summary"),
        ),
        "receipt_ready": bool(receipt) and receipt.get("status") == "ready",
        "receipt_embedded_in_handoff": bool(receipt)
        and bool(handoff_receipt)
        and handoff_receipt.get("status") == receipt.get("status")
        and _object_field(handoff_receipt, "private_adapter_command")
        == _object_field(receipt, "private_adapter_command"),
        "handoff_ready_to_submit": bool(handoff)
        and handoff.get("handoff_status") == "ready_to_submit",
        "audit_refs_complete": handoff_audit_refs.get("complete") is True,
        "no_synthetic_conformance": receipt_conformance.get("synthetic_only") is not True
        and (not receipt or receipt.get("status") != "synthetic_only"),
        "private_adapter_command_consistent": _private_adapter_command_consistent(
            preflight,
            receipt,
            handoff_receipt,
        ),
    }


def _blocking_reasons(
    *,
    artifacts: Mapping[str, Mapping[str, object]],
    consistency: Mapping[str, object],
    preflight: Mapping[str, object] | None,
    conformance: Mapping[str, object] | None,
    receipt: Mapping[str, object] | None,
    handoff: Mapping[str, object] | None,
) -> list[str]:
    reasons: list[str] = []
    for artifact_id, artifact in artifacts.items():
        if artifact["loaded"] is not True:
            reasons.append(f"missing_artifact:{artifact_id}")
        elif artifact["blocking_reason"]:
            reasons.append(str(artifact["blocking_reason"]))
    if preflight is not None and preflight.get("status") != "ready_for_conformance":
        reasons.append("preflight_not_ready")
    if conformance is not None and conformance.get("ok") is not True:
        reasons.append("conformance_not_passed")
    if receipt is not None and receipt.get("status") != "ready":
        reasons.append("receipt_not_ready")
    if handoff is not None and handoff.get("handoff_status") != "ready_to_submit":
        reasons.append("handoff_not_ready_to_submit")
    if loaded_all(preflight, conformance, receipt, handoff):
        if consistency["runtime_match"] is not True:
            reasons.append("artifact_runtime_mismatch")
        if consistency["conformance_embedded_in_receipt"] is not True:
            reasons.append("receipt_conformance_mismatch")
        if consistency["receipt_embedded_in_handoff"] is not True:
            reasons.append("handoff_receipt_mismatch")
        if consistency["audit_refs_complete"] is not True:
            reasons.append("missing_audit_refs")
        if consistency["no_synthetic_conformance"] is not True:
            reasons.append("synthetic_conformance_only")
        if consistency["private_adapter_command_consistent"] is not True:
            reasons.append("private_adapter_command_mismatch")
    return reasons


def loaded_all(*artifacts: Mapping[str, object] | None) -> bool:
    return all(artifact is not None for artifact in artifacts)


def _object_field(value: object, field: str) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        child = value.get(field, {})
        if isinstance(child, Mapping):
            return child
    return {}


def _summary_matches(
    actual: Mapping[str, object],
    expected: Mapping[str, object],
) -> bool:
    return bool(actual) and actual == expected


def _private_adapter_command_consistent(
    preflight: Mapping[str, object] | None,
    receipt: Mapping[str, object] | None,
    handoff_receipt: Mapping[str, object],
) -> bool:
    preflight_command = _object_field(_object_field(preflight, "private_adapter_command"), "selected")
    receipt_command = _object_field(receipt, "private_adapter_command")
    handoff_command = _object_field(handoff_receipt, "private_adapter_command")
    if not preflight_command or not receipt_command or not handoff_command:
        return False
    return (
        preflight_command.get("provided") is True
        and receipt_command.get("provided") is True
        and handoff_command.get("provided") is True
        and str(preflight_command.get("path", ""))
        == str(receipt_command.get("path", ""))
        == str(handoff_command.get("path", ""))
    )
