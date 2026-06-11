from __future__ import annotations

from typing import Mapping

from .cli import BridgeConfig
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
    private_adapter_well_known_paths,
)
from .host_shell_pilot_handoff import DISTRIBUTION_AUDIT_REFS, DRILL_AUDIT_REFS
from .host_shell_pilot_preflight import build_host_shell_pilot_preflight


SCHEMA_VERSION = "kaka.host_shell_pilot_runbook.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_runbook"
P3_4_COMPLETION_OWNER = "external_host_shell"


def build_host_shell_pilot_runbook(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    applications_root: str = "/Applications",
    home: str | None = None,
    path_env: str | None = None,
    distribution_source: str = "local_checkout",
    distribution_channel: str = "development",
    package_version: str = "development",
    host_api_level: str = "preview",
    native_channel_verified: bool = False,
    signature_verified: bool = False,
    update_feed_verified: bool = False,
    install_verified: bool = False,
    update_verified: bool = False,
    failure_recovery_verified: bool = False,
    release_notes_verified: bool = False,
    native_channel_ref: str = "",
    signature_subject: str = "",
    notarization_team_id: str = "",
    update_feed_ref: str = "",
    install_receipt_ref: str = "",
    update_receipt_ref: str = "",
    failure_recovery_receipt_ref: str = "",
    release_notes_ref: str = "",
) -> Mapping[str, object]:
    runtime = config.runtime
    preflight = build_host_shell_pilot_preflight(
        config,
        private_adapter_command=private_adapter_command,
        applications_root=applications_root,
        home=home,
        path_env=path_env,
    )
    can_run_conformance = preflight["ok"] is True
    blocking_reasons = list(preflight["release_preflight"]["blocking_reasons"])
    selected = preflight["private_adapter_command"]["selected"]
    command_path = str(selected["path"]) if selected["provided"] is True else ""
    evidence_values = {
        "native_channel_ref": native_channel_ref,
        "signature_subject": signature_subject,
        "notarization_team_id": notarization_team_id,
        "update_feed_ref": update_feed_ref,
        "install_receipt_ref": install_receipt_ref,
        "update_receipt_ref": update_receipt_ref,
        "failure_recovery_receipt_ref": failure_recovery_receipt_ref,
        "release_notes_ref": release_notes_ref,
    }
    verified_flags = {
        "native_channel_verified": native_channel_verified,
        "signature_verified": signature_verified,
        "update_feed_verified": update_feed_verified,
        "install_verified": install_verified,
        "update_verified": update_verified,
        "failure_recovery_verified": failure_recovery_verified,
        "release_notes_verified": release_notes_verified,
    }
    command_artifacts = _command_artifacts(
        runtime=runtime,
        command_path=command_path,
        distribution_source=distribution_source,
        distribution_channel=distribution_channel,
        package_version=package_version,
        host_api_level=host_api_level,
        evidence_values=evidence_values,
        verified_flags=verified_flags,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ok": can_run_conformance,
        "runbook_status": "ready_for_conformance" if can_run_conformance else "blocked",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": P3_4_COMPLETION_OWNER,
        "brief": _brief(blocking_reasons),
        "pilot_target": _pilot_target(
            runtime=runtime,
            distribution_source=distribution_source,
            distribution_channel=distribution_channel,
            package_version=package_version,
            host_api_level=host_api_level,
        ),
        "preflight": {
            "status": preflight["status"],
            "can_run_conformance": can_run_conformance,
            "blocking_reasons": blocking_reasons,
            "host_shell_detected": preflight["host_shell"]["detected"],
            "private_adapter_command": {
                "provided": selected["provided"],
                "source": selected["source"],
                "path": command_path,
            },
        },
        "ordered_steps": _ordered_steps(
            can_run_conformance=can_run_conformance,
            blocking_reasons=blocking_reasons,
            evidence_complete=_evidence_complete(evidence_values),
        ),
        "command_artifacts": command_artifacts,
        "evidence_requirements": _evidence_requirements(evidence_values),
        "acceptance_gates": {
            "can_run_conformance": can_run_conformance,
            "can_emit_ready_receipt": False,
            "can_submit_handoff": False,
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


def _brief(blocking_reasons: list[str]) -> Mapping[str, object]:
    if "missing_private_adapter_command" in blocking_reasons:
        requested = "provide_private_adapter_command"
    elif "missing_host_shell" in blocking_reasons:
        requested = "install_or_open_host_shell"
    elif blocking_reasons:
        requested = "resolve_preflight_blockers"
    else:
        requested = "run_host_private_adapter_conformance"
    return {
        "goal": "prepare_external_host_shell_pilot",
        "current_blocker": blocking_reasons[0] if blocking_reasons else "",
        "requested_host_owner_action": requested,
        "non_goals": [
            "does_not_complete_p3_4",
            "does_not_bundle_proprietary_host_binary",
            "does_not_expose_private_host_api_to_phone",
        ],
    }


def _pilot_target(
    *,
    runtime: str,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    host_api_level: str,
) -> Mapping[str, object]:
    default_command = default_private_adapter_command_name(runtime)
    return {
        "default_command_name": default_command,
        "environment_variable": private_adapter_environment_variable(runtime),
        "manifest_key": "host_private_adapter.command",
        "well_known_paths": private_adapter_well_known_paths(runtime, default_command),
        "distribution_source": distribution_source,
        "distribution_channel": distribution_channel,
        "package_version": package_version,
        "host_api_level": host_api_level,
    }


def _ordered_steps(
    *,
    can_run_conformance: bool,
    blocking_reasons: list[str],
    evidence_complete: bool,
) -> list[Mapping[str, object]]:
    first_blocker = blocking_reasons[0] if blocking_reasons else ""
    evidence_status = "provided" if evidence_complete else "waiting_for_host_evidence"
    return [
        _step(
            "host_shell_pilot_preflight",
            "runtime_kit",
            "ready" if can_run_conformance else "blocked",
            "kaka.host_shell_pilot_preflight.v1",
            first_blocker,
        ),
        _step(
            "host_private_adapter_conformance",
            "runtime_kit",
            "ready" if can_run_conformance else "blocked",
            "kaka.host_private_adapter_conformance.v1",
            "" if can_run_conformance else first_blocker,
        ),
        _step(
            "distribution_and_signing_evidence",
            "host_shell",
            evidence_status,
            "kaka.host_shell_pilot_receipt.v1",
            "",
        ),
        _step(
            "install_update_failure_drills",
            "host_shell",
            evidence_status,
            "kaka.host_shell_pilot_receipt.v1",
            "",
        ),
        _step(
            "host_shell_pilot_report",
            "runtime_kit",
            "waiting_for_conformance_and_evidence" if can_run_conformance else "blocked",
            "kaka.host_shell_pilot_receipt.v1",
            "" if can_run_conformance else first_blocker,
        ),
        _step(
            "host_shell_pilot_handoff",
            "runtime_kit",
            "waiting_for_conformance_and_evidence" if can_run_conformance else "blocked",
            "kaka.host_shell_pilot_handoff.v1",
            "" if can_run_conformance else first_blocker,
        ),
    ]


def _step(
    step_id: str,
    owner: str,
    status: str,
    output_schema: str,
    blocking_reason: str,
) -> Mapping[str, object]:
    return {
        "id": step_id,
        "owner": owner,
        "required": True,
        "status": status,
        "output_schema": output_schema,
        "blocking_reason": blocking_reason,
    }


def _command_artifacts(
    *,
    runtime: str,
    command_path: str,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    host_api_level: str,
    evidence_values: Mapping[str, str],
    verified_flags: Mapping[str, bool],
) -> Mapping[str, object]:
    return {
        "host_shell_pilot_preflight": _base_command("host-shell-pilot-preflight", runtime),
        "host_private_adapter_conformance": _command_with_private_adapter(
            "host-private-adapter-conformance",
            runtime,
            command_path,
        ),
        "host_shell_pilot_report": _pilot_command(
            "host-shell-pilot-report",
            runtime,
            command_path,
            distribution_source,
            distribution_channel,
            package_version,
            host_api_level,
            evidence_values,
            verified_flags,
        ),
        "host_shell_pilot_handoff": _pilot_command(
            "host-shell-pilot-handoff",
            runtime,
            command_path,
            distribution_source,
            distribution_channel,
            package_version,
            host_api_level,
            evidence_values,
            verified_flags,
        ),
    }


def _base_command(command_name: str, runtime: str) -> list[str]:
    return [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        command_name,
        "--runtime",
        runtime,
    ]


def _command_with_private_adapter(
    command_name: str,
    runtime: str,
    command_path: str,
) -> list[str]:
    command = _base_command(command_name, runtime)
    if command_path:
        command.extend(["--private-adapter-command", command_path])
    return command


def _pilot_command(
    command_name: str,
    runtime: str,
    command_path: str,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    host_api_level: str,
    evidence_values: Mapping[str, str],
    verified_flags: Mapping[str, bool],
) -> list[str]:
    command = _command_with_private_adapter(command_name, runtime, command_path)
    command.extend([
        "--distribution-source",
        distribution_source,
        "--distribution-channel",
        distribution_channel,
        "--package-version",
        package_version,
        "--host-api-level",
        host_api_level,
    ])
    for flag_name, enabled in verified_flags.items():
        if enabled:
            command.append(f"--{flag_name.replace('_', '-')}")
    for name in (*DISTRIBUTION_AUDIT_REFS, *DRILL_AUDIT_REFS):
        value = evidence_values.get(name, "")
        if _has_value(value):
            command.extend([f"--{name.replace('_', '-')}", value.strip()])
    return command


def _evidence_requirements(values: Mapping[str, str]) -> Mapping[str, object]:
    distribution_items = [
        _evidence_item(name, values.get(name, ""), f"distribution.evidence.{name}")
        for name in DISTRIBUTION_AUDIT_REFS
    ]
    drill_items = [
        _evidence_item(name, values.get(name, ""), f"drills.evidence.{name}")
        for name in DRILL_AUDIT_REFS
    ]
    distribution_missing = [
        item["id"] for item in distribution_items if item["provided"] is not True
    ]
    drill_missing = [
        item["id"] for item in drill_items if item["provided"] is not True
    ]
    return {
        "required": True,
        "complete": not distribution_missing and not drill_missing,
        "distribution": {
            "items": distribution_items,
            "provided": [item["id"] for item in distribution_items if item["provided"] is True],
            "missing": distribution_missing,
        },
        "drills": {
            "items": drill_items,
            "provided": [item["id"] for item in drill_items if item["provided"] is True],
            "missing": drill_missing,
        },
    }


def _evidence_item(name: str, value: str, receipt_path: str) -> Mapping[str, object]:
    return {
        "id": name,
        "owner": "host_shell",
        "required": True,
        "provided": _has_value(value),
        "cli_flag": f"--{name.replace('_', '-')}",
        "receipt_path": receipt_path,
    }


def _evidence_complete(values: Mapping[str, str]) -> bool:
    return all(
        _has_value(values.get(name, ""))
        for name in (*DISTRIBUTION_AUDIT_REFS, *DRILL_AUDIT_REFS)
    )


def _has_value(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())
