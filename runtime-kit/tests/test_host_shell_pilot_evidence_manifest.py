import hashlib
import json
from pathlib import Path

from kaka_mobile_runtime_kit.cli import main
from kaka_mobile_runtime_kit.host_shell_pilot_evidence_manifest import (
    build_host_shell_pilot_evidence_manifest,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pilot_artifacts(root: Path, runtime: str) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    command_path = root / "hermes-kaka-host-api"
    command_path.write_text("#!/bin/sh\nexit 99\n")
    command_path.chmod(0o755)
    conformance = {
        "schema_version": "kaka.host_private_adapter_conformance.v1",
        "surface": "hermes_openclaw_host_private_adapter_conformance",
        "runtime": runtime,
        "ok": True,
        "summary": {"total": 9, "passed": 9, "failed": 0},
    }
    return {
        "preflight": _write_json(
            root / "preflight.json",
            {
                "schema_version": "kaka.host_shell_pilot_preflight.v1",
                "surface": "hermes_openclaw_host_shell_pilot_preflight",
                "runtime": runtime,
                "ok": True,
                "status": "ready_for_conformance",
            },
        ),
        "conformance": _write_json(root / "conformance.json", conformance),
        "receipt": _write_json(
            root / "pilot-receipt.json",
            {
                "schema_version": "kaka.host_shell_pilot_receipt.v1",
                "surface": "hermes_openclaw_external_host_shell_pilot",
                "runtime": runtime,
                "ok": True,
                "status": "ready",
                "private_adapter_command": {
                    "provided": True,
                    "path": str(command_path),
                },
                "release_readiness": {
                    "can_mark_p3_4_complete": True,
                    "blocking_reasons": [],
                },
            },
        ),
        "handoff": _write_json(
            root / "handoff.json",
            {
                "schema_version": "kaka.host_shell_pilot_handoff.v1",
                "surface": "hermes_openclaw_host_shell_pilot_handoff",
                "runtime": runtime,
                "ok": True,
                "handoff_status": "ready_to_submit",
                "p3_4_complete": False,
            },
        ),
        "artifact_review": _write_json(
            root / "artifact-review.json",
            {
                "schema_version": "kaka.host_shell_pilot_artifact_review.v1",
                "surface": "hermes_openclaw_host_shell_pilot_artifact_review",
                "runtime": runtime,
                "ok": True,
                "review_status": "ready_for_external_review",
                "p3_4_complete": False,
                "release_review": {
                    "can_submit_to_external_review": True,
                    "can_mark_p3_4_complete": False,
                    "blocking_reasons": [],
                },
            },
        ),
        "request": _write_json(
            root / "request.json",
            {
                "schema_version": "kaka.host_shell_pilot_request.v1",
                "surface": "hermes_openclaw_host_shell_pilot_request",
                "runtime": runtime,
                "ok": True,
                "request_status": "ready_to_send",
                "p3_4_complete": False,
            },
        ),
    }


def test_evidence_manifest_blocks_missing_required_artifacts(tmp_path):
    manifest = build_host_shell_pilot_evidence_manifest(
        runtime="hermes",
        package_id="P3.4-hermes",
        artifact_paths={
            "preflight": str(tmp_path / "missing-preflight.json"),
            "conformance": str(tmp_path / "missing-conformance.json"),
            "receipt": str(tmp_path / "missing-receipt.json"),
            "handoff": str(tmp_path / "missing-handoff.json"),
            "artifact_review": str(tmp_path / "missing-artifact-review.json"),
        },
    )

    assert manifest["schema_version"] == "kaka.host_shell_pilot_evidence_manifest.v1"
    assert manifest["surface"] == "hermes_openclaw_host_shell_pilot_evidence_manifest"
    assert manifest["runtime"] == "hermes"
    assert manifest["ok"] is False
    assert manifest["manifest_status"] == "blocked_missing_artifacts"
    assert manifest["runtime_side_only"] is True
    assert manifest["phone_api_path"] == "/mobile/v1"
    assert manifest["phone_api_unchanged"] is True
    assert manifest["p3_4_complete"] is False
    assert manifest["p3_4_completion_owner"] == "external_host_shell"
    assert manifest["artifacts"][0]["loaded"] is False
    assert "missing_artifact:preflight" in manifest["archive_gates"]["blocking_reasons"]
    assert manifest["archive_gates"]["can_create_external_archive"] is False
    assert manifest["archive_gates"]["can_mark_p3_4_complete"] is False
    assert manifest["safety"]["does_not_create_archive_by_default"] is True


def test_evidence_manifest_hashes_local_artifacts_without_executing_commands(tmp_path):
    paths = _pilot_artifacts(tmp_path, "hermes")
    manifest = build_host_shell_pilot_evidence_manifest(
        runtime="hermes",
        package_id="P3.4-hermes",
        created_at="2026-06-06T00:00:00Z",
        archive_filename="kaka-p3.4-hermes-pilot-evidence.zip",
        artifact_paths={key: str(value) for key, value in paths.items()},
    )

    preflight = manifest["artifacts"][0]
    receipt = next(item for item in manifest["artifacts"] if item["id"] == "receipt_json")
    assert manifest["ok"] is True
    assert manifest["manifest_status"] == "ready_for_archive"
    assert manifest["package"]["id"] == "P3.4-hermes"
    assert manifest["package"]["archive_creation"] == "external"
    assert preflight["byte_size"] == paths["preflight"].stat().st_size
    assert preflight["sha256"] == _sha256(paths["preflight"])
    assert receipt["loaded"] is True
    assert manifest["artifact_review_summary"]["provided"] is True
    assert manifest["artifact_review_summary"]["review_status"] == "ready_for_external_review"
    assert manifest["artifact_review_summary"]["can_submit_to_external_review"] is True
    assert manifest["archive_gates"]["all_required_artifacts_present"] is True
    assert manifest["archive_gates"]["artifact_review_ready"] is True
    assert manifest["archive_gates"]["can_create_external_archive"] is True
    assert manifest["archive_gates"]["can_mark_p3_4_complete"] is False
    assert manifest["safety"]["does_not_invoke_private_adapter_command"] is True
    assert manifest["safety"]["hashes_local_artifact_files_only"] is True


def test_evidence_manifest_blocks_artifacts_that_are_not_ok(tmp_path):
    paths = _pilot_artifacts(tmp_path, "hermes")
    conformance = json.loads(paths["conformance"].read_text())
    conformance["ok"] = False
    paths["conformance"].write_text(json.dumps(conformance, sort_keys=True))

    manifest = build_host_shell_pilot_evidence_manifest(
        runtime="hermes",
        artifact_paths={key: str(value) for key, value in paths.items()},
    )

    conformance_artifact = next(
        item for item in manifest["artifacts"] if item["id"] == "conformance_json"
    )
    assert manifest["ok"] is False
    assert manifest["manifest_status"] == "blocked_missing_artifacts"
    assert conformance_artifact["loaded"] is True
    assert conformance_artifact["ok"] is False
    assert conformance_artifact["blocking_reason"] == "artifact_not_ok:conformance"
    assert "artifact_not_ok:conformance" in manifest["archive_gates"]["blocking_reasons"]
    assert manifest["archive_gates"]["can_create_external_archive"] is False


def test_evidence_manifest_blocks_oversized_artifact(tmp_path):
    paths = _pilot_artifacts(tmp_path, "hermes")

    manifest = build_host_shell_pilot_evidence_manifest(
        runtime="hermes",
        artifact_paths={key: str(value) for key, value in paths.items()},
        max_artifact_bytes=1,
    )

    assert manifest["ok"] is False
    assert manifest["manifest_status"] == "blocked_missing_artifacts"
    assert "artifact_too_large:preflight" in manifest["archive_gates"]["blocking_reasons"]


def test_evidence_manifest_cli_uses_artifact_root_defaults(tmp_path, capsys):
    paths = _pilot_artifacts(tmp_path / "artifacts" / "hermes", "hermes")

    exit_code = main([
        "host-shell-pilot-evidence-manifest",
        "--runtime",
        "hermes",
        "--package-id",
        "P3.4-hermes",
        "--created-at",
        "2026-06-06T00:00:00Z",
        "--artifact-root",
        str(tmp_path / "artifacts" / "hermes"),
        "--archive-filename",
        "kaka-p3.4-hermes-pilot-evidence.zip",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == "kaka.host_shell_pilot_evidence_manifest.v1"
    assert payload["manifest_status"] == "ready_for_archive"
    assert payload["artifacts"][0]["path"] == str(paths["preflight"])
    assert payload["p3_4_complete"] is False
