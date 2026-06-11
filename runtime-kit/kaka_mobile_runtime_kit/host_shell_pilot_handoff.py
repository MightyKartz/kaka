from __future__ import annotations

from typing import Mapping

from .cli import BridgeConfig
from .host_shell_pilot import build_host_shell_pilot_receipt


SCHEMA_VERSION = "kaka.host_shell_pilot_handoff.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_handoff"
P3_4_COMPLETION_OWNER = "external_host_shell"

DISTRIBUTION_AUDIT_REFS = (
    "native_channel_ref",
    "signature_subject",
    "notarization_team_id",
    "update_feed_ref",
)
DRILL_AUDIT_REFS = (
    "install_receipt_ref",
    "update_receipt_ref",
    "failure_recovery_receipt_ref",
    "release_notes_ref",
)


def build_host_shell_pilot_handoff(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    host_api_level: str,
    private_adapter_timeout_seconds: float = 10,
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
    conformance_report: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    receipt = build_host_shell_pilot_receipt(
        config,
        private_adapter_command=private_adapter_command,
        distribution_source=distribution_source,
        distribution_channel=distribution_channel,
        package_version=package_version,
        host_api_level=host_api_level,
        private_adapter_timeout_seconds=private_adapter_timeout_seconds,
        native_channel_verified=native_channel_verified,
        signature_verified=signature_verified,
        update_feed_verified=update_feed_verified,
        install_verified=install_verified,
        update_verified=update_verified,
        failure_recovery_verified=failure_recovery_verified,
        release_notes_verified=release_notes_verified,
        native_channel_ref=native_channel_ref,
        signature_subject=signature_subject,
        notarization_team_id=notarization_team_id,
        update_feed_ref=update_feed_ref,
        install_receipt_ref=install_receipt_ref,
        update_receipt_ref=update_receipt_ref,
        failure_recovery_receipt_ref=failure_recovery_receipt_ref,
        release_notes_ref=release_notes_ref,
        conformance_report=conformance_report,
    )
    audit_refs = _audit_ref_summary(receipt)
    receipt_blocking_reasons = list(
        receipt.get("release_readiness", {}).get("blocking_reasons", [])
    )
    audit_blocking_reasons = [
        f"missing_audit_ref:{name}"
        for name in (
            list(audit_refs["distribution"]["missing"])
            + list(audit_refs["drills"]["missing"])
        )
    ]
    blocking_reasons = receipt_blocking_reasons + audit_blocking_reasons
    ready_to_submit = receipt.get("status") == "ready" and audit_refs["complete"] is True
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": config.runtime,
        "ok": ready_to_submit,
        "handoff_status": "ready_to_submit" if ready_to_submit else "incomplete",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": P3_4_COMPLETION_OWNER,
        "pilot_receipt": receipt,
        "audit_refs": audit_refs,
        "deliverables": _deliverables(receipt, audit_refs),
        "release_handoff": {
            "can_submit_to_external_pilot": ready_to_submit,
            "can_mark_p3_4_complete": False,
            "blocking_reasons": blocking_reasons,
        },
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
            "does_not_fetch_audit_refs": True,
            "does_not_change_receipt_gate": True,
        },
    }


def _audit_ref_summary(receipt: Mapping[str, object]) -> Mapping[str, object]:
    distribution = receipt.get("distribution", {})
    drills = receipt.get("drills", {})
    distribution_evidence = _object_field(distribution, "evidence")
    drill_evidence = _object_field(drills, "evidence")
    distribution_provided = [
        name for name in DISTRIBUTION_AUDIT_REFS if _has_string(distribution_evidence, name)
    ]
    drill_provided = [
        name for name in DRILL_AUDIT_REFS if _has_string(drill_evidence, name)
    ]
    distribution_missing = [
        name for name in DISTRIBUTION_AUDIT_REFS if name not in distribution_provided
    ]
    drill_missing = [
        name for name in DRILL_AUDIT_REFS if name not in drill_provided
    ]
    return {
        "required": True,
        "complete": not distribution_missing and not drill_missing,
        "distribution": {
            "provided": distribution_provided,
            "missing": distribution_missing,
        },
        "drills": {
            "provided": drill_provided,
            "missing": drill_missing,
        },
    }


def _deliverables(
    receipt: Mapping[str, object],
    audit_refs: Mapping[str, object],
) -> list[Mapping[str, object]]:
    command = _object_field(receipt, "private_adapter_command")
    conformance = _object_field(receipt, "conformance")
    distribution = _object_field(receipt, "distribution")
    drills = _object_field(receipt, "drills")
    return [
        {
            "id": "private_adapter_command",
            "owner": "host_shell",
            "required": True,
            "status": "provided" if command.get("provided") is True else "missing",
            "source": str(command.get("source", "missing")),
            "evidence_ref": str(command.get("path", "")),
            "blocking_reason": "" if command.get("provided") is True else "missing_private_adapter_command",
        },
        {
            "id": "conformance_report",
            "owner": "runtime_kit",
            "required": True,
            "status": "provided" if conformance.get("ok") is True else "missing",
            "source": "host-private-adapter-conformance",
            "evidence_ref": "embedded_pilot_receipt.conformance",
            "blocking_reason": "" if conformance.get("ok") is True else "conformance_not_passed",
        },
        {
            "id": "distribution_audit_refs",
            "owner": str(receipt.get("distribution_owner", "")),
            "required": True,
            "status": "provided" if not audit_refs["distribution"]["missing"] else "missing",
            "source": str(distribution.get("source", "")),
            "evidence_ref": "embedded_pilot_receipt.distribution.evidence",
            "blocking_reason": ""
            if not audit_refs["distribution"]["missing"]
            else "missing_distribution_audit_refs",
        },
        {
            "id": "drill_audit_refs",
            "owner": str(receipt.get("distribution_owner", "")),
            "required": True,
            "status": "provided" if not audit_refs["drills"]["missing"] else "missing",
            "source": "host-shell-pilot-report",
            "evidence_ref": "embedded_pilot_receipt.drills.evidence",
            "blocking_reason": ""
            if not audit_refs["drills"]["missing"]
            else "missing_drill_audit_refs",
        },
        {
            "id": "release_notes_ref",
            "owner": str(receipt.get("distribution_owner", "")),
            "required": True,
            "status": "provided"
            if "release_notes_ref" not in audit_refs["drills"]["missing"]
            else "missing",
            "source": "host-shell-pilot-report",
            "evidence_ref": "embedded_pilot_receipt.drills.evidence.release_notes_ref",
            "blocking_reason": ""
            if "release_notes_ref" not in audit_refs["drills"]["missing"]
            else "missing_audit_ref:release_notes_ref",
        },
    ]


def _object_field(value: object, field: str) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        child = value.get(field, {})
        if isinstance(child, Mapping):
            return child
    return {}


def _has_string(values: Mapping[str, object], key: str) -> bool:
    value = values.get(key)
    return isinstance(value, str) and bool(value.strip())
