import json
from pathlib import Path

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_shell_pilot_runbook import (
    build_host_shell_pilot_runbook,
)


def _executable(path: Path, body: str = "#!/bin/sh\nexit 99\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)
    return path


def test_pilot_runbook_blocks_before_host_shell_and_command_exist(tmp_path, monkeypatch):
    monkeypatch.delenv("HERMES_KAKA_HOST_API", raising=False)

    runbook = build_host_shell_pilot_runbook(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=tmp_path / "Applications",
        home=tmp_path / "home",
        path_env="",
    )

    assert runbook["schema_version"] == "kaka.host_shell_pilot_runbook.v1"
    assert runbook["surface"] == "hermes_openclaw_host_shell_pilot_runbook"
    assert runbook["runtime"] == "hermes"
    assert runbook["ok"] is False
    assert runbook["runbook_status"] == "blocked"
    assert runbook["runtime_side_only"] is True
    assert runbook["phone_api_path"] == "/mobile/v1"
    assert runbook["phone_api_unchanged"] is True
    assert runbook["p3_4_complete"] is False
    assert runbook["p3_4_completion_owner"] == "external_host_shell"
    assert runbook["brief"]["requested_host_owner_action"] == "provide_private_adapter_command"
    assert "does_not_complete_p3_4" in runbook["brief"]["non_goals"]
    assert runbook["preflight"]["status"] == "blocked"
    assert runbook["acceptance_gates"]["can_run_conformance"] is False
    assert runbook["acceptance_gates"]["can_submit_handoff"] is False
    assert runbook["acceptance_gates"]["can_mark_p3_4_complete"] is False
    assert "missing_host_shell" in runbook["acceptance_gates"]["blocking_reasons"]
    assert "missing_private_adapter_command" in runbook["acceptance_gates"]["blocking_reasons"]

    steps = {step["id"]: step for step in runbook["ordered_steps"]}
    assert steps["host_shell_pilot_preflight"]["status"] == "blocked"
    assert steps["host_private_adapter_conformance"]["status"] == "blocked"
    assert steps["host_shell_pilot_handoff"]["status"] == "blocked"
    assert runbook["safety"]["does_not_invoke_private_adapter_command"] is True
    assert runbook["safety"]["does_not_run_conformance"] is True


def test_pilot_runbook_is_ready_for_conformance_without_invoking_command(tmp_path, monkeypatch):
    sentinel = tmp_path / "called.txt"
    command = _executable(
        tmp_path / "hermes-kaka-host-api",
        body=f"#!/bin/sh\ntouch {sentinel}\nexit 0\n",
    )
    monkeypatch.setenv("HERMES_KAKA_HOST_API", str(command))
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)

    runbook = build_host_shell_pilot_runbook(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
    )

    assert sentinel.exists() is False
    assert runbook["ok"] is True
    assert runbook["runbook_status"] == "ready_for_conformance"
    assert runbook["preflight"]["private_adapter_command"]["source"] == "environment_variable"
    assert runbook["pilot_target"]["default_command_name"] == "hermes-kaka-host-api"
    assert runbook["pilot_target"]["environment_variable"] == "HERMES_KAKA_HOST_API"
    assert runbook["acceptance_gates"]["can_run_conformance"] is True
    assert runbook["acceptance_gates"]["can_submit_handoff"] is False
    assert runbook["acceptance_gates"]["can_mark_p3_4_complete"] is False

    conformance_command = runbook["command_artifacts"]["host_private_adapter_conformance"]
    assert conformance_command[:4] == [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-private-adapter-conformance",
    ]
    assert "--private-adapter-command" in conformance_command
    assert str(command) in conformance_command

    steps = {step["id"]: step for step in runbook["ordered_steps"]}
    assert steps["host_private_adapter_conformance"]["status"] == "ready"
    assert steps["host_shell_pilot_report"]["status"] == "waiting_for_conformance_and_evidence"
    assert steps["host_shell_pilot_handoff"]["output_schema"] == "kaka.host_shell_pilot_handoff.v1"


def test_pilot_runbook_lists_required_evidence_refs_without_fetching_them(tmp_path, monkeypatch):
    command = _executable(tmp_path / "openclaw-kaka-host-api")
    apps = tmp_path / "Applications"
    (apps / "OpenClaw.app").mkdir(parents=True)
    monkeypatch.delenv("OPENCLAW_KAKA_HOST_API", raising=False)

    runbook = build_host_shell_pilot_runbook(
        BridgeConfig(runtime="openclaw", repo_root=Path.cwd()),
        private_adapter_command=str(command),
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
        native_channel_ref="OpenClaw stable channel receipt #1",
        signature_subject="Developer ID Application: Example OpenClaw Team",
        notarization_team_id="TEAMID1234",
        update_feed_ref="https://example.invalid/openclaw/appcast.xml",
        install_receipt_ref="pilot://openclaw/install",
        update_receipt_ref="pilot://openclaw/update",
        failure_recovery_receipt_ref="pilot://openclaw/failure-recovery",
        release_notes_ref="https://example.invalid/openclaw/releases/1.0.0",
    )

    assert runbook["runbook_status"] == "ready_for_conformance"
    requirements = runbook["evidence_requirements"]
    assert requirements["complete"] is True
    assert requirements["distribution"]["missing"] == []
    assert requirements["drills"]["missing"] == []
    assert requirements["distribution"]["items"][0]["cli_flag"] == "--native-channel-ref"
    assert requirements["drills"]["items"][-1]["receipt_path"] == "drills.evidence.release_notes_ref"
    assert runbook["acceptance_gates"]["can_submit_handoff"] is False
    assert runbook["safety"]["does_not_fetch_audit_refs"] is True


def test_host_shell_pilot_runbook_cli_outputs_machine_readable_json(capsys, tmp_path):
    exit_code = main([
        "host-shell-pilot-runbook",
        "--runtime",
        "openclaw",
        "--applications-root",
        str(tmp_path / "Applications"),
        "--home",
        str(tmp_path / "home"),
        "--path-env",
        "",
    ])

    runbook = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert runbook["schema_version"] == "kaka.host_shell_pilot_runbook.v1"
    assert runbook["runtime"] == "openclaw"
    assert runbook["runbook_status"] == "blocked"
    assert runbook["p3_4_complete"] is False
