import json
from pathlib import Path
import sys

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_shell_pilot import build_host_shell_pilot_receipt


def _fake_private_command() -> str:
    return f"{sys.executable} {Path('runtime-kit/tests/fixtures/fake_private_host_api.py')}"


def _fake_private_command_at(path: Path) -> str:
    path.write_text(
        "#!/bin/sh\n"
        f"exec {sys.executable} {Path.cwd() / 'runtime-kit/tests/fixtures/fake_private_host_api.py'}\n"
    )
    path.chmod(0o755)
    return str(path)


def test_pilot_receipt_is_not_ready_without_external_command():
    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes"),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["schema_version"] == "kaka.host_shell_pilot_receipt.v1"
    assert receipt["surface"] == "hermes_openclaw_external_host_shell_pilot"
    assert receipt["runtime"] == "hermes"
    assert receipt["ok"] is False
    assert receipt["status"] == "not_ready"
    assert receipt["external_binary_required"] is True
    assert receipt["binary_owner"] == "host_shell"
    assert receipt["distribution_owner"] == "hermes"
    assert receipt["private_adapter_command"]["provided"] is False
    assert receipt["conformance"]["ran"] is False
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is False
    assert "missing_private_adapter_command" in receipt["release_readiness"]["blocking_reasons"]
    assert receipt["phone_api_path"] == "/mobile/v1"
    assert receipt["safety"]["phone_settings_owner"] is False


def test_pilot_receipt_discovers_command_from_runtime_environment(monkeypatch, tmp_path):
    command = _fake_private_command_at(tmp_path / "hermes-kaka-host-api")
    monkeypatch.setenv("HERMES_KAKA_HOST_API", command)

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["private_adapter_command"]["provided"] is True
    assert receipt["private_adapter_command"]["source"] == "environment_variable"
    assert receipt["private_adapter_command"]["path"] == command
    assert receipt["private_adapter_command"]["outside_kaka_repo"] is True
    assert receipt["conformance"]["ran"] is True
    assert receipt["conformance"]["ok"] is True
    assert receipt["status"] == "not_ready"


def test_pilot_receipt_prefers_explicit_command_over_environment(monkeypatch, tmp_path):
    explicit_command = _fake_private_command_at(tmp_path / "explicit-hermes-kaka-host-api")
    env_command = _fake_private_command_at(tmp_path / "env-hermes-kaka-host-api")
    monkeypatch.setenv("HERMES_KAKA_HOST_API", env_command)

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=explicit_command,
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["private_adapter_command"]["source"] == "argument"
    assert receipt["private_adapter_command"]["path"] == explicit_command


def test_pilot_receipt_ignores_blank_environment_command(monkeypatch):
    monkeypatch.setenv("OPENCLAW_KAKA_HOST_API", "   ")

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="openclaw"),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["private_adapter_command"]["provided"] is False
    assert receipt["private_adapter_command"]["source"] == "missing"
    assert "missing_private_adapter_command" in receipt["release_readiness"]["blocking_reasons"]


def test_pilot_receipt_discovers_command_from_well_known_path(monkeypatch, tmp_path):
    home = tmp_path / "home"
    well_known = (
        home
        / "Library"
        / "Application Support"
        / "OpenClaw"
        / "Kaka"
        / "openclaw-kaka-host-api"
    )
    well_known.parent.mkdir(parents=True)
    command = _fake_private_command_at(well_known)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("OPENCLAW_KAKA_HOST_API", raising=False)

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="openclaw", repo_root=Path.cwd()),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["private_adapter_command"]["provided"] is True
    assert receipt["private_adapter_command"]["source"] == "well_known_path"
    assert receipt["private_adapter_command"]["path"] == command
    assert receipt["private_adapter_command"]["outside_kaka_repo"] is True
    assert receipt["conformance"]["ran"] is True


def test_pilot_receipt_discovers_command_from_manifest_entrypoint(tmp_path):
    command = _fake_private_command_at(tmp_path / "manifest-hermes-kaka-host-api")
    repo_root = tmp_path / "repo"
    manifest_path = repo_root / "runtime-kit" / "hermes-plugin" / "kaka-mobile-bridge.package.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({
        "host_private_adapter": {
            "command": command,
        },
    }))

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=repo_root),
        private_adapter_command="",
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["private_adapter_command"]["provided"] is True
    assert receipt["private_adapter_command"]["source"] == "manifest_entrypoint"
    assert receipt["private_adapter_command"]["path"] == command


def test_pilot_receipt_marks_fake_fixture_as_synthetic_only():
    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="openclaw"),
        private_adapter_command=_fake_private_command(),
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["ok"] is False
    assert receipt["status"] == "synthetic_only"
    assert receipt["distribution_owner"] == "openclaw"
    assert receipt["private_adapter_command"]["provided"] is True
    assert receipt["private_adapter_command"]["outside_kaka_repo"] is False
    assert receipt["conformance"]["ran"] is True
    assert receipt["conformance"]["ok"] is True
    assert receipt["conformance"]["synthetic_only"] is True
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is False
    assert "synthetic_conformance_only" in receipt["release_readiness"]["blocking_reasons"]


def test_pilot_receipt_marks_failed_fake_fixture_conformance_as_not_ready():
    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="openclaw"),
        private_adapter_command=_fake_private_command(),
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
        conformance_report={
            "ok": False,
            "summary": {
                "total": 9,
                "passed": 8,
                "failed": 1,
            },
        },
    )

    assert receipt["ok"] is False
    assert receipt["status"] == "not_ready"
    assert receipt["conformance"]["ran"] is True
    assert receipt["conformance"]["ok"] is False
    assert receipt["conformance"]["synthetic_only"] is True
    assert receipt["release_readiness"]["can_start_external_pilot"] is False
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is False
    assert "conformance_not_passed" in receipt["release_readiness"]["blocking_reasons"]


def test_pilot_receipt_handles_malformed_private_command_as_not_ready():
    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes"),
        private_adapter_command='"unterminated',
        distribution_source="local_checkout",
        distribution_channel="development",
        package_version="development",
        host_api_level="preview",
    )

    assert receipt["ok"] is False
    assert receipt["status"] == "not_ready"
    assert receipt["conformance"]["ran"] is True
    assert receipt["conformance"]["ok"] is False
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is False
    assert "conformance_not_passed" in receipt["release_readiness"]["blocking_reasons"]


def test_pilot_receipt_can_be_ready_for_real_external_command_with_evidence(tmp_path):
    outside_repo_command = tmp_path / "hermes-kaka-host-api"
    outside_repo_command.write_text("#!/bin/sh\nexit 99\n")

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=str(outside_repo_command),
        distribution_source="signed_download",
        distribution_channel="stable",
        package_version="1.0.0",
        host_api_level="v1",
        native_channel_verified=True,
        signature_verified=True,
        update_feed_verified=True,
        install_verified=True,
        update_verified=True,
        failure_recovery_verified=True,
        release_notes_verified=True,
        conformance_report={
            "ok": True,
            "summary": {
                "total": 9,
                "passed": 9,
                "failed": 0,
            },
        },
    )

    assert receipt["ok"] is True
    assert receipt["status"] == "ready"
    assert receipt["private_adapter_command"]["outside_kaka_repo"] is True
    assert receipt["distribution"]["native_channel_verified"] is True
    assert receipt["distribution"]["signature_verified"] is True
    assert receipt["distribution"]["update_feed_verified"] is True
    assert receipt["release_readiness"]["blocking_reasons"] == []
    assert receipt["release_readiness"]["can_start_external_pilot"] is True
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is True


def test_pilot_receipt_records_host_supplied_evidence_references(tmp_path):
    outside_repo_command = tmp_path / "hermes-kaka-host-api"
    outside_repo_command.write_text("#!/bin/sh\nexit 99\n")

    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=str(outside_repo_command),
        distribution_source="signed_download",
        distribution_channel="stable",
        package_version="1.0.0",
        host_api_level="v1",
        native_channel_verified=True,
        signature_verified=True,
        update_feed_verified=True,
        install_verified=True,
        update_verified=True,
        failure_recovery_verified=True,
        release_notes_verified=True,
        native_channel_ref="Hermes stable channel receipt #2026-06-06",
        signature_subject="Developer ID Application: Example Hermes Team",
        notarization_team_id="TEAMID1234",
        update_feed_ref="https://updates.example.invalid/hermes/kaka/appcast.xml",
        install_receipt_ref="qa://hermes/install/2026-06-06",
        update_receipt_ref="qa://hermes/update/2026-06-06",
        failure_recovery_receipt_ref="qa://hermes/recovery/2026-06-06",
        release_notes_ref="https://example.invalid/hermes/kaka/release-notes/1.0.0",
        conformance_report={
            "ok": True,
            "summary": {
                "total": 9,
                "passed": 9,
                "failed": 0,
            },
        },
    )

    assert receipt["status"] == "ready"
    assert receipt["distribution"]["evidence"] == {
        "native_channel_ref": "Hermes stable channel receipt #2026-06-06",
        "signature_subject": "Developer ID Application: Example Hermes Team",
        "notarization_team_id": "TEAMID1234",
        "update_feed_ref": "https://updates.example.invalid/hermes/kaka/appcast.xml",
    }
    assert receipt["drills"]["evidence"] == {
        "install_receipt_ref": "qa://hermes/install/2026-06-06",
        "update_receipt_ref": "qa://hermes/update/2026-06-06",
        "failure_recovery_receipt_ref": "qa://hermes/recovery/2026-06-06",
        "release_notes_ref": "https://example.invalid/hermes/kaka/release-notes/1.0.0",
    }


def test_host_shell_pilot_report_cli_outputs_structured_not_ready_report(capsys):
    exit_code = main([
        "host-shell-pilot-report",
        "--runtime",
        "hermes",
    ])

    receipt = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert receipt["status"] == "not_ready"
    assert receipt["release_readiness"]["can_mark_p3_4_complete"] is False


def test_host_shell_pilot_report_cli_discovers_environment_command(monkeypatch, tmp_path, capsys):
    command = _fake_private_command_at(tmp_path / "hermes-kaka-host-api")
    monkeypatch.setenv("HERMES_KAKA_HOST_API", command)

    exit_code = main([
        "host-shell-pilot-report",
        "--runtime",
        "hermes",
    ])

    receipt = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert receipt["private_adapter_command"]["provided"] is True
    assert receipt["private_adapter_command"]["source"] == "environment_variable"
    assert receipt["conformance"]["ran"] is True


def test_host_shell_pilot_report_cli_records_evidence_refs(monkeypatch, tmp_path, capsys):
    command = _fake_private_command_at(tmp_path / "hermes-kaka-host-api")
    monkeypatch.setenv("HERMES_KAKA_HOST_API", command)

    exit_code = main([
        "host-shell-pilot-report",
        "--runtime",
        "hermes",
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

    receipt = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert receipt["private_adapter_command"]["source"] == "environment_variable"
    assert receipt["distribution"]["evidence"]["signature_subject"] == (
        "Developer ID Application: Example Hermes Team"
    )
    assert receipt["drills"]["evidence"]["release_notes_ref"] == (
        "https://example.invalid/hermes/kaka/release-notes/1.0.0"
    )
