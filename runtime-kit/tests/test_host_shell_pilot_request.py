import json
from pathlib import Path

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_adapter import HOST_ADAPTER_ACTIONS
from kaka_mobile_runtime_kit.host_shell_pilot_request import (
    build_host_shell_pilot_request,
)


def _executable(path: Path, body: str = "#!/bin/sh\nexit 99\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)
    return path


def test_host_shell_pilot_request_lists_what_host_team_must_provide():
    request = build_host_shell_pilot_request(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        request_id="P3.4-hermes-2026-06-06",
        pilot_owner="Hermes host team",
        expected_private_adapter_command_path=(
            "/Users/kartz/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api"
        ),
        artifact_root="artifacts/hermes",
    )

    assert request["schema_version"] == "kaka.host_shell_pilot_request.v1"
    assert request["surface"] == "hermes_openclaw_host_shell_pilot_request"
    assert request["runtime"] == "hermes"
    assert request["ok"] is True
    assert request["request_status"] == "ready_to_send"
    assert request["runtime_side_only"] is True
    assert request["phone_api_path"] == "/mobile/v1"
    assert request["phone_api_unchanged"] is True
    assert request["p3_4_complete"] is False
    assert request["p3_4_completion_owner"] == "external_host_shell"
    assert request["pilot_request"]["id"] == "P3.4-hermes-2026-06-06"
    assert request["pilot_request"]["audience"] == "Hermes host team"
    assert request["target_host"]["default_command_name"] == "hermes-kaka-host-api"
    assert request["target_host"]["environment_variable"] == "HERMES_KAKA_HOST_API"
    assert request["target_host"]["manifest_key"] == "host_private_adapter.command"
    assert request["target_host"]["expected_private_adapter_command_path"].endswith(
        "Hermes/Kaka/hermes-kaka-host-api"
    )
    assert request["required_action_ids"] == list(HOST_ADAPTER_ACTIONS)
    assert request["required_capabilities"] == [
        "distribution",
        "install",
        "login_item",
        "update",
        "uninstall",
        "logs",
        "health",
        "port_repair",
        "supervision",
    ]
    assert [item["id"] for item in request["required_host_deliverables"]] == [
        "private_adapter_command_binary",
        "private_adapter_request_response_contract",
        "host_action_matrix",
        "native_distribution_channel",
        "signature_or_notarization",
        "update_feed",
        "install_drill_receipt",
        "update_drill_receipt",
        "failure_recovery_drill_receipt",
        "release_notes",
    ]
    assert request["required_audit_refs"]["distribution"] == [
        "native_channel_ref",
        "signature_subject",
        "notarization_team_id",
        "update_feed_ref",
    ]
    assert request["required_audit_refs"]["drills"] == [
        "install_receipt_ref",
        "update_receipt_ref",
        "failure_recovery_receipt_ref",
        "release_notes_ref",
    ]
    assert [artifact["id"] for artifact in request["expected_runtime_kit_artifacts"]] == [
        "preflight_json",
        "conformance_json",
        "pilot_receipt_json",
        "handoff_json",
        "artifact_review_json",
    ]
    assert request["expected_runtime_kit_artifacts"][0]["suggested_path"] == (
        "artifacts/hermes/preflight.json"
    )
    assert request["acceptance_gates"]["can_mark_p3_4_complete"] is False
    assert request["safety"]["does_not_invoke_private_adapter_command"] is True
    assert request["safety"]["does_not_run_conformance"] is True
    assert request["safety"]["does_not_fetch_audit_refs"] is True


def test_host_shell_pilot_request_uses_openclaw_defaults():
    request = build_host_shell_pilot_request(
        BridgeConfig(runtime="openclaw", repo_root=Path.cwd()),
    )

    assert request["runtime"] == "openclaw"
    assert request["target_host"]["default_command_name"] == "openclaw-kaka-host-api"
    assert request["target_host"]["environment_variable"] == "OPENCLAW_KAKA_HOST_API"
    assert request["pilot_request"]["audience"] == "OpenClaw host team"
    assert request["expected_runtime_kit_artifacts"][0]["suggested_path"] == (
        "artifacts/openclaw/preflight.json"
    )


def test_host_shell_pilot_request_cli_does_not_run_expected_command(tmp_path, capsys):
    sentinel = tmp_path / "called.txt"
    command = _executable(
        tmp_path / "Hermes" / "Kaka" / "hermes-kaka-host-api",
        body=f"#!/bin/sh\ntouch {sentinel}\nexit 0\n",
    )

    exit_code = main([
        "host-shell-pilot-request",
        "--runtime",
        "hermes",
        "--request-id",
        "P3.4-hermes",
        "--pilot-owner",
        "Hermes release desk",
        "--expected-private-adapter-command-path",
        str(command),
        "--artifact-root",
        str(tmp_path / "artifacts" / "hermes"),
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert sentinel.exists() is False
    assert payload["schema_version"] == "kaka.host_shell_pilot_request.v1"
    assert payload["request_status"] == "ready_to_send"
    assert payload["pilot_request"]["audience"] == "Hermes release desk"
    assert payload["target_host"]["expected_private_adapter_command_path"] == str(command)
    assert payload["expected_runtime_kit_artifacts"][0]["suggested_path"].endswith(
        "artifacts/hermes/preflight.json"
    )
    assert payload["p3_4_complete"] is False
