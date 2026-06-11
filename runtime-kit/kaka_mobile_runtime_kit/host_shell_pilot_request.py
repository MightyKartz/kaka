from __future__ import annotations

from typing import Mapping

from .cli import BridgeConfig
from .host_adapter import HOST_ADAPTER_ACTIONS
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
    private_adapter_well_known_paths,
)
from .host_private_adapter_conformance import REQUIRED_CAPABILITIES
from .host_shell_pilot_handoff import DISTRIBUTION_AUDIT_REFS, DRILL_AUDIT_REFS


SCHEMA_VERSION = "kaka.host_shell_pilot_request.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_request"
P3_4_COMPLETION_OWNER = "external_host_shell"


def build_host_shell_pilot_request(
    config: BridgeConfig,
    *,
    request_id: str = "",
    pilot_owner: str = "",
    expected_private_adapter_command_path: str = "",
    artifact_root: str = "",
) -> Mapping[str, object]:
    runtime = config.runtime
    default_command = default_private_adapter_command_name(runtime)
    resolved_artifact_root = artifact_root.strip() or f"artifacts/{runtime}"
    expected_command_path = (
        expected_private_adapter_command_path.strip()
        or private_adapter_well_known_paths(runtime, default_command)[0]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ok": True,
        "request_status": "ready_to_send",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": P3_4_COMPLETION_OWNER,
        "pilot_request": {
            "id": request_id.strip() or f"P3.4-{runtime}-host-shell-pilot",
            "audience": pilot_owner.strip() or _default_pilot_owner(runtime),
            "purpose": "request_external_host_shell_pilot_materials",
            "status": "waiting_for_host_owned_materials",
        },
        "target_host": {
            "default_command_name": default_command,
            "environment_variable": private_adapter_environment_variable(runtime),
            "manifest_key": "host_private_adapter.command",
            "well_known_paths": private_adapter_well_known_paths(runtime, default_command),
            "expected_private_adapter_command_path": expected_command_path,
            "accepted_discovery_sources": [
                "explicit_cli_argument",
                "runtime_environment_variable",
                "manifest_entrypoint",
                "well_known_path",
            ],
        },
        "required_action_ids": list(HOST_ADAPTER_ACTIONS),
        "required_capabilities": list(REQUIRED_CAPABILITIES),
        "required_host_deliverables": _required_host_deliverables(expected_command_path),
        "required_audit_refs": {
            "distribution": list(DISTRIBUTION_AUDIT_REFS),
            "drills": list(DRILL_AUDIT_REFS),
        },
        "expected_runtime_kit_artifacts": _expected_artifacts(
            runtime=runtime,
            artifact_root=resolved_artifact_root,
        ),
        "acceptance_gates": {
            "can_start_external_review": False,
            "requires_host_owned_private_adapter_command": True,
            "requires_conformance_passed": True,
            "requires_handoff_ready_to_submit": True,
            "requires_artifact_review_ready": True,
            "can_mark_p3_4_complete": False,
            "blocking_reason": "waiting_for_host_owned_materials",
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
            "does_not_submit_handoff": True,
        },
    }


def _default_pilot_owner(runtime: str) -> str:
    if runtime == "hermes":
        return "Hermes host team"
    if runtime == "openclaw":
        return "OpenClaw host team"
    return "Host team"


def _required_host_deliverables(command_path: str) -> list[Mapping[str, object]]:
    return [
        _deliverable(
            "private_adapter_command_binary",
            "host_shell",
            command_path,
            "Host-owned executable command outside the Kaka repository.",
            "missing_private_adapter_command",
        ),
        _deliverable(
            "private_adapter_request_response_contract",
            "host_shell",
            "runtime-kit/packaging/HOST_PRIVATE_ADAPTER_IMPLEMENTATION.md",
            "Adapter implements kaka.host_private_adapter_request.v1 and response v1.",
            "missing_private_adapter_contract_ack",
        ),
        _deliverable(
            "host_action_matrix",
            "host_shell",
            "install/login-item/update/uninstall/logs/health/port-repair/supervision",
            "Adapter supports all required host lifecycle actions.",
            "missing_host_action_matrix",
        ),
        _deliverable(
            "native_distribution_channel",
            "host_shell",
            "native_channel_ref",
            "Host-owned distribution channel evidence.",
            "missing_audit_ref:native_channel_ref",
        ),
        _deliverable(
            "signature_or_notarization",
            "host_shell",
            "signature_subject + notarization_team_id",
            "Signature or notarization evidence for the command/package.",
            "missing_signature_or_notarization",
        ),
        _deliverable(
            "update_feed",
            "host_shell",
            "update_feed_ref",
            "Host-owned update feed reference.",
            "missing_audit_ref:update_feed_ref",
        ),
        _deliverable(
            "install_drill_receipt",
            "host_shell",
            "install_receipt_ref",
            "Install drill receipt for ordinary-user release review.",
            "missing_audit_ref:install_receipt_ref",
        ),
        _deliverable(
            "update_drill_receipt",
            "host_shell",
            "update_receipt_ref",
            "Update drill receipt for ordinary-user release review.",
            "missing_audit_ref:update_receipt_ref",
        ),
        _deliverable(
            "failure_recovery_drill_receipt",
            "host_shell",
            "failure_recovery_receipt_ref",
            "Failure-recovery drill receipt for ordinary-user release review.",
            "missing_audit_ref:failure_recovery_receipt_ref",
        ),
        _deliverable(
            "release_notes",
            "host_shell",
            "release_notes_ref",
            "User-facing release notes reference.",
            "missing_audit_ref:release_notes_ref",
        ),
    ]


def _deliverable(
    deliverable_id: str,
    owner: str,
    requested_value: str,
    description: str,
    blocking_reason: str,
) -> Mapping[str, object]:
    return {
        "id": deliverable_id,
        "owner": owner,
        "required": True,
        "status": "requested",
        "requested_value": requested_value,
        "description": description,
        "blocking_reason": blocking_reason,
    }


def _expected_artifacts(
    *,
    runtime: str,
    artifact_root: str,
) -> list[Mapping[str, object]]:
    return [
        _artifact(
            "preflight_json",
            "host-shell-pilot-preflight",
            "kaka.host_shell_pilot_preflight.v1",
            f"{artifact_root}/preflight.json",
            "Host-shell and private command discovery inputs are ready.",
        ),
        _artifact(
            "conformance_json",
            "host-private-adapter-conformance",
            "kaka.host_private_adapter_conformance.v1",
            f"{artifact_root}/conformance.json",
            "Host-owned command passed the lifecycle conformance matrix.",
        ),
        _artifact(
            "pilot_receipt_json",
            "host-shell-pilot-report",
            "kaka.host_shell_pilot_receipt.v1",
            f"{artifact_root}/pilot-receipt.json",
            "Readiness receipt records conformance and host evidence.",
        ),
        _artifact(
            "handoff_json",
            "host-shell-pilot-handoff",
            "kaka.host_shell_pilot_handoff.v1",
            f"{artifact_root}/handoff.json",
            "Handoff bundle is ready to submit for external review.",
        ),
        _artifact(
            "artifact_review_json",
            "host-shell-pilot-artifact-review",
            "kaka.host_shell_pilot_artifact_review.v1",
            f"{artifact_root}/artifact-review.json",
            "Post-run artifact review reports ready_for_external_review.",
        ),
    ]


def _artifact(
    artifact_id: str,
    command: str,
    output_schema: str,
    suggested_path: str,
    acceptance_note: str,
) -> Mapping[str, object]:
    return {
        "id": artifact_id,
        "owner": "runtime_kit",
        "required": True,
        "command": command,
        "output_schema": output_schema,
        "suggested_path": suggested_path,
        "acceptance_note": acceptance_note,
    }
