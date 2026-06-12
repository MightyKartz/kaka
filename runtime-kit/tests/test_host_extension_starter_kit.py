import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_extension_starter_kit import (
    build_host_extension_starter_kit,
    write_host_extension_starter_kit,
)


def test_host_extension_starter_kit_preview_is_ordinary_user_package_shape() -> None:
    kit = build_host_extension_starter_kit(runtime="hermes")

    assert kit["schema_version"] == "kaka.host_extension_starter_kit.v1"
    assert kit["surface"] == "hermes_openclaw_host_extension_starter_kit"
    assert kit["runtime"] == "hermes"
    assert kit["package"]["install_shape"] == "hermes_plugin"
    assert kit["package"]["ordinary_user_entrypoint"] == "Hermes Plugin: Kaka Mobile Bridge"
    assert kit["adapter_command"]["default_command_name"] == "hermes-kaka-host-api"
    assert kit["adapter_command"]["visibility"] == "extension_internal"
    assert kit["adapter_command"]["developer_fallback_only"] is True
    assert kit["safety"]["requires_manual_adapter_code"] is False
    assert kit["safety"]["requires_environment_variable"] is False
    assert kit["safety"]["starts_bridge_on_install"] is False
    assert kit["phone_api"]["base_path"] == "/mobile/v1"
    assert kit["phone_api"]["private_host_api_exposed"] is False
    assert "settings-preview" in kit["runtime_contracts"]["required_entrypoints"]
    assert "host-extension-readiness" in kit["runtime_contracts"]["required_entrypoints"]


def test_host_extension_starter_kit_openclaw_uses_skill_shape() -> None:
    kit = build_host_extension_starter_kit(runtime="openclaw")

    assert kit["package"]["install_shape"] == "openclaw_skill"
    assert kit["package"]["ordinary_user_entrypoint"] == "OpenClaw Skill: Kaka Mobile Bridge"
    assert kit["adapter_command"]["default_command_name"] == "openclaw-kaka-host-api"
    assert kit["adapter_command"]["environment_variable"] == "OPENCLAW_KAKA_HOST_API"


def test_host_extension_starter_kit_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host extension runtime"):
        build_host_extension_starter_kit(runtime="sidecar")


def test_host_extension_starter_kit_validates_against_schema() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-starter-kit.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_host_extension_starter_kit(runtime="hermes"))
    Draft202012Validator(schema).validate(build_host_extension_starter_kit(runtime="openclaw"))


def test_host_extension_starter_kit_schema_rejects_manual_user_setup_drift() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-starter-kit.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    kit = json.loads(json.dumps(build_host_extension_starter_kit(runtime="hermes")))

    manual_code = json.loads(json.dumps(kit))
    manual_code["safety"]["requires_manual_adapter_code"] = True
    assert not validator.is_valid(manual_code)

    phone_private_api = json.loads(json.dumps(kit))
    phone_private_api["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_private_api)

    visible_adapter = json.loads(json.dumps(kit))
    visible_adapter["adapter_command"]["visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)

    autostart = json.loads(json.dumps(kit))
    autostart["safety"]["starts_bridge_on_install"] = True
    assert not validator.is_valid(autostart)


def test_write_host_extension_starter_kit_materializes_safe_files(tmp_path: Path) -> None:
    result = write_host_extension_starter_kit(runtime="openclaw", output_dir=tmp_path)

    root = tmp_path / "kaka-mobile-bridge-openclaw"
    assert result["written"] is True
    assert result["output_root"] == str(root)
    assert (root / "README.md").read_text().startswith("# Kaka Mobile Bridge For OpenClaw")
    assert (root / "manifest.json").exists()
    assert (root / "bin" / "openclaw-kaka-host-api.README.md").exists()
    assert (root / "runtime-contracts" / "start-bridge.command.json").exists()

    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["runtime"] == "openclaw"
    assert manifest["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert manifest["adapter_command"]["visibility"] == "extension_internal"


def test_host_extension_starter_kit_cli_prints_preview(capsys) -> None:
    from kaka_mobile_runtime_kit.cli import main

    exit_code = main(["host-extension-starter-kit", "--runtime", "hermes"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "kaka.host_extension_starter_kit.v1"
    assert output["runtime"] == "hermes"
    assert output["written"] is False


def test_host_extension_starter_kit_cli_writes_output(tmp_path: Path, capsys) -> None:
    from kaka_mobile_runtime_kit.cli import main

    exit_code = main(
        [
            "host-extension-starter-kit",
            "--runtime",
            "openclaw",
            "--output-dir",
            str(tmp_path),
            "--write",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["written"] is True
    assert Path(output["output_root"]).name == "kaka-mobile-bridge-openclaw"
