from __future__ import annotations

from typing import Mapping

from .host_extension_preview import build_host_extension_preview


SCHEMA_VERSION = "kaka.host_extension_readiness.v1"
SURFACE = "hermes_openclaw_host_extension_readiness"
REQUIRED_INPUTS = (
    "install_command",
    "update_channel",
    "adapter_command_location",
    "host_ui_entrypoint",
    "signed_package_ref",
    "signature_ref",
    "conformance_report_ref",
    "evidence_manifest_ref",
)


def _clean(value: str) -> str:
    return value.strip()


def _missing_inputs(values: Mapping[str, str]) -> list[Mapping[str, str]]:
    labels = {
        "install_command": "Ordinary-user plugin or skill install command",
        "update_channel": "Host-owned update channel name",
        "adapter_command_location": "Extension-internal adapter command location",
        "host_ui_entrypoint": "Host UI entry point for enable, QR, health, revoke, update, uninstall, and logs",
        "signed_package_ref": "Signed host extension package reference",
        "signature_ref": "Signature, notarization, or equivalent host trust reference",
        "conformance_report_ref": "P3.2 host-private-adapter-conformance report reference",
        "evidence_manifest_ref": "P3.4 host-shell-pilot-evidence-manifest reference",
    }
    return [
        {"id": key, "label": labels[key]}
        for key in REQUIRED_INPUTS
        if not _clean(values.get(key, ""))
    ]


def build_host_extension_readiness(
    *,
    runtime: str,
    install_command: str = "",
    update_channel: str = "",
    adapter_command_location: str = "",
    host_ui_entrypoint: str = "",
    signed_package_ref: str = "",
    signature_ref: str = "",
    conformance_report_ref: str = "",
    evidence_manifest_ref: str = "",
) -> Mapping[str, object]:
    preview = build_host_extension_preview(runtime=runtime)
    values = {
        "install_command": install_command,
        "update_channel": update_channel,
        "adapter_command_location": adapter_command_location,
        "host_ui_entrypoint": host_ui_entrypoint,
        "signed_package_ref": signed_package_ref,
        "signature_ref": signature_ref,
        "conformance_report_ref": conformance_report_ref,
        "evidence_manifest_ref": evidence_manifest_ref,
    }
    missing = _missing_inputs(values)
    ready = not missing
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": preview["runtime"],
        "status": "ready_for_external_install_drill" if ready else "blocked",
        "ready_for_external_install_drill": ready,
        "missing_inputs": missing,
        "ordinary_user_install": preview["ordinary_user_install"],
        "adapter_command": {
            "visibility": preview["adapter_command"]["visibility"],
            "developer_fallback_only": preview["adapter_command"]["developer_fallback_only"],
            "default_command_name": preview["adapter_command"]["default_command_name"],
            "extension_internal_location": _clean(adapter_command_location),
        },
        "distribution": {
            "install_command": _clean(install_command),
            "update_channel": _clean(update_channel),
            "signed_package_ref": _clean(signed_package_ref),
            "signature_ref": _clean(signature_ref),
            "host_ui_entrypoint": _clean(host_ui_entrypoint),
        },
        "evidence": {
            "conformance_report_ref": _clean(conformance_report_ref),
            "evidence_manifest_ref": _clean(evidence_manifest_ref),
        },
        "phone_api": preview["phone_api"],
        "gates": {
            "requires_p3_2_conformance": True,
            "requires_p3_4_evidence_manifest": True,
            "requires_external_install_drill": True,
            "can_mark_p3_4_complete": False,
        },
        "safety": {
            "runtime_side_only": True,
            "does_not_install_package": True,
            "does_not_invoke_private_adapter": True,
            "does_not_start_bridge": True,
            "does_not_bind_lan": True,
            "does_not_advertise_bonjour": True,
            "does_not_mint_credentials": True,
            "does_not_create_login_item": True,
            "does_not_fetch_audit_refs": True,
        },
    }
