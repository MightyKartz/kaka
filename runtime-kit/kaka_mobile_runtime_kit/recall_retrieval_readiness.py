from __future__ import annotations

from typing import Mapping


RECALL_RETRIEVAL_READINESS_SCHEMA_VERSION = "kaka.recall_retrieval_readiness.v1"
RECALL_RETRIEVAL_STRATEGIES = (
    "host_native_embeddings",
    "sidecar_adapter",
    "capability_negotiated_hybrid",
)
REQUIRED_MATERIAL_FIELDS = (
    "adapter_package_ref",
    "runtime_settings_ui_ref",
    "signature_ref",
    "conformance_report_ref",
    "privacy_review_ref",
    "fallback_drill_ref",
    "release_notes_ref",
)


def build_recall_retrieval_readiness(
    *,
    runtime: str = "hermes",
    strategy: str = "sidecar_adapter",
    adapter_package_ref: str = "",
    runtime_settings_ui_ref: str = "",
    signature_ref: str = "",
    conformance_report_ref: str = "",
    privacy_review_ref: str = "",
    fallback_drill_ref: str = "",
    release_notes_ref: str = "",
) -> dict[str, object]:
    normalized_runtime = runtime.strip()
    if normalized_runtime not in {"hermes", "openclaw"}:
        raise ValueError(f"Unsupported Recall retrieval runtime: {runtime}")
    normalized_strategy = strategy.strip()
    if normalized_strategy not in RECALL_RETRIEVAL_STRATEGIES:
        raise ValueError(f"Unsupported Recall retrieval packaging strategy: {strategy}")

    materials: dict[str, str] = {
        "adapter_package_ref": adapter_package_ref.strip(),
        "runtime_settings_ui_ref": runtime_settings_ui_ref.strip(),
        "signature_ref": signature_ref.strip(),
        "conformance_report_ref": conformance_report_ref.strip(),
        "privacy_review_ref": privacy_review_ref.strip(),
        "fallback_drill_ref": fallback_drill_ref.strip(),
        "release_notes_ref": release_notes_ref.strip(),
    }
    missing_materials = [
        field
        for field in REQUIRED_MATERIAL_FIELDS
        if not materials[field]
    ]
    ready = not missing_materials
    status = "ready_for_production_recall_retrieval_packaging" if ready else "blocked"
    return {
        "schema_version": RECALL_RETRIEVAL_READINESS_SCHEMA_VERSION,
        "surface": "recall_retrieval_packaging_readiness",
        "runtime": normalized_runtime,
        "strategy": normalized_strategy,
        "status": status,
        "ready_for_production_recall_retrieval_packaging": ready,
        "required_materials": materials,
        "missing_materials": missing_materials,
        "release_gates": _release_gates(),
        "phone_api": {
            "base_path": "/mobile/v1/recall/search",
            "phone_api_unchanged": True,
            "search_response_allowlist": ["item", "score", "match_reason"],
        },
        "safety": _safety(),
        "notes": [
            "This report is read-only and does not choose or implement a proprietary embeddings provider.",
            "Runtime-owned retrieval packaging must keep provider configuration off the iPhone.",
        ],
    }


def _release_gates() -> Mapping[str, bool]:
    return {
        "requires_adapter_package_ref": True,
        "requires_runtime_settings_ui_ref": True,
        "requires_signature_ref": True,
        "requires_conformance_report": True,
        "requires_privacy_review": True,
        "requires_fallback_drill": True,
        "requires_release_notes": True,
    }


def _safety() -> Mapping[str, bool]:
    return {
        "runtime_side_only": True,
        "runtime_owned_provider": True,
        "phone_can_configure_provider": False,
        "provider_endpoint_visible_to_phone": False,
        "provider_keys_visible_to_phone": False,
        "returns_raw_embeddings_to_phone": False,
        "returns_retrieval_index_rows_to_phone": False,
        "returns_raw_provider_responses_to_phone": False,
        "included_in_recall_export": False,
        "invokes_provider": False,
        "fetches_refs": False,
    }
