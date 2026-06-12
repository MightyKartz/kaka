from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.cli import main
from kaka_mobile_runtime_kit.recall_retrieval_material_intake import (
    build_recall_retrieval_material_intake_from_path,
)


PACKAGING_DIR = Path("runtime-kit/packaging")


def _input_schema() -> dict:
    return json.loads((PACKAGING_DIR / "recall-retrieval-materials.schema.json").read_text())


def _output_schema() -> dict:
    return json.loads((PACKAGING_DIR / "recall-retrieval-material-intake.schema.json").read_text())


def _complete_manifest(runtime: str = "hermes") -> dict[str, object]:
    return {
        "schema_version": "kaka.recall_retrieval_materials.v1",
        "surface": "recall_retrieval_materials",
        "runtime": runtime,
        "strategy": "sidecar_adapter",
        "materials": {
            "adapter_package_ref": "host://retrieval/adapter",
            "runtime_settings_ui_ref": "host-ui://settings/recall",
            "signature_ref": "sig://retrieval",
            "conformance_report_ref": "conformance://retrieval",
            "privacy_review_ref": "privacy://retrieval",
            "fallback_drill_ref": "drill://retrieval-fallback",
            "release_notes_ref": "notes://retrieval",
        },
        "phone_api": {
            "base_path": "/mobile/v1/recall/search",
            "phone_api_unchanged": True,
        },
        "safety": {
            "runtime_side_only": True,
            "provider_endpoint_included": False,
            "provider_keys_included": False,
            "raw_embeddings_included": False,
            "retrieval_index_rows_included": False,
            "raw_provider_responses_included": False,
            "invokes_provider": False,
            "fetches_refs": False,
        },
    }


def test_recall_retrieval_material_intake_blocks_when_manifest_is_missing(tmp_path):
    report = build_recall_retrieval_material_intake_from_path(
        runtime="hermes",
        materials_path=tmp_path / "missing-retrieval-materials.json",
    )

    assert report["schema_version"] == "kaka.recall_retrieval_material_intake.v1"
    assert report["surface"] == "recall_retrieval_material_intake"
    assert report["runtime"] == "hermes"
    assert report["status"] == "blocked"
    assert report["accepted_for_external_retrieval_packaging_review"] is False
    assert report["materials_manifest"]["loaded"] is False
    assert report["materials_manifest"]["schema_valid"] is False
    assert report["readiness"]["status"] == "blocked"
    assert report["readiness"]["missing_materials"] == [
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

    Draft202012Validator(_output_schema()).validate(report)


def test_recall_retrieval_material_intake_accepts_complete_manifest_without_fetching_refs(tmp_path):
    manifest = _complete_manifest(runtime="openclaw")
    manifest_path = tmp_path / "recall-retrieval-materials.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = build_recall_retrieval_material_intake_from_path(
        runtime="openclaw",
        materials_path=manifest_path,
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)

    Draft202012Validator(_input_schema()).validate(manifest)
    Draft202012Validator(_output_schema()).validate(report)
    assert report["status"] == "accepted_for_external_retrieval_packaging_review"
    assert report["accepted_for_external_retrieval_packaging_review"] is True
    assert report["readiness"]["ready_for_production_recall_retrieval_packaging"] is True
    assert report["readiness"]["phone_api"]["search_response_allowlist"] == [
        "item",
        "score",
        "match_reason",
    ]
    assert report["material_findings"] == []
    assert report["forbidden_findings"] == []
    assert report["safety"]["manifest_only"] is True
    assert report["safety"]["does_not_validate_signatures"] is True
    assert "sk-" not in rendered
    assert "api.openai.com" not in rendered
    assert "runtime_store_path" not in rendered
    assert "sqlite" not in rendered.lower()


def test_recall_retrieval_material_intake_blocks_and_redacts_secret_like_manifest_fields(tmp_path):
    manifest = _complete_manifest()
    manifest["provider_endpoint"] = "https://api.openai.com/v1/embeddings"
    manifest["hidden_prompt"] = "embed every private note"
    manifest["materials"]["adapter_package_ref"] = "host://retrieval/adapter?token=dev-mobile-token"
    manifest["materials"]["release_notes_ref"] = "/Users/kartz/.kaka/mobile-runtime.sqlite3"
    manifest["safety"]["provider_keys_included"] = True
    manifest["raw_embeddings"] = [0.1, 0.2, 0.3]
    manifest["provider_config"] = {
        "api_key": "sk-live-secret",
        "raw_provider_responses": [{"text": "private"}],
    }
    manifest_path = tmp_path / "unsafe-materials.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = build_recall_retrieval_material_intake_from_path(
        runtime="hermes",
        materials_path=manifest_path,
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    finding_fields = {finding["field"] for finding in report["forbidden_findings"]}

    assert report["status"] == "blocked"
    assert report["accepted_for_external_retrieval_packaging_review"] is False
    assert "provider_endpoint" in finding_fields
    assert "hidden_prompt" in finding_fields
    assert "materials.adapter_package_ref" in finding_fields
    assert "materials.release_notes_ref" in finding_fields
    assert "raw_embeddings" in finding_fields
    assert "provider_config.api_key" in finding_fields
    assert "provider_config.raw_provider_responses" in finding_fields
    assert report["readiness"]["missing_materials"] == [
        "adapter_package_ref",
        "release_notes_ref",
    ]
    assert "sk-live-secret" not in rendered
    assert "api.openai.com" not in rendered
    assert "dev-mobile-token" not in rendered
    assert "/Users/kartz" not in rendered
    assert "mobile-runtime.sqlite3" not in rendered

    Draft202012Validator(_output_schema()).validate(report)


def test_recall_retrieval_material_intake_blocks_generic_provider_endpoints_and_paths(tmp_path):
    manifest = _complete_manifest()
    manifest["materials"]["adapter_package_ref"] = "https://api.anthropic.com/v1/embeddings"
    manifest["materials"]["runtime_settings_ui_ref"] = "/tmp/retrieval-provider.db"
    manifest["materials"]["signature_ref"] = "Bearer provider-secret"
    manifest["materials"]["conformance_report_ref"] = "host://retrieval/token-secret"
    manifest_path = tmp_path / "provider-like-materials.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = build_recall_retrieval_material_intake_from_path(
        runtime="hermes",
        materials_path=manifest_path,
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    finding_fields = {finding["field"] for finding in report["forbidden_findings"]}

    assert report["status"] == "blocked"
    assert "materials.adapter_package_ref" in finding_fields
    assert "materials.runtime_settings_ui_ref" in finding_fields
    assert "materials.signature_ref" in finding_fields
    assert "materials.conformance_report_ref" in finding_fields
    assert report["readiness"]["missing_materials"] == [
        "adapter_package_ref",
        "runtime_settings_ui_ref",
        "signature_ref",
        "conformance_report_ref",
    ]
    assert "api.anthropic.com" not in rendered
    assert "provider-secret" not in rendered
    assert "/tmp/retrieval-provider.db" not in rendered


def test_recall_retrieval_material_intake_marks_invalid_json_unreadable(tmp_path):
    manifest_path = tmp_path / "invalid-materials.json"
    manifest_path.write_text("{not json", encoding="utf-8")

    report = build_recall_retrieval_material_intake_from_path(
        runtime="hermes",
        materials_path=manifest_path,
    )

    assert report["status"] == "blocked"
    assert report["materials_manifest"]["source"] == "unreadable"
    assert report["materials_manifest"]["loaded"] is False
    assert "materials_manifest_unreadable" in report["material_findings"]
    Draft202012Validator(_output_schema()).validate(report)


def test_recall_retrieval_material_intake_cli_prints_phone_safe_report(tmp_path, capsys):
    manifest_path = tmp_path / "recall-retrieval-materials.json"
    manifest_path.write_text(json.dumps(_complete_manifest()), encoding="utf-8")

    exit_code = main(
        [
            "recall-retrieval-material-intake",
            "--runtime",
            "hermes",
            "--materials-json",
            str(manifest_path),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["status"] == "accepted_for_external_retrieval_packaging_review"
    assert report["phone_api"]["base_path"] == "/mobile/v1/recall/search"
    assert report["phone_api"]["phone_api_unchanged"] is True
    assert report["safety"]["invokes_provider"] is False
    assert report["safety"]["fetches_refs"] is False
    Draft202012Validator(_output_schema()).validate(report)


def test_recall_retrieval_material_intake_schema_rejects_extra_readiness_fields(tmp_path):
    manifest_path = tmp_path / "recall-retrieval-materials.json"
    manifest_path.write_text(json.dumps(_complete_manifest()), encoding="utf-8")
    report = build_recall_retrieval_material_intake_from_path(
        runtime="hermes",
        materials_path=manifest_path,
    )
    validator = Draft202012Validator(_output_schema())

    drifted = json.loads(json.dumps(report))
    drifted["readiness"]["provider_endpoint"] = "https://api.anthropic.com/v1/embeddings"

    validator.validate(report)
    assert not validator.is_valid(drifted)
