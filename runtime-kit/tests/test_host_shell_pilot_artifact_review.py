import json
from pathlib import Path

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_shell_pilot import build_host_shell_pilot_receipt
from kaka_mobile_runtime_kit.host_shell_pilot_artifact_review import (
    build_host_shell_pilot_artifact_review,
)
from kaka_mobile_runtime_kit.host_shell_pilot_handoff import build_host_shell_pilot_handoff
from kaka_mobile_runtime_kit.host_shell_pilot_preflight import build_host_shell_pilot_preflight


def _executable(path: Path, body: str = "#!/bin/sh\nexit 99\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)
    return path


def _ready_conformance(runtime: str) -> dict[str, object]:
    return {
        "schema_version": "kaka.host_private_adapter_conformance.v1",
        "surface": "hermes_openclaw_host_private_adapter_conformance",
        "runtime": runtime,
        "ok": True,
        "summary": {
            "total": 9,
            "passed": 9,
            "failed": 0,
        },
    }


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
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload))
    return path


def test_artifact_review_blocks_when_required_artifacts_are_missing():
    review = build_host_shell_pilot_artifact_review(
        runtime="hermes",
        preflight=None,
        conformance=None,
        receipt=None,
        handoff=None,
    )

    assert review["schema_version"] == "kaka.host_shell_pilot_artifact_review.v1"
    assert review["surface"] == "hermes_openclaw_host_shell_pilot_artifact_review"
    assert review["runtime"] == "hermes"
    assert review["ok"] is False
    assert review["review_status"] == "blocked"
    assert review["runtime_side_only"] is True
    assert review["phone_api_path"] == "/mobile/v1"
    assert review["phone_api_unchanged"] is True
    assert review["p3_4_complete"] is False
    assert review["p3_4_completion_owner"] == "external_host_shell"
    assert review["artifacts"]["preflight"]["loaded"] is False
    assert review["artifacts"]["preflight"]["required"] is True
    assert review["artifacts"]["preflight"]["schema_valid"] is False
    assert review["artifacts"]["handoff"]["loaded"] is False
    assert "missing_artifact:preflight" in review["release_review"]["blocking_reasons"]
    assert "missing_artifact:handoff" in review["release_review"]["blocking_reasons"]
    assert review["release_review"]["can_submit_to_external_review"] is False
    assert review["release_review"]["can_mark_p3_4_complete"] is False
    assert review["safety"]["does_not_invoke_private_adapter_command"] is True


def test_artifact_review_accepts_ready_artifacts_without_invoking_command(tmp_path):
    sentinel = tmp_path / "called.txt"
    command = _executable(
        tmp_path / "hermes-kaka-host-api",
        body=f"#!/bin/sh\ntouch {sentinel}\nexit 0\n",
    )
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)
    config = BridgeConfig(runtime="hermes", repo_root=Path.cwd())
    conformance = _ready_conformance("hermes")
    preflight = build_host_shell_pilot_preflight(
        config,
        private_adapter_command=str(command),
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
    )
    receipt = build_host_shell_pilot_receipt(
        config,
        private_adapter_command=str(command),
        conformance_report=conformance,
        **_ready_kwargs(),
    )
    handoff = build_host_shell_pilot_handoff(
        config,
        private_adapter_command=str(command),
        conformance_report=conformance,
        **_ready_kwargs(),
    )

    review = build_host_shell_pilot_artifact_review(
        runtime="hermes",
        preflight=preflight,
        conformance=conformance,
        receipt=receipt,
        handoff=handoff,
    )

    assert sentinel.exists() is False
    assert review["ok"] is True
    assert review["review_status"] == "ready_for_external_review"
    assert review["artifacts"]["preflight"]["schema_valid"] is True
    assert review["artifacts"]["conformance"]["summary"] == {
        "total": 9,
        "passed": 9,
        "failed": 0,
    }
    assert review["artifact_consistency"]["runtime_match"] is True
    assert review["artifact_consistency"]["preflight_allows_conformance"] is True
    assert review["artifact_consistency"]["conformance_passed"] is True
    assert review["artifact_consistency"]["conformance_embedded_in_receipt"] is True
    assert review["artifact_consistency"]["receipt_ready"] is True
    assert review["artifact_consistency"]["receipt_embedded_in_handoff"] is True
    assert review["artifact_consistency"]["handoff_ready_to_submit"] is True
    assert review["artifact_consistency"]["audit_refs_complete"] is True
    assert review["artifact_consistency"]["no_synthetic_conformance"] is True
    assert review["release_review"]["can_submit_to_external_review"] is True
    assert review["release_review"]["can_mark_p3_4_complete"] is False
    assert review["safety"]["does_not_run_conformance"] is True


def test_artifact_review_blocks_runtime_mismatch_and_missing_audit_refs(tmp_path):
    conformance = _ready_conformance("openclaw")
    receipt = build_host_shell_pilot_receipt(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command=str(_executable(tmp_path / "hermes-kaka-host-api")),
        conformance_report=conformance,
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
    )

    review = build_host_shell_pilot_artifact_review(
        runtime="hermes",
        preflight={
            "schema_version": "kaka.host_shell_pilot_preflight.v1",
            "runtime": "hermes",
            "ok": True,
            "status": "ready_for_conformance",
        },
        conformance=conformance,
        receipt=receipt,
        handoff={
            "schema_version": "kaka.host_shell_pilot_handoff.v1",
            "runtime": "hermes",
            "ok": False,
            "handoff_status": "incomplete",
            "pilot_receipt": receipt,
            "audit_refs": {"complete": False},
            "p3_4_complete": False,
        },
    )

    assert review["ok"] is False
    assert review["artifacts"]["preflight"]["schema_valid"] is False
    assert "surface" in review["artifacts"]["preflight"]["schema_errors"]
    assert review["artifact_consistency"]["runtime_match"] is False
    assert review["artifact_consistency"]["audit_refs_complete"] is False
    assert "artifact_runtime_mismatch" in review["release_review"]["blocking_reasons"]
    assert "handoff_not_ready_to_submit" in review["release_review"]["blocking_reasons"]
    assert "missing_audit_refs" in review["release_review"]["blocking_reasons"]


def test_artifact_review_cli_reads_json_files_without_running_them(tmp_path, capsys):
    command = _executable(tmp_path / "hermes-kaka-host-api")
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)
    config = BridgeConfig(runtime="hermes", repo_root=Path.cwd())
    conformance = _ready_conformance("hermes")
    preflight = build_host_shell_pilot_preflight(
        config,
        private_adapter_command=str(command),
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
    )
    receipt = build_host_shell_pilot_receipt(
        config,
        private_adapter_command=str(command),
        conformance_report=conformance,
        **_ready_kwargs(),
    )
    handoff = build_host_shell_pilot_handoff(
        config,
        private_adapter_command=str(command),
        conformance_report=conformance,
        **_ready_kwargs(),
    )

    exit_code = main([
        "host-shell-pilot-artifact-review",
        "--runtime",
        "hermes",
        "--preflight-json",
        str(_write_json(tmp_path / "preflight.json", preflight)),
        "--conformance-json",
        str(_write_json(tmp_path / "conformance.json", conformance)),
        "--receipt-json",
        str(_write_json(tmp_path / "receipt.json", receipt)),
        "--handoff-json",
        str(_write_json(tmp_path / "handoff.json", handoff)),
    ])

    review = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert review["schema_version"] == "kaka.host_shell_pilot_artifact_review.v1"
    assert review["review_status"] == "ready_for_external_review"
    assert review["artifacts"]["preflight"]["path"].endswith("preflight.json")
    assert review["p3_4_complete"] is False
