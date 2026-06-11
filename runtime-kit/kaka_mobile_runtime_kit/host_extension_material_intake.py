from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .host_extension_readiness import REQUIRED_INPUTS, build_host_extension_readiness


HOST_EXTENSION_MATERIALS_SCHEMA_VERSION = "kaka.host_extension_materials.v1"
HOST_EXTENSION_MATERIAL_INTAKE_SCHEMA_VERSION = "kaka.host_extension_material_intake.v1"
HOST_EXTENSION_MATERIAL_INTAKE_SURFACE = "hermes_openclaw_host_extension_material_intake"
HOST_EXTENSION_MATERIAL_INTAKE_ACCEPTED_STATUS = "accepted_for_external_install_drill_review"
HOST_EXTENSION_MATERIAL_INTAKE_BLOCKED_STATUS = "blocked"
INSTALL_DRILL_REF_FIELDS = (
    "install_receipt_ref",
    "enable_receipt_ref",
    "pairing_receipt_ref",
    "health_receipt_ref",
    "revoke_repair_receipt_ref",
    "update_receipt_ref",
    "failure_recovery_receipt_ref",
    "uninstall_receipt_ref",
)
FORBIDDEN_KEY_MARKERS = (
    "api_key",
    "apikey",
    "bearer",
    "credential",
    "password",
    "private_key",
    "raw_asset",
    "raw_log",
    "secret",
    "sqlite",
    "token",
)
FORBIDDEN_VALUE_MARKERS = (
    "/users/",
    ".db",
    ".key",
    ".pem",
    ".sqlite",
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "credential",
    "dev-mobile-token",
    "mobile-runtime.sqlite",
    "password",
    "private key",
    "secret",
    "sk-",
    "sqlite",
    "token",
    "token=",
    "x-api-key",
)


def build_host_extension_material_intake_from_path(
    materials_path: str | Path,
    *,
    runtime: str | None = None,
) -> dict[str, object]:
    path = Path(materials_path)
    if not path.exists():
        return build_host_extension_material_intake(
            None,
            runtime=runtime,
            source="missing",
            findings=["materials_manifest_missing"],
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_host_extension_material_intake(
            None,
            runtime=runtime,
            source="unreadable",
            findings=["materials_manifest_unreadable"],
        )
    return build_host_extension_material_intake(manifest, runtime=runtime, source="file")


def build_host_extension_material_intake(
    manifest: Mapping[str, Any] | None,
    *,
    runtime: str | None = None,
    source: str = "direct",
    findings: list[str] | None = None,
) -> dict[str, object]:
    loaded = isinstance(manifest, Mapping)
    manifest_obj: Mapping[str, Any] = manifest if isinstance(manifest, Mapping) else {}
    report_findings = list(findings or [])
    manifest_schema_valid = _manifest_schema_valid(manifest_obj) if loaded else False
    if loaded and not manifest_schema_valid:
        report_findings.append("materials_manifest_schema_invalid")

    manifest_runtime = _safe_runtime(str(manifest_obj.get("runtime", "")).strip())
    normalized_runtime = _safe_runtime(runtime or manifest_runtime or "hermes")
    if manifest_runtime and runtime and manifest_runtime != normalized_runtime:
        report_findings.append("runtime_argument_manifest_mismatch")

    redacted_fields = _redacted_fields(manifest_obj) if loaded else []
    package_facts = _safe_string_fields(
        manifest_obj.get("package_facts") if loaded else {},
        REQUIRED_INPUTS,
        "package_facts",
        redacted_fields,
    )
    install_drill_refs = _safe_string_fields(
        manifest_obj.get("install_drill_refs") if loaded else {},
        INSTALL_DRILL_REF_FIELDS,
        "install_drill_refs",
        redacted_fields,
    )
    readiness = build_host_extension_readiness(
        runtime=normalized_runtime,
        install_command=package_facts["install_command"],
        update_channel=package_facts["update_channel"],
        adapter_command_location=package_facts["adapter_command_location"],
        host_ui_entrypoint=package_facts["host_ui_entrypoint"],
        signed_package_ref=package_facts["signed_package_ref"],
        signature_ref=package_facts["signature_ref"],
        conformance_report_ref=package_facts["conformance_report_ref"],
        evidence_manifest_ref=package_facts["evidence_manifest_ref"],
    )
    missing_package_facts = [
        field
        for field in REQUIRED_INPUTS
        if not str(package_facts.get(field, "")).strip()
    ]
    missing_install_drill_refs = [
        field
        for field in INSTALL_DRILL_REF_FIELDS
        if not str(install_drill_refs.get(field, "")).strip()
    ]
    accepted = (
        loaded
        and manifest_schema_valid
        and not report_findings
        and not redacted_fields
        and not missing_package_facts
        and not missing_install_drill_refs
        and bool(readiness["ready_for_external_install_drill"])
    )
    return {
        "schema_version": HOST_EXTENSION_MATERIAL_INTAKE_SCHEMA_VERSION,
        "surface": HOST_EXTENSION_MATERIAL_INTAKE_SURFACE,
        "runtime": normalized_runtime,
        "status": (
            HOST_EXTENSION_MATERIAL_INTAKE_ACCEPTED_STATUS
            if accepted
            else HOST_EXTENSION_MATERIAL_INTAKE_BLOCKED_STATUS
        ),
        "ordinary_user_install_surface": "host_native_extension",
        "source": {
            "source": source,
            "loaded": loaded,
            "schema_valid": manifest_schema_valid,
            "manifest_schema_version": str(manifest_obj.get("schema_version", "")) if loaded else "",
            "local_manifest_only": True,
        },
        "readiness": readiness,
        "package_facts": package_facts,
        "install_drill_refs": install_drill_refs,
        "missing_package_facts": missing_package_facts,
        "missing_install_drill_refs": missing_install_drill_refs,
        "redacted_fields": redacted_fields,
        "findings": _dedupe_strings(report_findings),
        "next_step": (
            "run_external_p3_7_install_drill"
            if accepted
            else "collect_host_owned_package_facts"
        ),
        "phone_api": {
            "base_path": "/mobile/v1",
            "private_host_api_exposed": False,
            "phone_api_unchanged": True,
        },
        "safety": _safety(),
        "notes": [
            "This report reviews a local host-owned materials manifest only; it does not fetch refs or mutate host state.",
            "Accepted intake means the materials are ready for external install-drill review, not that P3.7 has been executed.",
        ],
    }


def _safe_runtime(value: str) -> str:
    return value if value in {"hermes", "openclaw"} else "hermes"


def _manifest_schema_valid(manifest: Mapping[str, Any]) -> bool:
    if set(manifest.keys()) != {
        "schema_version",
        "runtime",
        "package_facts",
        "install_drill_refs",
    }:
        return False
    if manifest.get("schema_version") != HOST_EXTENSION_MATERIALS_SCHEMA_VERSION:
        return False
    if manifest.get("runtime") not in {"hermes", "openclaw"}:
        return False
    if not isinstance(manifest.get("package_facts"), Mapping):
        return False
    if not isinstance(manifest.get("install_drill_refs"), Mapping):
        return False
    package_facts = manifest["package_facts"]
    install_drill_refs = manifest["install_drill_refs"]
    if set(package_facts.keys()) != set(REQUIRED_INPUTS):
        return False
    if set(install_drill_refs.keys()) != set(INSTALL_DRILL_REF_FIELDS):
        return False
    if any(not isinstance(package_facts.get(field), str) for field in REQUIRED_INPUTS):
        return False
    return all(
        isinstance(install_drill_refs.get(field), str)
        for field in INSTALL_DRILL_REF_FIELDS
    )


def _safe_string_fields(
    raw_values: object,
    field_names: tuple[str, ...],
    prefix: str,
    redacted_fields: list[str],
) -> dict[str, str]:
    values = {field: "" for field in field_names}
    if not isinstance(raw_values, Mapping):
        return values
    redacted = set(redacted_fields)
    for field in field_names:
        path = f"{prefix}.{field}"
        value = raw_values.get(field, "")
        if path in redacted or not isinstance(value, str):
            continue
        stripped = value.strip()
        if _unsafe_value_for_path(path, stripped):
            continue
        values[field] = stripped
    return values


def _redacted_fields(manifest: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    _collect_redacted_fields(manifest, "", findings)
    return _dedupe_strings(findings)


def _collect_redacted_fields(value: object, path: str, findings: list[str]) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = f"{path}.{key}" if path else key
            if _unsafe_key(key):
                findings.append(child_path)
                continue
            _collect_redacted_fields(child, child_path, findings)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _collect_redacted_fields(child, f"{path}[{index}]", findings)
    elif isinstance(value, str) and _unsafe_value_for_path(path, value):
        findings.append(path)


def _unsafe_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in FORBIDDEN_KEY_MARKERS)


def _unsafe_value_for_path(path: str, value: str) -> bool:
    lowered = value.lower().strip()
    if lowered.startswith(("/", "~")):
        return True
    if path.startswith("package_facts.") and ".key" in lowered:
        return True
    return any(marker in lowered for marker in FORBIDDEN_VALUE_MARKERS)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _safety() -> Mapping[str, bool]:
    return {
        "does_not_install_package": True,
        "does_not_sign_or_publish": True,
        "does_not_fetch_refs": True,
        "does_not_start_bridge": True,
        "does_not_bind_lan": True,
        "does_not_advertise_bonjour": True,
        "does_not_mint_mobile_tokens": True,
        "does_not_invoke_private_adapter": True,
        "does_not_write_codex_user_home": True,
        "does_not_change_mobile_bridge_api": True,
    }
