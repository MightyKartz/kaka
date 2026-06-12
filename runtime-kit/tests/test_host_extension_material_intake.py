from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_extension_material_intake import (
    build_host_extension_material_intake,
    build_host_extension_material_intake_from_path,
)


PACKAGING_DIR = Path("runtime-kit/packaging")


def _input_schema() -> dict:
    return json.loads((PACKAGING_DIR / "host-extension-materials.schema.json").read_text())


def _output_schema() -> dict:
    return json.loads(
        (PACKAGING_DIR / "host-extension-material-intake.schema.json").read_text()
    )


def _readiness_schema() -> dict:
    return json.loads((PACKAGING_DIR / "host-extension-readiness.schema.json").read_text())


def _complete_manifest(runtime: str = "hermes") -> dict[str, object]:
    return {
        "schema_version": "kaka.host_extension_materials.v1",
        "runtime": runtime,
        "package_facts": {
            "install_command": f"{runtime} plugins install example/kaka-mobile --no-enable",
            "update_channel": f"{runtime.title()} stable plugin channel ref 2026-06-11",
            "adapter_command_location": (
                "extension-internal:kaka-mobile-bridge/"
                f"{runtime}-kaka-host-api"
            ),
            "host_ui_entrypoint": "Settings > Plugins > Kaka Mobile Bridge",
            "signed_package_ref": (
                f"artifact://{runtime}/kaka-mobile-bridge/1.0.0/package"
            ),
            "signature_ref": (
                f"artifact://{runtime}/kaka-mobile-bridge/1.0.0/signature"
            ),
            "conformance_report_ref": f"artifact://{runtime}/kaka/p3.2/conformance.json",
            "evidence_manifest_ref": (
                f"artifact://{runtime}/kaka/p3.4/evidence-manifest.json"
            ),
        },
        "install_drill_refs": {
            "install_receipt_ref": f"artifact://{runtime}/kaka/p3.7/install.json",
            "enable_receipt_ref": f"artifact://{runtime}/kaka/p3.7/enable.json",
            "pairing_receipt_ref": f"artifact://{runtime}/kaka/p3.7/pairing.json",
            "health_receipt_ref": f"artifact://{runtime}/kaka/p3.7/health.json",
            "revoke_repair_receipt_ref": (
                f"artifact://{runtime}/kaka/p3.7/revoke-repair.json"
            ),
            "update_receipt_ref": f"artifact://{runtime}/kaka/p3.7/update.json",
            "failure_recovery_receipt_ref": (
                f"artifact://{runtime}/kaka/p3.7/failure-recovery.json"
            ),
            "uninstall_receipt_ref": f"artifact://{runtime}/kaka/p3.7/uninstall.json",
        },
    }


def test_complete_host_extension_materials_are_accepted():
    manifest = _complete_manifest(runtime="hermes")

    report = build_host_extension_material_intake(manifest)

    Draft202012Validator(_input_schema()).validate(manifest)
    Draft202012Validator(_output_schema()).validate(report)
    Draft202012Validator(_readiness_schema()).validate(report["readiness"])
    assert report["schema_version"] == "kaka.host_extension_material_intake.v1"
    assert report["surface"] == "hermes_openclaw_host_extension_material_intake"
    assert report["runtime"] == "hermes"
    assert report["status"] == "accepted_for_external_install_drill_review"
    assert report["ordinary_user_install_surface"] == "host_native_extension"
    assert report["readiness"]["status"] == "ready_for_external_install_drill"
    assert report["readiness"]["ready_for_external_install_drill"] is True
    assert report["missing_package_facts"] == []
    assert report["missing_install_drill_refs"] == []
    assert report["redacted_fields"] == []
    assert report["next_step"] == "run_external_p3_7_install_drill"
    assert report["safety"]["does_not_install_package"] is True
    assert report["safety"]["does_not_invoke_private_adapter"] is True
    assert report["safety"]["does_not_change_mobile_bridge_api"] is True


def test_missing_package_facts_are_blocked_without_installing():
    report = build_host_extension_material_intake(
        {
            "schema_version": "kaka.host_extension_materials.v1",
            "runtime": "openclaw",
            "package_facts": {},
            "install_drill_refs": {},
        }
    )

    Draft202012Validator(_output_schema()).validate(report)
    assert report["status"] == "blocked"
    assert "install_command" in report["missing_package_facts"]
    assert "signed_package_ref" in report["missing_package_facts"]
    assert "install_receipt_ref" in report["missing_install_drill_refs"]
    assert report["readiness"]["status"] == "blocked"
    assert report["readiness"]["ready_for_external_install_drill"] is False
    assert report["safety"]["does_not_install_package"] is True
    assert report["safety"]["does_not_fetch_refs"] is True


def test_secret_like_values_are_redacted_and_blocked():
    manifest = _complete_manifest(runtime="hermes")
    manifest["package_facts"]["install_command"] = (
        "hermes plugins install example/kaka-mobile --token sk-test"
    )
    manifest["package_facts"]["update_channel"] = "Bearer abc123"
    manifest["package_facts"]["adapter_command_location"] = (
        "/Users/example/private/hermes-kaka-host-api"
    )
    manifest["install_drill_refs"]["health_receipt_ref"] = (
        "/Users/example/.kaka/mobile-runtime.sqlite3"
    )

    report = build_host_extension_material_intake(manifest)
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)

    Draft202012Validator(_output_schema()).validate(report)
    assert report["status"] == "blocked"
    assert "package_facts.install_command" in report["redacted_fields"]
    assert "package_facts.update_channel" in report["redacted_fields"]
    assert "package_facts.adapter_command_location" in report["redacted_fields"]
    assert "install_drill_refs.health_receipt_ref" in report["redacted_fields"]
    assert "install_command" in report["missing_package_facts"]
    assert "adapter_command_location" in report["missing_package_facts"]
    assert "health_receipt_ref" in report["missing_install_drill_refs"]
    assert "sk-test" not in rendered
    assert "Bearer abc123" not in rendered
    assert "/Users/example" not in rendered
    assert "mobile-runtime.sqlite3" not in rendered


def test_material_intake_blocks_unreadable_or_missing_manifest(tmp_path):
    missing = build_host_extension_material_intake_from_path(tmp_path / "missing.json")
    assert missing["status"] == "blocked"
    assert missing["source"]["loaded"] is False
    assert missing["source"]["source"] == "missing"

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not json", encoding="utf-8")
    unreadable = build_host_extension_material_intake_from_path(invalid_path)
    assert unreadable["status"] == "blocked"
    assert unreadable["source"]["loaded"] is False
    assert unreadable["source"]["source"] == "unreadable"
    Draft202012Validator(_output_schema()).validate(unreadable)


def test_material_intake_blocks_runtime_argument_manifest_mismatch(tmp_path):
    manifest_path = tmp_path / "materials.json"
    manifest_path.write_text(json.dumps(_complete_manifest(runtime="openclaw")), encoding="utf-8")

    report = build_host_extension_material_intake_from_path(
        manifest_path,
        runtime="hermes",
    )

    assert report["status"] == "blocked"
    assert report["runtime"] == "hermes"
    assert "runtime_argument_manifest_mismatch" in report["findings"]
    assert report["readiness"]["status"] == "ready_for_external_install_drill"
    Draft202012Validator(_output_schema()).validate(report)


def test_host_extension_material_intake_schema_rejects_drift():
    manifest = _complete_manifest()
    report = build_host_extension_material_intake(manifest)
    output_validator = Draft202012Validator(_output_schema())
    input_validator = Draft202012Validator(_input_schema())

    output_validator.validate(report)
    drifted_report = json.loads(json.dumps(report))
    drifted_report["safety"]["does_not_fetch_refs"] = False
    assert not output_validator.is_valid(drifted_report)

    drifted_report = json.loads(json.dumps(report))
    drifted_report["phone_api"] = {"base_path": "/mobile/v2"}
    assert not output_validator.is_valid(drifted_report)

    drifted_report = json.loads(json.dumps(report))
    drifted_report["package_facts"]["mobile_token"] = "dev-mobile-token"
    assert not output_validator.is_valid(drifted_report)

    drifted_manifest = json.loads(json.dumps(manifest))
    drifted_manifest["unexpected"] = "extra"
    assert not input_validator.is_valid(drifted_manifest)
