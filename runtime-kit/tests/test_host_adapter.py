import json
from pathlib import Path
import sys

import pytest

from kaka_mobile_runtime_kit.cli import BridgeConfig, build_runtime_host_package, main
from kaka_mobile_runtime_kit.host_adapter import (
    HOST_ADAPTER_ACTIONS,
    HOST_ADAPTER_ACTION_ADAPTERS,
    HOST_ADAPTER_MUTATING_ACTIONS,
    build_host_adapter_action_result,
    registered_host_adapter_actions,
)
from kaka_mobile_runtime_kit.private_host_api import build_private_host_adapter_request


def _fake_private_command(*args: str) -> str:
    command = f"{sys.executable} {Path('runtime-kit/tests/fixtures/fake_private_host_api.py')}"
    if args:
        command = f"{command} {' '.join(args)}"
    return command


def test_host_adapter_actions_match_host_package_contract():
    package = build_runtime_host_package(BridgeConfig(runtime="hermes"))

    assert [action["id"] for action in package["host_actions"]] == list(HOST_ADAPTER_ACTIONS)
    assert registered_host_adapter_actions() == HOST_ADAPTER_ACTION_ADAPTERS


def test_mock_host_adapter_requires_explicit_approval_for_mutating_actions():
    for action_id in HOST_ADAPTER_MUTATING_ACTIONS:
        result = build_host_adapter_action_result(
            build_runtime_host_package(BridgeConfig(runtime="hermes")),
            action_id=action_id,
            approved=False,
            adapter_mode="mock",
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "explicit_approval_required"
        assert result["mutated_host_state"] is False


def test_mock_host_adapter_install_does_not_start_or_create_login_item():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="hermes")),
        action_id="install_runtime_package",
        approved=True,
        adapter_mode="mock",
    )

    assert result["ok"] is True
    assert result["schema_version"] == "kaka.host_adapter_action_result.v1"
    assert result["surface"] == "hermes_openclaw_host_adapter_binding"
    assert result["runtime"] == "hermes"
    assert result["adapter_mode"] == "mock"
    assert result["action_id"] == "install_runtime_package"
    assert result["adapter"] == "host_native_install"
    assert result["mutated_host_state"] is True
    assert result["explicit_user_approval"] is True
    assert result["runtime_side_only"] is True
    assert result["state"] == {
        "installed": True,
        "start_with_runtime": False,
        "process_state": "stopped",
        "process_supervision": "not_configured",
        "health_status": "unknown",
        "port_conflict": False,
    }
    assert result["safety"]["no_autostart_on_install"] is True
    assert result["safety"]["no_login_item_creation_by_runtime_kit"] is True
    assert result["safety"]["phone_settings_owner"] is False
    assert "runtime_store_path" in result["safety"]["forbidden_phone_safe_fields"]
    assert "mobile_tokens" in result["safety"]["forbidden_phone_safe_fields"]


def test_mock_host_adapter_health_check_is_non_mutating_and_uses_bridge_health_url():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="openclaw", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="mock",
    )

    assert result["ok"] is True
    assert result["mutated_host_state"] is False
    assert result["explicit_user_approval"] is False
    assert result["state"]["health_status"] == "healthy"
    assert result["detail"]["url"] == "http://127.0.0.1:8765/mobile/v1/health"


def test_private_host_adapter_placeholder_is_unavailable_without_mutation():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="hermes", installed=True)),
        action_id="update_runtime_package",
        approved=True,
        adapter_mode="private",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_unavailable"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is False


def test_private_host_adapter_command_runs_health_check_without_mutation():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command(),
    )

    assert result["ok"] is True
    assert result["adapter_mode"] == "private"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is True
    assert result["detail"]["private_api_called"] is True
    assert result["detail"]["private_api_provider"] == "fake_private_host_api"
    assert result["state"]["health_status"] == "healthy"


def test_private_host_adapter_request_matches_schema_declared_contract():
    package = build_runtime_host_package(
        BridgeConfig(runtime="hermes", installed=True),
        bridge_enabled=True,
    )
    state = {
        "installed": True,
        "start_with_runtime": False,
        "process_state": "running",
        "process_supervision": "host_managed",
        "health_status": "healthy",
        "port_conflict": False,
        "runtime_store_path": "/private/store.sqlite",
    }

    request = build_private_host_adapter_request(
        package,
        action_id="run_health_check",
        approved=False,
        adapter="host_native_health_check",
        state=state,
    )

    assert request["schema_version"] == "kaka.host_private_adapter_request.v1"
    assert request["surface"] == "hermes_openclaw_host_private_adapter_command"
    assert request["runtime"] == "hermes"
    assert request["runtime_side_only"] is True
    assert request["host_action"]["id"] == "run_health_check"
    assert request["host_action"]["owner"] == "host_native_adapter"
    assert request["host_action"]["enabled"] is True
    assert request["safety"] == {
        "phone_api_unchanged": True,
        "runtime_side_only": True,
        "phone_settings_owner": False,
        "no_autostart_on_install": True,
        "no_login_item_creation_by_runtime_kit": True,
    }
    assert "forbidden_phone_safe_fields" in request
    assert "runtime_store_path" in request["forbidden_phone_safe_fields"]
    assert "runtime_store_path" not in request["state"]
    assert "host_api_level" not in request
    assert "action" not in request


def test_private_host_adapter_command_runs_mutating_install_after_approval():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="openclaw")),
        action_id="install_runtime_package",
        approved=True,
        adapter_mode="private",
        private_adapter_command=_fake_private_command(),
    )

    assert result["ok"] is True
    assert result["mutated_host_state"] is True
    assert result["state"]["installed"] is True
    assert result["state"]["start_with_runtime"] is False
    assert result["safety"]["no_autostart_on_install"] is True
    assert result["safety"]["no_login_item_creation_by_runtime_kit"] is True


def test_private_host_adapter_without_command_remains_structured_unavailable():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="hermes", installed=True)),
        action_id="update_runtime_package",
        approved=True,
        adapter_mode="private",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_unavailable"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is False


def test_private_host_adapter_does_not_call_command_before_mutating_approval():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="hermes")),
        action_id="install_runtime_package",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--fail"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "explicit_approval_required"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is False


def test_private_host_adapter_does_not_call_command_for_disabled_non_mutating_action():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=False,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--fail"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "host_adapter_action_disabled"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is False


def test_private_host_adapter_invalid_response_is_safe_failure():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--invalid-json"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_invalid_response"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is True


def test_private_host_adapter_invalid_schema_is_safe_failure():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--invalid-schema"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_invalid_response"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is True


def test_private_host_adapter_rejects_extra_private_response_fields():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--extra-secret"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_invalid_response"
    assert result["mutated_host_state"] is False
    assert "secret" not in json.dumps(result)
    assert "secret_log_path" not in json.dumps(result)
    assert "/private/log" not in json.dumps(result)


def test_private_host_adapter_failed_command_is_safe_failure():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--fail"),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_command_failed"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is True
    assert "stdout" not in result["detail"]
    assert "stderr" not in result["detail"]


def test_private_host_adapter_timeout_is_safe_failure():
    result = build_host_adapter_action_result(
        build_runtime_host_package(
            BridgeConfig(runtime="hermes", installed=True),
            bridge_enabled=True,
        ),
        action_id="run_health_check",
        approved=False,
        adapter_mode="private",
        private_adapter_command=_fake_private_command("--sleep", "1"),
        private_adapter_timeout_seconds=0.01,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "private_host_adapter_timeout"
    assert result["mutated_host_state"] is False
    assert result["safety"]["private_host_api_called"] is True


def test_private_host_api_command_uses_shell_false_and_json_stdin(monkeypatch):
    from kaka_mobile_runtime_kit import private_host_api

    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))

        class Completed:
            returncode = 0
            stdout = json.dumps({
                "schema_version": "kaka.host_private_adapter_response.v1",
                "ok": True,
                "mutated_host_state": False,
                "state": {
                    "installed": True,
                    "start_with_runtime": False,
                    "process_state": "running",
                    "process_supervision": "host_managed",
                    "health_status": "healthy",
                    "port_conflict": False,
                },
                "detail": {"private_api_called": True},
            })
            stderr = "secret stderr"

        return Completed()

    monkeypatch.setattr(private_host_api.subprocess, "run", fake_run)

    result = private_host_api.run_private_host_adapter_command(
        f"{sys.executable} -m fake_private_api",
        {
            "schema_version": "kaka.host_private_adapter_request.v1",
            "action_id": "run_health_check",
            "approved": False,
            "state": {"health_status": "unknown"},
        },
    )

    assert result["ok"] is True
    argv, kwargs = calls[0]
    assert argv == [sys.executable, "-m", "fake_private_api"]
    assert kwargs["shell"] is False
    assert json.loads(kwargs["input"])["action_id"] == "run_health_check"
    assert "secret stderr" not in json.dumps(result)


def test_mock_host_adapter_respects_disabled_action_state():
    result = build_host_adapter_action_result(
        build_runtime_host_package(BridgeConfig(runtime="hermes", installed=False)),
        action_id="enable_start_with_runtime",
        approved=True,
        adapter_mode="mock",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "host_adapter_action_disabled"
    assert result["mutated_host_state"] is False
    assert result["state"]["start_with_runtime"] is False
    assert result["detail"]["enabled"] is False


def test_host_adapter_rejects_unknown_direct_inputs_before_result_output():
    package = build_runtime_host_package(BridgeConfig(runtime="hermes"))

    with pytest.raises(ValueError, match="Unknown host adapter action"):
        build_host_adapter_action_result(
            package,
            action_id="unknown_action",
            approved=True,
            adapter_mode="mock",
        )

    with pytest.raises(ValueError, match="Unsupported host adapter mode"):
        build_host_adapter_action_result(
            package,
            action_id="run_health_check",
            approved=False,
            adapter_mode="unsupported",
        )


def test_host_adapter_run_cli_outputs_structured_result(capsys):
    exit_code = main(
        [
            "host-adapter-run",
            "--runtime",
            "openclaw",
            "--installed",
            "--bridge-enabled",
            "--action-id",
            "run_health_check",
        ]
    )

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert result["surface"] == "hermes_openclaw_host_adapter_binding"
    assert result["runtime"] == "openclaw"
    assert result["action_id"] == "run_health_check"
    assert result["ok"] is True


def test_host_adapter_run_cli_requires_approval_for_mutating_action(capsys):
    exit_code = main(
        [
            "host-adapter-run",
            "--runtime",
            "hermes",
            "--action-id",
            "install_runtime_package",
        ]
    )

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["error"]["code"] == "explicit_approval_required"


def test_host_adapter_run_cli_accepts_private_command_flags(capsys):
    exit_code = main(
        [
            "host-adapter-run",
            "--runtime",
            "hermes",
            "--installed",
            "--bridge-enabled",
            "--adapter",
            "private",
            "--private-adapter-command",
            _fake_private_command(),
            "--private-adapter-timeout-seconds",
            "3",
            "--action-id",
            "run_health_check",
        ]
    )

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert result["ok"] is True
    assert result["safety"]["private_host_api_called"] is True
    assert result["detail"]["private_api_provider"] == "fake_private_host_api"


def test_host_package_preview_includes_host_adapter_run_artifact():
    package = build_runtime_host_package(BridgeConfig(runtime="hermes"))

    command = package["artifacts"]["host_adapter_run_command"]

    assert command[2] == "kaka_mobile_runtime_kit"
    assert command[3] == "host-adapter-run"
    assert command[command.index("--runtime") + 1] == "hermes"
    assert "--action-id" not in command
