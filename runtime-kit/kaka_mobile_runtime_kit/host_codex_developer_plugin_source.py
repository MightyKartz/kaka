from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .host_extension_install_package import build_host_extension_install_package


SCHEMA_VERSION = "kaka.host_codex_developer_plugin_source.v1"
SURFACE = "hermes_openclaw_host_codex_developer_plugin_source"
PLUGIN_BASE_NAME = "kaka-host-extension-developer"
SKILL_NAME = "kaka-host-extension-developer"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")
DISPLAY_NAMES = {"hermes": "Hermes", "openclaw": "OpenClaw"}
INSTALL_SHAPES = {"hermes": "hermes_plugin", "openclaw": "openclaw_skill"}


def build_host_codex_developer_plugin_source(
    *,
    runtime: str,
    output_dir: str = "",
    written: bool = False,
) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    install_package = build_host_extension_install_package(runtime=runtime)
    plugin_name = _plugin_name(runtime)
    output_root = str(Path(output_dir) / plugin_name) if str(output_dir).strip() else ""

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "written": written,
        "output_root": output_root,
        "developer_only": True,
        "ordinary_user_install": False,
        "plugin": {
            "name": plugin_name,
            "version": "0.1.0",
            "source_scope": "explicit_output_dir",
            "plugin_manifest_path": ".codex-plugin/plugin.json",
            "skill_path": f"skills/{SKILL_NAME}/SKILL.md",
            "updates_marketplace": False,
        },
        "skill": {
            "name": SKILL_NAME,
            "target_runtimes": [runtime],
            "purpose": "host_team_scaffold_validate_review",
            "ordinary_user_install_surface": False,
            "references": [f"skills/{SKILL_NAME}/references/runtime-kit-commands.md"],
        },
        "host_extension": {
            "install_shape": INSTALL_SHAPES[runtime],
            "ordinary_user_entrypoint": install_package["package"]["ordinary_user_entrypoint"],
            "stable_package_owner": "host_shell",
            "developer_plugin_owner": "host_engineering_team",
        },
        "generated_files": [
            {"path": ".codex-plugin/plugin.json", "kind": "codex_plugin_manifest"},
            {"path": f"skills/{SKILL_NAME}/SKILL.md", "kind": "codex_skill"},
            {
                "path": f"skills/{SKILL_NAME}/references/runtime-kit-commands.md",
                "kind": "codex_skill_reference",
            },
            {"path": "source.json", "kind": "source_manifest"},
        ],
        "codex_install": {
            "installs_codex_plugin": False,
            "updates_marketplace": False,
            "writes_user_home": False,
            "requires_install_target_decision": True,
            "marketplace_entry_created": False,
        },
        "ordinary_user_boundary": {
            "install_surface": "host_native_plugin_or_skill",
            "phone_api_path": "/mobile/v1",
            "codex_plugin_required": False,
            "manual_adapter_code_required": False,
            "environment_variable_required": False,
        },
        "phone_api": install_package["phone_api"],
        "runtime_kit_commands": [
            "host-plugin-skill-devkit",
            "host-extension-install-package",
            "host-extension-readiness",
            "host-private-adapter-conformance",
            "host-shell-pilot-evidence-manifest",
            "host-shell-pilot-artifact-review",
        ],
        "safety": {
            "does_not_install_package": True,
            "does_not_install_codex_plugin": True,
            "does_not_update_marketplace": True,
            "does_not_write_user_home": True,
            "does_not_start_bridge": True,
            "does_not_bind_lan": True,
            "does_not_advertise_bonjour": True,
            "does_not_mint_credentials": True,
            "does_not_run_conformance": True,
            "does_not_invoke_private_adapter": True,
            "does_not_change_phone_api": True,
        },
    }


def write_host_codex_developer_plugin_source(
    *,
    runtime: str,
    output_dir: Path,
) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    _require_safe_output_dir(output_dir)
    root = Path(output_dir) / _plugin_name(runtime)
    skill_root = root / "skills" / SKILL_NAME
    (root / ".codex-plugin").mkdir(parents=True, exist_ok=True)
    (skill_root / "references").mkdir(parents=True, exist_ok=True)

    source = build_host_codex_developer_plugin_source(
        runtime=runtime,
        output_dir=str(output_dir),
        written=True,
    )
    display_name = DISPLAY_NAMES[runtime]

    _write_json(root / ".codex-plugin" / "plugin.json", _plugin_json(display_name, _plugin_name(runtime)))
    _write_text(skill_root / "SKILL.md", _skill_md(display_name, runtime))
    _write_text(
        skill_root / "references" / "runtime-kit-commands.md",
        _runtime_kit_commands_reference(runtime),
    )
    _write_json(root / "source.json", source)
    return source


def _plugin_json(runtime_name: str, plugin_name: str) -> Mapping[str, object]:
    return {
        "name": plugin_name,
        "version": "0.1.0",
        "description": "Host-team Codex developer plugin source for Pocket Agent Mobile Bridge extensions.",
        "author": {"name": "Pocket Agent Runtime Kit"},
        "skills": "./skills/",
        "interface": {
            "displayName": "Pocket Agent Host Extension Developer",
            "shortDescription": "Validate Pocket Agent Mobile Bridge host extension materials.",
            "longDescription": (
                "Developer-only Codex plugin source for host engineers building "
                f"{runtime_name} Pocket Agent Mobile Bridge extension materials."
            ),
            "developerName": "Pocket Agent Runtime Kit",
            "category": "Productivity",
            "capabilities": [],
            "defaultPrompt": "Help validate Pocket Agent Mobile Bridge host extension materials.",
        },
    }


def _skill_md(runtime_name: str, runtime: str) -> str:
    return (
        "---\n"
        f"name: {SKILL_NAME}\n"
        "description: Use when a host engineer is scaffolding, validating, or reviewing Pocket Agent Mobile Bridge Host Extension materials.\n"
        "---\n\n"
        "# Pocket Agent Host Extension Developer\n\n"
        "Use this skill only for host-team development of the native Hermes Plugin or "
        "OpenClaw Skill/sidecar package. It is not the ordinary-user installation surface.\n\n"
        "Safety rules:\n\n"
        "- Do not install Hermes/OpenClaw packages.\n"
        "- Do not start Pocket Agent Mobile Bridge, bind LAN, advertise Bonjour, or mint mobile tokens.\n"
        "- Do not invoke private host adapter commands or run conformance without explicit host-team approval.\n"
        "- Do not update Codex marketplaces or write user-home plugin directories.\n"
        "- Keep Pocket Agent iPhone on `/mobile/v1`; do not expose private host APIs to the phone.\n\n"
        "Workflow:\n\n"
        "1. Generate or inspect Runtime Kit `host-plugin-skill-devkit` output for the target runtime.\n"
        "2. Check host UI contract files and release-gate command files.\n"
        "3. Verify the private adapter command remains extension-internal.\n"
        "4. Confirm install, update, failure recovery, log redaction, uninstall, conformance, and evidence-manifest refs are present before external install drills.\n"
        "5. Keep ordinary-user instructions focused on installing the host-native Plugin/Skill and pairing Pocket Agent iPhone by QR or Bonjour.\n\n"
        f"Default runtime context for this generated source: `{runtime}` ({runtime_name}).\n\n"
        "For command details, read `references/runtime-kit-commands.md`.\n"
    )


def _runtime_kit_commands_reference(runtime: str) -> str:
    return (
        "# Runtime Kit Commands\n\n"
        "Run these from the Pocket Agent repository root with `PYTHONPATH=runtime-kit:mock_bridge`.\n\n"
        "```bash\n"
        f"python3 -m kaka_mobile_runtime_kit host-plugin-skill-devkit --runtime {runtime}\n"
        f"python3 -m kaka_mobile_runtime_kit host-extension-install-package --runtime {runtime}\n"
        f"python3 -m kaka_mobile_runtime_kit host-extension-readiness --runtime {runtime}\n"
        f"python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance --runtime {runtime} --private-adapter-command /path/to/host-owned-command\n"
        f"python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest --runtime {runtime} --artifact-root artifacts/{runtime}\n"
        "```\n\n"
        "These commands are host-team development and release gates. They are not ordinary-user Pocket Agent setup steps.\n"
    )


def _write_text(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _plugin_name(runtime: str) -> str:
    return f"{PLUGIN_BASE_NAME}-{runtime}"


def _require_safe_output_dir(output_dir: Path) -> None:
    if not str(output_dir).strip():
        raise ValueError("host-codex-developer-plugin-source --write requires --output-dir")

    target = Path(output_dir).expanduser().resolve(strict=False)
    home = Path.home().resolve(strict=False)
    forbidden_roots = [
        home / "plugins",
        home / ".codex" / "skills",
        home / ".agents" / "plugins",
    ]
    for forbidden in forbidden_roots:
        forbidden_resolved = forbidden.resolve(strict=False)
        if target == forbidden_resolved or forbidden_resolved in target.parents:
            raise ValueError(f"Refusing to write developer plugin source inside user install root: {forbidden}")


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported host Codex developer plugin runtime: {runtime}")
