from __future__ import annotations

from typing import Mapping

from .host_adapter import HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
    private_adapter_well_known_paths,
)


SCHEMA_VERSION = "kaka.host_extension_preview.v1"
SURFACE = "hermes_openclaw_host_extension_preview"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")

INSTALL_SHAPES = {
    "hermes": "hermes_plugin",
    "openclaw": "openclaw_skill",
}


def build_host_extension_preview(runtime: str) -> Mapping[str, object]:
    _require_supported_runtime(runtime)
    command_name = default_private_adapter_command_name(runtime)
    environment_variable = private_adapter_environment_variable(runtime)
    well_known_paths = private_adapter_well_known_paths(runtime, command_name)

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ordinary_user_install": {
            "install_shape": INSTALL_SHAPES[runtime],
            "requires_manual_adapter_code": False,
            "requires_environment_variable": False,
            "starts_bridge_on_install": False,
            "creates_login_item_on_install": False,
            "requires_explicit_enable": True,
        },
        "extension_package": {
            "owner": "host_shell",
            "adapter_command_owner": "host_shell",
            "adapter_command_packaging": "bundled_or_host_discovered",
            "stable_distribution_requires_host_signature": True,
        },
        "adapter_command": {
            "default_command_name": command_name,
            "visibility": "extension_internal",
            "developer_fallback_only": True,
            "environment_variable": environment_variable,
            "discovery_sources": [
                "extension_internal_bundle",
                "host_extension_config",
                "manifest_entrypoint",
                "well_known_path",
                "environment_variable_developer_fallback",
                "explicit_command_developer_fallback",
            ],
            "manifest_entrypoint": "host_private_adapter.command",
            "well_known_paths": well_known_paths,
        },
        "runtime_contracts": {
            "settings_preview": "settings-preview",
            "package_preview": "package-preview",
            "host_package_preview": "host-package-preview",
            "consumer_ui": "settings_preview.runtime_side_ui.consumer_ui",
            "process_ownership": "settings_preview.runtime_side_ui.process_ownership",
            "private_adapter_package": "host_package.private_adapter_package",
        },
        "pairing_ux": {
            "enable_bridge": True,
            "show_qr": True,
            "bonjour_optional": True,
            "revoke_iphone": True,
            "saved_token_reconnect": True,
            "production_qr_recommended": True,
        },
        "phone_api": {
            "base_path": "/mobile/v1",
            "private_host_api_exposed": False,
            "phone_api_unchanged": True,
        },
        "release_gates": {
            "requires_p3_2_conformance": True,
            "requires_p3_4_external_pilot_evidence": True,
            "requires_host_signature": True,
            "can_mark_p3_4_complete": False,
        },
        "safety": {
            "runtime_side_only": True,
            "phone_settings_owner": False,
            "no_autostart_on_install": True,
            "no_lan_bind_on_install": True,
            "no_bonjour_on_install": True,
            "no_credentials_minted_on_install": True,
            "no_login_item_creation_on_install": True,
            "forbidden_phone_safe_fields": list(HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS),
        },
    }


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported host extension runtime: {runtime}")
