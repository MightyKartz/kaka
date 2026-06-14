from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .host_extension_preview import build_host_extension_preview
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
)


SCHEMA_VERSION = "kaka.host_extension_starter_kit.v1"
SURFACE = "hermes_openclaw_host_extension_starter_kit"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")
INSTALL_SHAPES = {
    "hermes": "hermes_plugin",
    "openclaw": "openclaw_skill",
}
ENTRYPOINT_LABELS = {
    "hermes": "Hermes Plugin: Pocket Agent Mobile Bridge",
    "openclaw": "OpenClaw Skill: Pocket Agent Mobile Bridge",
}
DISPLAY_NAMES = {
    "hermes": "Hermes",
    "openclaw": "OpenClaw",
}


def build_host_extension_starter_kit(
    *,
    runtime: str,
    output_dir: str = "",
    written: bool = False,
) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    preview = build_host_extension_preview(runtime=runtime)
    command_name = default_private_adapter_command_name(runtime)
    environment_variable = private_adapter_environment_variable(runtime)
    root_name = f"kaka-mobile-bridge-{runtime}"
    output_root = str(Path(output_dir) / root_name) if str(output_dir).strip() else ""

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "written": written,
        "output_root": output_root,
        "package": {
            "install_shape": INSTALL_SHAPES[runtime],
            "ordinary_user_entrypoint": ENTRYPOINT_LABELS[runtime],
            "stable_package_owner": "host_shell",
            "starter_kit_owner": "kaka_runtime_kit",
            "final_distribution_requires_host_signature": True,
        },
        "generated_files": [
            {"path": "README.md", "kind": "operator_readme"},
            {"path": "manifest.json", "kind": "starter_manifest"},
            {"path": f"bin/{command_name}.README.md", "kind": "private_adapter_stub_readme"},
            {"path": "runtime-contracts/settings-preview.command.json", "kind": "runtime_command"},
            {"path": "runtime-contracts/package-preview.command.json", "kind": "runtime_command"},
            {"path": "runtime-contracts/host-package-preview.command.json", "kind": "runtime_command"},
            {"path": "runtime-contracts/host-extension-readiness.command.json", "kind": "runtime_command"},
            {"path": "runtime-contracts/start-bridge.command.json", "kind": "runtime_command"},
        ],
        "adapter_command": {
            "default_command_name": command_name,
            "visibility": preview["adapter_command"]["visibility"],
            "developer_fallback_only": True,
            "environment_variable": environment_variable,
            "implementation_owner": "host_shell",
            "starter_kit_contains_proprietary_implementation": False,
        },
        "runtime_contracts": {
            "required_entrypoints": [
                "settings-preview",
                "package-preview",
                "host-package-preview",
                "host-extension-preview",
                "host-extension-readiness",
                "host-adapter-run",
                "host-private-adapter-conformance",
            ],
            "phone_api": "/mobile/v1",
        },
        "ordinary_user_flow": [
            "Install the host Plugin/Skill package from the host-owned channel.",
            "Open the host UI entry point for Pocket Agent Mobile Bridge.",
            "Enable Pocket Agent Mobile Bridge explicitly.",
            "Show a short-lived QR or opt into Bonjour on a trusted LAN.",
            "Pair Pocket Agent iPhone through /mobile/v1.",
            "Run Health Check, Revoke iPhone, Update, Uninstall, and Open Logs from the host UI.",
        ],
        "phone_api": preview["phone_api"],
        "readiness_inputs": [
            "install_command",
            "update_channel",
            "adapter_command_location",
            "host_ui_entrypoint",
            "signed_package_ref",
            "signature_ref",
            "conformance_report_ref",
            "evidence_manifest_ref",
        ],
        "safety": {
            "requires_manual_adapter_code": False,
            "requires_environment_variable": False,
            "starts_bridge_on_install": False,
            "binds_lan_on_install": False,
            "advertises_bonjour_on_install": False,
            "creates_login_item_on_install": False,
            "mints_credentials_on_install": False,
            "invokes_private_adapter": False,
            "runtime_side_only": True,
        },
    }


def write_host_extension_starter_kit(*, runtime: str, output_dir: Path) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    output_root = Path(output_dir) / f"kaka-mobile-bridge-{runtime}"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "bin").mkdir(exist_ok=True)
    (output_root / "runtime-contracts").mkdir(exist_ok=True)

    kit = build_host_extension_starter_kit(
        runtime=runtime,
        output_dir=str(output_dir),
        written=True,
    )
    command_name = default_private_adapter_command_name(runtime)
    runtime_name = DISPLAY_NAMES[runtime]

    _write_text(output_root / "README.md", _readme(runtime_name=runtime_name, command_name=command_name))
    _write_json(output_root / "manifest.json", _starter_manifest(kit))
    _write_text(output_root / "bin" / f"{command_name}.README.md", _adapter_readme(runtime_name, command_name))
    _write_json(output_root / "runtime-contracts" / "settings-preview.command.json", _command(["settings-preview", "--runtime", runtime]))
    _write_json(output_root / "runtime-contracts" / "package-preview.command.json", _command(["package-preview", "--runtime", runtime]))
    _write_json(output_root / "runtime-contracts" / "host-package-preview.command.json", _command(["host-package-preview", "--runtime", runtime]))
    _write_json(output_root / "runtime-contracts" / "host-extension-readiness.command.json", _command(["host-extension-readiness", "--runtime", runtime]))
    _write_json(output_root / "runtime-contracts" / "start-bridge.command.json", _command(["start", "--runtime", runtime]))
    return kit


def _starter_manifest(kit: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "schema_version": kit["schema_version"],
        "runtime": kit["runtime"],
        "package": kit["package"],
        "ordinary_user_install": {
            "requires_manual_adapter_code": False,
            "requires_environment_variable": False,
            "requires_explicit_enable": True,
            "starts_bridge_on_install": False,
            "creates_login_item_on_install": False,
        },
        "adapter_command": kit["adapter_command"],
        "runtime_contracts": kit["runtime_contracts"],
        "phone_api": kit["phone_api"],
        "safety": kit["safety"],
    }


def _command(args: list[str]) -> Mapping[str, object]:
    return {
        "argv": ["python3", "-m", "kaka_mobile_runtime_kit", *args],
        "mutates_host": False,
        "requires_explicit_user_action_before_runtime_use": True,
    }


def _readme(*, runtime_name: str, command_name: str) -> str:
    return (
        f"# Pocket Agent Mobile Bridge For {runtime_name}\n\n"
        "This starter kit is a host-side packaging scaffold. It is not the final signed "
        "public package and it does not start Pocket Agent Mobile Bridge during installation.\n\n"
        "Ordinary-user flow:\n\n"
        "1. Install the host Plugin/Skill package from the host-owned channel.\n"
        "2. Open the host Pocket Agent Mobile Bridge settings surface.\n"
        "3. Enable the bridge explicitly.\n"
        "4. Show a short-lived QR or opt into Bonjour on a trusted LAN.\n"
        "5. Pair Pocket Agent iPhone through `/mobile/v1`.\n\n"
        f"The extension-internal adapter command is `{command_name}`. The host team owns "
        "the real implementation and signature for that command.\n"
    )


def _adapter_readme(runtime_name: str, command_name: str) -> str:
    return (
        f"# {command_name}\n\n"
        f"{runtime_name} owns this extension-internal command. Runtime Kit defines the "
        "stdin/stdout JSON contract and conformance checks, but this starter kit does "
        "not include proprietary host API code.\n"
    )


def _write_text(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported host extension runtime: {runtime}")
