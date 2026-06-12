import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_codex_developer_plugin_source import (
    build_host_codex_developer_plugin_source,
    write_host_codex_developer_plugin_source,
)


SCHEMA_PATH = Path("runtime-kit/packaging/host-codex-developer-plugin-source.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_source_preview_is_developer_only_and_schema_validates() -> None:
    source = build_host_codex_developer_plugin_source(runtime="hermes")

    assert source["schema_version"] == "kaka.host_codex_developer_plugin_source.v1"
    assert source["surface"] == "hermes_openclaw_host_codex_developer_plugin_source"
    assert source["runtime"] == "hermes"
    assert source["written"] is False
    assert source["developer_only"] is True
    assert source["ordinary_user_install"] is False
    assert source["plugin"]["name"] == "kaka-host-extension-developer-hermes"
    assert source["plugin"]["plugin_manifest_path"] == ".codex-plugin/plugin.json"
    assert source["plugin"]["skill_path"] == "skills/kaka-host-extension-developer/SKILL.md"
    assert source["codex_install"]["installs_codex_plugin"] is False
    assert source["codex_install"]["updates_marketplace"] is False
    assert source["codex_install"]["writes_user_home"] is False
    assert source["ordinary_user_boundary"]["install_surface"] == "host_native_plugin_or_skill"
    assert source["ordinary_user_boundary"]["codex_plugin_required"] is False
    assert source["phone_api"]["base_path"] == "/mobile/v1"
    assert source["phone_api"]["private_host_api_exposed"] is False
    assert source["safety"]["does_not_invoke_private_adapter"] is True
    assert source["safety"]["does_not_run_conformance"] is True

    Draft202012Validator(_schema()).validate(source)


def test_source_preview_supports_openclaw_skill_context() -> None:
    source = build_host_codex_developer_plugin_source(runtime="openclaw")

    assert source["runtime"] == "openclaw"
    assert source["host_extension"]["install_shape"] == "openclaw_skill"
    assert "openclaw" in source["skill"]["target_runtimes"]

    Draft202012Validator(_schema()).validate(source)


def test_source_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host Codex developer plugin runtime"):
        build_host_codex_developer_plugin_source(runtime="sidecar")


def test_source_schema_rejects_install_or_marketplace_drift() -> None:
    validator = Draft202012Validator(_schema())
    source = json.loads(json.dumps(build_host_codex_developer_plugin_source(runtime="hermes")))

    ordinary_user_install = json.loads(json.dumps(source))
    ordinary_user_install["ordinary_user_install"] = True
    assert not validator.is_valid(ordinary_user_install)

    installs_plugin = json.loads(json.dumps(source))
    installs_plugin["codex_install"]["installs_codex_plugin"] = True
    assert not validator.is_valid(installs_plugin)

    updates_marketplace = json.loads(json.dumps(source))
    updates_marketplace["codex_install"]["updates_marketplace"] = True
    assert not validator.is_valid(updates_marketplace)

    writes_user_home = json.loads(json.dumps(source))
    writes_user_home["codex_install"]["writes_user_home"] = True
    assert not validator.is_valid(writes_user_home)

    phone_private_api = json.loads(json.dumps(source))
    phone_private_api["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_private_api)


def test_source_schema_binds_runtime_to_plugin_name_and_install_shape() -> None:
    validator = Draft202012Validator(_schema())
    source = json.loads(json.dumps(build_host_codex_developer_plugin_source(runtime="hermes")))

    wrong_plugin = json.loads(json.dumps(source))
    wrong_plugin["plugin"]["name"] = "kaka-host-extension-developer-openclaw"
    assert not validator.is_valid(wrong_plugin)

    wrong_target_runtime = json.loads(json.dumps(source))
    wrong_target_runtime["skill"]["target_runtimes"] = ["openclaw"]
    assert not validator.is_valid(wrong_target_runtime)

    wrong_install_shape = json.loads(json.dumps(source))
    wrong_install_shape["host_extension"]["install_shape"] = "openclaw_skill"
    assert not validator.is_valid(wrong_install_shape)


def test_write_source_materializes_real_plugin_source_without_marketplace(tmp_path: Path) -> None:
    result = write_host_codex_developer_plugin_source(runtime="hermes", output_dir=tmp_path)

    root = tmp_path / "kaka-host-extension-developer-hermes"
    assert result["written"] is True
    assert result["output_root"] == str(root)
    assert (root / ".codex-plugin" / "plugin.json").exists()
    assert (root / "skills" / "kaka-host-extension-developer" / "SKILL.md").exists()
    assert (
        root
        / "skills"
        / "kaka-host-extension-developer"
        / "references"
        / "runtime-kit-commands.md"
    ).exists()
    assert (root / "source.json").exists()
    assert not (root / ".agents" / "plugins" / "marketplace.json").exists()
    assert not (root / "marketplace.json").exists()

    plugin_json = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
    assert plugin_json["name"] == "kaka-host-extension-developer-hermes"
    assert plugin_json["skills"] == "./skills/"
    assert "marketplace" not in json.dumps(plugin_json).lower()

    skill_text = (root / "skills" / "kaka-host-extension-developer" / "SKILL.md").read_text()
    assert "ordinary-user installation surface" in skill_text
    assert "Do not install Hermes/OpenClaw packages" in skill_text
    assert "Do not update Codex marketplaces" in skill_text
