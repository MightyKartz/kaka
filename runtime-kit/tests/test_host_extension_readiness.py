import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_extension_readiness import (
    build_host_extension_readiness,
)


READY_INPUTS = {
    "install_command": "openclaw skill install kaka-mobile-bridge",
    "update_channel": "stable",
    "adapter_command_location": "$EXTENSION_ROOT/bin/openclaw-kaka-host-api",
    "host_ui_entrypoint": "Settings > Skills > Kaka Mobile Bridge",
    "signed_package_ref": "openclaw-store://skills/kaka-mobile-bridge/1.0.0",
    "signature_ref": "notarization-team:OPENCLAW-KAKA",
    "conformance_report_ref": "artifacts/openclaw/conformance.json",
    "evidence_manifest_ref": "artifacts/openclaw/evidence-manifest.json",
}


def test_host_extension_readiness_blocks_missing_distribution_details() -> None:
    report = build_host_extension_readiness(runtime="hermes")

    assert report["schema_version"] == "kaka.host_extension_readiness.v1"
    assert report["surface"] == "hermes_openclaw_host_extension_readiness"
    assert report["runtime"] == "hermes"
    assert report["status"] == "blocked"
    assert report["ready_for_external_install_drill"] is False
    assert [item["id"] for item in report["missing_inputs"]] == [
        "install_command",
        "update_channel",
        "adapter_command_location",
        "host_ui_entrypoint",
        "signed_package_ref",
        "signature_ref",
        "conformance_report_ref",
        "evidence_manifest_ref",
    ]
    assert report["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert report["ordinary_user_install"]["requires_environment_variable"] is False
    assert report["adapter_command"]["visibility"] == "extension_internal"
    assert report["phone_api"]["base_path"] == "/mobile/v1"
    assert report["phone_api"]["private_host_api_exposed"] is False


def test_host_extension_readiness_accepts_complete_openclaw_distribution_metadata() -> None:
    report = build_host_extension_readiness(runtime="openclaw", **READY_INPUTS)

    assert report["status"] == "ready_for_external_install_drill"
    assert report["ready_for_external_install_drill"] is True
    assert report["missing_inputs"] == []
    assert report["ordinary_user_install"]["install_shape"] == "openclaw_skill"
    assert report["distribution"]["install_command"] == "openclaw skill install kaka-mobile-bridge"
    assert report["distribution"]["update_channel"] == "stable"
    assert report["distribution"]["signed_package_ref"] == "openclaw-store://skills/kaka-mobile-bridge/1.0.0"
    assert report["gates"]["requires_p3_2_conformance"] is True
    assert report["gates"]["requires_p3_4_evidence_manifest"] is True
    assert report["gates"]["can_mark_p3_4_complete"] is False
    assert report["safety"]["does_not_install_package"] is True
    assert report["safety"]["does_not_invoke_private_adapter"] is True


def test_host_extension_readiness_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host extension runtime"):
        build_host_extension_readiness(runtime="sidecar")


def test_host_extension_readiness_validates_against_schema() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-readiness.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_host_extension_readiness(runtime="hermes"))
    Draft202012Validator(schema).validate(
        build_host_extension_readiness(runtime="openclaw", **READY_INPUTS)
    )


def test_host_extension_readiness_schema_rejects_false_ready_states() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-readiness.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    report = json.loads(json.dumps(build_host_extension_readiness(runtime="openclaw", **READY_INPUTS)))

    ready_with_empty_ref = json.loads(json.dumps(report))
    ready_with_empty_ref["evidence"]["conformance_report_ref"] = ""
    assert not validator.is_valid(ready_with_empty_ref)

    blocked_but_ready = json.loads(json.dumps(build_host_extension_readiness(runtime="hermes")))
    blocked_but_ready["ready_for_external_install_drill"] = True
    assert not validator.is_valid(blocked_but_ready)


def test_host_extension_readiness_schema_rejects_phone_or_host_mutation_drift() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-readiness.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    report = json.loads(json.dumps(build_host_extension_readiness(runtime="openclaw", **READY_INPUTS)))

    p3_4_complete = json.loads(json.dumps(report))
    p3_4_complete["gates"]["can_mark_p3_4_complete"] = True
    assert not validator.is_valid(p3_4_complete)

    phone_private_api = json.loads(json.dumps(report))
    phone_private_api["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_private_api)

    visible_adapter_command = json.loads(json.dumps(report))
    visible_adapter_command["adapter_command"]["visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter_command)

    mutating_report = json.loads(json.dumps(report))
    mutating_report["safety"]["does_not_install_package"] = False
    assert not validator.is_valid(mutating_report)
