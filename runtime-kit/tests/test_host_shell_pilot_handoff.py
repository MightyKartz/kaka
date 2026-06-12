import json
from pathlib import Path
import sys

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_shell_pilot_handoff import (
    build_host_shell_pilot_handoff,
)


def _fake_private_command_at(path: Path) -> str:
    path.write_text(
        "#!/bin/sh\n"
        f"exec {sys.executable} {Path.cwd() / 'runtime-kit/tests/fixtures/fake_private_host_api.py'}\n"
    )
    path.chmod(0o755)
    return str(path)


def _ready_kwargs() -> dict[str, object]:
    return {
        "distribution_source": "signed_download",
        "distribution_channel": "stable",
        "package_version": "1.0.0",
        "host_api_level": "v1",
        "native_channel_verified": True,
        "signature_verified": True,
        "update_feed_verified": True,
        "install_verified": True,
        "update_verified": True,
        "failure_recovery_verified": True,
        "release_notes_verified": True,
        "native_channel_ref": "Hermes stable channel receipt #2026-06-06",
        "signature_subject": "Developer ID Application: Example Hermes Team",
        "notarization_team_id": "TEAMID1234",
        "update_feed_ref": "https://updates.example.invalid/hermes/kaka/appcast.xml",
        "install_receipt_ref": "qa://hermes/install/2026-06-06",
        "update_receipt_ref": "qa://hermes/update/2026-06-06",
        "failure_recovery_receipt_ref": "qa://hermes/recovery/2026-06-06",
        "release_notes_ref": "https://example.invalid/hermes/kaka/release-notes/1.0.0",
        "conformance_report": {
            "ok": True,
            "summary": {
                "total": 9,
                "passed": 9,
                "failed": 0,
            },
        },
    }


def test_pilot_handoff_reports_missing_external_deliverables():
    handoff = build_host_shell_pilot_handoff(
        BridgeConfig(runtime="hermes"),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert handoff["schema_version"] == "kaka.host_shell_pilot_handoff.v1"
    assert handoff["surface"] == "hermes_openclaw_host_shell_pilot_handoff"
    assert handoff["runtime"] == "hermes"
    assert handoff["ok"] is False
    assert handoff["handoff_status"] == "incomplete"
    assert handoff["runtime_side_only"] is True
    assert handoff["phone_api_path"] == "/mobile/v1"
    assert handoff["phone_api_unchanged"] is True
    assert handoff["p3_4_complete"] is False
    assert handoff["p3_4_completion_owner"] == "external_host_shell"
    assert handoff["pilot_receipt"]["status"] == "not_ready"
    assert handoff["audit_refs"]["complete"] is False
    assert handoff["audit_refs"]["distribution"]["missing"] == [
        "native_channel_ref",
        "signature_subject",
        "notarization_team_id",
        "update_feed_ref",
    ]
    assert handoff["audit_refs"]["drills"]["missing"] == [
        "install_receipt_ref",
        "update_receipt_ref",
        "failure_recovery_receipt_ref",
        "release_notes_ref",
    ]
    assert "missing_private_adapter_command" in handoff["release_handoff"]["blocking_reasons"]
    assert "missing_audit_ref:native_channel_ref" in handoff["release_handoff"]["blocking_reasons"]
    assert handoff["release_handoff"]["can_submit_to_external_pilot"] is False
    assert handoff["release_handoff"]["can_mark_p3_4_complete"] is False


def test_pilot_handoff_can_be_ready_to_submit_with_ready_receipt_and_all_refs(tmp_path):
    command = tmp_path / "hermes-kaka-host-api"
    command.write_text("#!/bin/sh\nexit 99\n")

    handoff = build_host_shell_pilot_handoff(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=str(command),
        **_ready_kwargs(),
    )

    assert handoff["ok"] is True
    assert handoff["handoff_status"] == "ready_to_submit"
    assert handoff["pilot_receipt"]["status"] == "ready"
    assert handoff["audit_refs"]["complete"] is True
    assert handoff["audit_refs"]["distribution"]["provided"] == [
        "native_channel_ref",
        "signature_subject",
        "notarization_team_id",
        "update_feed_ref",
    ]
    assert handoff["audit_refs"]["drills"]["provided"] == [
        "install_receipt_ref",
        "update_receipt_ref",
        "failure_recovery_receipt_ref",
        "release_notes_ref",
    ]
    assert handoff["release_handoff"]["blocking_reasons"] == []
    assert handoff["release_handoff"]["can_submit_to_external_pilot"] is True
    assert handoff["release_handoff"]["can_mark_p3_4_complete"] is False
    assert handoff["p3_4_complete"] is False
    assert handoff["p3_4_completion_owner"] == "external_host_shell"
    assert handoff["deliverables"][0]["id"] == "private_adapter_command"
    assert handoff["safety"]["no_proprietary_binary_bundled_by_kaka"] is True


def test_pilot_handoff_keeps_receipt_ready_but_blocks_submission_when_refs_missing(tmp_path):
    command = tmp_path / "hermes-kaka-host-api"
    command.write_text("#!/bin/sh\nexit 99\n")
    kwargs = _ready_kwargs()
    for key in (
        "native_channel_ref",
        "signature_subject",
        "notarization_team_id",
        "update_feed_ref",
        "install_receipt_ref",
        "update_receipt_ref",
        "failure_recovery_receipt_ref",
        "release_notes_ref",
    ):
        kwargs[key] = ""

    handoff = build_host_shell_pilot_handoff(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=str(command),
        **kwargs,
    )

    assert handoff["pilot_receipt"]["status"] == "ready"
    assert handoff["pilot_receipt"]["release_readiness"]["can_mark_p3_4_complete"] is True
    assert handoff["p3_4_complete"] is False
    assert handoff["audit_refs"]["complete"] is False
    assert handoff["ok"] is False
    assert handoff["handoff_status"] == "incomplete"
    assert handoff["release_handoff"]["can_mark_p3_4_complete"] is False
    assert "missing_audit_ref:release_notes_ref" in handoff["release_handoff"]["blocking_reasons"]


def test_host_shell_pilot_handoff_cli_outputs_incomplete_bundle(capsys):
    exit_code = main([
        "host-shell-pilot-handoff",
        "--runtime",
        "openclaw",
    ])

    handoff = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert handoff["schema_version"] == "kaka.host_shell_pilot_handoff.v1"
    assert handoff["runtime"] == "openclaw"
    assert handoff["handoff_status"] == "incomplete"
    assert handoff["pilot_receipt"]["status"] == "not_ready"


def test_host_shell_pilot_handoff_cli_can_emit_ready_bundle(monkeypatch, tmp_path, capsys):
    command = _fake_private_command_at(tmp_path / "hermes-kaka-host-api")
    monkeypatch.setenv("HERMES_KAKA_HOST_API", command)

    exit_code = main([
        "host-shell-pilot-handoff",
        "--runtime",
        "hermes",
        "--distribution-source",
        "signed_download",
        "--distribution-channel",
        "stable",
        "--package-version",
        "1.0.0",
        "--host-api-level",
        "v1",
        "--native-channel-verified",
        "--signature-verified",
        "--update-feed-verified",
        "--install-verified",
        "--update-verified",
        "--failure-recovery-verified",
        "--release-notes-verified",
        "--native-channel-ref",
        "Hermes stable channel receipt #2026-06-06",
        "--signature-subject",
        "Developer ID Application: Example Hermes Team",
        "--notarization-team-id",
        "TEAMID1234",
        "--update-feed-ref",
        "https://updates.example.invalid/hermes/kaka/appcast.xml",
        "--install-receipt-ref",
        "qa://hermes/install/2026-06-06",
        "--update-receipt-ref",
        "qa://hermes/update/2026-06-06",
        "--failure-recovery-receipt-ref",
        "qa://hermes/recovery/2026-06-06",
        "--release-notes-ref",
        "https://example.invalid/hermes/kaka/release-notes/1.0.0",
    ])

    handoff = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert handoff["handoff_status"] == "ready_to_submit"
    assert handoff["pilot_receipt"]["private_adapter_command"]["source"] == "environment_variable"
    assert handoff["audit_refs"]["complete"] is True
