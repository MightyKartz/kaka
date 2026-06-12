from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlsplit

from .host_adapter import (
    HOST_ADAPTER_ACTIONS,
    HOST_ADAPTER_ACTION_ADAPTERS,
    HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS,
    HOST_ADAPTER_MUTATING_ACTIONS,
    build_host_adapter_action_result,
)
from .host_extension_preview import build_host_extension_preview
from .host_extension_readiness import build_host_extension_readiness
from .host_extension_install_package import (
    build_host_extension_install_package,
    write_host_extension_install_package,
)
from .host_extension_starter_kit import (
    build_host_extension_starter_kit,
    write_host_extension_starter_kit,
)
from .host_plugin_skill_devkit import (
    build_host_plugin_skill_devkit,
    write_host_plugin_skill_devkit,
)
from .host_codex_developer_plugin_source import (
    build_host_codex_developer_plugin_source,
    write_host_codex_developer_plugin_source,
)
from .host_private_adapter_package import build_host_private_adapter_package
from .local_tls_readiness import build_local_tls_readiness
from .recall_retrieval_readiness import (
    RECALL_RETRIEVAL_STRATEGIES,
    build_recall_retrieval_readiness,
)
from .retention_purge import build_runtime_retention_purge_receipt
from .runtime_store import SQLiteRuntimeStore


DEFAULT_PORT = 8765
DEFAULT_PHOTO_PROVIDER = "recipe_local"
DEFAULT_BONJOUR_NAME = "Kaka Mobile Bridge"
DEFAULT_INPUT_ASSETS_DAYS = 7
DEFAULT_OUTPUT_ASSETS_DAYS = 30
DEFAULT_TASK_HISTORY_DAYS = 30
RETENTION_MIN_DAYS = 1
RETENTION_MAX_DAYS = 3650
PROVIDER_CHOICES = ("fixture", "script", "recipe_local", "openai")
INTELLIGENCE_PROVIDER_CHOICES = ("fake", "anthropic")
VISION_PROVIDER_CHOICES = ("fixture", "runtime_http")
RECALL_SEARCH_PROVIDER_CHOICES = ("local", "fixture", "runtime_http")
PAIRING_MODE_CHOICES = ("development", "production")
PROCESS_STATE_CHOICES = ("stopped", "running", "unhealthy", "unknown")
PROCESS_SUPERVISION_CHOICES = ("not_configured", "host_managed", "misconfigured")
HEALTH_STATUS_CHOICES = ("unknown", "healthy", "unhealthy")
DISTRIBUTION_SOURCE_CHOICES = (
    "local_checkout",
    "signed_download",
    "host_store",
    "enterprise_distribution",
)
HOST_PACKAGE_RUNTIME_CHOICES = ("hermes", "openclaw")
HOST_PACKAGE_ACTIONS = HOST_ADAPTER_ACTIONS
HOST_PACKAGE_ACTION_ADAPTERS = HOST_ADAPTER_ACTION_ADAPTERS
HOST_PACKAGE_FORBIDDEN_PHONE_SAFE_FIELDS = HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS
RUNTIME_SIDE_VALUES = (
    "runtime_store_path",
    "recall_search_endpoint",
    "env_file",
    "auth_file",
    "auth_files",
    "provider_credentials",
    "mobile_bearer_token",
    "tls_certificate_chain_path",
    "tls_private_key_path",
    "hidden_prompt",
    "hidden_prompts",
)
FORBIDDEN_PHONE_SAFE_FIELDS = (
    "runtime_store_path",
    "recall_search_endpoint",
    "env_file",
    "auth_file",
    "auth_files",
    "provider_credentials",
    "mobile_bearer_token",
    "tls_certificate_chain_path",
    "tls_private_key_path",
    "hidden_prompt",
    "hidden_prompts",
    "raw_embeddings",
    "retrieval_index_rows",
    "raw_provider_responses",
)


@dataclass(frozen=True)
class BridgeConfig:
    repo_root: Path = Path(".")
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    lan: bool = False
    bonjour: bool = False
    bonjour_host: str = ""
    bonjour_name: str = DEFAULT_BONJOUR_NAME
    pairing_code: str = "pair_dev"
    runtime: str = "hermes"
    provider: str = "fake"
    installed: bool = False
    start_with_runtime: bool = False
    process_state: str = "stopped"
    process_supervision: str = "not_configured"
    health_status: str = "unknown"
    port_conflict: bool = False
    photo_provider: str = DEFAULT_PHOTO_PROVIDER
    photo_pack_root: str = "photo-pack"
    vision_provider: str = "fixture"
    vision_endpoint: str = ""
    recall_search_provider: str = "local"
    recall_search_endpoint: str = ""
    pairing_mode: str = "development"
    pairing_code_ttl_seconds: int = 120
    token_ttl_seconds: int = 0
    trusted_local_tls: bool = False
    tls_trust_state: str = "not_configured"
    tls_certificate_label: str = ""
    tls_public_key_sha256: str = ""
    tls_certificate_chain_path: str = ""
    tls_private_key_path: str = ""
    hermes_home: str = ""
    hermes_profile: str = ""
    env_file: str = ""
    runtime_store_path: str = ""
    input_assets_days: int = DEFAULT_INPUT_ASSETS_DAYS
    output_assets_days: int = DEFAULT_OUTPUT_ASSETS_DAYS
    task_history_days: int = DEFAULT_TASK_HISTORY_DAYS

    @property
    def bind_host(self) -> str:
        return "0.0.0.0" if self.lan else self.host

    @property
    def advertised_host(self) -> str:
        if self.bonjour_host:
            return self.bonjour_host
        if self.lan:
            return "<mac-lan-ip>"
        return self.host

    @property
    def scheme(self) -> str:
        return "https" if self.trusted_local_tls else "http"


def build_server_command(config: BridgeConfig) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "agent_pocket_mock_bridge.server",
        "--host",
        config.bind_host,
        "--port",
        str(config.port),
        "--runtime",
        config.runtime,
    ]
    if config.provider != "fake":
        command.extend(["--provider", config.provider])
    command.extend([
        "--photo-provider",
        config.photo_provider,
        "--photo-pack-root",
        config.photo_pack_root,
        "--vision-provider",
        config.vision_provider,
    ])
    if config.vision_endpoint:
        command.extend(["--vision-endpoint", config.vision_endpoint])
    if config.recall_search_provider != "local":
        command.extend(["--recall-search-provider", config.recall_search_provider])
    if config.recall_search_endpoint:
        command.extend(["--recall-search-endpoint", config.recall_search_endpoint])
    if config.pairing_mode != "development":
        command.extend(["--pairing-mode", config.pairing_mode])
    if config.pairing_code_ttl_seconds != 120:
        command.extend(["--pairing-code-ttl-seconds", str(config.pairing_code_ttl_seconds)])
    if config.token_ttl_seconds > 0:
        command.extend(["--token-ttl-seconds", str(config.token_ttl_seconds)])
    if config.trusted_local_tls:
        command.append("--trusted-local-tls")
    if config.tls_trust_state != "not_configured":
        command.extend(["--tls-trust-state", config.tls_trust_state])
    if config.tls_certificate_label:
        command.extend(["--tls-certificate-label", config.tls_certificate_label])
    if config.tls_public_key_sha256:
        command.extend(["--tls-public-key-sha256", config.tls_public_key_sha256])
    if config.tls_certificate_chain_path:
        command.extend(["--tls-certificate-chain-path", config.tls_certificate_chain_path])
    if config.tls_private_key_path:
        command.extend(["--tls-private-key-path", config.tls_private_key_path])
    if config.bonjour:
        command.append("--bonjour")
        command.extend(["--bonjour-name", config.bonjour_name])
        command.extend(["--pairing-code", config.pairing_code])
        if config.bonjour_host:
            command.extend(["--bonjour-host", config.bonjour_host])
    if config.hermes_home:
        command.extend(["--hermes-home", config.hermes_home])
    if config.hermes_profile:
        command.extend(["--hermes-profile", config.hermes_profile])
    if config.env_file:
        command.extend(["--env-file", config.env_file])
    if config.runtime_store_path:
        command.extend(["--runtime-store-path", config.runtime_store_path])
    if config.input_assets_days != DEFAULT_INPUT_ASSETS_DAYS:
        command.extend(["--input-assets-days", str(config.input_assets_days)])
    if config.output_assets_days != DEFAULT_OUTPUT_ASSETS_DAYS:
        command.extend(["--output-assets-days", str(config.output_assets_days)])
    if config.task_history_days != DEFAULT_TASK_HISTORY_DAYS:
        command.extend(["--task-history-days", str(config.task_history_days)])
    return command


def build_retention_policy(config: BridgeConfig) -> Mapping[str, int]:
    return {
        "input_assets_days": int(config.input_assets_days),
        "output_assets_days": int(config.output_assets_days),
        "task_history_days": int(config.task_history_days),
    }


def build_phone_safe_runtime_summary(config: BridgeConfig) -> Mapping[str, object]:
    return {
        "recall_store_enabled": bool(config.runtime_store_path.strip()),
        "recall_store_owner": "runtime" if config.runtime_store_path.strip() else "mock_bridge",
        "semantic_recall_mode": "provider_backed"
        if config.recall_search_provider != "local"
        else "local_deterministic",
    }


def build_provider_environment_summary(
    config: BridgeConfig,
    env: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    values = os.environ if env is None else env
    if config.provider == "anthropic":
        return {
            "provider": "anthropic",
            "required_env_vars": ["ANTHROPIC_API_KEY"],
            "api_key_env_var": "ANTHROPIC_API_KEY",
            "api_key_state": "set" if str(values.get("ANTHROPIC_API_KEY", "")).strip() else "missing",
            "model_env_var": "KAKA_MODEL",
            "default_model": "claude-opus-4-8",
        }
    return {
        "provider": config.provider,
        "required_env_vars": [],
        "api_key_env_var": "",
        "api_key_state": "not_required",
        "model_env_var": "",
        "default_model": "",
    }


def build_provider_warnings(config: BridgeConfig, env: Mapping[str, str] | None = None) -> list[Mapping[str, str]]:
    provider_environment = build_provider_environment_summary(config, env=env)
    if (
        config.provider == "anthropic"
        and provider_environment.get("api_key_state") == "missing"
    ):
        return [
            {
                "id": "missing_anthropic_api_key",
                "message": "Set ANTHROPIC_API_KEY in the runtime environment before starting without --dry-run.",
            }
        ]
    return []


def build_runtime_connection_security_summary(config: BridgeConfig) -> Mapping[str, object]:
    token_ttl_seconds = int(config.token_ttl_seconds)
    return {
        "pairing_code_ttl_seconds": min(max(int(config.pairing_code_ttl_seconds), 60), 300),
        "mobile_token_ttl_seconds": token_ttl_seconds if token_ttl_seconds > 0 else None,
        "mobile_token_revocation_supported": config.pairing_mode == "production",
        "trusted_local_tls_required": bool(config.trusted_local_tls),
        "tls_trust_state": config.tls_trust_state,
        "tls_certificate_label": config.tls_certificate_label,
        **({"tls_public_key_sha256": config.tls_public_key_sha256} if config.tls_public_key_sha256 else {}),
    }


def build_runtime_process_ownership(
    config: BridgeConfig,
    bridge_enabled: bool,
) -> Mapping[str, object]:
    health_url = f"{config.scheme}://{config.advertised_host}:{config.port}/mobile/v1/health"
    warnings: list[Mapping[str, object]] = []
    if config.start_with_runtime:
        warnings.append({
            "id": "start_with_runtime_enabled",
            "tone": "warning",
            "message": "Start with runtime is enabled. The bridge still starts only under this runtime host, not during package install.",
        })
    if config.port_conflict:
        warnings.append({
            "id": "port_conflict",
            "tone": "warning",
            "message": "Another local process may already be using this bridge port.",
        })

    actions = [
        {
            "id": "install_runtime_package",
            "label": "Install",
            "style": "secondary",
            "enabled": not config.installed,
            "requires_explicit_user_approval": True,
        },
        {
            "id": "enable_start_with_runtime",
            "label": "Start with runtime",
            "style": "secondary",
            "enabled": config.installed and not config.start_with_runtime,
            "requires_explicit_user_approval": True,
        },
        {
            "id": "disable_start_with_runtime",
            "label": "Disable start with runtime",
            "style": "secondary",
            "enabled": config.installed and config.start_with_runtime,
            "requires_explicit_user_approval": True,
        },
        {
            "id": "update_runtime_package",
            "label": "Update",
            "style": "secondary",
            "enabled": config.installed,
            "requires_explicit_user_approval": True,
        },
        {
            "id": "uninstall_runtime_package",
            "label": "Uninstall",
            "style": "destructive",
            "enabled": config.installed,
            "requires_explicit_user_approval": True,
        },
        {
            "id": "open_runtime_logs",
            "label": "Open Logs",
            "style": "secondary",
            "enabled": config.installed,
            "target": "host_runtime_logs",
        },
        {
            "id": "run_health_check",
            "label": "Health Check",
            "style": "secondary",
            "enabled": bridge_enabled,
            "url": health_url,
        },
        {
            "id": "repair_port_conflict",
            "label": "Repair Port",
            "style": "secondary",
            "enabled": config.port_conflict,
            "requires_explicit_user_approval": True,
        },
    ]

    return {
        "schema_version": "kaka.runtime_process_ownership.v1",
        "surface": "hermes_openclaw_process_ownership",
        "owner": config.runtime,
        "state": {
            "installed": bool(config.installed),
            "running": bool(bridge_enabled),
            "process_state": config.process_state,
            "start_with_runtime": bool(config.start_with_runtime),
            "supervision": config.process_supervision,
            "health": config.health_status,
            "port": int(config.port),
            "port_conflict": bool(config.port_conflict),
        },
        "actions": actions,
        "warnings": warnings,
        "runtime_side_only": True,
    }


def build_runtime_consumer_ui(
    config: BridgeConfig,
    bridge_enabled: bool,
    pairing_page: str,
) -> Mapping[str, object]:
    safe_summary = build_phone_safe_runtime_summary(config)
    pairing_is_production = config.pairing_mode == "production"
    tls_configured = bool(config.trusted_local_tls and config.tls_trust_state == "configured")
    network_label = "LAN + Bonjour" if config.lan and config.bonjour else "LAN" if config.lan else "Loopback only"
    warnings: list[Mapping[str, object]] = []
    if config.lan or config.bonjour:
        warnings.append({
            "id": "lan_visible",
            "tone": "warning",
            "message": "LAN and Bonjour make this runtime discoverable on the local network."
            if config.lan and config.bonjour
            else "LAN mode exposes this runtime beyond loopback.",
        })
    if not pairing_is_production:
        warnings.append({
            "id": "development_pairing",
            "tone": "warning",
            "message": "Development pairing is intended for local testing. Use production pairing for ordinary users.",
        })
    if pairing_is_production and config.trusted_local_tls and not tls_configured:
        warnings.append({
            "id": "tls_attention",
            "tone": "warning",
            "message": "Trusted local TLS is enabled but not fully configured.",
        })

    primary_actions: list[Mapping[str, object]]
    if bridge_enabled:
        primary_actions = [
            {
                "id": "stop_bridge",
                "label": "Stop Bridge",
                "style": "secondary",
                "enabled": True,
                "action": "stop_bridge",
            },
            {
                "id": "show_qr",
                "label": "Show QR",
                "style": "primary",
                "enabled": True,
                "url": pairing_page,
            },
        ]
        if pairing_is_production:
            primary_actions.append({
                "id": "revoke_mobile_tokens",
                "label": "Revoke iPhone",
                "style": "destructive",
                "enabled": True,
                "endpoint": "/mobile/v1/pairing/revoke",
            })
    else:
        primary_actions = [
            {
                "id": "start_bridge",
                "label": "Start Bridge",
                "style": "primary",
                "enabled": True,
                "action": "start_bridge",
            }
        ]

    return {
        "schema_version": "kaka.runtime_consumer_ui.v1",
        "surface": "hermes_openclaw_consumer_runtime_ui",
        "title": "Kaka Mobile Bridge",
        "subtitle": "Connect Kaka iPhone to this local runtime after explicit approval.",
        "status_badges": [
            {
                "id": "bridge",
                "label": "Running" if bridge_enabled else "Stopped",
                "tone": "success" if bridge_enabled else "neutral",
            },
            {
                "id": "network",
                "label": network_label,
                "tone": "warning" if config.lan or config.bonjour else "neutral",
            },
            {
                "id": "pairing",
                "label": "Production QR" if pairing_is_production else "Development pairing",
                "tone": "success" if pairing_is_production else "warning",
            },
            {
                "id": "trust",
                "label": "TLS configured" if tls_configured else "TLS not configured",
                "tone": "success" if tls_configured else "neutral",
            },
        ],
        "primary_actions": primary_actions,
        "empty_state": None if bridge_enabled else {
            "id": "bridge_stopped",
            "title": "Bridge is stopped",
            "message": "Start Kaka Mobile Bridge from this runtime before pairing an iPhone.",
            "primary_action": "start_bridge",
        },
        "sections": [
            {
                "id": "process",
                "title": "Process",
                "summary": "Install, update, uninstall, inspect logs, run health checks, and repair host-side process issues.",
                "controls": [
                    "install_runtime_package",
                    "start_with_runtime",
                    "update_runtime_package",
                    "uninstall_runtime_package",
                    "open_runtime_logs",
                    "run_health_check",
                    "repair_port_conflict",
                ],
            },
            {
                "id": "connection",
                "title": "Connection",
                "summary": "Choose where the bridge listens and whether iPhone discovery is visible on the LAN.",
                "controls": ["bridge_enabled", "bind_mode", "bonjour_enabled", "trusted_local_tls"],
            },
            {
                "id": "pairing",
                "title": "Pairing",
                "summary": "Show a QR code, choose production pairing, and revoke a paired iPhone when needed.",
                "controls": ["pairing_mode", "qr_ttl_seconds", "revoke_mobile_tokens"],
            },
            {
                "id": "memory",
                "title": "Local Memory",
                "summary": "Keep Recall and task state in a runtime-owned local SQLite store and configure retention windows.",
                "controls": [
                    "local_store_enabled",
                    "runtime_store_path",
                    "input_assets_days",
                    "output_assets_days",
                    "task_history_days",
                ],
            },
            {
                "id": "retrieval",
                "title": "Recall Retrieval",
                "summary": "Choose local deterministic Recall search or a runtime-owned retrieval adapter.",
                "controls": ["recall_search_provider", "recall_search_endpoint"],
            },
        ],
        "warnings": warnings,
        "safe_summary": safe_summary,
    }


def build_runtime_settings_preview(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> Mapping[str, object]:
    pairing_page = pairing_url(
        config.advertised_host,
        config.port,
        mode=config.pairing_mode,
        scheme=config.scheme,
    )
    bind_mode = "lan" if config.lan else "loopback"
    command = build_server_command(config)
    local_store_enabled = bool(config.runtime_store_path.strip())
    qr_ttl_seconds = min(max(int(config.pairing_code_ttl_seconds), 60), 300)
    provider_environment = build_provider_environment_summary(config)
    consumer_ui = build_runtime_consumer_ui(
        config,
        bridge_enabled=bridge_enabled,
        pairing_page=pairing_page,
    )
    process_ownership = build_runtime_process_ownership(
        config,
        bridge_enabled=bridge_enabled,
    )
    return {
        "bridge": "Kaka Mobile Bridge",
        "surface": "runtime_side_settings_preview",
        "bridge_enabled": bridge_enabled,
        "runtime": config.runtime,
        "provider": config.provider,
        "provider_environment": provider_environment,
        "bind_url": f"{config.scheme}://{config.bind_host}:{config.port}",
        "lan_exposed": config.lan,
        "bonjour": config.bonjour,
        "pairing_page": pairing_page,
        "pairing_mode": config.pairing_mode,
        "runtime_store_path": config.runtime_store_path,
        "retention": build_retention_policy(config),
        "recall_search_provider": config.recall_search_provider,
        "recall_search_endpoint": config.recall_search_endpoint,
        "runtime_side_ui": {
            "surface": "hermes_openclaw_settings",
            "connection_security": build_runtime_connection_security_summary(config),
            "process_ownership": process_ownership,
            "consumer_ui": consumer_ui,
            "controls": {
                "bridge_enabled": {
                    "kind": "toggle",
                    "value": bridge_enabled,
                },
                "start_with_runtime": {
                    "kind": "toggle",
                    "value": config.start_with_runtime,
                },
                "install_runtime_package": {
                    "kind": "button",
                    "style": "secondary",
                    "enabled": not config.installed,
                },
                "update_runtime_package": {
                    "kind": "button",
                    "style": "secondary",
                    "enabled": config.installed,
                },
                "uninstall_runtime_package": {
                    "kind": "button",
                    "style": "destructive",
                    "enabled": config.installed,
                },
                "open_runtime_logs": {
                    "kind": "button",
                    "style": "secondary",
                    "enabled": config.installed,
                },
                "run_health_check": {
                    "kind": "button",
                    "style": "secondary",
                    "enabled": bridge_enabled,
                },
                "provider": {
                    "kind": "menu",
                    "value": config.provider,
                    "options": list(INTELLIGENCE_PROVIDER_CHOICES),
                },
                "provider_environment": {
                    "kind": "status",
                    "value": provider_environment,
                },
                "repair_port_conflict": {
                    "kind": "button",
                    "style": "secondary",
                    "enabled": config.port_conflict,
                },
                "bind_mode": {
                    "kind": "segmented_control",
                    "value": bind_mode,
                    "options": ["loopback", "lan"],
                },
                "bonjour_enabled": {
                    "kind": "toggle",
                    "value": config.bonjour,
                    "requires": "lan_or_bonjour_host",
                },
                "pairing_mode": {
                    "kind": "segmented_control",
                    "value": config.pairing_mode,
                    "options": list(PAIRING_MODE_CHOICES),
                },
                "qr_ttl_seconds": {
                    "kind": "stepper",
                    "value": qr_ttl_seconds,
                    "minimum": 60,
                    "maximum": 300,
                },
                "trusted_local_tls": {
                    "kind": "toggle",
                    "value": bool(config.trusted_local_tls),
                },
                "tls_certificate_chain_path": {
                    "kind": "path_picker",
                    "enabled": bool(config.trusted_local_tls),
                    "value": config.tls_certificate_chain_path,
                },
                "tls_private_key_path": {
                    "kind": "path_picker",
                    "enabled": bool(config.trusted_local_tls),
                    "value": config.tls_private_key_path,
                },
                "revoke_mobile_tokens": {
                    "kind": "button",
                    "style": "destructive",
                    "endpoint": "/mobile/v1/pairing/revoke",
                },
                "local_store_enabled": {
                    "kind": "toggle",
                    "value": local_store_enabled,
                },
                "runtime_store_path": {
                    "kind": "path_picker",
                    "enabled": local_store_enabled,
                    "value": config.runtime_store_path,
                },
                "input_assets_days": {
                    "kind": "stepper",
                    "value": int(config.input_assets_days),
                    "minimum": RETENTION_MIN_DAYS,
                    "maximum": RETENTION_MAX_DAYS,
                },
                "output_assets_days": {
                    "kind": "stepper",
                    "value": int(config.output_assets_days),
                    "minimum": RETENTION_MIN_DAYS,
                    "maximum": RETENTION_MAX_DAYS,
                },
                "task_history_days": {
                    "kind": "stepper",
                    "value": int(config.task_history_days),
                    "minimum": RETENTION_MIN_DAYS,
                    "maximum": RETENTION_MAX_DAYS,
                },
                "recall_search_provider": {
                    "kind": "menu",
                    "value": config.recall_search_provider,
                    "options": list(RECALL_SEARCH_PROVIDER_CHOICES),
                },
                "recall_search_endpoint": {
                    "kind": "url_input",
                    "enabled": config.recall_search_provider == "runtime_http",
                    "value": config.recall_search_endpoint,
                },
            },
        },
        "actions": {
            "start_bridge": command,
            "stop_bridge": "terminate_launched_bridge_process",
            "show_qr": pairing_page,
        },
        "phone_safe_summary": build_phone_safe_runtime_summary(config),
    }


def build_runtime_settings_preview_command(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "kaka_mobile_runtime_kit",
        "settings-preview",
        "--repo-root",
        str(config.repo_root),
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--runtime",
        config.runtime,
    ]
    if config.provider != "fake":
        command.extend(["--provider", config.provider])
    command.extend([
        "--photo-provider",
        config.photo_provider,
        "--photo-pack-root",
        config.photo_pack_root,
        "--vision-provider",
        config.vision_provider,
        "--recall-search-provider",
        config.recall_search_provider,
    ])
    if bridge_enabled:
        command.append("--bridge-enabled")
    if config.lan:
        command.append("--lan")
    if config.bonjour:
        command.append("--bonjour")
    if config.bonjour_host:
        command.extend(["--bonjour-host", config.bonjour_host])
    if config.bonjour_name != DEFAULT_BONJOUR_NAME:
        command.extend(["--bonjour-name", config.bonjour_name])
    if config.pairing_code != "pair_dev":
        command.extend(["--pairing-code", config.pairing_code])
    if config.vision_endpoint:
        command.extend(["--vision-endpoint", config.vision_endpoint])
    if config.recall_search_endpoint:
        command.extend(["--recall-search-endpoint", config.recall_search_endpoint])
    if config.pairing_mode != "development":
        command.extend(["--pairing-mode", config.pairing_mode])
    if config.pairing_code_ttl_seconds != 120:
        command.extend(["--pairing-code-ttl-seconds", str(config.pairing_code_ttl_seconds)])
    if config.token_ttl_seconds > 0:
        command.extend(["--token-ttl-seconds", str(config.token_ttl_seconds)])
    if config.trusted_local_tls:
        command.append("--trusted-local-tls")
    if config.tls_trust_state != "not_configured":
        command.extend(["--tls-trust-state", config.tls_trust_state])
    if config.tls_certificate_label:
        command.extend(["--tls-certificate-label", config.tls_certificate_label])
    if config.tls_public_key_sha256:
        command.extend(["--tls-public-key-sha256", config.tls_public_key_sha256])
    if config.tls_certificate_chain_path:
        command.extend(["--tls-certificate-chain-path", config.tls_certificate_chain_path])
    if config.tls_private_key_path:
        command.extend(["--tls-private-key-path", config.tls_private_key_path])
    if config.hermes_home:
        command.extend(["--hermes-home", config.hermes_home])
    if config.hermes_profile:
        command.extend(["--hermes-profile", config.hermes_profile])
    if config.env_file:
        command.extend(["--env-file", config.env_file])
    if config.runtime_store_path:
        command.extend(["--runtime-store-path", config.runtime_store_path])
    if config.input_assets_days != DEFAULT_INPUT_ASSETS_DAYS:
        command.extend(["--input-assets-days", str(config.input_assets_days)])
    if config.output_assets_days != DEFAULT_OUTPUT_ASSETS_DAYS:
        command.extend(["--output-assets-days", str(config.output_assets_days)])
    if config.task_history_days != DEFAULT_TASK_HISTORY_DAYS:
        command.extend(["--task-history-days", str(config.task_history_days)])
    if config.installed:
        command.append("--installed")
    if config.start_with_runtime:
        command.append("--start-with-runtime")
    if config.process_state != "stopped":
        command.extend(["--process-state", config.process_state])
    if config.process_supervision != "not_configured":
        command.extend(["--process-supervision", config.process_supervision])
    if config.health_status != "unknown":
        command.extend(["--health-status", config.health_status])
    if config.port_conflict:
        command.append("--port-conflict")
    return command


def build_runtime_package_preview_command(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> list[str]:
    command = build_runtime_settings_preview_command(config, bridge_enabled=bridge_enabled)
    command[command.index("settings-preview")] = "package-preview"
    return command


def build_runtime_process_preview_command(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> list[str]:
    command = build_runtime_settings_preview_command(config, bridge_enabled=bridge_enabled)
    command[command.index("settings-preview")] = "process-preview"
    return _without_retention_policy_arguments(command)


def build_runtime_host_adapter_run_command(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> list[str]:
    command = build_runtime_settings_preview_command(config, bridge_enabled=bridge_enabled)
    command[command.index("settings-preview")] = "host-adapter-run"
    return _without_retention_policy_arguments(command)


def _without_retention_policy_arguments(command: list[str]) -> list[str]:
    filtered: list[str] = []
    skip_next = False
    retention_flags = {"--input-assets-days", "--output-assets-days", "--task-history-days"}
    for part in command:
        if skip_next:
            skip_next = False
            continue
        if part in retention_flags:
            skip_next = True
            continue
        filtered.append(part)
    return filtered


def build_runtime_host_package(
    config: BridgeConfig,
    bridge_enabled: bool = False,
    *,
    distribution_source: str = "local_checkout",
    distribution_channel: str = "development",
    package_version: str = "development",
    host_api_level: str = "preview",
) -> Mapping[str, object]:
    if config.runtime not in HOST_PACKAGE_RUNTIME_CHOICES:
        raise ValueError(f"Unsupported host package runtime: {config.runtime}")
    settings_preview = build_runtime_settings_preview(config, bridge_enabled=bridge_enabled)
    process_ownership = settings_preview["runtime_side_ui"]["process_ownership"]
    consumer_ui = settings_preview["runtime_side_ui"]["consumer_ui"]
    process_actions_by_id = {
        str(action["id"]): action
        for action in process_ownership["actions"]
    }
    host_actions: list[Mapping[str, object]] = []
    for action_id in HOST_PACKAGE_ACTIONS:
        source_action = process_actions_by_id.get(action_id, {})
        mutates_host_state = action_id in HOST_ADAPTER_MUTATING_ACTIONS
        host_action = {
            "id": action_id,
            "owner": "host_native_adapter",
            "adapter": HOST_PACKAGE_ACTION_ADAPTERS[action_id],
            "mutates_host_state": mutates_host_state,
            "requires_explicit_user_approval": mutates_host_state,
            "runtime_side_only": True,
            "enabled": source_action.get("enabled", bool(config.installed)),
        }
        if "label" in source_action:
            host_action["label"] = source_action["label"]
        if "style" in source_action:
            host_action["style"] = source_action["style"]
        if "target" in source_action:
            host_action["target"] = source_action["target"]
        if "url" in source_action:
            host_action["url"] = source_action["url"]
        if action_id == "supervise_bridge":
            host_action.update({
                "label": "Supervise Bridge",
                "style": "secondary",
                "enabled": bool(config.installed),
            })
        host_actions.append(host_action)

    return {
        "schema_version": "kaka.runtime_host_package.v1",
        "surface": "hermes_openclaw_host_package",
        "runtime": config.runtime,
        "host_api_level": host_api_level,
        "distribution": {
            "source": distribution_source,
            "channel": distribution_channel,
            "version": package_version,
            "update_policy": "explicit_user_approved",
        },
        "private_adapter_package": build_host_private_adapter_package(
            config,
            distribution_source=distribution_source,
            distribution_channel=distribution_channel,
            package_version=package_version,
        ),
        "install_policy": {
            "enabled_by_default": False,
            "auto_start_on_install": False,
            "requires_explicit_start": True,
            "login_item_default": False,
            "creates_login_item_on_install": False,
        },
        "host_actions": host_actions,
        "artifacts": {
            "settings_preview_command": build_runtime_settings_preview_command(
                config,
                bridge_enabled=bridge_enabled,
            ),
            "package_preview_command": build_runtime_package_preview_command(
                config,
                bridge_enabled=bridge_enabled,
            ),
            "process_preview_command": build_runtime_process_preview_command(
                config,
                bridge_enabled=bridge_enabled,
            ),
            "host_adapter_run_command": build_runtime_host_adapter_run_command(
                config,
                bridge_enabled=bridge_enabled,
            ),
            "start_bridge_command": build_server_command(config),
        },
        "process_ownership": process_ownership,
        "consumer_ui": consumer_ui,
        "safety": {
            "runtime_side_only": True,
            "phone_settings_owner": False,
            "no_autostart_on_install": True,
            "no_login_item_creation_by_runtime_kit": True,
            "requires_host_native_adapter": True,
            "forbidden_phone_safe_fields": list(HOST_PACKAGE_FORBIDDEN_PHONE_SAFE_FIELDS),
        },
    }


def build_runtime_package_manifest(
    config: BridgeConfig,
    bridge_enabled: bool = False,
) -> Mapping[str, object]:
    settings_preview = build_runtime_settings_preview(config, bridge_enabled=bridge_enabled)
    return {
        "schema_version": "kaka.runtime_package.v1",
        "package": "kaka-mobile-bridge",
        "bridge": "Kaka Mobile Bridge",
        "surface": "native_runtime_package_preview",
        "runtime": config.runtime,
        "install": {
            "enabled_by_default": False,
            "auto_start_on_install": False,
            "requires_explicit_start": True,
        },
        "defaults": {
            "lan_exposed": False,
            "bonjour": False,
            "start_with_runtime": False,
        },
        "settings_preview_command": build_runtime_settings_preview_command(
            config,
            bridge_enabled=bridge_enabled,
        ),
        "settings_preview": settings_preview,
        "process_ownership": settings_preview["runtime_side_ui"]["process_ownership"],
        "consumer_ui": settings_preview["runtime_side_ui"]["consumer_ui"],
        "actions": settings_preview["actions"],
        "runtime_side_values": list(RUNTIME_SIDE_VALUES),
        "forbidden_phone_safe_fields": list(FORBIDDEN_PHONE_SAFE_FIELDS),
        "follow_up_security": {
            "short_lived_qr": "implemented" if config.pairing_mode == "production" else "development_only",
            "token_revocation": "implemented" if config.pairing_mode == "production" else "development_only",
            "trusted_local_tls": "metadata_ready" if config.trusted_local_tls else "not_configured",
        },
    }


def build_bridge_environment(
    repo_root: Path,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    mock_bridge_path = str((repo_root / "mock_bridge").resolve())
    existing = env.get("PYTHONPATH", "")
    parts = [mock_bridge_path]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def pairing_url(host: str, port: int, mode: str = "development", scheme: str = "http") -> str:
    route = "qr" if mode == "production" else "dev"
    return f"{scheme}://{host}:{port}/mobile/v1/pairing/{route}.html"


def validate_start_config(
    config: BridgeConfig,
    *,
    require_tls_serving_files: bool = True,
    require_provider_credentials: bool = True,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if config.provider not in INTELLIGENCE_PROVIDER_CHOICES:
        errors.append(f"Unsupported provider: {config.provider}")
    if (
        require_provider_credentials
        and config.provider == "anthropic"
        and build_provider_environment_summary(config, env=env).get("api_key_state") == "missing"
    ):
        errors.append("--provider anthropic requires ANTHROPIC_API_KEY in the runtime environment.")
    if config.photo_provider not in PROVIDER_CHOICES:
        errors.append(f"Unsupported photo provider: {config.photo_provider}")
    if config.vision_provider not in VISION_PROVIDER_CHOICES:
        errors.append(f"Unsupported vision provider: {config.vision_provider}")
    if config.vision_provider == "runtime_http" and not config.vision_endpoint:
        errors.append("--vision-endpoint is required when --vision-provider runtime_http.")
    if config.recall_search_provider not in RECALL_SEARCH_PROVIDER_CHOICES:
        errors.append(f"Unsupported Recall search provider: {config.recall_search_provider}")
    if config.pairing_mode not in PAIRING_MODE_CHOICES:
        errors.append(f"Unsupported pairing mode: {config.pairing_mode}")
    if config.recall_search_provider == "runtime_http" and not config.recall_search_endpoint:
        errors.append("--recall-search-endpoint is required when --recall-search-provider runtime_http.")
    if config.recall_search_provider == "runtime_http" and config.recall_search_endpoint:
        if not _is_http_endpoint(config.recall_search_endpoint):
            errors.append("--recall-search-endpoint must be an http:// or https:// URL.")
        elif not _is_local_or_private_endpoint(config.recall_search_endpoint):
            errors.append("--recall-search-endpoint must point to localhost, Tailscale, or a private LAN endpoint.")
    if config.bonjour and not config.lan and not config.bonjour_host:
        errors.append("Bonjour discovery for iPhone requires --lan or --bonjour-host.")
    if config.lan and config.host not in ("127.0.0.1", "localhost"):
        errors.append("Use --lan by itself instead of combining it with a custom --host.")
    if (
        require_tls_serving_files
        and config.trusted_local_tls
        and not str(config.tls_certificate_chain_path).strip()
    ):
        errors.append("--tls-certificate-chain-path is required when --trusted-local-tls starts the bridge.")
    if (
        require_tls_serving_files
        and config.trusted_local_tls
        and not str(config.tls_private_key_path).strip()
    ):
        errors.append("--tls-private-key-path is required when --trusted-local-tls starts the bridge.")
    errors.extend(_retention_day_errors(config))
    return errors


def _retention_day_errors(config: BridgeConfig) -> list[str]:
    errors: list[str] = []
    for flag, value in (
        ("--input-assets-days", config.input_assets_days),
        ("--output-assets-days", config.output_assets_days),
        ("--task-history-days", config.task_history_days),
    ):
        if int(value) < RETENTION_MIN_DAYS or int(value) > RETENTION_MAX_DAYS:
            errors.append(f"{flag} must be between {RETENTION_MIN_DAYS} and {RETENTION_MAX_DAYS}.")
    return errors


def _is_http_endpoint(value: str) -> bool:
    parsed = urlsplit(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_local_or_private_endpoint(value: str) -> bool:
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host in {"localhost"} or host.endswith(".local"):
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or _is_tailscale_cgnat(address)
    )


def _is_tailscale_cgnat(address) -> bool:
    return address.version == 4 and int(ip_address("100.64.0.0")) <= int(address) <= int(ip_address("100.127.255.255"))


def doctor_report(
    repo_root: Path,
    photo_pack_root: str = "photo-pack",
    provider: str = "fake",
    env: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    root = repo_root.resolve()
    mock_bridge_dir = root / "mock_bridge"
    photo_pack_dir = root / photo_pack_root
    adapter_path = photo_pack_dir / "adapters" / "recipe_local.py"
    checks: dict[str, Mapping[str, object]] = {
        "python": {
            "ok": True,
            "detail": sys.executable,
        },
        "mock_bridge_directory": {
            "ok": mock_bridge_dir.exists(),
            "detail": str(mock_bridge_dir),
        },
        "photo_pack_directory": {
            "ok": photo_pack_dir.exists(),
            "detail": str(photo_pack_dir),
        },
        "recipe_local_adapter": {
            "ok": adapter_path.exists(),
            "detail": str(adapter_path),
        },
        "dns_sd": {
            "ok": bool(shutil.which("dns-sd")),
            "detail": shutil.which("dns-sd") or "missing; Bonjour discovery will not work until dns-sd is available",
            "required_for": "bonjour",
        },
    }

    import_ok, import_detail = _can_import_mock_bridge(mock_bridge_dir)
    checks["mock_bridge_import"] = {
        "ok": import_ok,
        "detail": import_detail,
    }
    if provider == "anthropic":
        provider_environment = build_provider_environment_summary(BridgeConfig(provider=provider), env=env)
        checks["anthropic_provider"] = {
            "ok": provider_environment["api_key_state"] == "set",
            "detail": (
                "ANTHROPIC_API_KEY is set in the runtime environment."
                if provider_environment["api_key_state"] == "set"
                else "missing ANTHROPIC_API_KEY in the runtime environment"
            ),
            "env_var": "ANTHROPIC_API_KEY",
            "required_for": "--provider anthropic",
        }
    required = ("python", "mock_bridge_directory", "photo_pack_directory", "recipe_local_adapter", "mock_bridge_import")
    if provider == "anthropic":
        required = (*required, "anthropic_provider")
    ok = all(bool(checks[name]["ok"]) for name in required)
    return {
        "ok": ok,
        "scope": "local Kaka Mobile Bridge launcher",
        "secrets": "not inspected or printed",
        "checks": checks,
    }


def run_doctor(args: argparse.Namespace) -> int:
    report = doctor_report(Path(args.repo_root), photo_pack_root=args.photo_pack_root, provider=args.provider)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def run_pairing_url(args: argparse.Namespace) -> int:
    print(pairing_url(args.host, args.port, mode=args.pairing_mode, scheme=args.scheme))
    return 0


def run_start(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_provider_credentials=not bool(args.dry_run))
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    repo_root = config.repo_root.resolve()
    command = build_server_command(config)
    phone_safe_summary = build_phone_safe_runtime_summary(config)
    summary = {
        "bridge": "Kaka Mobile Bridge",
        "runtime": config.runtime,
        "bind_url": f"{config.scheme}://{config.bind_host}:{config.port}",
        "lan_exposed": config.lan,
        "bonjour": config.bonjour,
        "pairing_page": pairing_url(
            config.advertised_host,
            config.port,
            mode=config.pairing_mode,
            scheme=config.scheme,
        ),
        "pairing_mode": config.pairing_mode,
        "provider": config.provider,
        "provider_environment": build_provider_environment_summary(config),
        "photo_provider": config.photo_provider,
        "vision_provider": config.vision_provider,
        "recall_search_provider": config.recall_search_provider,
        "semantic_recall_mode": "provider_backed"
        if config.recall_search_provider != "local"
        else "local_deterministic",
        "runtime_store_path": config.runtime_store_path,
        "recall_store_enabled": bool(config.runtime_store_path.strip()),
        "recall_store_owner": "runtime" if config.runtime_store_path.strip() else "mock_bridge",
        "retention": build_retention_policy(config),
        "phone_safe_summary": phone_safe_summary,
        "warnings": build_provider_warnings(config),
        "command": command,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return 0
    env = build_bridge_environment(repo_root)
    return subprocess.call(command, cwd=repo_root, env=env)


def run_settings_preview(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    preview = build_runtime_settings_preview(
        config,
        bridge_enabled=bool(args.bridge_enabled),
    )
    print(json.dumps(preview, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_connection_qa_preview(args: argparse.Namespace) -> int:
    from .connection_qa import build_connection_qa_preview

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    preview = build_connection_qa_preview(
        config,
        bridge_enabled=bool(args.bridge_enabled),
    )
    print(json.dumps(preview, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_package_preview(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    manifest = build_runtime_package_manifest(
        config,
        bridge_enabled=bool(args.bridge_enabled),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_package_preview(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    package = build_runtime_host_package(
        config,
        bridge_enabled=bool(args.bridge_enabled),
        distribution_source=args.distribution_source,
        distribution_channel=args.distribution_channel,
        package_version=args.package_version,
        host_api_level=args.host_api_level,
    )
    print(json.dumps(package, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_extension_preview(args: argparse.Namespace) -> int:
    preview = build_host_extension_preview(runtime=args.runtime)
    print(json.dumps(preview, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_extension_readiness(args: argparse.Namespace) -> int:
    readiness = build_host_extension_readiness(
        runtime=args.runtime,
        install_command=args.install_command,
        update_channel=args.update_channel,
        adapter_command_location=args.adapter_command_location,
        host_ui_entrypoint=args.host_ui_entrypoint,
        signed_package_ref=args.signed_package_ref,
        signature_ref=args.signature_ref,
        conformance_report_ref=args.conformance_report_ref,
        evidence_manifest_ref=args.evidence_manifest_ref,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_extension_material_intake(args: argparse.Namespace) -> int:
    from .host_extension_material_intake import (
        HOST_EXTENSION_MATERIAL_INTAKE_ACCEPTED_STATUS,
        build_host_extension_material_intake_from_path,
    )

    report = build_host_extension_material_intake_from_path(
        args.manifest,
        runtime=args.runtime,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report.get("status") == HOST_EXTENSION_MATERIAL_INTAKE_ACCEPTED_STATUS else 1


def run_host_extension_starter_kit(args: argparse.Namespace) -> int:
    if args.write:
        payload = write_host_extension_starter_kit(
            runtime=args.runtime,
            output_dir=Path(args.output_dir),
        )
    else:
        payload = build_host_extension_starter_kit(
            runtime=args.runtime,
            output_dir=args.output_dir,
            written=False,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_extension_install_package(args: argparse.Namespace) -> int:
    if args.write:
        payload = write_host_extension_install_package(
            runtime=args.runtime,
            output_dir=Path(args.output_dir),
        )
    else:
        payload = build_host_extension_install_package(
            runtime=args.runtime,
            output_dir=args.output_dir,
            written=False,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_plugin_skill_devkit(args: argparse.Namespace) -> int:
    if args.write:
        payload = write_host_plugin_skill_devkit(
            runtime=args.runtime,
            output_dir=Path(args.output_dir or "."),
        )
    else:
        payload = build_host_plugin_skill_devkit(
            runtime=args.runtime,
            output_dir=args.output_dir,
            written=False,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_codex_developer_plugin_source(args: argparse.Namespace) -> int:
    if args.write:
        if not str(args.output_dir).strip():
            raise ValueError("host-codex-developer-plugin-source --write requires --output-dir")
        payload = write_host_codex_developer_plugin_source(
            runtime=args.runtime,
            output_dir=Path(args.output_dir),
        )
    else:
        payload = build_host_codex_developer_plugin_source(
            runtime=args.runtime,
            output_dir=args.output_dir,
            written=False,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_local_tls_readiness(args: argparse.Namespace) -> int:
    readiness = build_local_tls_readiness(
        runtime=args.runtime,
        tls_trust_state=args.tls_trust_state,
        tls_certificate_label=args.tls_certificate_label,
        tls_certificate_ref=args.tls_certificate_ref,
        tls_public_key_sha256=args.tls_public_key_sha256,
        tls_expires_at=args.tls_expires_at,
        trust_store_ref=args.trust_store_ref,
        renewal_procedure_ref=args.renewal_procedure_ref,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_local_renderer_backend_readiness(args: argparse.Namespace) -> int:
    from .local_renderer_backend_readiness import build_local_renderer_backend_readiness

    readiness = build_local_renderer_backend_readiness(
        repo_root=args.repo_root,
        photo_pack_root=args.photo_pack_root,
        provider=args.photo_provider,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2), flush=True)
    return 0 if bool(readiness.get("ready_for_local_recipe_flow")) else 1


def run_local_renderer_backend_capability_manifest(args: argparse.Namespace) -> int:
    from .local_renderer_backend_capability_manifest import (
        build_local_renderer_backend_capability_manifest,
    )

    manifest = build_local_renderer_backend_capability_manifest(
        repo_root=args.repo_root,
        photo_pack_root=args.photo_pack_root,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if bool(manifest.get("ready_for_backend_gate_planning")) else 1


def run_recall_retrieval_readiness(args: argparse.Namespace) -> int:
    readiness = build_recall_retrieval_readiness(
        runtime=args.runtime,
        strategy=args.strategy,
        adapter_package_ref=args.adapter_package_ref,
        runtime_settings_ui_ref=args.runtime_settings_ui_ref,
        signature_ref=args.signature_ref,
        conformance_report_ref=args.conformance_report_ref,
        privacy_review_ref=args.privacy_review_ref,
        fallback_drill_ref=args.fallback_drill_ref,
        release_notes_ref=args.release_notes_ref,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_recall_retrieval_material_intake(args: argparse.Namespace) -> int:
    from .recall_retrieval_material_intake import (
        build_recall_retrieval_material_intake_from_path,
    )

    report = build_recall_retrieval_material_intake_from_path(
        runtime=args.runtime,
        materials_path=args.materials_json,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_retention_purge(args: argparse.Namespace) -> int:
    config = BridgeConfig(
        runtime=args.runtime,
        runtime_store_path=args.runtime_store_path,
        input_assets_days=args.input_assets_days,
        output_assets_days=args.output_assets_days,
        task_history_days=args.task_history_days,
    )
    errors = validate_start_config(config, require_tls_serving_files=False)
    if bool(args.apply) and bool(args.dry_run):
        errors.append("--apply and --dry-run cannot be used together.")

    store_path = Path(args.runtime_store_path).expanduser() if args.runtime_store_path else None
    if bool(args.apply) and (store_path is None or not store_path.exists()):
        errors.append("runtime store path must exist before --apply.")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    now_iso = str(args.now).strip()
    if not now_iso:
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    store = None
    if store_path is not None:
        store = SQLiteRuntimeStore(store_path)
        store.initialize()
    receipt = build_runtime_retention_purge_receipt(
        runtime=config.runtime,
        policy=build_retention_policy(config),
        now_iso=now_iso,
        dry_run=not bool(args.apply),
        store=store,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_adapter_run(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    package = build_runtime_host_package(
        config,
        bridge_enabled=bool(args.bridge_enabled),
    )
    result = build_host_adapter_action_result(
        package,
        action_id=args.action_id,
        approved=bool(args.approved),
        adapter_mode=args.adapter,
        private_adapter_command=args.private_adapter_command,
        private_adapter_timeout_seconds=args.private_adapter_timeout_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result["ok"] is True else 2


def run_host_private_adapter_conformance(args: argparse.Namespace) -> int:
    from .host_private_adapter_conformance import (
        build_host_private_adapter_conformance_report,
    )

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    report = build_host_private_adapter_conformance_report(
        config,
        private_adapter_command=args.private_adapter_command,
        private_adapter_timeout_seconds=args.private_adapter_timeout_seconds,
        include_negative_checks=not bool(args.skip_negative_checks),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["ok"] is True else 2


def run_host_shell_pilot_report(args: argparse.Namespace) -> int:
    from .host_shell_pilot import build_host_shell_pilot_receipt

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    receipt = build_host_shell_pilot_receipt(
        config,
        private_adapter_command=args.private_adapter_command,
        private_adapter_timeout_seconds=args.private_adapter_timeout_seconds,
        distribution_source=args.distribution_source,
        distribution_channel=args.distribution_channel,
        package_version=args.package_version,
        host_api_level=args.host_api_level,
        native_channel_verified=bool(args.native_channel_verified),
        signature_verified=bool(args.signature_verified),
        update_feed_verified=bool(args.update_feed_verified),
        install_verified=bool(args.install_verified),
        update_verified=bool(args.update_verified),
        failure_recovery_verified=bool(args.failure_recovery_verified),
        release_notes_verified=bool(args.release_notes_verified),
        native_channel_ref=args.native_channel_ref,
        signature_subject=args.signature_subject,
        notarization_team_id=args.notarization_team_id,
        update_feed_ref=args.update_feed_ref,
        install_receipt_ref=args.install_receipt_ref,
        update_receipt_ref=args.update_receipt_ref,
        failure_recovery_receipt_ref=args.failure_recovery_receipt_ref,
        release_notes_ref=args.release_notes_ref,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
    return 0 if receipt["ok"] is True else 2


def run_host_shell_pilot_handoff(args: argparse.Namespace) -> int:
    from .host_shell_pilot_handoff import build_host_shell_pilot_handoff

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    handoff = build_host_shell_pilot_handoff(
        config,
        private_adapter_command=args.private_adapter_command,
        private_adapter_timeout_seconds=args.private_adapter_timeout_seconds,
        distribution_source=args.distribution_source,
        distribution_channel=args.distribution_channel,
        package_version=args.package_version,
        host_api_level=args.host_api_level,
        native_channel_verified=bool(args.native_channel_verified),
        signature_verified=bool(args.signature_verified),
        update_feed_verified=bool(args.update_feed_verified),
        install_verified=bool(args.install_verified),
        update_verified=bool(args.update_verified),
        failure_recovery_verified=bool(args.failure_recovery_verified),
        release_notes_verified=bool(args.release_notes_verified),
        native_channel_ref=args.native_channel_ref,
        signature_subject=args.signature_subject,
        notarization_team_id=args.notarization_team_id,
        update_feed_ref=args.update_feed_ref,
        install_receipt_ref=args.install_receipt_ref,
        update_receipt_ref=args.update_receipt_ref,
        failure_recovery_receipt_ref=args.failure_recovery_receipt_ref,
        release_notes_ref=args.release_notes_ref,
    )
    print(json.dumps(handoff, ensure_ascii=False, indent=2), flush=True)
    return 0 if handoff["ok"] is True else 2


def run_host_shell_pilot_preflight(args: argparse.Namespace) -> int:
    from .host_shell_pilot_preflight import build_host_shell_pilot_preflight

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    preflight = build_host_shell_pilot_preflight(
        config,
        private_adapter_command=args.private_adapter_command,
        applications_root=args.applications_root,
        home=args.home or None,
        path_env=args.path_env,
    )
    print(json.dumps(preflight, ensure_ascii=False, indent=2), flush=True)
    return 0 if preflight["ok"] is True else 2


def run_host_shell_pilot_runbook(args: argparse.Namespace) -> int:
    from .host_shell_pilot_runbook import build_host_shell_pilot_runbook

    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    runbook = build_host_shell_pilot_runbook(
        config,
        private_adapter_command=args.private_adapter_command,
        applications_root=args.applications_root,
        home=args.home or None,
        path_env=args.path_env,
        distribution_source=args.distribution_source,
        distribution_channel=args.distribution_channel,
        package_version=args.package_version,
        host_api_level=args.host_api_level,
        native_channel_verified=bool(args.native_channel_verified),
        signature_verified=bool(args.signature_verified),
        update_feed_verified=bool(args.update_feed_verified),
        install_verified=bool(args.install_verified),
        update_verified=bool(args.update_verified),
        failure_recovery_verified=bool(args.failure_recovery_verified),
        release_notes_verified=bool(args.release_notes_verified),
        native_channel_ref=args.native_channel_ref,
        signature_subject=args.signature_subject,
        notarization_team_id=args.notarization_team_id,
        update_feed_ref=args.update_feed_ref,
        install_receipt_ref=args.install_receipt_ref,
        update_receipt_ref=args.update_receipt_ref,
        failure_recovery_receipt_ref=args.failure_recovery_receipt_ref,
        release_notes_ref=args.release_notes_ref,
    )
    print(json.dumps(runbook, ensure_ascii=False, indent=2), flush=True)
    return 0 if runbook["ok"] is True else 2


def run_host_shell_pilot_request(args: argparse.Namespace) -> int:
    from .host_shell_pilot_request import build_host_shell_pilot_request

    request = build_host_shell_pilot_request(
        BridgeConfig(repo_root=Path(args.repo_root), runtime=args.runtime),
        request_id=args.request_id,
        pilot_owner=args.pilot_owner,
        expected_private_adapter_command_path=args.expected_private_adapter_command_path,
        artifact_root=args.artifact_root,
    )
    print(json.dumps(request, ensure_ascii=False, indent=2), flush=True)
    return 0


def run_host_shell_pilot_artifact_review(args: argparse.Namespace) -> int:
    from .host_shell_pilot_artifact_review import (
        build_host_shell_pilot_artifact_review_from_paths,
    )

    review = build_host_shell_pilot_artifact_review_from_paths(
        runtime=args.runtime,
        preflight_path=args.preflight_json,
        conformance_path=args.conformance_json,
        receipt_path=args.receipt_json,
        handoff_path=args.handoff_json,
    )
    print(json.dumps(review, ensure_ascii=False, indent=2), flush=True)
    return 0 if review["ok"] is True else 2


def run_host_shell_pilot_evidence_manifest(args: argparse.Namespace) -> int:
    from .host_shell_pilot_evidence_manifest import (
        artifact_paths_from_root,
        build_host_shell_pilot_evidence_manifest,
    )

    artifact_paths = artifact_paths_from_root(
        args.artifact_root,
        preflight_json=args.preflight_json,
        conformance_json=args.conformance_json,
        receipt_json=args.receipt_json,
        handoff_json=args.handoff_json,
        artifact_review_json=args.artifact_review_json,
        request_json=args.request_json,
        runbook_json=args.runbook_json,
    )
    manifest = build_host_shell_pilot_evidence_manifest(
        runtime=args.runtime,
        package_id=args.package_id,
        created_at=args.created_at,
        archive_filename=args.archive_filename,
        artifact_paths=artifact_paths,
        max_artifact_bytes=args.max_artifact_bytes,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if manifest["ok"] is True else 2


def run_process_preview(args: argparse.Namespace) -> int:
    config = bridge_config_from_args(args)
    errors = validate_start_config(config, require_tls_serving_files=False, require_provider_credentials=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    ownership = build_runtime_process_ownership(
        config,
        bridge_enabled=bool(args.bridge_enabled),
    )
    print(json.dumps(ownership, ensure_ascii=False, indent=2), flush=True)
    return 0


def bridge_config_from_args(args: argparse.Namespace) -> BridgeConfig:
    return BridgeConfig(
        repo_root=Path(args.repo_root),
        host=args.host,
        port=args.port,
        lan=args.lan,
        bonjour=args.bonjour,
        bonjour_host=args.bonjour_host,
        bonjour_name=args.bonjour_name,
        pairing_code=args.pairing_code,
        runtime=args.runtime,
        provider=getattr(args, "provider", "fake"),
        installed=args.installed,
        start_with_runtime=args.start_with_runtime,
        process_state=args.process_state,
        process_supervision=args.process_supervision,
        health_status=args.health_status,
        port_conflict=args.port_conflict,
        photo_provider=args.photo_provider,
        photo_pack_root=args.photo_pack_root,
        vision_provider=args.vision_provider,
        vision_endpoint=args.vision_endpoint,
        recall_search_provider=args.recall_search_provider,
        recall_search_endpoint=args.recall_search_endpoint,
        pairing_mode=args.pairing_mode,
        pairing_code_ttl_seconds=args.pairing_code_ttl_seconds,
        token_ttl_seconds=args.token_ttl_seconds,
        trusted_local_tls=args.trusted_local_tls,
        tls_trust_state=args.tls_trust_state,
        tls_certificate_label=args.tls_certificate_label,
        tls_public_key_sha256=getattr(args, "tls_public_key_sha256", ""),
        tls_certificate_chain_path=getattr(args, "tls_certificate_chain_path", ""),
        tls_private_key_path=args.tls_private_key_path,
        hermes_home=args.hermes_home,
        hermes_profile=args.hermes_profile,
        env_file=args.env_file,
        runtime_store_path=args.runtime_store_path,
        input_assets_days=getattr(args, "input_assets_days", DEFAULT_INPUT_ASSETS_DAYS),
        output_assets_days=getattr(args, "output_assets_days", DEFAULT_OUTPUT_ASSETS_DAYS),
        task_history_days=getattr(args, "task_history_days", DEFAULT_TASK_HISTORY_DAYS),
    )


def _add_pairing_security_arguments(parser_for_command: argparse.ArgumentParser) -> None:
    parser_for_command.add_argument("--pairing-mode", default="development", choices=PAIRING_MODE_CHOICES)
    parser_for_command.add_argument("--pairing-code-ttl-seconds", default=120, type=int)
    parser_for_command.add_argument("--token-ttl-seconds", default=0, type=int)
    parser_for_command.add_argument("--trusted-local-tls", action="store_true")
    parser_for_command.add_argument("--tls-trust-state", default="not_configured")
    parser_for_command.add_argument("--tls-certificate-label", default="")
    parser_for_command.add_argument("--tls-public-key-sha256", default="")
    parser_for_command.add_argument("--tls-certificate-chain-path", default="")
    parser_for_command.add_argument("--tls-private-key-path", default="")


def _add_process_ownership_arguments(parser_for_command: argparse.ArgumentParser) -> None:
    parser_for_command.add_argument("--installed", action="store_true")
    parser_for_command.add_argument("--start-with-runtime", action="store_true")
    parser_for_command.add_argument("--process-state", default="stopped", choices=PROCESS_STATE_CHOICES)
    parser_for_command.add_argument("--process-supervision", default="not_configured", choices=PROCESS_SUPERVISION_CHOICES)
    parser_for_command.add_argument("--health-status", default="unknown", choices=HEALTH_STATUS_CHOICES)
    parser_for_command.add_argument("--port-conflict", action="store_true")


def _add_retention_policy_arguments(parser_for_command: argparse.ArgumentParser) -> None:
    parser_for_command.add_argument("--input-assets-days", default=DEFAULT_INPUT_ASSETS_DAYS, type=int)
    parser_for_command.add_argument("--output-assets-days", default=DEFAULT_OUTPUT_ASSETS_DAYS, type=int)
    parser_for_command.add_argument("--task-history-days", default=DEFAULT_TASK_HISTORY_DAYS, type=int)


def _add_intelligence_provider_arguments(parser_for_command: argparse.ArgumentParser) -> None:
    parser_for_command.add_argument(
        "--provider",
        default="fake",
        choices=INTELLIGENCE_PROVIDER_CHOICES,
        help="General intelligence provider for vision and intake. Default keeps deterministic fake behavior.",
    )


def _add_host_package_distribution_arguments(parser_for_command: argparse.ArgumentParser) -> None:
    parser_for_command.add_argument(
        "--distribution-source",
        default="local_checkout",
        choices=DISTRIBUTION_SOURCE_CHOICES,
    )
    parser_for_command.add_argument("--distribution-channel", default="development")
    parser_for_command.add_argument("--package-version", default="development")
    parser_for_command.add_argument("--host-api-level", default="preview")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaka-mobile-runtime-kit",
        description="Explicit local launcher for Kaka Mobile Bridge development and runtime adapters.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local runtime-kit prerequisites without printing secrets.")
    doctor.add_argument("--repo-root", default=".", help="Kaka repository root.")
    doctor.add_argument("--photo-pack-root", default="photo-pack", help="Photo Pack root relative to repo root.")
    _add_intelligence_provider_arguments(doctor)
    doctor.set_defaults(func=run_doctor)

    start = subparsers.add_parser("start", help="Explicitly start the local Mobile Bridge.")
    start.add_argument("--repo-root", default=".", help="Kaka repository root.")
    start.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    start.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    start.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    start.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    start.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    start.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    start.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    start.add_argument("--runtime", default="hermes", help="Runtime id, for example hermes, openclaw, or sidecar.")
    _add_intelligence_provider_arguments(start)
    start.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    start.add_argument("--photo-pack-root", default="photo-pack")
    start.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    start.add_argument("--vision-endpoint", default="")
    start.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    start.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(start)
    _add_process_ownership_arguments(start)
    start.add_argument("--hermes-home", default="")
    start.add_argument("--hermes-profile", default="")
    start.add_argument("--env-file", default="")
    start.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    _add_retention_policy_arguments(start)
    start.add_argument("--dry-run", action="store_true", help="Print the exact server command but do not start it.")
    start.set_defaults(func=run_start)

    settings = subparsers.add_parser(
        "settings-preview",
        help="Print a runtime-side Hermes/OpenClaw settings UI contract without starting the bridge.",
    )
    settings.add_argument("--repo-root", default=".", help="Kaka repository root.")
    settings.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    settings.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    settings.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    settings.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    settings.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    settings.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    settings.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    settings.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    settings.add_argument("--runtime", default="hermes", help="Runtime id, for example hermes, openclaw, or sidecar.")
    _add_intelligence_provider_arguments(settings)
    settings.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    settings.add_argument("--photo-pack-root", default="photo-pack")
    settings.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    settings.add_argument("--vision-endpoint", default="")
    settings.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    settings.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(settings)
    _add_process_ownership_arguments(settings)
    settings.add_argument("--hermes-home", default="")
    settings.add_argument("--hermes-profile", default="")
    settings.add_argument("--env-file", default="")
    settings.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    _add_retention_policy_arguments(settings)
    settings.set_defaults(func=run_settings_preview)

    connection_qa = subparsers.add_parser(
        "connection-qa-preview",
        help="Print a deterministic ordinary-user first-run connection QA report without starting the bridge.",
    )
    connection_qa.add_argument("--repo-root", default=".", help="Kaka repository root.")
    connection_qa.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    connection_qa.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    connection_qa.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    connection_qa.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    connection_qa.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    connection_qa.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    connection_qa.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    connection_qa.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    connection_qa.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(connection_qa)
    connection_qa.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    connection_qa.add_argument("--photo-pack-root", default="photo-pack")
    connection_qa.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    connection_qa.add_argument("--vision-endpoint", default="")
    connection_qa.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    connection_qa.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(connection_qa)
    _add_process_ownership_arguments(connection_qa)
    connection_qa.add_argument("--hermes-home", default="")
    connection_qa.add_argument("--hermes-profile", default="")
    connection_qa.add_argument("--env-file", default="")
    connection_qa.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    connection_qa.set_defaults(func=run_connection_qa_preview)

    package = subparsers.add_parser(
        "package-preview",
        help="Print a native Hermes/OpenClaw package shell contract without starting the bridge.",
    )
    package.add_argument("--repo-root", default=".", help="Kaka repository root.")
    package.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    package.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    package.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    package.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    package.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    package.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    package.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    package.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    package.add_argument("--runtime", default="hermes", help="Runtime id, for example hermes, openclaw, or sidecar.")
    _add_intelligence_provider_arguments(package)
    package.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    package.add_argument("--photo-pack-root", default="photo-pack")
    package.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    package.add_argument("--vision-endpoint", default="")
    package.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    package.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(package)
    _add_process_ownership_arguments(package)
    package.add_argument("--hermes-home", default="")
    package.add_argument("--hermes-profile", default="")
    package.add_argument("--env-file", default="")
    package.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    _add_retention_policy_arguments(package)
    package.set_defaults(func=run_package_preview)

    host_package = subparsers.add_parser(
        "host-package-preview",
        help="Print the host-native Hermes/OpenClaw package handoff contract without starting the bridge.",
    )
    host_package.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_package.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    host_package.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_package.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_package.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_package.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_package.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_package.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_package.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_package.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_package)
    host_package.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_package.add_argument("--photo-pack-root", default="photo-pack")
    host_package.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_package.add_argument("--vision-endpoint", default="")
    host_package.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_package.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_package)
    _add_process_ownership_arguments(host_package)
    _add_host_package_distribution_arguments(host_package)
    host_package.add_argument("--hermes-home", default="")
    host_package.add_argument("--hermes-profile", default="")
    host_package.add_argument("--env-file", default="")
    host_package.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_package.set_defaults(func=run_host_package_preview)

    host_extension = subparsers.add_parser(
        "host-extension-preview",
        help="Print the installable Hermes/OpenClaw Host Extension productization contract.",
    )
    host_extension.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_extension.set_defaults(func=run_host_extension_preview)

    host_extension_readiness = subparsers.add_parser(
        "host-extension-readiness",
        help="Print the P3.6 Host Extension distribution readiness contract.",
    )
    host_extension_readiness.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_extension_readiness.add_argument("--install-command", default="")
    host_extension_readiness.add_argument("--update-channel", default="")
    host_extension_readiness.add_argument("--adapter-command-location", default="")
    host_extension_readiness.add_argument("--host-ui-entrypoint", default="")
    host_extension_readiness.add_argument("--signed-package-ref", default="")
    host_extension_readiness.add_argument("--signature-ref", default="")
    host_extension_readiness.add_argument("--conformance-report-ref", default="")
    host_extension_readiness.add_argument("--evidence-manifest-ref", default="")
    host_extension_readiness.set_defaults(func=run_host_extension_readiness)

    host_extension_material_intake = subparsers.add_parser(
        "host-extension-material-intake",
        help="Review a local Host Extension materials manifest without installing or fetching refs.",
    )
    host_extension_material_intake.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Runtime id expected for the Host Extension materials manifest.",
    )
    host_extension_material_intake.add_argument(
        "--manifest",
        required=True,
        help="Path to the host-supplied Host Extension materials manifest.",
    )
    host_extension_material_intake.set_defaults(func=run_host_extension_material_intake)

    host_extension_starter = subparsers.add_parser(
        "host-extension-starter-kit",
        help="Print or write a safe Hermes/OpenClaw Host Extension starter package scaffold.",
    )
    host_extension_starter.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_extension_starter.add_argument(
        "--output-dir",
        default="",
        help="Parent directory for --write output. Preview mode records the intended root only.",
    )
    host_extension_starter.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write a starter package tree. This does not install, start, bind LAN, "
            "advertise Bonjour, or invoke private commands."
        ),
    )
    host_extension_starter.set_defaults(func=run_host_extension_starter_kit)

    host_extension_install = subparsers.add_parser(
        "host-extension-install-package",
        help="Print or write a host-team installable Plugin/Skill package handoff.",
    )
    host_extension_install.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_extension_install.add_argument(
        "--output-dir",
        default="",
        help="Parent directory for --write output. Preview mode records the intended root only.",
    )
    host_extension_install.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write a package handoff tree. This does not install, start, bind LAN, "
            "advertise Bonjour, or invoke private commands."
        ),
    )
    host_extension_install.set_defaults(func=run_host_extension_install_package)

    host_plugin_skill_devkit = subparsers.add_parser(
        "host-plugin-skill-devkit",
        help="Print or write a host-team Hermes/OpenClaw Plugin/Skill development materials bundle.",
    )
    host_plugin_skill_devkit.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_plugin_skill_devkit.add_argument(
        "--output-dir",
        default="",
        help="Parent directory for --write output. Preview mode records the intended root only.",
    )
    host_plugin_skill_devkit.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write a devkit tree. This does not install, sign, publish, start, "
            "bind LAN, advertise Bonjour, run conformance, or invoke private commands."
        ),
    )
    host_plugin_skill_devkit.set_defaults(func=run_host_plugin_skill_devkit)

    host_codex_developer_plugin_source = subparsers.add_parser(
        "host-codex-developer-plugin-source",
        help="Print or write a host-team Codex developer plugin source tree without installing it.",
    )
    host_codex_developer_plugin_source.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host extension runtime id.",
    )
    host_codex_developer_plugin_source.add_argument(
        "--output-dir",
        default="",
        help="Parent directory for --write output. Preview mode records the intended plugin source root only.",
    )
    host_codex_developer_plugin_source.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write a developer plugin source tree. This does not install Codex plugins, "
            "write marketplaces, write user-home directories, or install host packages."
        ),
    )
    host_codex_developer_plugin_source.set_defaults(func=run_host_codex_developer_plugin_source)

    local_tls_readiness = subparsers.add_parser(
        "local-tls-readiness",
        help="Print the read-only local TLS certificate readiness contract.",
    )
    local_tls_readiness.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Runtime id for the TLS readiness report.",
    )
    local_tls_readiness.add_argument("--tls-trust-state", default="not_configured")
    local_tls_readiness.add_argument("--tls-certificate-label", default="")
    local_tls_readiness.add_argument("--tls-certificate-ref", default="")
    local_tls_readiness.add_argument("--tls-public-key-sha256", default="")
    local_tls_readiness.add_argument("--tls-expires-at", default="")
    local_tls_readiness.add_argument("--trust-store-ref", default="")
    local_tls_readiness.add_argument("--renewal-procedure-ref", default="")
    local_tls_readiness.set_defaults(func=run_local_tls_readiness)

    local_renderer_readiness = subparsers.add_parser(
        "local-renderer-backend-readiness",
        help="Run a read-only local recipe renderer backend readiness probe.",
    )
    local_renderer_readiness.add_argument("--repo-root", default=".", help="Kaka repository root.")
    local_renderer_readiness.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    local_renderer_readiness.add_argument("--photo-pack-root", default="photo-pack")
    local_renderer_readiness.set_defaults(func=run_local_renderer_backend_readiness)

    local_renderer_capability_manifest = subparsers.add_parser(
        "local-renderer-backend-capability-manifest",
        help="Print the read-only local renderer backend capability planning manifest.",
    )
    local_renderer_capability_manifest.add_argument("--repo-root", default=".", help="Kaka repository root.")
    local_renderer_capability_manifest.add_argument("--photo-pack-root", default="photo-pack")
    local_renderer_capability_manifest.set_defaults(func=run_local_renderer_backend_capability_manifest)

    recall_retrieval_readiness = subparsers.add_parser(
        "recall-retrieval-readiness",
        help="Print the read-only production Recall retrieval packaging readiness contract.",
    )
    recall_retrieval_readiness.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Runtime id for the Recall retrieval readiness report.",
    )
    recall_retrieval_readiness.add_argument(
        "--strategy",
        default="sidecar_adapter",
        choices=RECALL_RETRIEVAL_STRATEGIES,
        help="Production packaging strategy being prepared by the host runtime.",
    )
    recall_retrieval_readiness.add_argument("--adapter-package-ref", default="")
    recall_retrieval_readiness.add_argument("--runtime-settings-ui-ref", default="")
    recall_retrieval_readiness.add_argument("--signature-ref", default="")
    recall_retrieval_readiness.add_argument("--conformance-report-ref", default="")
    recall_retrieval_readiness.add_argument("--privacy-review-ref", default="")
    recall_retrieval_readiness.add_argument("--fallback-drill-ref", default="")
    recall_retrieval_readiness.add_argument("--release-notes-ref", default="")
    recall_retrieval_readiness.set_defaults(func=run_recall_retrieval_readiness)

    recall_retrieval_material_intake = subparsers.add_parser(
        "recall-retrieval-material-intake",
        help="Review a local Recall retrieval materials manifest without fetching refs.",
    )
    recall_retrieval_material_intake.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Runtime id expected for the Recall retrieval materials manifest.",
    )
    recall_retrieval_material_intake.add_argument(
        "--materials-json",
        required=True,
        help="Path to the host/runtime-supplied Recall retrieval materials manifest.",
    )
    recall_retrieval_material_intake.set_defaults(func=run_recall_retrieval_material_intake)

    retention_purge = subparsers.add_parser(
        "retention-purge",
        help="Explicitly dry-run or apply runtime-owned retention cleanup and print a purge receipt.",
    )
    retention_purge.add_argument("--runtime", default="hermes", help="Runtime id.")
    retention_purge.add_argument("--runtime-store-path", default="", help="Runtime-owned SQLite store path.")
    retention_purge.add_argument("--now", default="", help="UTC ISO timestamp used for deterministic purge cutoffs.")
    retention_purge.add_argument("--dry-run", action="store_true", help="Print would-delete receipt without deleting.")
    retention_purge.add_argument("--apply", action="store_true", help="Apply explicit runtime-owned cleanup.")
    _add_retention_policy_arguments(retention_purge)
    retention_purge.set_defaults(func=run_retention_purge)

    host_adapter = subparsers.add_parser(
        "host-adapter-run",
        help="Run a Runtime Kit host adapter action and print its structured result.",
    )
    host_adapter.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_adapter.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    host_adapter.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_adapter.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_adapter.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_adapter.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_adapter.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_adapter.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_adapter.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_adapter.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_adapter)
    host_adapter.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_adapter.add_argument("--photo-pack-root", default="photo-pack")
    host_adapter.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_adapter.add_argument("--vision-endpoint", default="")
    host_adapter.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_adapter.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_adapter)
    _add_process_ownership_arguments(host_adapter)
    host_adapter.add_argument("--hermes-home", default="")
    host_adapter.add_argument("--hermes-profile", default="")
    host_adapter.add_argument("--env-file", default="")
    host_adapter.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_adapter.add_argument("--adapter", default="mock", choices=("mock", "private"))
    host_adapter.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-provided private adapter command for --adapter private.",
    )
    host_adapter.add_argument(
        "--private-adapter-timeout-seconds",
        default=10.0,
        type=float,
        help="Timeout for the host-provided private adapter command.",
    )
    host_adapter.add_argument("--action-id", required=True, choices=HOST_PACKAGE_ACTIONS)
    host_adapter.add_argument("--approved", action="store_true")
    host_adapter.set_defaults(func=run_host_adapter_run)

    host_private_conformance = subparsers.add_parser(
        "host-private-adapter-conformance",
        help="Run host-owned private adapter conformance checks and print a structured report.",
    )
    host_private_conformance.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_private_conformance.add_argument(
        "--bridge-enabled",
        action="store_true",
        help="Preview the bridge as enabled in runtime UI.",
    )
    host_private_conformance.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_private_conformance.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_private_conformance.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_private_conformance.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_private_conformance.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_private_conformance.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_private_conformance.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_private_conformance.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_private_conformance)
    host_private_conformance.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_private_conformance.add_argument("--photo-pack-root", default="photo-pack")
    host_private_conformance.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_private_conformance.add_argument("--vision-endpoint", default="")
    host_private_conformance.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_private_conformance.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_private_conformance)
    _add_process_ownership_arguments(host_private_conformance)
    host_private_conformance.add_argument("--hermes-home", default="")
    host_private_conformance.add_argument("--hermes-profile", default="")
    host_private_conformance.add_argument("--env-file", default="")
    host_private_conformance.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_private_conformance.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-provided private adapter command to validate.",
    )
    host_private_conformance.add_argument(
        "--private-adapter-timeout-seconds",
        default=10.0,
        type=float,
        help="Timeout for the host-provided private adapter command.",
    )
    host_private_conformance.add_argument(
        "--skip-negative-checks",
        action="store_true",
        help="Skip approval and disabled-action no-call checks.",
    )
    host_private_conformance.set_defaults(func=run_host_private_adapter_conformance)

    host_shell_pilot = subparsers.add_parser(
        "host-shell-pilot-report",
        help="Print a P3.4 external host-shell pilot readiness receipt.",
    )
    host_shell_pilot.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_shell_pilot.add_argument(
        "--bridge-enabled",
        action="store_true",
        help="Preview the bridge as enabled in runtime UI.",
    )
    host_shell_pilot.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_shell_pilot.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_shell_pilot.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_shell_pilot.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_shell_pilot.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_shell_pilot.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_shell_pilot.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_shell_pilot.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_shell_pilot)
    host_shell_pilot.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_shell_pilot.add_argument("--photo-pack-root", default="photo-pack")
    host_shell_pilot.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_shell_pilot.add_argument("--vision-endpoint", default="")
    host_shell_pilot.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_shell_pilot.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_shell_pilot)
    _add_process_ownership_arguments(host_shell_pilot)
    _add_host_package_distribution_arguments(host_shell_pilot)
    host_shell_pilot.add_argument("--hermes-home", default="")
    host_shell_pilot.add_argument("--hermes-profile", default="")
    host_shell_pilot.add_argument("--env-file", default="")
    host_shell_pilot.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_shell_pilot.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-owned private adapter command for the external pilot.",
    )
    host_shell_pilot.add_argument(
        "--private-adapter-timeout-seconds",
        default=10.0,
        type=float,
        help="Timeout for the host-owned private adapter command.",
    )
    host_shell_pilot.add_argument("--native-channel-verified", action="store_true")
    host_shell_pilot.add_argument("--signature-verified", action="store_true")
    host_shell_pilot.add_argument("--update-feed-verified", action="store_true")
    host_shell_pilot.add_argument("--install-verified", action="store_true")
    host_shell_pilot.add_argument("--update-verified", action="store_true")
    host_shell_pilot.add_argument("--failure-recovery-verified", action="store_true")
    host_shell_pilot.add_argument("--release-notes-verified", action="store_true")
    host_shell_pilot.add_argument("--native-channel-ref", default="")
    host_shell_pilot.add_argument("--signature-subject", default="")
    host_shell_pilot.add_argument("--notarization-team-id", default="")
    host_shell_pilot.add_argument("--update-feed-ref", default="")
    host_shell_pilot.add_argument("--install-receipt-ref", default="")
    host_shell_pilot.add_argument("--update-receipt-ref", default="")
    host_shell_pilot.add_argument("--failure-recovery-receipt-ref", default="")
    host_shell_pilot.add_argument("--release-notes-ref", default="")
    host_shell_pilot.set_defaults(func=run_host_shell_pilot_report)

    host_shell_handoff = subparsers.add_parser(
        "host-shell-pilot-handoff",
        help="Print a P3.4 external host-shell pilot handoff bundle.",
    )
    host_shell_handoff.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_shell_handoff.add_argument(
        "--bridge-enabled",
        action="store_true",
        help="Preview the bridge as enabled in runtime UI.",
    )
    host_shell_handoff.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_shell_handoff.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_shell_handoff.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_shell_handoff.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_shell_handoff.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_shell_handoff.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_shell_handoff.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_shell_handoff.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_shell_handoff)
    host_shell_handoff.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_shell_handoff.add_argument("--photo-pack-root", default="photo-pack")
    host_shell_handoff.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_shell_handoff.add_argument("--vision-endpoint", default="")
    host_shell_handoff.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_shell_handoff.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_shell_handoff)
    _add_process_ownership_arguments(host_shell_handoff)
    _add_host_package_distribution_arguments(host_shell_handoff)
    host_shell_handoff.add_argument("--hermes-home", default="")
    host_shell_handoff.add_argument("--hermes-profile", default="")
    host_shell_handoff.add_argument("--env-file", default="")
    host_shell_handoff.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_shell_handoff.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-owned private adapter command for the external pilot.",
    )
    host_shell_handoff.add_argument(
        "--private-adapter-timeout-seconds",
        default=10.0,
        type=float,
        help="Timeout for the host-owned private adapter command.",
    )
    host_shell_handoff.add_argument("--native-channel-verified", action="store_true")
    host_shell_handoff.add_argument("--signature-verified", action="store_true")
    host_shell_handoff.add_argument("--update-feed-verified", action="store_true")
    host_shell_handoff.add_argument("--install-verified", action="store_true")
    host_shell_handoff.add_argument("--update-verified", action="store_true")
    host_shell_handoff.add_argument("--failure-recovery-verified", action="store_true")
    host_shell_handoff.add_argument("--release-notes-verified", action="store_true")
    host_shell_handoff.add_argument("--native-channel-ref", default="")
    host_shell_handoff.add_argument("--signature-subject", default="")
    host_shell_handoff.add_argument("--notarization-team-id", default="")
    host_shell_handoff.add_argument("--update-feed-ref", default="")
    host_shell_handoff.add_argument("--install-receipt-ref", default="")
    host_shell_handoff.add_argument("--update-receipt-ref", default="")
    host_shell_handoff.add_argument("--failure-recovery-receipt-ref", default="")
    host_shell_handoff.add_argument("--release-notes-ref", default="")
    host_shell_handoff.set_defaults(func=run_host_shell_pilot_handoff)

    host_shell_preflight = subparsers.add_parser(
        "host-shell-pilot-preflight",
        help="Print a read-only P3.4 host-shell pilot preflight report.",
    )
    host_shell_preflight.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_shell_preflight.add_argument(
        "--bridge-enabled",
        action="store_true",
        help="Preview the bridge as enabled in runtime UI.",
    )
    host_shell_preflight.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_shell_preflight.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_shell_preflight.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_shell_preflight.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_shell_preflight.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_shell_preflight.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_shell_preflight.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_shell_preflight.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_shell_preflight)
    host_shell_preflight.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_shell_preflight.add_argument("--photo-pack-root", default="photo-pack")
    host_shell_preflight.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_shell_preflight.add_argument("--vision-endpoint", default="")
    host_shell_preflight.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_shell_preflight.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_shell_preflight)
    _add_process_ownership_arguments(host_shell_preflight)
    host_shell_preflight.add_argument("--hermes-home", default="")
    host_shell_preflight.add_argument("--hermes-profile", default="")
    host_shell_preflight.add_argument("--env-file", default="")
    host_shell_preflight.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_shell_preflight.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-owned private adapter command to check without invoking it.",
    )
    host_shell_preflight.add_argument(
        "--applications-root",
        default="/Applications",
        help="Applications directory to inspect for host shells.",
    )
    host_shell_preflight.add_argument(
        "--home",
        default="",
        help="Home directory used to expand well-known host adapter paths.",
    )
    host_shell_preflight.add_argument(
        "--path-env",
        default=None,
        help="PATH value to inspect for informational command discovery.",
    )
    host_shell_preflight.set_defaults(func=run_host_shell_pilot_preflight)

    host_shell_runbook = subparsers.add_parser(
        "host-shell-pilot-runbook",
        help="Print a read-only P3.4 host-shell pilot runbook.",
    )
    host_shell_runbook.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_shell_runbook.add_argument(
        "--bridge-enabled",
        action="store_true",
        help="Preview the bridge as enabled in runtime UI.",
    )
    host_shell_runbook.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    host_shell_runbook.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    host_shell_runbook.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    host_shell_runbook.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    host_shell_runbook.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    host_shell_runbook.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    host_shell_runbook.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    host_shell_runbook.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    _add_intelligence_provider_arguments(host_shell_runbook)
    host_shell_runbook.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    host_shell_runbook.add_argument("--photo-pack-root", default="photo-pack")
    host_shell_runbook.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    host_shell_runbook.add_argument("--vision-endpoint", default="")
    host_shell_runbook.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    host_shell_runbook.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(host_shell_runbook)
    _add_process_ownership_arguments(host_shell_runbook)
    _add_host_package_distribution_arguments(host_shell_runbook)
    host_shell_runbook.add_argument("--hermes-home", default="")
    host_shell_runbook.add_argument("--hermes-profile", default="")
    host_shell_runbook.add_argument("--env-file", default="")
    host_shell_runbook.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    host_shell_runbook.add_argument(
        "--private-adapter-command",
        default="",
        help="Host-owned private adapter command to include without invoking it.",
    )
    host_shell_runbook.add_argument(
        "--applications-root",
        default="/Applications",
        help="Applications directory to inspect for host shells.",
    )
    host_shell_runbook.add_argument(
        "--home",
        default="",
        help="Home directory used to expand well-known host adapter paths.",
    )
    host_shell_runbook.add_argument(
        "--path-env",
        default=None,
        help="PATH value to inspect for informational command discovery.",
    )
    host_shell_runbook.add_argument("--native-channel-verified", action="store_true")
    host_shell_runbook.add_argument("--signature-verified", action="store_true")
    host_shell_runbook.add_argument("--update-feed-verified", action="store_true")
    host_shell_runbook.add_argument("--install-verified", action="store_true")
    host_shell_runbook.add_argument("--update-verified", action="store_true")
    host_shell_runbook.add_argument("--failure-recovery-verified", action="store_true")
    host_shell_runbook.add_argument("--release-notes-verified", action="store_true")
    host_shell_runbook.add_argument("--native-channel-ref", default="")
    host_shell_runbook.add_argument("--signature-subject", default="")
    host_shell_runbook.add_argument("--notarization-team-id", default="")
    host_shell_runbook.add_argument("--update-feed-ref", default="")
    host_shell_runbook.add_argument("--install-receipt-ref", default="")
    host_shell_runbook.add_argument("--update-receipt-ref", default="")
    host_shell_runbook.add_argument("--failure-recovery-receipt-ref", default="")
    host_shell_runbook.add_argument("--release-notes-ref", default="")
    host_shell_runbook.set_defaults(func=run_host_shell_pilot_runbook)

    host_shell_request = subparsers.add_parser(
        "host-shell-pilot-request",
        help="Print a read-only P3.4 host-shell pilot materials request.",
    )
    host_shell_request.add_argument("--repo-root", default=".", help="Kaka repository root.")
    host_shell_request.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    host_shell_request.add_argument(
        "--request-id",
        default="",
        help="Optional external pilot request identifier.",
    )
    host_shell_request.add_argument(
        "--pilot-owner",
        default="",
        help="Optional host team or release desk audience.",
    )
    host_shell_request.add_argument(
        "--expected-private-adapter-command-path",
        default="",
        help="Expected host-owned private adapter command path to request.",
    )
    host_shell_request.add_argument(
        "--artifact-root",
        default="",
        help="Suggested directory for generated pilot JSON artifacts.",
    )
    host_shell_request.set_defaults(func=run_host_shell_pilot_request)

    host_shell_artifact_review = subparsers.add_parser(
        "host-shell-pilot-artifact-review",
        help="Review P3.4 host-shell pilot JSON artifacts without running them.",
    )
    host_shell_artifact_review.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    host_shell_artifact_review.add_argument(
        "--preflight-json",
        default="",
        help="Path to a host-shell-pilot-preflight JSON artifact.",
    )
    host_shell_artifact_review.add_argument(
        "--conformance-json",
        default="",
        help="Path to a host-private-adapter-conformance JSON artifact.",
    )
    host_shell_artifact_review.add_argument(
        "--receipt-json",
        default="",
        help="Path to a host-shell-pilot-report JSON artifact.",
    )
    host_shell_artifact_review.add_argument(
        "--handoff-json",
        default="",
        help="Path to a host-shell-pilot-handoff JSON artifact.",
    )
    host_shell_artifact_review.set_defaults(func=run_host_shell_pilot_artifact_review)

    host_shell_evidence = subparsers.add_parser(
        "host-shell-pilot-evidence-manifest",
        help="Hash P3.4 host-shell pilot JSON artifacts into a non-mutating evidence manifest.",
    )
    host_shell_evidence.add_argument(
        "--runtime",
        default="hermes",
        choices=HOST_PACKAGE_RUNTIME_CHOICES,
        help="Host package runtime id.",
    )
    host_shell_evidence.add_argument(
        "--package-id",
        default="",
        help="Optional evidence package identifier.",
    )
    host_shell_evidence.add_argument(
        "--created-at",
        default="",
        help="Optional package creation timestamp.",
    )
    host_shell_evidence.add_argument(
        "--artifact-root",
        default="",
        help="Directory containing preflight/conformance/receipt/handoff/artifact-review JSON artifacts.",
    )
    host_shell_evidence.add_argument(
        "--preflight-json",
        default="",
        help="Path to a host-shell-pilot-preflight JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--conformance-json",
        default="",
        help="Path to a host-private-adapter-conformance JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--receipt-json",
        default="",
        help="Path to a host-shell-pilot-report JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--handoff-json",
        default="",
        help="Path to a host-shell-pilot-handoff JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--artifact-review-json",
        default="",
        help="Path to a host-shell-pilot-artifact-review JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--request-json",
        default="",
        help="Optional path to a host-shell-pilot-request JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--runbook-json",
        default="",
        help="Optional path to a host-shell-pilot-runbook JSON artifact.",
    )
    host_shell_evidence.add_argument(
        "--archive-filename",
        default="",
        help="Expected external archive filename; the command does not create it.",
    )
    host_shell_evidence.add_argument(
        "--max-artifact-bytes",
        default=1_048_576,
        type=int,
        help="Maximum size for each JSON artifact loaded into the manifest.",
    )
    host_shell_evidence.set_defaults(func=run_host_shell_pilot_evidence_manifest)

    process = subparsers.add_parser(
        "process-preview",
        help="Print the runtime-side process ownership contract without starting the bridge.",
    )
    process.add_argument("--repo-root", default=".", help="Kaka repository root.")
    process.add_argument("--bridge-enabled", action="store_true", help="Preview the bridge as enabled in runtime UI.")
    process.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    process.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    process.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    process.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    process.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    process.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    process.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    process.add_argument("--runtime", default="hermes", help="Runtime id, for example hermes, openclaw, or sidecar.")
    _add_intelligence_provider_arguments(process)
    process.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    process.add_argument("--photo-pack-root", default="photo-pack")
    process.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    process.add_argument("--vision-endpoint", default="")
    process.add_argument("--recall-search-provider", default="local", choices=RECALL_SEARCH_PROVIDER_CHOICES)
    process.add_argument("--recall-search-endpoint", default="")
    _add_pairing_security_arguments(process)
    _add_process_ownership_arguments(process)
    process.add_argument("--hermes-home", default="")
    process.add_argument("--hermes-profile", default="")
    process.add_argument("--env-file", default="")
    process.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    process.set_defaults(func=run_process_preview)

    url = subparsers.add_parser("pairing-url", help="Print the development pairing page URL.")
    url.add_argument("--host", default="127.0.0.1")
    url.add_argument("--port", default=DEFAULT_PORT, type=int)
    url.add_argument("--pairing-mode", default="development", choices=PAIRING_MODE_CHOICES)
    url.add_argument("--scheme", default="http", choices=("http", "https"))
    url.set_defaults(func=run_pairing_url)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if (
        getattr(args, "command", "") == "host-codex-developer-plugin-source"
        and getattr(args, "write", False)
        and not str(getattr(args, "output_dir", "")).strip()
    ):
        parser.error("host-codex-developer-plugin-source --write requires --output-dir")
    return int(args.func(args))


def _can_import_mock_bridge(mock_bridge_dir: Path) -> tuple[bool, str]:
    if not mock_bridge_dir.exists():
        return False, "mock_bridge directory missing"
    path = str(mock_bridge_dir.resolve())
    inserted = False
    if path not in sys.path:
        sys.path.insert(0, path)
        inserted = True
    try:
        importlib.import_module("agent_pocket_mock_bridge.server")
        return True, "agent_pocket_mock_bridge.server importable"
    except Exception as error:  # pragma: no cover - detail belongs in doctor output
        return False, f"{type(error).__name__}: {error}"
    finally:
        if inserted:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
