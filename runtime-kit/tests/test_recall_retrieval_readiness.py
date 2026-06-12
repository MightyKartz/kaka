from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.cli import main
from kaka_mobile_runtime_kit.recall_retrieval_readiness import (
    build_recall_retrieval_readiness,
)


PACKAGING_DIR = Path("runtime-kit/packaging")


def _schema() -> dict:
    return json.loads((PACKAGING_DIR / "recall-retrieval-readiness.schema.json").read_text())


def _ready_kwargs() -> dict[str, str]:
    return {
        "strategy": "sidecar_adapter",
        "adapter_package_ref": "host://retrieval/adapter",
        "runtime_settings_ui_ref": "host-ui://settings/recall",
        "signature_ref": "sig://retrieval",
        "conformance_report_ref": "conformance://retrieval",
        "privacy_review_ref": "privacy://retrieval",
        "fallback_drill_ref": "drill://retrieval-fallback",
        "release_notes_ref": "notes://retrieval",
    }


def test_recall_retrieval_readiness_blocks_until_required_materials_exist() -> None:
    report = build_recall_retrieval_readiness(runtime="hermes")

    assert report["schema_version"] == "kaka.recall_retrieval_readiness.v1"
    assert report["runtime"] == "hermes"
    assert report["status"] == "blocked"
    assert report["ready_for_production_recall_retrieval_packaging"] is False
    assert report["phone_api"]["base_path"] == "/mobile/v1/recall/search"
    assert report["phone_api"]["phone_api_unchanged"] is True
    assert report["missing_materials"] == [
        "adapter_package_ref",
        "runtime_settings_ui_ref",
        "signature_ref",
        "conformance_report_ref",
        "privacy_review_ref",
        "fallback_drill_ref",
        "release_notes_ref",
    ]
    assert report["safety"]["invokes_provider"] is False
    assert report["safety"]["fetches_refs"] is False

    Draft202012Validator(_schema()).validate(report)


def test_recall_retrieval_readiness_can_be_ready_for_sidecar_packaging() -> None:
    report = build_recall_retrieval_readiness(runtime="openclaw", **_ready_kwargs())
    rendered_materials = json.dumps(report["required_materials"], ensure_ascii=False, sort_keys=True)

    assert report["status"] == "ready_for_production_recall_retrieval_packaging"
    assert report["ready_for_production_recall_retrieval_packaging"] is True
    assert report["strategy"] == "sidecar_adapter"
    assert report["missing_materials"] == []
    assert report["required_materials"]["adapter_package_ref"] == "host://retrieval/adapter"
    assert report["release_gates"]["requires_conformance_report"] is True
    assert report["release_gates"]["requires_privacy_review"] is True
    assert report["safety"] == {
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
    assert "https://api.example.com" not in rendered_materials
    assert "sk-" not in rendered_materials
    assert "embedding_recall" not in rendered_materials
    assert "runtime_store_path" not in rendered_materials
    assert "sqlite" not in rendered_materials.lower()

    Draft202012Validator(_schema()).validate(report)


def test_recall_retrieval_readiness_schema_rejects_phone_leakage_drift() -> None:
    validator = Draft202012Validator(_schema())
    report = build_recall_retrieval_readiness(runtime="hermes", **_ready_kwargs())

    changed_phone_api = json.loads(json.dumps(report))
    changed_phone_api["phone_api"]["phone_api_unchanged"] = False
    assert not validator.is_valid(changed_phone_api)

    endpoint_leak = json.loads(json.dumps(report))
    endpoint_leak["safety"]["provider_endpoint_visible_to_phone"] = True
    assert not validator.is_valid(endpoint_leak)

    raw_embedding_leak = json.loads(json.dumps(report))
    raw_embedding_leak["safety"]["returns_raw_embeddings_to_phone"] = True
    assert not validator.is_valid(raw_embedding_leak)


def test_recall_retrieval_readiness_cli_prints_phone_safe_report(capsys) -> None:
    exit_code = main(
        [
            "recall-retrieval-readiness",
            "--runtime",
            "hermes",
            "--strategy",
            "sidecar_adapter",
            "--adapter-package-ref",
            "host://retrieval/adapter",
            "--runtime-settings-ui-ref",
            "host-ui://settings/recall",
            "--signature-ref",
            "sig://retrieval",
            "--conformance-report-ref",
            "conformance://retrieval",
            "--privacy-review-ref",
            "privacy://retrieval",
            "--fallback-drill-ref",
            "drill://retrieval-fallback",
            "--release-notes-ref",
            "notes://retrieval",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    rendered_materials = json.dumps(report["required_materials"], ensure_ascii=False, sort_keys=True)
    assert exit_code == 0
    assert report["ready_for_production_recall_retrieval_packaging"] is True
    assert report["phone_api"]["base_path"] == "/mobile/v1/recall/search"
    assert "https://api.example.com" not in rendered_materials
    assert "bearer_token" not in rendered_materials
    assert "sk-" not in rendered_materials
    assert "embedding_recall" not in rendered_materials
    assert "sqlite" not in rendered_materials.lower()
