from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .recall_retrieval_readiness import (
    RECALL_RETRIEVAL_STRATEGIES,
    REQUIRED_MATERIAL_FIELDS,
    build_recall_retrieval_readiness,
)


RECALL_RETRIEVAL_MATERIALS_SCHEMA_VERSION = "kaka.recall_retrieval_materials.v1"
RECALL_RETRIEVAL_MATERIAL_INTAKE_SCHEMA_VERSION = "kaka.recall_retrieval_material_intake.v1"
RECALL_RETRIEVAL_MATERIAL_INTAKE_ACCEPTED_STATUS = "accepted_for_external_retrieval_packaging_review"
RECALL_RETRIEVAL_MATERIAL_INTAKE_BLOCKED_STATUS = "blocked"
RECALL_RETRIEVAL_MATERIAL_SAFETY_KEYS = (
    "runtime_side_only",
    "provider_endpoint_included",
    "provider_keys_included",
    "raw_embeddings_included",
    "retrieval_index_rows_included",
    "raw_provider_responses_included",
    "invokes_provider",
    "fetches_refs",
)
FORBIDDEN_RECALL_RETRIEVAL_MATERIAL_KEY_MARKERS = (
    "api_key",
    "apikey",
    "bearer",
    "credential",
    "hidden_prompt",
    "password",
    "provider_endpoint",
    "raw_embeddings",
    "raw_provider_response",
    "raw_provider_responses",
    "retrieval_index_row",
    "retrieval_index_rows",
    "runtime_store_path",
    "secret",
    "sqlite_path",
    "token",
)
FORBIDDEN_RECALL_RETRIEVAL_MATERIAL_VALUE_MARKERS = (
    "/users/",
    "/v1/embeddings",
    ".sqlite",
    ".db",
    "://api.",
    "api.openai.com",
    "anthropic.com",
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "cohere.ai",
    "dev-mobile-token",
    "generativelanguage.googleapis.com",
    "hidden_prompt",
    "mistral.ai",
    "password",
    "provider_endpoint",
    "raw_embeddings",
    "raw_provider_response",
    "raw_provider_responses",
    "retrieval_index_row",
    "retrieval_index_rows",
    "runtime_store_path",
    "secret",
    "sk-",
    "sqlite",
    "token",
    "token=",
    "x-api-key",
)


def build_recall_retrieval_material_intake_from_path(
    *,
    runtime: str = "hermes",
    materials_path: str | Path,
) -> dict[str, object]:
    path = Path(materials_path)
    if not path.exists():
        return build_recall_retrieval_material_intake(
            runtime=runtime,
            manifest=None,
            material_findings=["materials_manifest_missing"],
            manifest_source="missing",
        )
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_recall_retrieval_material_intake(
            runtime=runtime,
            manifest=None,
            material_findings=["materials_manifest_unreadable"],
            manifest_source="unreadable",
        )
    return build_recall_retrieval_material_intake(runtime=runtime, manifest=loaded)


def build_recall_retrieval_material_intake(
    *,
    runtime: str = "hermes",
    manifest: Mapping[str, Any] | None,
    material_findings: list[str] | None = None,
    manifest_source: str | None = None,
) -> dict[str, object]:
    findings = list(material_findings or [])
    loaded = isinstance(manifest, Mapping)
    manifest_obj: Mapping[str, Any] = manifest if isinstance(manifest, Mapping) else {}
    manifest_schema_valid = _manifest_schema_valid(manifest_obj) if loaded else False
    if loaded and not manifest_schema_valid:
        findings.append("materials_manifest_schema_invalid")

    normalized_runtime = _safe_choice(
        str(manifest_obj.get("runtime", runtime)).strip() if loaded else runtime,
        {"hermes", "openclaw"},
        "hermes",
    )
    if normalized_runtime != runtime.strip() and runtime.strip() in {"hermes", "openclaw"}:
        findings.append("runtime_argument_manifest_mismatch")
        normalized_runtime = runtime.strip()

    normalized_strategy = _safe_choice(
        str(manifest_obj.get("strategy", "sidecar_adapter")).strip() if loaded else "sidecar_adapter",
        set(RECALL_RETRIEVAL_STRATEGIES),
        "sidecar_adapter",
    )
    forbidden_findings = _forbidden_findings(manifest_obj) if loaded else []
    materials = _safe_materials(manifest_obj.get("materials") if loaded else {}, forbidden_findings)
    readiness = build_recall_retrieval_readiness(
        runtime=normalized_runtime,
        strategy=normalized_strategy,
        adapter_package_ref=materials["adapter_package_ref"],
        runtime_settings_ui_ref=materials["runtime_settings_ui_ref"],
        signature_ref=materials["signature_ref"],
        conformance_report_ref=materials["conformance_report_ref"],
        privacy_review_ref=materials["privacy_review_ref"],
        fallback_drill_ref=materials["fallback_drill_ref"],
        release_notes_ref=materials["release_notes_ref"],
    )
    accepted = (
        loaded
        and manifest_schema_valid
        and not findings
        and not forbidden_findings
        and bool(readiness["ready_for_production_recall_retrieval_packaging"])
    )
    status = (
        RECALL_RETRIEVAL_MATERIAL_INTAKE_ACCEPTED_STATUS
        if accepted
        else RECALL_RETRIEVAL_MATERIAL_INTAKE_BLOCKED_STATUS
    )
    return {
        "schema_version": RECALL_RETRIEVAL_MATERIAL_INTAKE_SCHEMA_VERSION,
        "surface": "recall_retrieval_material_intake",
        "runtime": normalized_runtime,
        "strategy": normalized_strategy,
        "status": status,
        "accepted_for_external_retrieval_packaging_review": accepted,
        "materials_manifest": {
            "source": manifest_source or ("file" if loaded else "missing"),
            "loaded": loaded,
            "schema_valid": manifest_schema_valid,
            "schema_version": str(manifest_obj.get("schema_version", "")) if loaded else "",
            "surface": str(manifest_obj.get("surface", "")) if loaded else "",
        },
        "readiness": readiness,
        "missing_materials": readiness["missing_materials"],
        "material_findings": findings,
        "forbidden_findings": forbidden_findings,
        "release_gates": _release_gates(),
        "phone_api": readiness["phone_api"],
        "safety": _safety(),
        "notes": [
            "This report ingests a local materials manifest only; it does not fetch or validate external refs.",
            "Accepted intake means the manifest is ready for external retrieval packaging review, not that production retrieval is implemented.",
        ],
    }


def _safe_choice(value: str, choices: set[str], fallback: str) -> str:
    return value if value in choices else fallback


def _manifest_schema_valid(manifest: Mapping[str, Any]) -> bool:
    if manifest.get("schema_version") != RECALL_RETRIEVAL_MATERIALS_SCHEMA_VERSION:
        return False
    if manifest.get("surface") != "recall_retrieval_materials":
        return False
    if manifest.get("runtime") not in {"hermes", "openclaw"}:
        return False
    if manifest.get("strategy") not in RECALL_RETRIEVAL_STRATEGIES:
        return False
    if not isinstance(manifest.get("materials"), Mapping):
        return False
    if not isinstance(manifest.get("phone_api"), Mapping):
        return False
    if not isinstance(manifest.get("safety"), Mapping):
        return False
    if set(manifest.keys()) != {
        "schema_version",
        "surface",
        "runtime",
        "strategy",
        "materials",
        "phone_api",
        "safety",
    }:
        return False
    materials = manifest["materials"]
    if set(materials.keys()) != set(REQUIRED_MATERIAL_FIELDS):
        return False
    if any(not isinstance(materials.get(field), str) for field in REQUIRED_MATERIAL_FIELDS):
        return False
    phone_api = manifest["phone_api"]
    if set(phone_api.keys()) != {"base_path", "phone_api_unchanged"}:
        return False
    if phone_api.get("base_path") != "/mobile/v1/recall/search":
        return False
    if phone_api.get("phone_api_unchanged") is not True:
        return False
    safety = manifest["safety"]
    if set(safety.keys()) != set(RECALL_RETRIEVAL_MATERIAL_SAFETY_KEYS):
        return False
    return (
        safety.get("runtime_side_only") is True
        and safety.get("provider_endpoint_included") is False
        and safety.get("provider_keys_included") is False
        and safety.get("raw_embeddings_included") is False
        and safety.get("retrieval_index_rows_included") is False
        and safety.get("raw_provider_responses_included") is False
        and safety.get("invokes_provider") is False
        and safety.get("fetches_refs") is False
    )


def _safe_materials(
    raw_materials: object,
    forbidden_findings: list[dict[str, str]],
) -> dict[str, str]:
    materials: dict[str, str] = {field: "" for field in REQUIRED_MATERIAL_FIELDS}
    if not isinstance(raw_materials, Mapping):
        return materials
    unsafe_fields = {finding["field"] for finding in forbidden_findings}
    for field in REQUIRED_MATERIAL_FIELDS:
        value = raw_materials.get(field, "")
        if not isinstance(value, str):
            continue
        if field in unsafe_fields or f"materials.{field}" in unsafe_fields:
            continue
        stripped = value.strip()
        if _unsafe_value(stripped):
            continue
        materials[field] = stripped
    return materials


def _forbidden_findings(manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    _collect_forbidden_findings(manifest, "", findings)
    safety = manifest.get("safety")
    if isinstance(safety, Mapping):
        for key in (
            "provider_endpoint_included",
            "provider_keys_included",
            "raw_embeddings_included",
            "retrieval_index_rows_included",
            "raw_provider_responses_included",
            "invokes_provider",
            "fetches_refs",
        ):
            if safety.get(key) is not False:
                findings.append({"field": f"safety.{key}", "reason": "unsafe_safety_declaration"})
        if safety.get("runtime_side_only") is not True:
            findings.append({"field": "safety.runtime_side_only", "reason": "unsafe_safety_declaration"})
    return _dedupe_findings(findings)


def _collect_forbidden_findings(
    value: object,
    path: str,
    findings: list[dict[str, str]],
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            field = str(key)
            child_path = f"{path}.{field}" if path else field
            if path != "safety" and _unsafe_key(field):
                findings.append({"field": child_path, "reason": "forbidden_key"})
                continue
            _collect_forbidden_findings(child, child_path, findings)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _collect_forbidden_findings(child, f"{path}[{index}]", findings)
    elif isinstance(value, str) and _unsafe_value_for_path(path, value):
        findings.append({"field": path, "reason": "forbidden_value"})


def _unsafe_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in FORBIDDEN_RECALL_RETRIEVAL_MATERIAL_KEY_MARKERS)


def _unsafe_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in FORBIDDEN_RECALL_RETRIEVAL_MATERIAL_VALUE_MARKERS)


def _unsafe_value_for_path(path: str, value: str) -> bool:
    lowered = value.lower().strip()
    if path.startswith("materials.") and lowered.startswith(("/", "~")):
        return True
    return _unsafe_value(value)


def _dedupe_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for finding in findings:
        key = (finding["field"], finding["reason"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _release_gates() -> Mapping[str, bool]:
    return {
        "requires_p3_21_readiness_ready": True,
        "requires_material_manifest_schema_valid": True,
        "requires_no_forbidden_material_fields": True,
        "requires_external_signature_review": True,
        "requires_external_privacy_review": True,
        "requires_external_fallback_drill": True,
        "requires_external_release_notes": True,
    }


def _safety() -> Mapping[str, bool]:
    return {
        "runtime_side_only": True,
        "manifest_only": True,
        "phone_api_unchanged": True,
        "provider_endpoint_visible_to_phone": False,
        "provider_keys_visible_to_phone": False,
        "returns_raw_embeddings_to_phone": False,
        "returns_retrieval_index_rows_to_phone": False,
        "returns_raw_provider_responses_to_phone": False,
        "included_in_recall_export": False,
        "invokes_provider": False,
        "fetches_refs": False,
        "does_not_validate_signatures": True,
    }
