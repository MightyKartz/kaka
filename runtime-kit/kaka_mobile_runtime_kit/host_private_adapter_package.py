from __future__ import annotations

from typing import Mapping

from .host_adapter import HOST_ADAPTER_ACTIONS, HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS


SCHEMA_VERSION = "kaka.host_private_adapter_package.v1"
SURFACE = "hermes_openclaw_host_private_adapter_package"
SUPPORTED_RUNTIMES = ("hermes", "openclaw")


def default_private_adapter_command_name(runtime: str) -> str:
    _require_supported_runtime(runtime)
    return f"{runtime}-kaka-host-api"


def private_adapter_environment_variable(runtime: str) -> str:
    if runtime == "hermes":
        return "HERMES_KAKA_HOST_API"
    if runtime == "openclaw":
        return "OPENCLAW_KAKA_HOST_API"
    raise ValueError(f"Unsupported private adapter package runtime: {runtime}")


def private_adapter_well_known_paths(runtime: str, command_name: str) -> list[str]:
    display_name = _runtime_display_name(runtime)
    return [f"~/Library/Application Support/{display_name}/Kaka/{command_name}"]


def conformance_command(runtime: str) -> list[str]:
    _require_supported_runtime(runtime)
    return [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-private-adapter-conformance",
        "--runtime",
        runtime,
        "--private-adapter-command",
        "<host-owned-private-adapter-command>",
    ]


def build_host_private_adapter_package(
    config,
    *,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    command_name: str | None = None,
) -> Mapping[str, object]:
    from .host_private_adapter_conformance import REQUIRED_CAPABILITIES

    runtime = str(config.runtime)
    resolved_command_name = command_name or default_private_adapter_command_name(runtime)
    _require_supported_runtime(runtime)
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "binary": {
            "owner": "host_shell",
            "repository_owner": "hermes_or_openclaw",
            "private_api_implementation": "not_bundled_in_kaka",
            "default_command_name": resolved_command_name,
        },
        "distribution": {
            "source": distribution_source,
            "channel": distribution_channel,
            "version": package_version,
            "update_policy": "explicit_user_approved",
            "download_owner": "host_shell",
            "signature_policy": "host_shell_required",
        },
        "discovery": {
            "config_key": "private_adapter_command",
            "environment_variable": private_adapter_environment_variable(runtime),
            "manifest_entrypoint": "host_private_adapter.command",
            "well_known_paths": private_adapter_well_known_paths(
                runtime,
                resolved_command_name,
            ),
        },
        "validation": {
            "requires_conformance_passed": True,
            "report_schema": "kaka.host_private_adapter_conformance.v1",
            "conformance_command": conformance_command(runtime),
        },
        "required_action_ids": list(HOST_ADAPTER_ACTIONS),
        "required_capabilities": list(REQUIRED_CAPABILITIES),
        "mobile_bridge": {
            "phone_api_path": "/mobile/v1",
            "phone_api_unchanged": True,
        },
        "safety": {
            "runtime_side_only": True,
            "phone_settings_owner": False,
            "forbidden_phone_safe_fields": list(HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS),
        },
    }


def _runtime_display_name(runtime: str) -> str:
    if runtime == "hermes":
        return "Hermes"
    if runtime == "openclaw":
        return "OpenClaw"
    raise ValueError(f"Unsupported private adapter package runtime: {runtime}")


def _require_supported_runtime(runtime: str) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported private adapter package runtime: {runtime}")
