import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_extension_preview import (
    build_host_extension_preview,
)


def test_host_extension_preview_is_user_install_shape() -> None:
    preview = build_host_extension_preview(runtime="hermes")

    assert preview["schema_version"] == "kaka.host_extension_preview.v1"
    assert preview["surface"] == "hermes_openclaw_host_extension_preview"
    assert preview["runtime"] == "hermes"
    assert preview["ordinary_user_install"]["install_shape"] == "hermes_plugin"
    assert preview["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert preview["ordinary_user_install"]["requires_environment_variable"] is False
    assert preview["ordinary_user_install"]["starts_bridge_on_install"] is False
    assert preview["ordinary_user_install"]["creates_login_item_on_install"] is False
    assert preview["ordinary_user_install"]["requires_explicit_enable"] is True
    assert preview["adapter_command"]["visibility"] == "extension_internal"
    assert preview["adapter_command"]["developer_fallback_only"] is True
    assert preview["adapter_command"]["default_command_name"] == "hermes-kaka-host-api"
    assert preview["phone_api"]["base_path"] == "/mobile/v1"
    assert preview["phone_api"]["private_host_api_exposed"] is False


def test_host_extension_preview_for_openclaw_uses_skill_install_shape() -> None:
    preview = build_host_extension_preview(runtime="openclaw")

    assert preview["ordinary_user_install"]["install_shape"] == "openclaw_skill"
    assert preview["adapter_command"]["default_command_name"] == "openclaw-kaka-host-api"
    assert preview["adapter_command"]["environment_variable"] == "OPENCLAW_KAKA_HOST_API"
    assert preview["adapter_command"]["developer_fallback_only"] is True


def test_host_extension_preview_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host extension runtime"):
        build_host_extension_preview(runtime="sidecar")


def test_host_extension_preview_cli_prints_contract(capsys) -> None:
    from kaka_mobile_runtime_kit.cli import main

    exit_code = main(["host-extension-preview", "--runtime", "hermes"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "kaka.host_extension_preview.v1"
    assert output["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert output["release_gates"]["requires_p3_2_conformance"] is True
    assert output["release_gates"]["requires_p3_4_external_pilot_evidence"] is True


def test_host_extension_preview_validates_against_schema() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-preview.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_host_extension_preview(runtime="hermes"))
    Draft202012Validator(schema).validate(build_host_extension_preview(runtime="openclaw"))
