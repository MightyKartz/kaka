from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .host_extension_install_package import build_host_extension_install_package
from .host_extension_starter_kit import build_host_extension_starter_kit
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
)


SCHEMA_VERSION = "kaka.host_plugin_skill_devkit.v1"
SURFACE = "hermes_openclaw_host_plugin_skill_devkit"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")
DISPLAY_NAMES = {"hermes": "Hermes", "openclaw": "OpenClaw"}
INSTALL_SHAPES = {"hermes": "hermes_plugin", "openclaw": "openclaw_skill"}
ENTRYPOINT_LABELS = {
    "hermes": "Hermes Plugin: Kaka Mobile Bridge",
    "openclaw": "OpenClaw Skill: Kaka Mobile Bridge",
}
COMMANDS = [
    "host-extension-starter-kit",
    "host-extension-install-package",
    "host-extension-readiness",
    "host-private-adapter-conformance",
    "host-shell-pilot-evidence-manifest",
    "host-shell-pilot-artifact-review",
]


def build_host_plugin_skill_devkit(
    *,
    runtime: str,
    output_dir: str = "",
    written: bool = False,
) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    starter = build_host_extension_starter_kit(runtime=runtime)
    install_package = build_host_extension_install_package(runtime=runtime)
    command_name = default_private_adapter_command_name(runtime)
    environment_variable = private_adapter_environment_variable(runtime)
    root_name = f"kaka-mobile-bridge-{runtime}-devkit"
    output_root = str(Path(output_dir) / root_name) if str(output_dir).strip() else ""

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "written": written,
        "output_root": output_root,
        "developer_kit_only": True,
        "ordinary_user_install": False,
        "package": {
            "install_shape": INSTALL_SHAPES[runtime],
            "ordinary_user_entrypoint": ENTRYPOINT_LABELS[runtime],
            "developer_kit_owner": "kaka_runtime_kit",
            "stable_package_owner": "host_shell",
            "final_distribution_requires_host_signature": True,
        },
        "generated_files": _generated_files(command_name),
        "contract_index": {
            "builds_on": [
                starter["schema_version"],
                install_package["schema_version"],
                "kaka.host_extension_readiness.v1",
                "kaka.host_private_adapter_conformance_report.v1",
                "kaka.host_shell_pilot_evidence_manifest.v1",
            ],
            "required_commands": list(COMMANDS),
            "phone_api_path": "/mobile/v1",
        },
        "adapter_template": {
            "default_command_name": command_name,
            "visibility": "extension_internal",
            "developer_fallback_only": True,
            "environment_variable": environment_variable,
            "implementation_owner": "host_shell",
            "contains_proprietary_implementation": False,
            "stdin_stdout_contract": "kaka.host_private_adapter_request.v1 -> kaka.host_private_adapter_response.v1",
        },
        "quality_gates": {
            "requires_host_signature": True,
            "requires_update_channel": True,
            "requires_conformance_report": True,
            "requires_evidence_manifest": True,
            "requires_install_drill_receipts": True,
            "requires_log_redaction_review": True,
            "can_mark_p3_4_complete": False,
        },
        "codex_automation": {
            "included": True,
            "kind": "template_only",
            "ordinary_user_install_surface": False,
            "developer_only": True,
            "installs_codex_plugin": False,
            "updates_marketplace": False,
        },
        "ordinary_user_boundary": {
            "install_surface": "host_native_plugin_or_skill",
            "phone_api_path": "/mobile/v1",
            "manual_adapter_code_required": False,
            "environment_variable_required": False,
            "codex_plugin_required": False,
        },
        "phone_api": install_package["phone_api"],
        "readiness_inputs": install_package["readiness_inputs"],
        "safety": {
            "manual_adapter_code_required": False,
            "environment_variable_required": False,
            "starts_bridge_on_install": False,
            "binds_lan_on_install": False,
            "advertises_bonjour_on_install": False,
            "creates_login_item_on_install": False,
            "mints_credentials_on_install": False,
            "does_not_install_package": True,
            "does_not_sign_package": True,
            "does_not_publish_package": True,
            "does_not_run_package_manager": True,
            "does_not_run_conformance": True,
            "does_not_modify_keychain": True,
            "does_not_invoke_private_adapter": True,
            "runtime_side_only": True,
        },
    }


def _generated_files(command_name: str) -> list[Mapping[str, str]]:
    return [
        {"path": "README.md", "kind": "developer_readme"},
        {"path": "devkit.json", "kind": "devkit_manifest"},
        {"path": "contracts/contract-index.json", "kind": "contract_index"},
        {"path": "commands/host-extension-starter-kit.command.json", "kind": "command_file"},
        {"path": "commands/host-extension-install-package.command.json", "kind": "command_file"},
        {"path": "commands/host-extension-readiness.command.json", "kind": "command_file"},
        {"path": "commands/host-private-adapter-conformance.command.json", "kind": "command_file"},
        {"path": "commands/host-shell-pilot-evidence-manifest.command.json", "kind": "command_file"},
        {"path": "commands/host-shell-pilot-artifact-review.command.json", "kind": "command_file"},
        {"path": "quality-gates/acceptance-gates.json", "kind": "quality_gate"},
        {"path": "boundaries/ordinary-user-boundary.json", "kind": "ordinary_user_boundary"},
        {"path": f"adapter-template/{command_name}.template.py", "kind": "adapter_template"},
        {"path": "adapter-template/README.template.md", "kind": "adapter_template_readme"},
        {"path": "codex-automation/README.md", "kind": "codex_automation_readme"},
        {"path": "codex-automation/SKILL.template.md", "kind": "codex_skill_template"},
        {"path": "codex-automation/plugin.template.json", "kind": "codex_plugin_template"},
    ]


def write_host_plugin_skill_devkit(*, runtime: str, output_dir: Path) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    root = Path(output_dir) / f"kaka-mobile-bridge-{runtime}-devkit"
    for child in ("contracts", "commands", "quality-gates", "boundaries", "adapter-template", "codex-automation"):
        (root / child).mkdir(parents=True, exist_ok=True)

    devkit = build_host_plugin_skill_devkit(runtime=runtime, output_dir=str(output_dir), written=True)
    command_name = default_private_adapter_command_name(runtime)
    display_name = DISPLAY_NAMES[runtime]

    _write_text(root / "README.md", _developer_readme(display_name))
    _write_json(root / "devkit.json", devkit)
    _write_json(root / "contracts" / "contract-index.json", devkit["contract_index"])
    for command in COMMANDS:
        _write_json(root / "commands" / f"{command}.command.json", _command([command, "--runtime", runtime]))
    _write_json(root / "quality-gates" / "acceptance-gates.json", devkit["quality_gates"])
    _write_json(root / "boundaries" / "ordinary-user-boundary.json", devkit["ordinary_user_boundary"])
    _write_text(root / "adapter-template" / f"{command_name}.template.py", _adapter_template(runtime, command_name))
    _write_text(root / "adapter-template" / "README.template.md", _adapter_template_readme(display_name, command_name))
    _write_text(root / "codex-automation" / "README.md", _codex_automation_readme(display_name))
    _write_text(root / "codex-automation" / "SKILL.template.md", _codex_skill_template(display_name))
    _write_json(root / "codex-automation" / "plugin.template.json", _codex_plugin_template())
    return devkit


def _command(args: list[str]) -> Mapping[str, object]:
    return {
        "argv": ["python3", "-m", "kaka_mobile_runtime_kit", *args],
        "mutates_host": False,
        "requires_host_team_review_before_use": True,
    }


def _developer_readme(runtime_name: str) -> str:
    return (
        f"# Kaka Mobile Bridge {runtime_name} Devkit\n\n"
        "This devkit is for the host team building the native Plugin/Skill package. "
        "It is not a signed public package, not a Codex marketplace package, and it "
        "does not perform installation.\n\n"
        "Ordinary users install the finished host extension, open the Kaka Mobile "
        "Bridge panel, enable it explicitly, then pair Kaka iPhone through `/mobile/v1`.\n\n"
        "Host teams own signing, update channels, release notes, conformance evidence, "
        "install-drill receipts, and extension-internal adapter implementation.\n"
    )


def _adapter_template_readme(runtime_name: str, command_name: str) -> str:
    return (
        f"# {command_name} Template\n\n"
        f"{runtime_name} owns the real extension-internal command implementation. "
        "Runtime Kit defines request/response contracts and release gates, but this "
        "template intentionally contains no proprietary host API calls.\n"
    )


def _adapter_template(runtime: str, command_name: str) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "\"\"\"Host-owned adapter template for Kaka Mobile Bridge devkit.\n\n"
        "Keep this command extension-internal. Replace the unavailable response inside\n"
        "the host extension repository after passing conformance with real host-owned\n"
        "implementation code.\n"
        "\"\"\"\n\n"
        "from __future__ import annotations\n\n"
        "import json\n"
        "import sys\n\n\n"
        f"COMMAND_NAME = {command_name!r}\n"
        f"RUNTIME = {runtime!r}\n\n\n"
        "def main() -> int:\n"
        "    request = json.load(sys.stdin)\n"
        "    action_id = str(request.get(\"action_id\", \"\"))\n"
        "    response = {\n"
        "        \"schema_version\": \"kaka.host_private_adapter_response.v1\",\n"
        "        \"runtime\": RUNTIME,\n"
        "        \"action_id\": action_id,\n"
        "        \"status\": \"unavailable\",\n"
        "        \"message\": \"Host team must implement this action inside the native extension.\",\n"
        "        \"details\": {\"command_name\": COMMAND_NAME},\n"
        "    }\n"
        "    json.dump(response, sys.stdout, sort_keys=True)\n"
        "    sys.stdout.write(\"\\n\")\n"
        "    return 0\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(main())\n"
    )


def _codex_automation_readme(runtime_name: str) -> str:
    return (
        f"# Optional Codex Automation For {runtime_name} Host Engineers\n\n"
        "These files are templates for host-team development automation only. They are "
        "not installed by Runtime Kit, not published to a marketplace, and not part of "
        "the ordinary-user Kaka setup flow.\n"
    )


def _codex_skill_template(runtime_name: str) -> str:
    return (
        "---\n"
        "name: kaka-host-extension-developer\n"
        "description: Use when a host engineer is building or validating a Kaka Mobile Bridge host Plugin/Skill package.\n"
        "---\n\n"
        "# Kaka Host Extension Developer\n\n"
        "Use this only for host-team development of the native Plugin/Skill package. "
        "Do not present this as the ordinary-user installation surface.\n\n"
        "Workflow:\n\n"
        "1. Validate host UI contract files.\n"
        "2. Validate release-gate command files.\n"
        "3. Check that the adapter command remains extension-internal.\n"
        "4. Collect install, update, failure recovery, log redaction, and uninstall receipts.\n"
        "5. Confirm Kaka iPhone still uses `/mobile/v1` only.\n\n"
        f"{runtime_name} owns signing, publishing, update channels, and proprietary adapter code.\n"
    )


def _codex_plugin_template() -> Mapping[str, object]:
    return {
        "template_only": True,
        "create_real_plugin_only_after_host_team_distribution_decision": True,
        "do_not_write_marketplace": True,
        "do_not_install_for_ordinary_users": True,
    }


def _write_text(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported host plugin/skill devkit runtime: {runtime}")
