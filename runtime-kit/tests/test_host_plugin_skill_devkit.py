import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_plugin_skill_devkit import (
    build_host_plugin_skill_devkit,
)


FORBIDDEN_USER_COPY = (
    "export HERMES_KAKA_HOST_API",
    "export OPENCLAW_KAKA_HOST_API",
    "--private-adapter-command",
    "write adapter code",
    "paste Runtime Kit command",
    "install Codex plugin",
    "Codex skill to connect Kaka",
)


def test_devkit_hermes_indexes_existing_host_extension_contracts() -> None:
    devkit = build_host_plugin_skill_devkit(runtime="hermes")

    assert devkit["schema_version"] == "kaka.host_plugin_skill_devkit.v1"
    assert devkit["surface"] == "hermes_openclaw_host_plugin_skill_devkit"
    assert devkit["runtime"] == "hermes"
    assert devkit["developer_kit_only"] is True
    assert devkit["ordinary_user_install"] is False
    assert devkit["package"]["install_shape"] == "hermes_plugin"
    assert devkit["package"]["ordinary_user_entrypoint"] == "Hermes Plugin: Kaka Mobile Bridge"
    assert devkit["package"]["final_distribution_requires_host_signature"] is True
    assert devkit["adapter_template"]["default_command_name"] == "hermes-kaka-host-api"
    assert devkit["adapter_template"]["visibility"] == "extension_internal"
    assert devkit["adapter_template"]["implementation_owner"] == "host_shell"
    assert devkit["adapter_template"]["contains_proprietary_implementation"] is False
    assert devkit["codex_automation"]["included"] is True
    assert devkit["codex_automation"]["ordinary_user_install_surface"] is False
    assert devkit["codex_automation"]["installs_codex_plugin"] is False
    assert devkit["codex_automation"]["updates_marketplace"] is False
    assert devkit["phone_api"]["base_path"] == "/mobile/v1"
    assert devkit["phone_api"]["private_host_api_exposed"] is False
    assert devkit["safety"]["manual_adapter_code_required"] is False
    assert devkit["safety"]["environment_variable_required"] is False
    assert devkit["safety"]["does_not_install_package"] is True
    assert devkit["safety"]["does_not_run_conformance"] is True
    assert devkit["safety"]["does_not_invoke_private_adapter"] is True
    assert devkit["quality_gates"]["requires_conformance_report"] is True
    assert devkit["quality_gates"]["requires_evidence_manifest"] is True
    assert devkit["quality_gates"]["requires_install_drill_receipts"] is True
    assert devkit["quality_gates"]["can_mark_p3_4_complete"] is False
    assert "host-extension-starter-kit" in devkit["contract_index"]["required_commands"]
    assert "host-extension-install-package" in devkit["contract_index"]["required_commands"]


def test_devkit_openclaw_uses_skill_shape_without_generating_host_skill() -> None:
    devkit = build_host_plugin_skill_devkit(runtime="openclaw")

    assert devkit["package"]["install_shape"] == "openclaw_skill"
    assert devkit["package"]["ordinary_user_entrypoint"] == "OpenClaw Skill: Kaka Mobile Bridge"
    assert devkit["adapter_template"]["default_command_name"] == "openclaw-kaka-host-api"
    assert devkit["adapter_template"]["environment_variable"] == "OPENCLAW_KAKA_HOST_API"
    generated_paths = {entry["path"] for entry in devkit["generated_files"]}
    assert "codex-automation/SKILL.template.md" in generated_paths
    assert "codex-automation/plugin.template.json" in generated_paths
    assert "host-project/openclaw-skill/SKILL.md" not in generated_paths
    assert ".codex-plugin/plugin.json" not in generated_paths
    assert all(not path.startswith("bin/") for path in generated_paths)


def test_devkit_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host plugin/skill devkit runtime"):
        build_host_plugin_skill_devkit(runtime="sidecar")


def test_devkit_schema_validates_supported_runtimes() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-plugin-skill-devkit.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_host_plugin_skill_devkit(runtime="hermes"))
    Draft202012Validator(schema).validate(build_host_plugin_skill_devkit(runtime="openclaw"))


def test_devkit_schema_rejects_user_adapter_or_codex_install_drift() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-plugin-skill-devkit.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    devkit = json.loads(json.dumps(build_host_plugin_skill_devkit(runtime="hermes")))

    manual_code = json.loads(json.dumps(devkit))
    manual_code["safety"]["manual_adapter_code_required"] = True
    assert not validator.is_valid(manual_code)

    env_required = json.loads(json.dumps(devkit))
    env_required["safety"]["environment_variable_required"] = True
    assert not validator.is_valid(env_required)

    phone_private_api = json.loads(json.dumps(devkit))
    phone_private_api["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_private_api)

    visible_adapter = json.loads(json.dumps(devkit))
    visible_adapter["adapter_template"]["visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)

    codex_install = json.loads(json.dumps(devkit))
    codex_install["codex_automation"]["installs_codex_plugin"] = True
    assert not validator.is_valid(codex_install)

    real_skill = json.loads(json.dumps(devkit))
    real_skill["generated_files"].append({"path": "codex-automation/SKILL.md", "kind": "codex_skill"})
    assert not validator.is_valid(real_skill)


def test_write_devkit_materializes_templates_without_real_codex_or_host_install_files(tmp_path: Path) -> None:
    from kaka_mobile_runtime_kit.host_plugin_skill_devkit import write_host_plugin_skill_devkit

    result = write_host_plugin_skill_devkit(runtime="openclaw", output_dir=tmp_path)

    root = tmp_path / "kaka-mobile-bridge-openclaw-devkit"
    assert result["written"] is True
    assert result["output_root"] == str(root)
    assert (root / "README.md").exists()
    assert (root / "devkit.json").exists()
    assert (root / "contracts" / "contract-index.json").exists()
    assert (root / "commands" / "host-extension-starter-kit.command.json").exists()
    assert (root / "commands" / "host-extension-install-package.command.json").exists()
    assert (root / "commands" / "host-extension-readiness.command.json").exists()
    assert (root / "commands" / "host-private-adapter-conformance.command.json").exists()
    assert (root / "commands" / "host-shell-pilot-evidence-manifest.command.json").exists()
    assert (root / "commands" / "host-shell-pilot-artifact-review.command.json").exists()
    assert (root / "quality-gates" / "acceptance-gates.json").exists()
    assert (root / "boundaries" / "ordinary-user-boundary.json").exists()
    assert (root / "adapter-template" / "openclaw-kaka-host-api.template.py").exists()
    assert (root / "adapter-template" / "README.template.md").exists()
    assert (root / "codex-automation" / "README.md").exists()
    assert (root / "codex-automation" / "SKILL.template.md").exists()
    assert (root / "codex-automation" / "plugin.template.json").exists()
    assert not (root / ".codex-plugin" / "plugin.json").exists()
    assert not (root / "codex-automation" / "SKILL.md").exists()
    assert not (root / "host-project" / "openclaw-skill" / "SKILL.md").exists()
    assert not (root / "bin" / "openclaw-kaka-host-api.README.md").exists()

    combined_copy = "\n".join(
        path.read_text()
        for path in (
            root / "README.md",
            root / "adapter-template" / "README.template.md",
            root / "codex-automation" / "README.md",
            root / "codex-automation" / "SKILL.template.md",
        )
    )
    for forbidden in FORBIDDEN_USER_COPY:
        assert forbidden not in combined_copy
