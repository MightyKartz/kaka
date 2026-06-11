from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any


HOST_PRIVATE_ADAPTER_REQUEST_SCHEMA_VERSION = "kaka.host_private_adapter_request.v1"
HOST_PRIVATE_ADAPTER_RESPONSE_SCHEMA_VERSION = "kaka.host_private_adapter_response.v1"

PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS = (
    "runtime_store_path",
    "recall_search_endpoint",
    "provider_keys",
    "auth_env_files",
    "mobile_tokens",
    "tls_private_key_paths",
    "env_file",
    "auth_file",
    "auth_files",
    "provider_credentials",
    "mobile_bearer_token",
    "tls_private_key_path",
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

PRIVATE_HOST_API_DETAIL_ALLOWLIST = (
    "private_api_called",
    "private_api_provider",
    "host_api_level",
    "url",
    "target",
    "checked_bridge",
    "enabled",
)

_HOST_ACTION_ALLOWLIST = (
    "id",
    "owner",
    "adapter",
    "mutates_host_state",
    "requires_explicit_user_approval",
    "runtime_side_only",
    "enabled",
    "label",
    "style",
    "target",
    "url",
)

_STATE_BOOL_FIELDS = ("installed", "start_with_runtime", "port_conflict")
_STATE_STRING_FIELDS = ("process_state", "process_supervision", "health_status")
_STATE_REQUIRED_FIELDS = _STATE_BOOL_FIELDS + _STATE_STRING_FIELDS
_PROCESS_STATE_VALUES = {"stopped", "running", "unhealthy", "unknown"}
_PROCESS_SUPERVISION_VALUES = {"not_configured", "host_managed", "misconfigured"}
_HEALTH_STATUS_VALUES = {"unknown", "healthy", "unhealthy"}
_RESPONSE_TOP_LEVEL_FIELDS = {
    "schema_version",
    "ok",
    "mutated_host_state",
    "state",
    "detail",
    "error",
}
_DETAIL_STRING_MAX_LENGTHS = {
    "private_api_provider": 64,
    "host_api_level": 64,
    "url": 2048,
    "target": 64,
}
_SAFE_ERROR_CODE = re.compile(r"^[a-z0-9_:-]{1,80}$")


def build_private_host_adapter_request(
    host_package: Mapping[str, object],
    *,
    action_id: str,
    approved: bool,
    adapter: str,
    state: Mapping[str, object],
) -> Mapping[str, object]:
    action = _host_action_by_id(host_package, action_id)
    return {
        "schema_version": HOST_PRIVATE_ADAPTER_REQUEST_SCHEMA_VERSION,
        "surface": "hermes_openclaw_host_private_adapter_command",
        "runtime": str(host_package.get("runtime", "unknown")),
        "action_id": action_id,
        "adapter": adapter,
        "approved": bool(approved),
        "runtime_side_only": True,
        "state": _safe_state(state),
        "host_action": _safe_action(action),
        "safety": {
            "phone_api_unchanged": True,
            "runtime_side_only": True,
            "phone_settings_owner": False,
            "no_autostart_on_install": True,
            "no_login_item_creation_by_runtime_kit": True,
        },
        "forbidden_phone_safe_fields": list(PRIVATE_HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS),
    }


def run_private_host_adapter_command(
    command: str,
    request: Mapping[str, object],
    *,
    timeout_seconds: float = 10,
) -> Mapping[str, object]:
    try:
        argv = _private_adapter_command_argv(command)
    except ValueError:
        return _safe_failure(
            "private_host_adapter_command_failed",
            "Private host adapter command is invalid.",
            request,
        )
    if not argv:
        return _safe_failure(
            "private_host_adapter_command_failed",
            "Private host adapter command is required.",
            request,
        )

    try:
        completed = subprocess.run(
            argv,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return _safe_failure(
            "private_host_adapter_timeout",
            "Private host adapter command timed out.",
            request,
        )
    except OSError:
        return _safe_failure(
            "private_host_adapter_command_failed",
            "Private host adapter command could not be launched.",
            request,
        )

    if completed.returncode != 0:
        return _safe_failure(
            "private_host_adapter_command_failed",
            "Private host adapter command exited with a non-zero status.",
            request,
        )

    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _safe_failure(
            "private_host_adapter_invalid_response",
            "Private host adapter command returned invalid JSON.",
            request,
        )

    return _normalize_private_response(response, request)


def _private_adapter_command_argv(command: str) -> list[str]:
    stripped = command.strip()
    if not stripped:
        return []
    path = Path(stripped).expanduser()
    if path.is_file():
        return [str(path)]
    return shlex.split(stripped)


def _normalize_private_response(
    response: Any,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(response, Mapping):
        return _invalid_response_failure(request)
    if set(response) - _RESPONSE_TOP_LEVEL_FIELDS:
        return _invalid_response_failure(request)
    if response.get("schema_version") != HOST_PRIVATE_ADAPTER_RESPONSE_SCHEMA_VERSION:
        return _invalid_response_failure(request)
    if not isinstance(response.get("ok"), bool):
        return _invalid_response_failure(request)
    if not isinstance(response.get("mutated_host_state"), bool):
        return _invalid_response_failure(request)

    state = response.get("state")
    if not _is_response_state(state):
        return _invalid_response_failure(request)
    detail = response.get("detail", {})
    if not _is_response_detail(detail):
        return _invalid_response_failure(request)
    if "error" in response and not _is_response_error(response["error"]):
        return _invalid_response_failure(request)

    ok = bool(response["ok"])
    result: dict[str, object] = {
        "ok": ok,
        "mutated_host_state": bool(response["mutated_host_state"]) if ok else False,
        "state": _safe_state(state),
        "detail": _safe_detail(detail),
    }
    result["detail"]["private_api_called"] = True
    if not ok:
        result["error"] = _safe_response_error(response.get("error"))
    return result


def _invalid_response_failure(request: Mapping[str, object]) -> Mapping[str, object]:
    return _safe_failure(
        "private_host_adapter_invalid_response",
        "Private host adapter command returned an invalid response.",
        request,
    )


def _safe_failure(
    code: str,
    message: str,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    return {
        "ok": False,
        "mutated_host_state": False,
        "state": _safe_state(_request_state(request)),
        "detail": {
            "private_api_called": True,
        },
        "error": {
            "code": code,
            "message": message,
        },
    }


def _safe_response_error(error: object) -> Mapping[str, object]:
    code = "private_host_adapter_host_error"
    if isinstance(error, Mapping):
        raw_code = error.get("code")
        if isinstance(raw_code, str) and _SAFE_ERROR_CODE.match(raw_code):
            code = raw_code
    return {
        "code": code,
        "message": "Private host adapter command returned an error.",
    }


def _safe_state(state: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key in _STATE_BOOL_FIELDS:
        if key in state:
            safe[key] = bool(state[key])
    for key in _STATE_STRING_FIELDS:
        if key in state:
            safe[key] = str(state[key])
    return safe


def _safe_detail(detail: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key in PRIVATE_HOST_API_DETAIL_ALLOWLIST:
        if key not in detail:
            continue
        value = detail[key]
        if isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, (int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:240]
    return safe


def _is_response_state(state: object) -> bool:
    if not isinstance(state, Mapping):
        return False
    if set(state) != set(_STATE_REQUIRED_FIELDS):
        return False
    for key in _STATE_BOOL_FIELDS:
        if not isinstance(state.get(key), bool):
            return False
    if state.get("process_state") not in _PROCESS_STATE_VALUES:
        return False
    if state.get("process_supervision") not in _PROCESS_SUPERVISION_VALUES:
        return False
    if state.get("health_status") not in _HEALTH_STATUS_VALUES:
        return False
    return True


def _is_response_detail(detail: object) -> bool:
    if not isinstance(detail, Mapping):
        return False
    if set(detail) - set(PRIVATE_HOST_API_DETAIL_ALLOWLIST):
        return False
    private_api_called = detail.get("private_api_called")
    if not isinstance(private_api_called, bool):
        return False
    for key, value in detail.items():
        if key in _DETAIL_STRING_MAX_LENGTHS:
            if not isinstance(value, str) or len(value) > _DETAIL_STRING_MAX_LENGTHS[key]:
                return False
        elif key in ("checked_bridge", "enabled"):
            if not isinstance(value, bool):
                return False
        elif key == "private_api_called":
            continue
        else:
            return False
    return True


def _is_response_error(error: object) -> bool:
    if not isinstance(error, Mapping):
        return False
    if set(error) != {"code", "message"}:
        return False
    code = error.get("code")
    message = error.get("message")
    return (
        isinstance(code, str)
        and len(code) <= 64
        and _SAFE_ERROR_CODE.match(code) is not None
        and isinstance(message, str)
        and len(message) <= 256
    )


def _safe_action(action: Mapping[str, object]) -> Mapping[str, object]:
    safe: dict[str, object] = {}
    for key in _HOST_ACTION_ALLOWLIST:
        if key in action:
            safe[key] = action[key]
    return safe


def _host_action_by_id(
    host_package: Mapping[str, object],
    action_id: str,
) -> Mapping[str, object]:
    actions = host_package.get("host_actions", [])
    if not isinstance(actions, list):
        return {}
    for action in actions:
        if isinstance(action, Mapping) and action.get("id") == action_id:
            return action
    return {}


def _request_state(request: Mapping[str, object]) -> Mapping[str, object]:
    state = request.get("state", {})
    if isinstance(state, Mapping):
        return state
    return {}
