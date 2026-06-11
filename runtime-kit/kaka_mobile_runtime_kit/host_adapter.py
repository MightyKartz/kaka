from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .private_host_api import (
    PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS,
    build_private_host_adapter_request,
    run_private_host_adapter_command,
)


HOST_ADAPTER_ACTIONS = (
    "install_runtime_package",
    "enable_start_with_runtime",
    "disable_start_with_runtime",
    "update_runtime_package",
    "uninstall_runtime_package",
    "open_runtime_logs",
    "run_health_check",
    "repair_port_conflict",
    "supervise_bridge",
)

HOST_ADAPTER_ACTION_ADAPTERS = {
    "install_runtime_package": "host_native_install",
    "enable_start_with_runtime": "host_native_enable_login_item",
    "disable_start_with_runtime": "host_native_disable_login_item",
    "update_runtime_package": "host_native_update",
    "uninstall_runtime_package": "host_native_uninstall",
    "open_runtime_logs": "host_native_open_logs",
    "run_health_check": "host_native_health_check",
    "repair_port_conflict": "host_native_repair_port",
    "supervise_bridge": "host_native_supervisor",
}

HOST_ADAPTER_MUTATING_ACTIONS = (
    "install_runtime_package",
    "enable_start_with_runtime",
    "disable_start_with_runtime",
    "update_runtime_package",
    "uninstall_runtime_package",
    "repair_port_conflict",
    "supervise_bridge",
)

HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS = PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS


@dataclass
class HostAdapterState:
    installed: bool = False
    start_with_runtime: bool = False
    process_state: str = "stopped"
    process_supervision: str = "not_configured"
    health_status: str = "unknown"
    port_conflict: bool = False

    @classmethod
    def from_host_package(cls, host_package: Mapping[str, object]) -> "HostAdapterState":
        process_ownership = host_package.get("process_ownership", {})
        state = {}
        if isinstance(process_ownership, Mapping):
            raw_state = process_ownership.get("state", {})
            if isinstance(raw_state, Mapping):
                state = raw_state

        return cls(
            installed=bool(state.get("installed", False)),
            start_with_runtime=bool(state.get("start_with_runtime", False)),
            process_state=str(state.get("process_state", "stopped")),
            process_supervision=str(
                state.get("process_supervision", state.get("supervision", "not_configured"))
            ),
            health_status=str(state.get("health_status", state.get("health", "unknown"))),
            port_conflict=bool(state.get("port_conflict", False)),
        )

    def as_result(self) -> Mapping[str, object]:
        return {
            "installed": self.installed,
            "start_with_runtime": self.start_with_runtime,
            "process_state": self.process_state,
            "process_supervision": self.process_supervision,
            "health_status": self.health_status,
            "port_conflict": self.port_conflict,
        }


def registered_host_adapter_actions() -> Mapping[str, str]:
    return dict(HOST_ADAPTER_ACTION_ADAPTERS)


def build_host_adapter_action_result(
    host_package: Mapping[str, object],
    *,
    action_id: str,
    approved: bool,
    adapter_mode: str = "mock",
    private_adapter_command: str = "",
    private_adapter_timeout_seconds: float = 10,
) -> Mapping[str, object]:
    if action_id not in HOST_ADAPTER_ACTION_ADAPTERS:
        raise ValueError(f"Unknown host adapter action: {action_id}")
    if adapter_mode not in ("mock", "private"):
        raise ValueError(f"Unsupported host adapter mode: {adapter_mode}")

    state = HostAdapterState.from_host_package(host_package)
    action = _host_action_by_id(host_package, action_id)
    adapter = HOST_ADAPTER_ACTION_ADAPTERS[action_id]
    is_mutating = action_id in HOST_ADAPTER_MUTATING_ACTIONS
    runtime = str(host_package.get("runtime", "unknown"))

    if is_mutating and not approved:
        return _result(
            host_package,
            action_id=action_id,
            adapter=adapter,
            adapter_mode=adapter_mode,
            approved=approved,
            state=state,
            ok=False,
            mutated_host_state=False,
            error={
                "code": "explicit_approval_required",
                "message": "This host action requires explicit user approval.",
            },
        )

    if adapter_mode == "private":
        if not private_adapter_command.strip():
            return _result(
                host_package,
                action_id=action_id,
                adapter=adapter,
                adapter_mode=adapter_mode,
                approved=approved,
                state=state,
                ok=False,
                mutated_host_state=False,
                error={
                    "code": "private_host_adapter_unavailable",
                    "message": f"{runtime} private host adapter APIs are not wired in Runtime Kit.",
                },
                detail={"private_api_called": False},
            )
        if action and action.get("enabled") is False:
            return _result(
                host_package,
                action_id=action_id,
                adapter=adapter,
                adapter_mode=adapter_mode,
                approved=approved,
                state=state,
                ok=False,
                mutated_host_state=False,
                error={
                    "code": "host_adapter_action_disabled",
                    "message": f"Host adapter action is disabled by the current runtime state: {action_id}",
                },
                detail=_action_detail(host_package, action),
            )
        request = build_private_host_adapter_request(
            host_package,
            action_id=action_id,
            approved=approved,
            adapter=adapter,
            state=state.as_result(),
        )
        private_result = run_private_host_adapter_command(
            private_adapter_command,
            request,
            timeout_seconds=private_adapter_timeout_seconds,
        )
        private_ok = bool(private_result.get("ok", False))
        private_state = _merge_private_state(state, private_result.get("state", {}))
        private_detail = private_result.get("detail", {})
        if not isinstance(private_detail, Mapping):
            private_detail = {}
        private_error = private_result.get("error")
        if not isinstance(private_error, Mapping):
            private_error = None
        return _result(
            host_package,
            action_id=action_id,
            adapter=adapter,
            adapter_mode=adapter_mode,
            approved=approved,
            state=private_state,
            ok=private_ok,
            mutated_host_state=bool(private_result.get("mutated_host_state", False))
            if private_ok and is_mutating
            else False,
            error=private_error,
            detail=private_detail,
        )

    if action and action.get("enabled") is False:
        return _result(
            host_package,
            action_id=action_id,
            adapter=adapter,
            adapter_mode=adapter_mode,
            approved=approved,
            state=state,
            ok=False,
            mutated_host_state=False,
            error={
                "code": "host_adapter_action_disabled",
                "message": f"Host adapter action is disabled by the current runtime state: {action_id}",
            },
            detail=_action_detail(host_package, action),
        )

    detail = _action_detail(host_package, action)
    mutated_host_state = _apply_mock_action(
        state,
        host_package=host_package,
        action_id=action_id,
        detail=detail,
    )
    return _result(
        host_package,
        action_id=action_id,
        adapter=adapter,
        adapter_mode=adapter_mode,
        approved=approved,
        state=state,
        ok=True,
        mutated_host_state=mutated_host_state,
        detail=detail,
    )


def _apply_mock_action(
    state: HostAdapterState,
    *,
    host_package: Mapping[str, object],
    action_id: str,
    detail: dict[str, object],
) -> bool:
    if action_id == "install_runtime_package":
        state.installed = True
        state.start_with_runtime = False
        state.process_state = "stopped"
        state.process_supervision = "not_configured"
        state.health_status = "unknown"
        state.port_conflict = False
        return True
    if action_id == "enable_start_with_runtime":
        state.start_with_runtime = True
        return True
    if action_id == "disable_start_with_runtime":
        state.start_with_runtime = False
        return True
    if action_id == "update_runtime_package":
        state.installed = True
        return True
    if action_id == "uninstall_runtime_package":
        state.installed = False
        state.start_with_runtime = False
        state.process_state = "stopped"
        state.process_supervision = "not_configured"
        state.health_status = "unknown"
        state.port_conflict = False
        return True
    if action_id == "repair_port_conflict":
        state.port_conflict = False
        return True
    if action_id == "supervise_bridge":
        state.process_supervision = "host_managed"
        return True
    if action_id == "open_runtime_logs":
        return False
    if action_id == "run_health_check":
        if _bridge_running(host_package):
            state.health_status = "healthy"
        detail.setdefault("checked_bridge", True)
    return False


def _result(
    host_package: Mapping[str, object],
    *,
    action_id: str,
    adapter: str,
    adapter_mode: str,
    approved: bool,
    state: HostAdapterState,
    ok: bool,
    mutated_host_state: bool,
    error: Mapping[str, object] | None = None,
    detail: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    result_detail = dict(detail or {})
    result: dict[str, object] = {
        "schema_version": "kaka.host_adapter_action_result.v1",
        "surface": "hermes_openclaw_host_adapter_binding",
        "runtime": str(host_package.get("runtime", "unknown")),
        "adapter_mode": adapter_mode,
        "action_id": action_id,
        "adapter": adapter,
        "ok": bool(ok),
        "mutated_host_state": bool(mutated_host_state),
        "explicit_user_approval": bool(approved),
        "runtime_side_only": True,
        "state": state.as_result(),
        "detail": result_detail,
        "safety": {
            "phone_api_unchanged": True,
            "runtime_side_only": True,
            "phone_settings_owner": False,
            "no_autostart_on_install": True,
            "no_login_item_creation_by_runtime_kit": True,
            "mock_does_not_mutate_host_os": adapter_mode == "mock",
            "private_host_api_called": adapter_mode == "private"
            and bool(result_detail.get("private_api_called", False)),
            "forbidden_phone_safe_fields": list(HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS),
        },
    }
    if error is not None:
        result["error"] = dict(error)
    return result


def _host_action_by_id(
    host_package: Mapping[str, object],
    action_id: str,
) -> Mapping[str, object]:
    raw_actions = host_package.get("host_actions", [])
    if not isinstance(raw_actions, list):
        return {}
    for action in raw_actions:
        if isinstance(action, Mapping) and action.get("id") == action_id:
            return action
    return {}


def _action_detail(
    host_package: Mapping[str, object],
    action: Mapping[str, object],
) -> dict[str, object]:
    detail: dict[str, object] = {}
    if "url" in action:
        detail["url"] = action["url"]
    if "target" in action:
        detail["target"] = action["target"]
    if action:
        detail["enabled"] = bool(action.get("enabled", False))
    detail["host_api_level"] = str(host_package.get("host_api_level", "preview"))
    return detail


def _bridge_running(host_package: Mapping[str, object]) -> bool:
    process_ownership = host_package.get("process_ownership", {})
    if not isinstance(process_ownership, Mapping):
        return False
    state = process_ownership.get("state", {})
    if not isinstance(state, Mapping):
        return False
    return bool(state.get("running", False))


def _merge_private_state(
    current: HostAdapterState,
    response_state: object,
) -> HostAdapterState:
    values = dict(current.as_result())
    if isinstance(response_state, Mapping):
        for key in ("installed", "start_with_runtime", "port_conflict"):
            if key in response_state:
                values[key] = bool(response_state[key])
        for key in ("process_state", "process_supervision", "health_status"):
            if key in response_state:
                values[key] = str(response_state[key])
    return HostAdapterState(
        installed=bool(values["installed"]),
        start_with_runtime=bool(values["start_with_runtime"]),
        process_state=str(values["process_state"]),
        process_supervision=str(values["process_supervision"]),
        health_status=str(values["health_status"]),
        port_conflict=bool(values["port_conflict"]),
    )
