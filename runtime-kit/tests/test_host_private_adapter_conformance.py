import json
from pathlib import Path
import sys

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_adapter import (
    HOST_ADAPTER_ACTIONS,
    HOST_ADAPTER_MUTATING_ACTIONS,
)
from kaka_mobile_runtime_kit.host_private_adapter_conformance import (
    build_host_private_adapter_conformance_report,
)


def _fake_private_command(*args: str) -> str:
    command = f"{sys.executable} {Path('runtime-kit/tests/fixtures/fake_private_host_api.py')}"
    if args:
        command = f"{command} {' '.join(args)}"
    return command


def _fake_private_command_at(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        f"exec {sys.executable} {Path.cwd() / 'runtime-kit/tests/fixtures/fake_private_host_api.py'}\n"
    )
    path.chmod(0o755)
    return str(path)


def test_conformance_report_covers_full_host_action_matrix():
    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="hermes"),
        private_adapter_command=_fake_private_command(),
    )

    assert report["schema_version"] == "kaka.host_private_adapter_conformance.v1"
    assert report["surface"] == "hermes_openclaw_host_private_adapter_conformance"
    assert report["runtime"] == "hermes"
    assert report["ok"] is True
    assert report["phone_api_unchanged"] is True
    assert report["private_api_called"] is True
    assert report["required_action_ids"] == list(HOST_ADAPTER_ACTIONS)
    assert [case["action_id"] for case in report["cases"]] == list(HOST_ADAPTER_ACTIONS)
    assert all(case["ok"] is True for case in report["cases"])
    assert all(case["adapter_mode"] == "private" for case in report["cases"])
    assert {
        case["action_id"]: case["approved"] for case in report["cases"]
    } == {
        action_id: action_id in HOST_ADAPTER_MUTATING_ACTIONS
        for action_id in HOST_ADAPTER_ACTIONS
    }
    assert "runtime_store_path" in report["safety"]["forbidden_phone_safe_fields"]
    rendered = json.dumps(report)
    assert "stdout" not in rendered
    assert "stderr" not in rendered
    assert "raw_detail" not in rendered
    assert "raw_secret" not in rendered


def test_conformance_accepts_executable_command_path_with_spaces(tmp_path):
    command = _fake_private_command_at(
        tmp_path
        / "Library"
        / "Application Support"
        / "Hermes"
        / "Kaka"
        / "hermes-kaka-host-api"
    )

    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="hermes"),
        private_adapter_command=command,
    )

    assert report["ok"] is True
    assert report["summary"]["passed"] == len(HOST_ADAPTER_ACTIONS)


def test_conformance_report_records_missing_command_without_calling_private_api():
    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="hermes"),
        private_adapter_command="",
    )

    assert report["ok"] is False
    assert report["private_api_called"] is False
    assert report["summary"]["failed"] == len(HOST_ADAPTER_ACTIONS)
    assert {case["error_code"] for case in report["cases"]} == {"private_host_adapter_unavailable"}


def test_conformance_report_proves_unapproved_and_disabled_gates_do_not_call_command():
    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="openclaw"),
        private_adapter_command=_fake_private_command("--fail"),
        include_negative_checks=True,
    )

    negative_by_id = {case["id"]: case for case in report["negative_checks"]}
    assert negative_by_id["unapproved_install"]["ok"] is True
    assert negative_by_id["unapproved_install"]["private_api_called"] is False
    assert negative_by_id["unapproved_install"]["error_code"] == "explicit_approval_required"
    assert negative_by_id["disabled_health_check"]["ok"] is True
    assert negative_by_id["disabled_health_check"]["private_api_called"] is False
    assert negative_by_id["disabled_health_check"]["error_code"] == "host_adapter_action_disabled"


def test_conformance_report_rejects_extra_private_response_fields():
    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="hermes"),
        private_adapter_command=_fake_private_command("--extra-secret"),
    )

    assert report["ok"] is False
    assert report["summary"]["failed"] >= 1
    assert "secret" not in json.dumps(report)
    assert "/private/log" not in json.dumps(report)


def test_host_private_adapter_conformance_cli_outputs_structured_report(capsys):
    exit_code = main([
        "host-private-adapter-conformance",
        "--runtime",
        "hermes",
        "--private-adapter-command",
        _fake_private_command(),
    ])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["ok"] is True
    assert report["runtime"] == "hermes"
    assert report["summary"]["passed"] == len(HOST_ADAPTER_ACTIONS)


def test_conformance_case_shapes_match_closed_schema_fields():
    report = build_host_private_adapter_conformance_report(
        BridgeConfig(runtime="hermes"),
        private_adapter_command=_fake_private_command(),
    )

    expected_keys = {
        "id",
        "action_id",
        "adapter",
        "adapter_mode",
        "ok",
        "mutating",
        "approved",
        "expected_mutation",
        "mutated_host_state",
        "private_api_called",
        "error_code",
        "state",
    }
    assert set(report["cases"][0]) == expected_keys
    assert set(report["negative_checks"][0]) == expected_keys


def test_host_private_adapter_conformance_cli_missing_command_exits_two(capsys):
    exit_code = main([
        "host-private-adapter-conformance",
        "--runtime",
        "hermes",
    ])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert report["ok"] is False
    assert report["private_api_called"] is False
    assert report["summary"]["failed"] == len(HOST_ADAPTER_ACTIONS)
