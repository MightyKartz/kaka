from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from .cli import (
    BridgeConfig,
    build_runtime_host_package,
    build_runtime_package_manifest,
    build_runtime_package_preview_command,
    build_runtime_settings_preview_command,
    build_server_command,
)
from .host_adapter import build_host_adapter_action_result


SCHEMA_VERSION = "kaka.connection_qa_preview.v1"
SURFACE = "ordinary_user_connection_qa"
PHONE_API_PATH = "/mobile/v1"
P3_1_PRIVATE_CAPABILITIES_REQUIRED = (
    "distribution",
    "install",
    "login_item",
    "update",
    "uninstall",
    "logs",
    "health",
    "port_repair",
    "supervision",
)
FORBIDDEN_PHONE_SAFE_FIELDS = (
    "runtime_store_path",
    "recall_search_endpoint",
    "env_file",
    "auth_file",
    "auth_files",
    "provider_credentials",
    "provider_keys",
    "auth_env_files",
    "mobile_bearer_token",
    "mobile_tokens",
    "tls_private_key_path",
    "tls_private_key_paths",
    "hidden_prompt",
    "hidden_prompts",
    "raw_embeddings",
    "index_rows",
    "retrieval_index_rows",
    "task_logs",
    "raw_provider_responses",
    "process_ids",
    "host_log_paths",
)
_SENSITIVE_COMMAND_FLAGS = {
    "--repo-root",
    "--photo-pack-root",
    "--vision-endpoint",
    "--recall-search-endpoint",
    "--pairing-code",
    "--tls-private-key-path",
    "--hermes-home",
    "--hermes-profile",
    "--env-file",
    "--runtime-store-path",
}


def build_connection_qa_preview(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> Mapping[str, object]:
    package_manifest = build_runtime_package_manifest(config, bridge_enabled=bridge_enabled)
    host_package = build_runtime_host_package(config, bridge_enabled=bridge_enabled)
    settings_command = build_runtime_settings_preview_command(config, bridge_enabled=bridge_enabled)
    package_command = build_runtime_package_preview_command(config, bridge_enabled=bridge_enabled)
    server_command = build_server_command(config)
    health_check_result = build_host_adapter_action_result(
        host_package,
        action_id="run_health_check",
        approved=False,
        adapter_mode="mock",
    )
    disabled_action_result = _build_disabled_action_fixture_result(config, bridge_enabled=bridge_enabled)

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "summary": _build_summary(config, bridge_enabled=bridge_enabled),
        "first_run_steps": _build_first_run_steps(host_package, config, bridge_enabled=bridge_enabled),
        "failure_fixtures": _build_failure_fixtures(disabled_action_result),
        "readiness_report": _build_readiness_report(config),
        "safety": _build_safety(),
        "runtime_side_artifacts": {
            "runtime_side_only": True,
            "package_manifest": _manifest_ref(package_manifest),
            "host_package": _host_package_ref(host_package),
            "settings_preview_command": _command_ref(
                settings_command,
                command_name="settings-preview",
                artifact="settings_preview_command",
            ),
            "package_preview_command": _command_ref(
                package_command,
                command_name="package-preview",
                artifact="package_preview_command",
            ),
            "start_bridge_command": _command_ref(
                server_command,
                command_name="start_bridge",
                artifact="start_bridge_command",
            ),
            "mock_adapter_results": {
                "health_check": _adapter_result_ref(health_check_result),
                "disabled_host_action": _adapter_result_ref(disabled_action_result),
            },
        },
    }


def _build_summary(config: BridgeConfig, *, bridge_enabled: bool) -> Mapping[str, object]:
    return {
        "runtime": config.runtime,
        "phone_api_path": PHONE_API_PATH,
        "bridge_url": f"{config.scheme}://{config.advertised_host}:{config.port}{PHONE_API_PATH}",
        "pairing_mode": config.pairing_mode,
        "lan_discovery": _lan_discovery(config),
        "bonjour_status": _bonjour_status(config),
        "bridge_enabled": bool(bridge_enabled),
        "runtime_side_only": True,
        "private_api_called": False,
    }


def _build_first_run_steps(
    host_package: Mapping[str, object],
    config: BridgeConfig,
    *,
    bridge_enabled: bool,
) -> list[Mapping[str, object]]:
    production_pairing = config.pairing_mode == "production"
    bonjour_ready = config.bonjour and (config.lan or bool(config.bonjour_host))
    return [
        {
            "id": "package_preview",
            "title": "Review Runtime Kit package preview",
            "status": "ready",
            "owner": "runtime_kit",
            "requires_user_action": False,
            "command_ref": {
                "command": "package-preview",
                "artifact": "runtime_side_artifacts.package_preview_command",
                "runtime_side_only": True,
            },
        },
        {
            "id": "host_package_preview",
            "title": "Review Hermes/OpenClaw host package handoff",
            "status": "ready",
            "owner": "host_runtime",
            "requires_user_action": False,
            "command_ref": {
                "command": "host-package-preview",
                "artifact": "runtime_side_artifacts.host_package",
                "runtime_side_only": True,
            },
        },
        {
            "id": "install_runtime_package",
            "title": "Install Pocket Agent Mobile Bridge package",
            "status": "complete" if config.installed else "requires_user_approval",
            "owner": "host_runtime",
            "requires_user_action": not config.installed,
            "action_ref": _action_ref(host_package, "install_runtime_package"),
        },
        {
            "id": "enable_start_with_runtime",
            "title": "Enable host-managed start with runtime",
            "status": "configured" if config.start_with_runtime else "optional_user_approval",
            "owner": "host_runtime",
            "requires_user_action": not config.start_with_runtime,
            "action_ref": _action_ref(host_package, "enable_start_with_runtime"),
        },
        {
            "id": "start_bridge",
            "title": "Start Pocket Agent Mobile Bridge explicitly",
            "status": "running_preview" if bridge_enabled else "requires_user_action",
            "owner": "host_runtime",
            "requires_user_action": not bridge_enabled,
            "command_ref": {
                "command": "start_bridge",
                "artifact": "runtime_side_artifacts.start_bridge_command",
                "runtime_side_only": True,
            },
        },
        {
            "id": "production_qr_pairing",
            "title": "Pair iPhone with a production QR code",
            "status": "ready" if bridge_enabled and production_pairing else "requires_production_pairing",
            "owner": "phone",
            "requires_user_action": True,
            "phone_api_ref": "/mobile/v1/pairing/qr.html",
        },
        {
            "id": "bonjour_lan_discovery",
            "title": "Verify Bonjour/LAN discovery",
            "status": "ready" if bonjour_ready else "manual_endpoint_fallback",
            "owner": "phone",
            "requires_user_action": not bonjour_ready,
            "phone_state_hint": "bonjour_host_visible" if bonjour_ready else "manual_endpoint_entry",
        },
        {
            "id": "health_check",
            "title": "Run Mobile Bridge health check",
            "status": "ready" if bridge_enabled else "blocked_until_bridge_running",
            "owner": "host_runtime",
            "requires_user_action": not bridge_enabled,
            "phone_api_ref": "/mobile/v1/health",
            "action_ref": _action_ref(host_package, "run_health_check"),
        },
        {
            "id": "token_revocation",
            "title": "Revoke paired iPhone token",
            "status": "ready" if production_pairing else "requires_production_pairing",
            "owner": "host_runtime",
            "requires_user_action": True,
            "phone_api_ref": "/mobile/v1/pairing/revoke",
        },
        {
            "id": "saved_token_reconnect",
            "title": "Verify saved-token reconnect",
            "status": "ready" if bridge_enabled else "blocked_until_bridge_running",
            "owner": "phone",
            "requires_user_action": True,
            "phone_state_hint": "saved_mobile_token_reconnects_without_new_qr",
        },
    ]


def _build_failure_fixtures(
    disabled_action_result: Mapping[str, object],
) -> list[Mapping[str, object]]:
    disabled_code = _error_code(disabled_action_result, fallback="host_adapter_action_disabled")
    return [
        {
            "id": "expired_pairing_qr",
            "source": "mobile_bridge_pairing",
            "user_message": "This QR code expired. Generate a fresh production pairing QR on the host.",
            "recommended_action": "show_new_production_qr",
            "phone_state_hint": "pairing_qr_expired",
        },
        {
            "id": "revoked_mobile_token",
            "source": "mobile_bridge_auth",
            "user_message": "This iPhone token was revoked. Pair again with a new production QR code.",
            "recommended_action": "pair_with_new_qr",
            "phone_state_hint": "unauthorized",
        },
        {
            "id": "bridge_unavailable",
            "source": "mobile_bridge_process",
            "user_message": "Pocket Agent Mobile Bridge is not reachable. Start it from the host runtime.",
            "recommended_action": "start_bridge_on_host",
            "phone_state_hint": "offline",
        },
        {
            "id": "missing_bonjour_host",
            "source": "local_network_discovery",
            "user_message": "No Bonjour host is visible on the local network. Scan QR again or enter the endpoint manually.",
            "recommended_action": "verify_lan_bonjour_or_manual_endpoint",
            "phone_state_hint": "bonjour_host_missing",
        },
        {
            "id": "port_conflict",
            "source": "host_runtime_process",
            "user_message": "The bridge port is already in use. Repair the port from the host runtime.",
            "recommended_action": "repair_host_port_conflict",
            "phone_state_hint": "offline",
            "host_action_id": "repair_port_conflict",
        },
        {
            "id": "disabled_host_action",
            "source": "host_adapter",
            "user_message": "This host action is disabled until the runtime state changes.",
            "recommended_action": "complete_required_host_runtime_state",
            "phone_state_hint": "host_action_unavailable",
            "host_action_id": "enable_start_with_runtime",
            "adapter_error_code": disabled_code,
        },
        {
            "id": "missing_runtime_store_path",
            "source": "runtime_store",
            "user_message": "Runtime-owned Recall storage is not configured. Configure it on the host runtime.",
            "recommended_action": "configure_runtime_owned_store",
            "phone_state_hint": "runtime_memory_unavailable",
        },
        {
            "id": "private_host_adapter_unavailable",
            "source": "host_private_api",
            "user_message": "Private Hermes/OpenClaw host APIs are not wired in P3.0.",
            "recommended_action": "use_mock_adapter_until_p3_1_private_api",
            "phone_state_hint": "host_private_api_unavailable",
        },
    ]


def _build_readiness_report(config: BridgeConfig) -> Mapping[str, object]:
    runtime_ready = config.runtime in {"hermes", "openclaw"}
    return {
        "runtime": config.runtime,
        "p3_0_ready": runtime_ready,
        "runtime_qa_preview_ready": True,
        "runtime_package_preview_ready": True,
        "host_package_preview_ready": runtime_ready,
        "failure_fixtures_ready": True,
        "mock_adapter_preview_ready": True,
        "p3_1_private_api_ready": False,
        "p3_1_private_capabilities_required": list(P3_1_PRIVATE_CAPABILITIES_REQUIRED),
        "private_api_called": False,
        "mobile_bridge_api_changed": False,
        "phone_owned_host_settings": False,
        "boundary_notes": [
            "P3.0 previews ordinary-user connection QA without starting bridge processes.",
            "Host install, login-item, update, uninstall, logs, health, port repair, and supervision remain host-owned.",
            "Real Hermes/OpenClaw private host adapter APIs remain a P3.1 dependency.",
        ],
    }


def _build_safety() -> Mapping[str, object]:
    return {
        "forbidden_phone_safe_fields": list(FORBIDDEN_PHONE_SAFE_FIELDS),
        "phone_safe_sections": [
            "summary",
            "first_run_steps",
            "failure_fixtures",
            "readiness_report",
            "safety",
        ],
        "does_not_start_processes": True,
        "does_not_mutate_host_os": True,
        "phone_api_unchanged": True,
        "mock_adapter_only": True,
        "private_api_called": False,
        "runtime_side_artifacts_only": True,
    }


def _build_disabled_action_fixture_result(
    config: BridgeConfig,
    *,
    bridge_enabled: bool,
) -> Mapping[str, object]:
    disabled_config = replace(config, installed=False, start_with_runtime=False)
    disabled_package = build_runtime_host_package(disabled_config, bridge_enabled=bridge_enabled)
    return build_host_adapter_action_result(
        disabled_package,
        action_id="enable_start_with_runtime",
        approved=True,
        adapter_mode="mock",
    )


def _action_ref(host_package: Mapping[str, object], action_id: str) -> Mapping[str, object]:
    action = _host_action_by_id(host_package, action_id)
    return {
        "action_id": action_id,
        "adapter": str(action.get("adapter", "")),
        "enabled": bool(action.get("enabled", False)),
        "requires_explicit_user_approval": bool(action.get("requires_explicit_user_approval", False)),
        "runtime_side_only": True,
    }


def _host_action_by_id(host_package: Mapping[str, object], action_id: str) -> Mapping[str, object]:
    actions = host_package.get("host_actions", [])
    if not isinstance(actions, list):
        return {}
    for action in actions:
        if isinstance(action, Mapping) and action.get("id") == action_id:
            return action
    return {}


def _manifest_ref(package_manifest: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "schema_version": str(package_manifest.get("schema_version", "")),
        "surface": str(package_manifest.get("surface", "")),
        "runtime": str(package_manifest.get("runtime", "")),
        "install": dict(package_manifest.get("install", {})),
        "runtime_side_only": True,
    }


def _host_package_ref(host_package: Mapping[str, object]) -> Mapping[str, object]:
    host_actions = host_package.get("host_actions", [])
    action_ids: list[str] = []
    if isinstance(host_actions, list):
        action_ids = [
            str(action.get("id", ""))
            for action in host_actions
            if isinstance(action, Mapping)
        ]
    return {
        "schema_version": str(host_package.get("schema_version", "")),
        "surface": str(host_package.get("surface", "")),
        "runtime": str(host_package.get("runtime", "")),
        "host_api_level": str(host_package.get("host_api_level", "")),
        "host_action_ids": action_ids,
        "runtime_side_only": True,
    }


def _command_ref(
    command: Sequence[object],
    *,
    command_name: str,
    artifact: str,
) -> Mapping[str, object]:
    return {
        "command": command_name,
        "artifact": artifact,
        "argv_preview": _redacted_command(command),
        "runtime_side_only": True,
    }


def _adapter_result_ref(result: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "schema_version": str(result.get("schema_version", "")),
        "surface": str(result.get("surface", "")),
        "action_id": str(result.get("action_id", "")),
        "adapter_mode": str(result.get("adapter_mode", "")),
        "ok": bool(result.get("ok", False)),
        "mutated_host_state": bool(result.get("mutated_host_state", False)),
        "private_api_called": False,
        "error_code": _error_code(result, fallback=None),
        "runtime_side_only": True,
    }


def _error_code(result: Mapping[str, object], *, fallback: str | None) -> str | None:
    error = result.get("error", {})
    if isinstance(error, Mapping) and error.get("code"):
        return str(error["code"])
    return fallback


def _redacted_command(command: Sequence[object]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for index, raw_part in enumerate(command):
        part = str(raw_part)
        if index == 0:
            redacted.append("<python>")
            continue
        if redact_next:
            redacted.append("<runtime-side-only>")
            redact_next = False
            continue
        redacted.append(part)
        if part in _SENSITIVE_COMMAND_FLAGS:
            redact_next = True
    return redacted


def _lan_discovery(config: BridgeConfig) -> str:
    if config.bonjour:
        return "bonjour"
    if config.lan:
        return "lan"
    return "manual_endpoint"


def _bonjour_status(config: BridgeConfig) -> str:
    if config.bonjour and (config.lan or config.bonjour_host):
        return "advertised_preview"
    if config.bonjour:
        return "blocked_missing_reachable_host"
    return "not_advertised"
