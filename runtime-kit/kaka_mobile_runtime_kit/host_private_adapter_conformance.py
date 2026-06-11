from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from .cli import BridgeConfig, build_runtime_host_package
from .host_adapter import (
    HOST_ADAPTER_ACTIONS,
    HOST_ADAPTER_MUTATING_ACTIONS,
    build_host_adapter_action_result,
)
from .private_host_api import PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS


SCHEMA_VERSION = "kaka.host_private_adapter_conformance.v1"
SURFACE = "hermes_openclaw_host_private_adapter_conformance"
REQUIRED_CAPABILITIES = (
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


def build_host_private_adapter_conformance_report(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    private_adapter_timeout_seconds: float = 10,
    include_negative_checks: bool = True,
) -> Mapping[str, object]:
    cases = [
        _run_case(
            config,
            action_id=action_id,
            private_adapter_command=private_adapter_command,
            timeout_seconds=private_adapter_timeout_seconds,
        )
        for action_id in HOST_ADAPTER_ACTIONS
    ]
    negative_checks = (
        _negative_checks(
            config,
            private_adapter_command=private_adapter_command,
            timeout_seconds=private_adapter_timeout_seconds,
        )
        if include_negative_checks
        else []
    )
    passed = sum(1 for case in cases if case["ok"] is True)
    failed = len(cases) - passed
    ok = failed == 0 and all(case["ok"] is True for case in negative_checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": config.runtime,
        "ok": ok,
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "private_api_called": any(case["private_api_called"] is True for case in cases),
        "required_capabilities": list(REQUIRED_CAPABILITIES),
        "required_action_ids": list(HOST_ADAPTER_ACTIONS),
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": failed,
        },
        "cases": cases,
        "negative_checks": negative_checks,
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_autostart_on_install": True,
            "no_login_item_creation_by_runtime_kit": True,
            "forbidden_phone_safe_fields": list(PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS),
        },
    }


def _run_case(
    config: BridgeConfig,
    *,
    action_id: str,
    private_adapter_command: str,
    timeout_seconds: float,
) -> Mapping[str, object]:
    enabled_config, bridge_enabled = _enabled_config_for_action(config, action_id)
    is_mutating = action_id in HOST_ADAPTER_MUTATING_ACTIONS
    result = build_host_adapter_action_result(
        build_runtime_host_package(enabled_config, bridge_enabled=bridge_enabled),
        action_id=action_id,
        approved=is_mutating,
        adapter_mode="private",
        private_adapter_command=private_adapter_command,
        private_adapter_timeout_seconds=timeout_seconds,
    )
    return _case_summary(
        result,
        case_id=f"case_{action_id}",
        mutating=is_mutating,
        approved=is_mutating,
        expected_mutation=is_mutating,
    )


def _negative_checks(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    timeout_seconds: float,
) -> list[Mapping[str, object]]:
    unapproved = build_host_adapter_action_result(
        build_runtime_host_package(replace(config, installed=False), bridge_enabled=False),
        action_id="install_runtime_package",
        approved=False,
        adapter_mode="private",
        private_adapter_command=private_adapter_command,
        private_adapter_timeout_seconds=timeout_seconds,
    )
    disabled_health = build_host_adapter_action_result(
        build_runtime_host_package(replace(config, installed=True), bridge_enabled=False),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=private_adapter_command,
        private_adapter_timeout_seconds=timeout_seconds,
    )
    return [
        _negative_summary(
            unapproved,
            check_id="unapproved_install",
            expected_error_code="explicit_approval_required",
        ),
        _negative_summary(
            disabled_health,
            check_id="disabled_health_check",
            expected_error_code="host_adapter_action_disabled",
        ),
    ]


def _enabled_config_for_action(
    config: BridgeConfig,
    action_id: str,
) -> tuple[BridgeConfig, bool]:
    if action_id == "install_runtime_package":
        return replace(
            config,
            installed=False,
            start_with_runtime=False,
            process_state="stopped",
            process_supervision="not_configured",
            health_status="unknown",
            port_conflict=False,
        ), False
    if action_id == "enable_start_with_runtime":
        return replace(config, installed=True, start_with_runtime=False), False
    if action_id == "disable_start_with_runtime":
        return replace(config, installed=True, start_with_runtime=True), False
    if action_id == "update_runtime_package":
        return replace(config, installed=True), False
    if action_id == "uninstall_runtime_package":
        return replace(
            config,
            installed=True,
            start_with_runtime=True,
            process_state="stopped",
            process_supervision="not_configured",
            health_status="unknown",
            port_conflict=False,
        ), False
    if action_id == "open_runtime_logs":
        return replace(config, installed=True), False
    if action_id == "run_health_check":
        return replace(
            config,
            installed=True,
            process_state="running",
            process_supervision="host_managed",
            health_status="unknown",
            port_conflict=False,
        ), True
    if action_id == "repair_port_conflict":
        return replace(config, installed=True, port_conflict=True), False
    if action_id == "supervise_bridge":
        return replace(
            config,
            installed=True,
            process_supervision="not_configured",
        ), False
    raise ValueError(f"Unknown host adapter action: {action_id}")


def _case_summary(
    result: Mapping[str, object],
    *,
    case_id: str,
    mutating: bool,
    approved: bool,
    expected_mutation: bool,
) -> Mapping[str, object]:
    result_ok = bool(result.get("ok", False))
    mutated_host_state = bool(result.get("mutated_host_state", False))
    ok = result_ok and (not expected_mutation or mutated_host_state)
    return {
        "id": case_id,
        "action_id": str(result.get("action_id", "")),
        "adapter": str(result.get("adapter", "")),
        "adapter_mode": str(result.get("adapter_mode", "")),
        "ok": ok,
        "mutating": bool(mutating),
        "approved": bool(approved),
        "expected_mutation": bool(expected_mutation),
        "mutated_host_state": mutated_host_state,
        "private_api_called": _private_api_called(result),
        "error_code": _error_code(result),
        "state": _safe_state_summary(result.get("state", {})),
    }


def _negative_summary(
    result: Mapping[str, object],
    *,
    check_id: str,
    expected_error_code: str,
) -> Mapping[str, object]:
    private_api_called = _private_api_called(result)
    error_code = _error_code(result)
    return {
        "id": check_id,
        "ok": bool(result.get("ok") is False and not private_api_called and error_code == expected_error_code),
        "action_id": str(result.get("action_id", "")),
        "adapter": str(result.get("adapter", "")),
        "adapter_mode": str(result.get("adapter_mode", "")),
        "mutating": str(result.get("action_id", "")) in HOST_ADAPTER_MUTATING_ACTIONS,
        "approved": bool(result.get("explicit_user_approval", False)),
        "expected_mutation": False,
        "mutated_host_state": bool(result.get("mutated_host_state", False)),
        "private_api_called": private_api_called,
        "error_code": error_code,
        "state": _safe_state_summary(result.get("state", {})),
    }


def _private_api_called(result: Mapping[str, object]) -> bool:
    safety = result.get("safety", {})
    if isinstance(safety, Mapping) and "private_host_api_called" in safety:
        return bool(safety["private_host_api_called"])
    detail = result.get("detail", {})
    if isinstance(detail, Mapping):
        return bool(detail.get("private_api_called", False))
    return False


def _error_code(result: Mapping[str, object]) -> str | None:
    error = result.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        if isinstance(code, str):
            return code[:80]
    return None


def _safe_state_summary(state: object) -> Mapping[str, object]:
    if not isinstance(state, Mapping):
        return {}
    summary: dict[str, object] = {}
    for key in ("installed", "start_with_runtime", "port_conflict"):
        if key in state:
            summary[key] = bool(state[key])
    for key in ("process_state", "process_supervision", "health_status"):
        if key in state:
            summary[key] = str(state[key])[:40]
    return summary
