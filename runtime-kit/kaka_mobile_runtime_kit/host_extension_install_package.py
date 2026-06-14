from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .host_extension_starter_kit import build_host_extension_starter_kit
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
)


SCHEMA_VERSION = "kaka.host_extension_install_package.v1"
SURFACE = "hermes_openclaw_host_extension_install_package"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")
DISPLAY_NAMES = {"hermes": "Hermes", "openclaw": "OpenClaw"}
INSTALL_SHAPES = {"hermes": "hermes_plugin", "openclaw": "openclaw_skill"}
ENTRYPOINT_LABELS = {
    "hermes": "Hermes Plugin: Pocket Agent Mobile Bridge",
    "openclaw": "OpenClaw Skill: Pocket Agent Mobile Bridge",
}
HOST_UI_FORBIDDEN_PHONE_FIELDS = [
    "provider_keys",
    "private_adapter_command_path",
    "runtime_store_path",
    "tls_private_key_path",
    "bearer_tokens",
    "mobile_tokens",
    "raw_logs",
    "embeddings",
]
INSTALL_DRILL_ORDERED_STEPS = [
    "install_host_extension",
    "verify_disabled_after_install",
    "enable_bridge",
    "verify_loopback_default",
    "check_tls_readiness",
    "show_short_lived_qr",
    "pair_iphone_mobile_v1",
    "opt_in_bonjour_on_trusted_lan",
    "run_health_check",
    "revoke_and_repair",
    "run_update_drill",
    "run_failure_recovery_drill",
    "open_redacted_logs",
    "uninstall_and_verify_cleanup",
    "archive_release_evidence",
]
INSTALL_DRILL_EVIDENCE_RECEIPTS = [
    "install_receipt_ref",
    "update_receipt_ref",
    "failure_recovery_receipt_ref",
    "log_redaction_review_ref",
    "uninstall_receipt_ref",
    "evidence_manifest_ref",
]
ORDINARY_USER_QUICKSTART_STEPS = [
    "install_host_extension_from_host_channel",
    "open_kaka_mobile_bridge_panel",
    "verify_installed_disabled",
    "enable_bridge_explicitly",
    "pair_with_short_lived_qr_or_bonjour_opt_in",
    "run_health_check",
]
ORDINARY_USER_NEVER_ASK = [
    "write_adapter_code",
    "set_private_adapter_command",
    "export_host_api_environment_variable",
    "paste_runtime_kit_command_chain",
    "install_codex_plugin_or_skill",
]
INSTALLATION_BLUEPRINT_SCHEMA_VERSION = "kaka.host_extension_installation_blueprint.v1"
INSTALLATION_BLUEPRINT_SURFACE = "hermes_openclaw_host_extension_installation_blueprint"
INSTALLATION_BLUEPRINT_STATES = [
    "installed_disabled",
    "enabled_stopped",
    "running_loopback",
    "pairing_qr_visible",
    "trusted_lan_bonjour_opted_in",
    "unhealthy_needs_repair",
    "revoked_needs_repair",
    "update_available",
]
INSTALLATION_BLUEPRINT_CONTROLS = [
    "enable_bridge",
    "start_bridge",
    "stop_bridge",
    "show_qr",
    "toggle_bonjour",
    "show_tls_readiness",
    "run_health_check",
    "revoke_iphone",
    "repair_port_conflict",
    "open_redacted_logs",
    "update_extension",
    "uninstall_extension",
]
INSTALLATION_BLUEPRINT_RECEIPTS = [
    "install_receipt_ref",
    "enable_receipt_ref",
    "pairing_receipt_ref",
    "health_receipt_ref",
    "revoke_repair_receipt_ref",
    "update_receipt_ref",
    "failure_recovery_receipt_ref",
    "log_redaction_review_ref",
    "uninstall_receipt_ref",
    "evidence_manifest_ref",
]
INSTALLATION_BLUEPRINT_EVIDENCE_GATES = [
    "p3_2_host_private_adapter_conformance",
    "p3_4_host_shell_pilot_evidence_manifest",
    "p3_6_host_extension_readiness",
    "local_tls_readiness",
    "p3_28_host_extension_material_intake",
    "p3_7_external_install_drill",
]


def build_host_extension_install_package(
    *,
    runtime: str,
    output_dir: str = "",
    written: bool = False,
) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    starter = build_host_extension_starter_kit(runtime=runtime)
    command_name = default_private_adapter_command_name(runtime)
    environment_variable = private_adapter_environment_variable(runtime)
    root_name = f"kaka-mobile-bridge-{runtime}-install-package"
    output_root = str(Path(output_dir) / root_name) if str(output_dir).strip() else ""

    generated_files = [
        {"path": "README.md", "kind": "host_operator_readme"},
        {"path": f"bin/{command_name}.README.md", "kind": "private_adapter_stub_readme"},
        {"path": "host-ui/kaka-mobile-bridge-panel.json", "kind": "host_ui_contract"},
        {"path": "host-ui/acceptance.json", "kind": "host_ui_acceptance"},
        {"path": "host-ui/installation-blueprint.json", "kind": "installation_blueprint"},
        {"path": "host-ui/user-quickstart.md", "kind": "ordinary_user_quickstart"},
        {"path": "install-drill/runbook.json", "kind": "install_drill_runbook"},
        {"path": "install-drill/user-journey.json", "kind": "ordinary_user_journey"},
        {
            "path": "release-gates/host-extension-readiness.command.json",
            "kind": "release_gate_command",
        },
        {
            "path": "release-gates/host-private-adapter-conformance.command.json",
            "kind": "release_gate_command",
        },
        {
            "path": "release-gates/local-tls-readiness.command.json",
            "kind": "release_gate_command",
        },
        {
            "path": "release-gates/host-shell-pilot-evidence-manifest.command.json",
            "kind": "release_gate_command",
        },
        {
            "path": "release-gates/host-codex-developer-plugin-source.command.json",
            "kind": "release_gate_command",
        },
    ]
    if runtime == "hermes":
        generated_files.append(
            {"path": "hermes-plugin/kaka-mobile-bridge.package.json", "kind": "host_manifest"}
        )
    else:
        generated_files.extend(
            [
                {"path": "openclaw-skill/SKILL.md", "kind": "host_skill"},
                {"path": "openclaw-skill/kaka-mobile-bridge.sidecar.json", "kind": "host_manifest"},
            ]
        )

    package = {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "written": written,
        "output_root": output_root,
        "package": {
            "install_shape": INSTALL_SHAPES[runtime],
            "ordinary_user_entrypoint": ENTRYPOINT_LABELS[runtime],
            "stable_package_owner": "host_shell",
            "handoff_owner": "kaka_runtime_kit",
            "final_distribution_requires_host_signature": True,
        },
        "generated_files": generated_files,
        "adapter_command": {
            "default_command_name": command_name,
            "visibility": "extension_internal",
            "developer_fallback_only": True,
            "environment_variable": environment_variable,
            "implementation_owner": "host_shell",
            "handoff_contains_proprietary_implementation": False,
        },
        "host_ui": {
            "panel_id": "kaka_mobile_bridge",
            "required_actions": [
                "enable_bridge",
                "show_qr",
                "toggle_bonjour",
                "show_tls_readiness",
                "run_health_check",
                "revoke_iphone",
                "repair_port_conflict",
                "show_failure_recovery",
                "update_extension",
                "uninstall_extension",
                "open_logs",
            ],
            "runtime_settings_owner": "host_shell",
            "acceptance": {
                "initial_state_after_install": "installed_disabled",
                "requires_explicit_enable": True,
                "default_bind_mode": "loopback",
                "lan_bonjour_requires_visible_opt_in": True,
                "pairing_methods": ["short_lived_qr", "bonjour_opt_in"],
                "must_not_expose_to_phone": list(HOST_UI_FORBIDDEN_PHONE_FIELDS),
            },
        },
        "install_drill": {
            "must_verify": [
                "install_does_not_start_bridge",
                "explicit_enable_required",
                "loopback_default_until_user_opts_into_lan",
                "tls_readiness_checked_before_trusted_lan_pairing",
                "bonjour_requires_visible_opt_in",
                "pairing_uses_mobile_v1",
                "health_check_keeps_adapter_internal",
                "revoke_old_token_then_repair",
                "update_drill_has_host_owned_evidence",
                "failure_recovery_drill_has_host_owned_evidence",
                "logs_are_redacted",
                "uninstall_stops_bridge_and_cleans_mobile_token",
            ],
            "ordered_steps": list(INSTALL_DRILL_ORDERED_STEPS),
            "evidence_receipts": list(INSTALL_DRILL_EVIDENCE_RECEIPTS),
        },
        "release_gates": {
            "requires_host_signature": True,
            "requires_conformance_report": True,
            "requires_evidence_manifest": True,
            "requires_host_ui_acceptance": True,
            "requires_install_drill_runbook": True,
            "requires_tls_readiness": True,
            "requires_host_extension_readiness": True,
            "requires_codex_developer_plugin_source": True,
            "can_mark_p3_4_complete": False,
        },
        "runtime_contracts": starter["runtime_contracts"],
        "ordinary_user_flow": starter["ordinary_user_flow"],
        "ordinary_user_quickstart": {
            "surface": "host_native_plugin_or_skill",
            "audience": "ordinary_user",
            "runtime_label": DISPLAY_NAMES[runtime],
            "entrypoint": ENTRYPOINT_LABELS[runtime],
            "phone_api_path": "/mobile/v1",
            "steps": list(ORDINARY_USER_QUICKSTART_STEPS),
            "user_copy": [
                f"Install Pocket Agent Mobile Bridge from the {DISPLAY_NAMES[runtime]} extension channel.",
                f"Open {ENTRYPOINT_LABELS[runtime]}.",
                "Confirm the bridge is installed but disabled after install.",
                "Enable Pocket Agent Mobile Bridge when you are ready to pair.",
                "Scan the short-lived QR code with Pocket Agent iPhone.",
                "Use Bonjour only after opting into trusted LAN discovery.",
                "Run the host health check if pairing does not complete.",
                "Pocket Agent iPhone connects through /mobile/v1 only.",
            ],
            "never_ask_user_to": list(ORDINARY_USER_NEVER_ASK),
        },
        "phone_api": starter["phone_api"],
        "readiness_inputs": starter["readiness_inputs"],
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
    package["installation_blueprint"] = _installation_blueprint(
        runtime=runtime,
        package=package,
        command_name=command_name,
        environment_variable=environment_variable,
    )
    return package


def _installation_blueprint(
    *,
    runtime: str,
    package: Mapping[str, object],
    command_name: str,
    environment_variable: str,
) -> Mapping[str, object]:
    manifest_paths = (
        ["hermes-plugin/kaka-mobile-bridge.package.json"]
        if runtime == "hermes"
        else [
            "openclaw-skill/SKILL.md",
            "openclaw-skill/kaka-mobile-bridge.sidecar.json",
        ]
    )
    return {
        "schema_version": INSTALLATION_BLUEPRINT_SCHEMA_VERSION,
        "surface": INSTALLATION_BLUEPRINT_SURFACE,
        "runtime": runtime,
        "package_manifest": {
            "install_shape": INSTALL_SHAPES[runtime],
            "ordinary_user_entrypoint": ENTRYPOINT_LABELS[runtime],
            "host_package_owner": "host_shell",
            "handoff_owner": "kaka_runtime_kit",
            "disabled_by_default": True,
            "requires_host_signature": True,
            "manifest_paths": manifest_paths,
        },
        "host_ui": {
            "panel_id": "kaka_mobile_bridge",
            "states": list(INSTALLATION_BLUEPRINT_STATES),
            "required_controls": list(INSTALLATION_BLUEPRINT_CONTROLS),
            "default_state_after_install": "installed_disabled",
            "requires_explicit_enable": True,
            "loopback_default": True,
            "trusted_lan_requires_visible_opt_in": True,
            "bonjour_requires_visible_opt_in": True,
            "must_not_expose_to_phone": list(HOST_UI_FORBIDDEN_PHONE_FIELDS),
        },
        "lifecycle_receipts": {
            "required_refs": list(INSTALLATION_BLUEPRINT_RECEIPTS),
            "receipt_values_must_not_contain_secrets": True,
        },
        "evidence_gates": {
            "required_gates": list(INSTALLATION_BLUEPRINT_EVIDENCE_GATES),
            "requires_material_intake_acceptance": True,
            "requires_external_install_drill": True,
            "can_mark_p3_7_ready_without_host_materials": False,
        },
        "adapter_command": {
            "default_command_name": command_name,
            "visibility": "extension_internal",
            "implementation_owner": "host_shell",
            "environment_variable": environment_variable,
            "developer_fallback_only": True,
            "blueprint_contains_proprietary_implementation": False,
        },
        "codex_automation_boundary": {
            "audience": "host_engineers",
            "source_only": True,
            "ordinary_user_installs_codex": False,
            "writes_user_home": False,
            "updates_marketplace": False,
        },
        "ordinary_user_story": package["ordinary_user_quickstart"],
        "phone_api": package["phone_api"],
        "side_effects": {
            "installs_package": False,
            "signs_package": False,
            "publishes_package": False,
            "starts_bridge": False,
            "binds_lan": False,
            "advertises_bonjour": False,
            "creates_login_item": False,
            "mints_tokens": False,
            "invokes_private_adapter": False,
            "writes_codex_user_home": False,
            "changes_mobile_bridge_api": False,
        },
    }


def write_host_extension_install_package(*, runtime: str, output_dir: Path) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    root = Path(output_dir) / f"kaka-mobile-bridge-{runtime}-install-package"
    for child in ("bin", "host-ui", "install-drill", "release-gates"):
        (root / child).mkdir(parents=True, exist_ok=True)
    if runtime == "hermes":
        (root / "hermes-plugin").mkdir(parents=True, exist_ok=True)
    else:
        (root / "openclaw-skill").mkdir(parents=True, exist_ok=True)

    package = build_host_extension_install_package(
        runtime=runtime,
        output_dir=str(output_dir),
        written=True,
    )
    command_name = default_private_adapter_command_name(runtime)
    display_name = DISPLAY_NAMES[runtime]

    _write_text(root / "README.md", _operator_readme(display_name))
    _write_text(root / "bin" / f"{command_name}.README.md", _adapter_readme(display_name, command_name))
    _write_json(root / "host-ui" / "kaka-mobile-bridge-panel.json", package["host_ui"])
    _write_json(root / "host-ui" / "acceptance.json", package["host_ui"]["acceptance"])
    _write_json(root / "host-ui" / "installation-blueprint.json", package["installation_blueprint"])
    _write_text(
        root / "host-ui" / "user-quickstart.md",
        _user_quickstart_markdown(package["ordinary_user_quickstart"]),
    )
    _write_json(root / "install-drill" / "runbook.json", package["install_drill"])
    _write_json(root / "install-drill" / "user-journey.json", package["ordinary_user_quickstart"])
    _write_json(
        root / "release-gates" / "host-extension-readiness.command.json",
        _command(["host-extension-readiness", "--runtime", runtime]),
    )
    _write_json(
        root / "release-gates" / "host-private-adapter-conformance.command.json",
        _command(["host-private-adapter-conformance", "--runtime", runtime]),
    )
    _write_json(
        root / "release-gates" / "local-tls-readiness.command.json",
        _command(["local-tls-readiness", "--runtime", runtime]),
    )
    _write_json(
        root / "release-gates" / "host-shell-pilot-evidence-manifest.command.json",
        _command(["host-shell-pilot-evidence-manifest", "--runtime", runtime]),
    )
    _write_json(
        root / "release-gates" / "host-codex-developer-plugin-source.command.json",
        _command(["host-codex-developer-plugin-source", "--runtime", runtime]),
    )

    if runtime == "hermes":
        _write_json(root / "hermes-plugin" / "kaka-mobile-bridge.package.json", _host_manifest(package))
    else:
        _write_text(root / "openclaw-skill" / "SKILL.md", _openclaw_skill(command_name))
        _write_json(root / "openclaw-skill" / "kaka-mobile-bridge.sidecar.json", _host_manifest(package))

    return package


def _host_manifest(package: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "schema_version": package["schema_version"],
        "runtime": package["runtime"],
        "package": package["package"],
        "adapter_command": package["adapter_command"],
        "host_ui": package["host_ui"],
        "install_drill": package["install_drill"],
        "ordinary_user_quickstart": package["ordinary_user_quickstart"],
        "installation_blueprint": package["installation_blueprint"],
        "release_gates": package["release_gates"],
        "phone_api": package["phone_api"],
        "safety": package["safety"],
    }


def _operator_readme(runtime_name: str) -> str:
    return (
        f"# Pocket Agent Mobile Bridge For {runtime_name}\n\n"
        "This package handoff is for the host team. It is not a signed public release.\n\n"
        "Ordinary users install the host extension, open the Pocket Agent Mobile Bridge panel, "
        "enable the bridge explicitly, show QR or opt into Bonjour, and pair Pocket Agent iPhone "
        "through `/mobile/v1`.\n\n"
        "Host teams own signing, update channels, release notes, conformance evidence, "
        "and the extension-internal private adapter implementation.\n"
    )


def _openclaw_skill(command_name: str) -> str:
    return (
        "---\n"
        "name: kaka-mobile-bridge\n"
        "description: Connect Pocket Agent iPhone to OpenClaw through a local Mobile Bridge "
        "after explicit user approval.\n"
        "---\n\n"
        "# Pocket Agent Mobile Bridge\n\n"
        "Use this skill when the user asks OpenClaw to connect Pocket Agent, show a pairing QR, "
        "or start the local Pocket Agent Mobile Bridge.\n\n"
        "Safety rules:\n\n"
        "- Do not start a listener during skill installation.\n"
        "- Require explicit approval for LAN bind and Bonjour advertisement.\n"
        "- Keep provider credentials inside OpenClaw or its sidecar.\n"
        "- Use a short-lived pairing QR and revocable mobile token.\n"
        "- Keep host lifecycle actions in the OpenClaw UI.\n"
        f"- Treat `{command_name}` as an extension-internal host-owned command.\n"
        "- Keep Pocket Agent iPhone on `/mobile/v1` only.\n"
    )


def _adapter_readme(runtime_name: str, command_name: str) -> str:
    return (
        f"# {command_name}\n\n"
        f"{runtime_name} owns this extension-internal command. Runtime Kit defines "
        "the stdin/stdout JSON contract and conformance checks, but this handoff "
        "does not include proprietary host API code.\n"
    )


def _user_quickstart_markdown(quickstart: Mapping[str, object]) -> str:
    lines = [
        f"# Pocket Agent Mobile Bridge {quickstart['runtime_label']} Quickstart",
        "",
        "This quickstart is for ordinary users installing the host-native Pocket Agent Mobile Bridge extension.",
        "",
        "## Steps",
        "",
    ]
    for index, sentence in enumerate(quickstart["user_copy"], start=1):
        display_sentence = str(sentence).replace("/mobile/v1", "`/mobile/v1`")
        lines.append(f"{index}. {display_sentence}")
    lines.extend(
        [
            "",
            "## Never Required",
            "",
        ]
    )
    for item in quickstart["never_ask_user_to"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _command(args: list[str]) -> Mapping[str, object]:
    return {
        "argv": ["python3", "-m", "kaka_mobile_runtime_kit", *args],
        "mutates_host": False,
        "requires_explicit_user_action_before_runtime_use": True,
    }


def _write_text(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported host extension runtime: {runtime}")
