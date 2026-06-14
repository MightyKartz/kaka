import json
import os
import subprocess
import struct
import threading
import zlib
from io import StringIO

from agent_pocket_mock_bridge import qa as qa_module
from agent_pocket_mock_bridge.qa import (
    CommandResult,
    build_gate_audit_report,
    build_gate_f_handoff_report,
    build_gate_f_preflight_report,
    build_iphone_credential_boundary_report,
    build_physical_device_preflight_report,
    build_preflight_report,
    build_provider_env_sources_report,
    build_provider_preflight_report,
    build_readiness_markdown,
    build_run_lan_command,
    build_run_tailscale_command,
    build_simulator_preflight_report,
    build_simulator_ui_test_preflight_report,
    build_physical_qa_commands,
    evaluate_connection_restore,
    evaluate_local_recipe_photo_flow,
    evaluate_photo_flow,
    fetch_qa_status,
    main,
    run_simulator_connection_session,
    run_simulator_capture_ready_session,
    run_simulator_result_gallery_downloaded_session,
    run_simulator_result_gallery_session,
    run_simulator_share_sheet_session,
    run_simulator_picker_ui_session,
    run_simulator_seed_photo_library,
    run_simulator_suite,
    run_test_receipt_command,
    run_openai_compatible_simulator_session,
    run_lan_qa_session,
    run_gate_f_resume,
    verify_receipt_payload,
)
from agent_pocket_mock_bridge.server import create_http_server


def _write_photo_flow_receipt(path, provider="fixture"):
    status = {
        "requests": {
            "asset_upload": 1,
            "photo_task_create": 1,
            "asset_download": 1,
        },
        "assets": {"download_request_count": 1},
        "tasks": {"completed": 1, "last_task": {"provider": provider}},
        "provider": {"name": provider},
    }
    path.write_text(json.dumps({
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://127.0.0.1:8769",
        "status": status,
    }))


def _write_connection_receipt(path):
    path.write_text(json.dumps({
        "phase": "connection",
        "ok": True,
        "missing": [],
        "base_url": "http://127.0.0.1:8766",
        "status": {
            "requests": {
                "health": 1,
                "capabilities": 1,
            },
            "assets": {"download_request_count": 0},
            "tasks": {"completed": 0},
        },
    }))


def _write_fake_openai_status(path):
    path.write_text(json.dumps({
        "request_count": 1,
        "last_request": {
            "path": "/images/edits",
            "authorization_present": True,
            "content_type": "multipart/form-data",
            "fields": {
                "model": "gpt-image-1.5",
                "n": "1",
                "output_format": "png",
            },
            "files": {
                "image": {
                    "filename": "input.jpg",
                    "mime_type": "image/jpeg",
                    "size_bytes": 4989,
                }
            },
        },
    }))


def test_build_iphone_credential_boundary_report_allows_hermes_bearer_only(tmp_path):
    app_root = tmp_path / "ios" / "AgentPocket"
    core_root = tmp_path / "Sources" / "AgentPocketCore"
    app_root.mkdir(parents=True)
    core_root.mkdir(parents=True)
    (app_root / "AgentPocketApp.swift").write_text(
        'let displayName = "Pocket Agent"\n',
        encoding="utf-8",
    )
    (core_root / "MobileBridgeClient.swift").write_text(
        'request.setValue("Bearer \\(token)", forHTTPHeaderField: "Authorization")\n',
        encoding="utf-8",
    )

    report = build_iphone_credential_boundary_report(root=str(tmp_path))

    assert report["ok"] is True
    assert report["iphone_credential_required"] is False
    assert report["scanned_files"] == 2
    assert report["violations"] == []


def test_build_iphone_credential_boundary_report_blocks_openai_provider_tokens_without_leaking(tmp_path):
    app_root = tmp_path / "ios" / "AgentPocket"
    app_root.mkdir(parents=True)
    (app_root / "Leaky.swift").write_text(
        'let key = "OPENAI_API_KEY"\nlet endpoint = "https://api.openai.com/v1/images/edits?token=secret-boundary-token"\n',
        encoding="utf-8",
    )

    report = build_iphone_credential_boundary_report(root=str(tmp_path))
    serialized = json.dumps(report)

    assert report["ok"] is False
    assert report["missing"] == ["iPhone OpenAI credential boundary"]
    assert {violation["rule"] for violation in report["violations"]} == {
        "openai_api_key_env",
        "openai_api_host",
        "openai_images_edits_path",
    }
    assert "secret-boundary-token" not in serialized


def test_cli_iphone_credential_boundary_writes_receipt(tmp_path, capsys):
    source_root = tmp_path / "Sources" / "AgentPocketCore"
    source_root.mkdir(parents=True)
    (source_root / "MobileBridgeClient.swift").write_text(
        'request.setValue("Bearer \\(token)", forHTTPHeaderField: "Authorization")\n',
        encoding="utf-8",
    )
    receipt_file = tmp_path / "iphone-boundary.json"

    exit_code = main([
        "iphone-credential-boundary",
        "--root",
        str(tmp_path),
        "--receipt-file",
        str(receipt_file),
    ])

    output = json.loads(capsys.readouterr().out)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert output["ok"] is True
    assert receipt["phase"] == "iphone-credential-boundary"
    assert receipt["scanned_files"] == 1


def test_build_readiness_markdown_summarizes_iphone_credential_boundary():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"title": "A", "status": "passed", "missing": []},
            "B": {"title": "B", "status": "passed", "missing": []},
            "C": {"title": "C", "status": "passed", "missing": []},
            "D": {"title": "D", "status": "passed", "missing": []},
            "E": {"title": "E", "status": "passed", "missing": []},
            "F": {"title": "F", "status": "missing_external_evidence", "missing": ["OPENAI_API_KEY"]},
        },
        "local": {
            "iphone_credential_boundary": {
                "path": "docs/qa-receipts/iphone-credential-boundary-latest.json",
                "exists": True,
                "ok": True,
                "scanned_files": 42,
                "violations": [],
            },
        },
        "external": {},
        "commands": {
            "iphone_credential_boundary": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa "
                "iphone-credential-boundary --receipt-file docs/qa-receipts/iphone-credential-boundary-latest.json"
            ),
        },
    }

    markdown = build_readiness_markdown(report)

    assert "## Client Credential Boundary" in markdown
    assert "- iPhone OpenAI credential boundary: passed (docs/qa-receipts/iphone-credential-boundary-latest.json)" in markdown
    assert "- Scanned client files: 42" in markdown
    assert "### iphone_credential_boundary" in markdown


def test_build_readiness_markdown_distinguishes_failed_provider_receipts():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"title": "A", "status": "passed", "missing": []},
            "B": {"title": "B", "status": "passed", "missing": []},
            "C": {"title": "C", "status": "passed", "missing": []},
            "D": {"title": "D", "status": "passed", "missing": []},
            "E": {"title": "E", "status": "passed", "missing": []},
            "F": {"title": "F", "status": "missing_external_evidence", "missing": ["OPENAI_API_KEY"]},
        },
        "local": {},
        "external": {
            "openai_api_key": "missing",
            "provider_preflight": {
                "path": "docs/qa-receipts/provider-openai-preflight-latest.json",
                "exists": True,
                "ok": False,
                "status": "missing_provider_evidence",
                "missing": ["OPENAI_API_KEY"],
            },
            "provider_env_sources": {
                "path": "docs/qa-receipts/provider-env-sources-latest.json",
                "exists": True,
                "ok": False,
                "status": "missing_provider_env_source",
                "missing": ["OPENAI_API_KEY"],
            },
        },
        "commands": {},
    }

    markdown = build_readiness_markdown(report)

    assert (
        "- Provider preflight receipt: failed "
        "(docs/qa-receipts/provider-openai-preflight-latest.json; missing OPENAI_API_KEY)"
    ) in markdown
    assert (
        "- Provider env source probe: failed "
        "(docs/qa-receipts/provider-env-sources-latest.json; missing OPENAI_API_KEY)"
    ) in markdown
    assert "- Provider preflight receipt: missing " not in markdown
    assert "- Provider env source probe: missing " not in markdown


def _write_test_receipt(path, name, command, stdout_tail="all tests passed"):
    path.write_text(json.dumps({
        "phase": "test-command",
        "name": name,
        "command": command,
        "ok": True,
        "returncode": 0,
        "stdout_tail": stdout_tail,
        "stderr_tail": "",
    }))


def _write_ui_test_preflight_receipt(path, ok=False):
    path.write_text(json.dumps({
        "ok": ok,
        "project": "ios/AgentPocket.xcodeproj",
        "scheme": "AgentPocket",
        "test_target": "AgentPocketPickerUITests",
        "sdk": {
            "ok": True,
            "versions": ["26.5"],
            "latest": "26.5",
            "error": "",
        },
        "runtime": {
            "ok": True,
            "versions": ["26.1"],
            "latest": "26.1",
            "error": "",
        },
        "destinations": {
            "ok": ok,
            "available": [] if not ok else [{"name": "iPhone 17", "os": "26.5", "id": "device-1", "raw": "{}"}],
            "ineligible": [] if ok else ["{ platform:iOS, name:Any iOS Device, error:iOS 26.5 is not installed. }"],
            "error": "",
        },
        "mismatch": {
            "ok": ok,
            "sdk_latest": "26.5",
            "runtime_latest": "26.1",
            "reason": "" if ok else "Installed iOS Simulator runtime does not match the active iOS Simulator SDK.",
        },
        "commands": {
            "run_picker_ui_test": "xcodebuild test -project ios/AgentPocket.xcodeproj -scheme AgentPocket",
        },
    }))


def _write_simulator_suite_receipt(path, ok=True):
    steps = {
        "ui_test_preflight": {
            "ok": True,
            "required": False,
            "runnable": False,
            "status": "blocked_by_local_xcode_runtime",
            "receipt": "docs/qa-receipts/simulator-ui-test-preflight-latest.json",
        },
        "seed_photo_library": {
            "ok": True,
            "required": True,
            "receipt": "/tmp/agent-pocket-simulator-library-fixture.png",
        },
        "connection_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-connection-latest.json",
        },
        "discovery_refresh_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-discovery-refresh-latest.json",
            "screenshot": "/tmp/agent-pocket-simulator-discovery-refresh.png",
        },
        "picker_ui_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "/tmp/agent-pocket-simulator-picker-ui-smoke.png",
        },
        "capture_ready_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-capture-ready-latest.json",
            "screenshot": "/tmp/agent-pocket-simulator-capture-ready.png",
        },
        "capture_completed_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-capture-completed-latest.json",
            "screenshot": "/tmp/agent-pocket-simulator-capture-completed.png",
        },
        "result_gallery_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-result-gallery-latest.json",
            "screenshot": "/tmp/agent-pocket-simulator-result-gallery.png",
        },
        "result_gallery_downloaded_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-result-gallery-downloaded-latest.json",
            "screenshot": "/tmp/agent-pocket-simulator-result-gallery-downloaded.png",
        },
        "openai_smoke": {
            "ok": True,
            "required": True,
            "returncode": 0,
            "receipt": "docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
        },
    }
    if not ok:
        steps["openai_smoke"]["ok"] = False
        steps["openai_smoke"]["returncode"] = 1
    path.write_text(json.dumps({
        "phase": "simulator-suite",
        "ok": ok,
        "failed_required_steps": [] if ok else ["openai_smoke"],
        "steps": steps,
    }))


def _write_simulator_only_resume_receipt(path, ok=True, physical_launch_attempted=False):
    path.write_text(json.dumps({
        "phase": "simulator-only-resume",
        "ok": ok,
        "execution_mode": "local-mac-simulator-only",
        "physical_iphone_used": False,
        "physical_device_launch_attempted": physical_launch_attempted,
        "real_device_commands_executed": [] if not physical_launch_attempted else ["devicectl launch"],
        "simulator_suite": {
            "ok": ok,
            "phase": "simulator-suite",
            "failed_required_steps": [] if ok else ["openai_smoke"],
        },
        "gate_audit_summary": {
            "simulator_evidence_ok": ok,
            "gate_f_ok": False,
            "remaining_external": ["OPENAI_API_KEY"],
        },
    }))


def _write_capture_ready_receipt(path, ok=True):
    path.write_text(json.dumps({
        "phase": "capture-ready",
        "ok": ok,
        "state": "ready" if ok else "failed",
        "file_name": "library.jpg" if ok else "",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": ok,
        "send_to_local_agent_enabled": ok,
        "send_to_hermes_enabled": ok,
        "selection_source": "library_fixture" if ok else "",
        "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage" if ok else "",
        "primary_action": "Send to Local Agent" if ok else "",
        "ready_status_accessibility_identifier": "selectedPhotoReadyStatus" if ok else "",
        "send_button_accessibility_identifier": "sendToLocalAgentButton" if ok else "",
    }))


def _write_discovery_refresh_receipt(path, ok=True):
    path.write_text(json.dumps({
        "phase": "discovery-refresh",
        "ok": ok,
        "missing": [],
        "base_url": "http://127.0.0.1:8767",
        "status": {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "pairing_dev": 1,
                "pairing_exchange": 1,
            },
            "assets": {},
            "tasks": {},
        },
    }))


def _write_capture_completed_receipt(path, ok=True):
    path.write_text(json.dumps({
        "phase": "capture-completed",
        "ok": ok,
        "state": "completed" if ok else "failed",
        "task_id": "task_123" if ok else "",
        "variants_count": 2 if ok else 0,
        "review_results_enabled": ok,
        "review_results_primary": ok,
        "send_to_local_agent_enabled": False,
        "send_to_hermes_enabled": False,
    }))


def _write_result_gallery_receipt(path, ok=True):
    path.write_text(json.dumps({
        "phase": "result-gallery",
        "ok": ok,
        "state": "ready" if ok else "failed",
        "task_status": "completed",
        "variants_count": 2 if ok else 0,
        "selected_variant_id": "variant_1" if ok else "",
        "selected_asset_id": "asset_1" if ok else "",
        "has_explanation": ok,
        "download_selected_enabled": ok,
        "save_enabled": False,
        "share_enabled": False,
    }))


def _write_result_gallery_downloaded_receipt(path, ok=True):
    path.write_text(json.dumps({
        "phase": "result-gallery-downloaded",
        "ok": ok,
        "state": "downloaded" if ok else "failed",
        "task_status": "completed",
        "variants_count": 2 if ok else 0,
        "selected_variant_id": "variant_1" if ok else "",
        "selected_asset_id": "asset_1" if ok else "",
        "downloaded_asset_bytes": 68 if ok else 0,
        "downloaded_mime_type": "image/png" if ok else "",
        "recipe_summary": "Balanced exposure while preserving the original frame." if ok else "",
        "share_caption": "Shot polished locally with Pocket Agent." if ok else "",
        "download_selected_enabled": False,
        "save_enabled": ok,
        "share_enabled": ok,
    }))


def _write_gate_f_preflight_receipt(path, ready_to_run=False):
    path.write_text(json.dumps({
        "ok": False,
        "ready_to_run": ready_to_run,
        "missing_to_start": [] if ready_to_run else ["OPENAI_API_KEY", "Tailscale endpoint evidence"],
        "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
        "checks": {
            "openai_api_key": "set" if ready_to_run else "missing",
            "tailscale": {
                "ok": ready_to_run,
                "cli": {"ok": ready_to_run, "path": "/usr/local/bin/tailscale" if ready_to_run else ""},
                "ip_check": {"ok": ready_to_run, "value": "100.101.102.103" if ready_to_run else ""},
            },
            "physical_openai_receipt": {
                "path": "docs/qa-receipts/openai-photo-flow.json",
                "exists": False,
                "ok": False,
                "missing": ["receipt file"],
            },
        },
        "commands": {
            "provider_preflight": (
                "OPENAI_API_KEY=<set-in-hermes-process> PYTHONPATH=mock_bridge "
                "python3 -m agent_pocket_mock_bridge.qa provider-preflight --photo-provider openai"
            ),
            "run_real_iphone_openai": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
                "--photo-provider openai --receipt-file docs/qa-receipts/openai-photo-flow.json"
            ),
            "verify_real_iphone_openai": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt "
                "--file docs/qa-receipts/openai-photo-flow.json --phase photo-flow --photo-provider openai"
            ),
        },
    }))


def _write_provider_preflight_receipt(path, key_state="set"):
    path.write_text(json.dumps({
        "ok": key_state == "set",
        "provider": "openai",
        "missing": [] if key_state == "set" else ["OPENAI_API_KEY"],
        "adapter": {
            "path": "photo-pack/adapters/openai_image.py",
            "exists": True,
        },
        "env": {
            "OPENAI_API_KEY": key_state,
        },
        "commands": {
            "server": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server "
                "--host 0.0.0.0 --port 8765 --bonjour --photo-provider openai "
                "--env-file /path/to/hermes-openai.env"
            ),
        },
    }))


def _write_hermes_profile(root, profile, env_text="", auth=None):
    profile_root = root / "profiles" / profile
    profile_root.mkdir(parents=True, exist_ok=True)
    if env_text is not None:
        (profile_root / ".env").write_text(env_text, encoding="utf-8")
    if auth is None:
        auth = {
            "version": 1,
            "credential_pool": {
                "openai-codex": [
                    {
                        "label": "codex-oauth",
                        "auth_type": "oauth",
                        "access_token": "codex-token-that-must-not-leak",
                    }
                ]
            },
        }
    (profile_root / "auth.json").write_text(json.dumps(auth), encoding="utf-8")
    return profile_root


def _write_hermes_shared_auth(root, auth):
    shared_auth_root = root / "shared-auth"
    shared_auth_root.mkdir(parents=True, exist_ok=True)
    (shared_auth_root / "auth.json").write_text(json.dumps(auth), encoding="utf-8")
    return shared_auth_root / "auth.json"


def _write_rgb_png(path, width, height, pixel_at):
    def chunk(kind, data):
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(pixel_at(x, y))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )


def _write_visible_simulator_screenshot(path):
    _write_rgb_png(
        path,
        80,
        120,
        lambda x, y: (32, 95, 210) if 16 <= x <= 64 and 32 <= y <= 82 else (255, 255, 255),
    )


def _write_status_bar_only_simulator_screenshot(path):
    _write_rgb_png(
        path,
        80,
        120,
        lambda _x, y: (20, 20, 20) if y < 10 else (255, 255, 255),
    )


def _write_openai_adapter(root):
    adapter_path = root / "photo-pack" / "adapters" / "openai_image.py"
    adapter_path.parent.mkdir(parents=True, exist_ok=True)
    adapter_path.write_text("# test adapter\n")


def test_evaluate_photo_flow_reports_missing_steps():
    status = {
        "requests": {"asset_upload": 1, "photo_task_create": 0, "asset_download": 0},
        "assets": {"uploaded_count": 1, "download_request_count": 0},
        "tasks": {"completed": 0},
    }

    result = evaluate_photo_flow(status)

    assert result.ok is False
    assert result.missing == [
        "photo_task_create request",
        "completed task",
        "asset_download request",
        "result download",
    ]


def test_evaluate_photo_flow_accepts_completed_upload_task_and_download():
    status = {
        "requests": {"asset_upload": 1, "photo_task_create": 1, "asset_download": 1},
        "assets": {"uploaded_count": 1, "download_request_count": 1},
        "tasks": {"completed": 1},
    }

    result = evaluate_photo_flow(status)

    assert result.ok is True
    assert result.missing == []


def test_evaluate_local_recipe_photo_flow_requires_recipe_metadata():
    status = {
        "requests": {"asset_upload": 1, "photo_task_create": 1, "asset_download": 1},
        "assets": {"uploaded_count": 1, "download_request_count": 1},
        "tasks": {
            "completed": 1,
            "last_task": {
                "provider": "recipe_local",
                "variant_count": 2,
                "composition": {
                    "selected_aspect_ratio": "original",
                    "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                },
                "qa": {
                    "master_difference_score": 0.18,
                    "social_difference_score": 0.31,
                },
                "renderer": "local_parametric",
            },
        },
        "provider": {"name": "recipe_local"},
    }

    result = evaluate_local_recipe_photo_flow(status)

    assert result.ok is True
    assert result.missing == []

    missing = evaluate_local_recipe_photo_flow({
        "requests": status["requests"],
        "assets": status["assets"],
        "tasks": {"completed": 1, "last_task": {"provider": "recipe_local", "variant_count": 1}},
        "provider": {"name": "recipe_local"},
    })

    assert missing.ok is False
    assert missing.missing == [
        "local recipe two variants",
        "local recipe renderer",
        "local recipe composition",
        "local recipe crop metadata",
        "local recipe difference metrics",
    ]


def test_evaluate_connection_restore_requires_health_and_capabilities():
    status = {
        "requests": {"health": 1, "capabilities": 0},
        "assets": {},
        "tasks": {},
    }

    result = evaluate_connection_restore(status)

    assert result.ok is False
    assert result.missing == ["capabilities request"]


def test_evaluate_discovery_refresh_requires_pairing_refresh_exchange_and_connection():
    result = qa_module.evaluate_discovery_refresh({
        "requests": {
            "health": 1,
            "capabilities": 1,
            "pairing_dev": 1,
            "pairing_exchange": 1,
        }
    })

    assert result.ok is True
    assert result.missing == []

    missing = qa_module.evaluate_discovery_refresh({
        "requests": {
            "health": 1,
            "capabilities": 1,
            "pairing_dev": 0,
            "pairing_exchange": 0,
        }
    })

    assert missing.ok is False
    assert missing.missing == ["pairing_dev request", "pairing_exchange request"]


def test_verify_receipt_payload_accepts_complete_photo_flow_receipt():
    receipt = {
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "script"}},
            "provider": {"name": "script"},
        },
    }

    result = verify_receipt_payload(receipt, expected_phase="photo-flow", expected_provider="script")

    assert result.ok is True
    assert result.missing == []


def test_verify_receipt_payload_rejects_provider_mismatch():
    receipt = {
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "fixture"}},
            "provider": {"name": "fixture"},
        },
    }

    result = verify_receipt_payload(receipt, expected_phase="photo-flow", expected_provider="script")

    assert result.ok is False
    assert result.missing == ["provider script"]


def test_verify_receipt_payload_recomputes_missing_photo_flow_steps():
    receipt = {
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 0,
            },
            "assets": {"download_request_count": 0},
            "tasks": {"completed": 1},
        },
    }

    result = verify_receipt_payload(receipt, expected_phase="photo-flow")

    assert result.ok is False
    assert result.missing == ["asset_download request", "result download"]


def test_verify_receipt_payload_rejects_phase_mismatch_and_false_ok_flag():
    receipt = {
        "phase": "connection",
        "ok": False,
        "missing": [],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {"download_request_count": 0},
            "tasks": {},
        },
    }

    result = verify_receipt_payload(receipt, expected_phase="photo-flow")

    assert result.ok is False
    assert result.missing == [
        "phase photo-flow",
        "ok receipt flag",
        "asset_upload request",
        "photo_task_create request",
        "completed task",
        "asset_download request",
        "result download",
    ]


def test_fetch_qa_status_reads_real_http_server():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status = fetch_qa_status(base_url, token="dev-mobile-token")

        assert status["pairing"]["current_development_code"] == "pair_dev"
        assert status["requests"]["health"] == 0
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_cli_status_prints_json(capsys):
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        exit_code = main(["status", "--base-url", base_url])

        output = json.loads(capsys.readouterr().out)
        assert exit_code == 0
        assert output["pairing"]["current_development_code"] == "pair_dev"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_cli_smoke_real_provider_fake_runs_full_http_task_chain(capsys):
    exit_code = main([
        "smoke-real-provider",
        "--fake",
        "--timeout",
        "5",
        "--interval",
        "0",
    ])

    report = json.loads(capsys.readouterr().out)
    step_names = [step["name"] for step in report["steps"]]

    assert exit_code == 0
    assert report["ok"] is True
    assert report["mode"] == "fake"
    assert report["provider"] == "fake"
    assert step_names == [
        "health",
        "capabilities",
        "asset_upload",
        "image_intake_create",
        "image_intake_status",
        "image_intake_result",
        "universal_intake_create",
        "universal_intake_status",
        "universal_intake_result",
        "recall_remember",
        "recall_forget",
    ]
    assert {step["status"] for step in report["steps"]} == {"passed"}
    assert report["artifacts"]["asset_id"].startswith("asset_")
    assert report["artifacts"]["image_source"] == "generated_file"
    assert report["artifacts"]["image_file"].endswith("kaka-smoke-real-provider.png")
    assert os.path.exists(report["artifacts"]["image_file"])
    assert report["tasks"]["image_intake"]["status"] == "completed"
    assert report["tasks"]["image_intake"]["result_type"] == "image_intake"
    assert report["tasks"]["universal_intake"]["status"] == "completed"
    assert report["tasks"]["universal_intake"]["result_type"] == "intake"
    assert report["recall"]["remember"]["status"] == "remembered"
    assert report["recall"]["forget"]["status"] == "forgotten"


def test_cli_smoke_real_provider_real_requires_anthropic_key(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    exit_code = main(["smoke-real-provider", "--real"])

    report = json.loads(capsys.readouterr().err)
    assert exit_code == 2
    assert report["ok"] is False
    assert report["mode"] == "real"
    assert report["provider"] == "anthropic"
    assert report["error"]["code"] == "missing_anthropic_api_key"
    assert "ANTHROPIC_API_KEY" in report["error"]["message"]


def test_cli_smoke_real_provider_hermes_requires_hermes_key(capsys, monkeypatch):
    monkeypatch.delenv("KAKA_HERMES_API_KEY", raising=False)

    exit_code = main(["smoke-real-provider", "--provider", "hermes"])

    report = json.loads(capsys.readouterr().err)
    assert exit_code == 2
    assert report["ok"] is False
    assert report["mode"] == "hermes"
    assert report["provider"] == "hermes"
    assert report["error"]["code"] == "missing_hermes_api_key"
    assert "KAKA_HERMES_API_KEY" in report["error"]["message"]


def test_cli_smoke_real_provider_hermes_dispatches_manual_provider(monkeypatch, capsys):
    captured = {}
    monkeypatch.setenv("KAKA_HERMES_API_KEY", "secret-runtime-key")

    def fake_smoke_real_provider(**kwargs):
        captured.update(kwargs)
        return {
            "schema_version": "kaka.smoke_real_provider.v1",
            "surface": "mock_bridge_server_smoke",
            "ok": True,
            "mode": kwargs["mode"],
            "provider": "hermes",
            "base_url": "http://127.0.0.1:8765",
            "steps": [],
            "artifacts": {},
            "tasks": {},
            "recall": {},
        }

    monkeypatch.setattr(qa_module, "run_smoke_real_provider", fake_smoke_real_provider)

    exit_code = main(["smoke-real-provider", "--provider", "hermes", "--timeout", "5"])

    report = json.loads(capsys.readouterr().out)
    rendered = json.dumps(report, sort_keys=True)
    assert exit_code == 0
    assert captured["mode"] == "hermes"
    assert report["provider"] == "hermes"
    assert "secret-runtime-key" not in rendered


def test_build_physical_qa_commands_includes_bridge_launch_app_launch_and_waits():
    commands = build_physical_qa_commands(
        host="192.0.2.10",
        port=8765,
        device_id="00000000-0000-0000-0000-000000000000",
    )

    joined = "\n".join(commands)
    assert "agent_pocket_mock_bridge.server --host 0.0.0.0 --port 8765 --bonjour --bonjour-host 192.0.2.10" in joined
    assert "devicectl device process launch --device 00000000-0000-0000-0000-000000000000 --terminate-existing com.kaka.AgentPocket" in joined
    assert "wait-connection --base-url http://192.0.2.10:8765" in joined
    assert "wait-photo-flow --base-url http://192.0.2.10:8765 --timeout 180" in joined


def test_build_run_lan_command_includes_single_session_runner():
    command = build_run_lan_command(
        host="192.0.2.10",
        port=8765,
        device_id="00000000-0000-0000-0000-000000000000",
    )

    assert command == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
        "--host 192.0.2.10 --port 8765 "
        "--device-id 00000000-0000-0000-0000-000000000000 "
        "--bundle-id com.kaka.AgentPocket "
        "--connection-timeout 60 --photo-timeout 180"
    )


def test_build_run_lan_command_can_select_real_photo_provider():
    command = build_run_lan_command(
        host="192.0.2.10",
        port=8765,
        device_id="00000000-0000-0000-0000-000000000000",
        photo_provider="openai",
    )

    assert "--photo-provider openai" in command


def test_build_run_tailscale_command_disables_bonjour_for_tailnet_manual_pairing():
    command = build_run_tailscale_command(
        host="100.101.102.103",
        port=8765,
        device_id="00000000-0000-0000-0000-000000000000",
    )

    assert command == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
        "--host 100.101.102.103 --port 8765 "
        "--device-id 00000000-0000-0000-0000-000000000000 "
        "--bundle-id com.kaka.AgentPocket "
        "--connection-timeout 60 --photo-timeout 180 --no-bonjour"
    )


def test_build_preflight_report_collects_lan_tailscale_device_and_commands():
    calls = []

    def run(command):
        calls.append(tuple(command))
        if command == ["ipconfig", "getifaddr", "en0"]:
            return CommandResult(returncode=0, stdout="192.0.2.10\n", stderr="")
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        if command == ["tailscale", "ip", "-4"]:
            return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Name             Hostname                          Identifier                             State\n"
                    "--------------   -------------------------------   ------------------------------------   ---------\n"
                    "iPhone 16 Plus   iPhone-16-Plus.coredevice.local   00000000-0000-0000-0000-000000000000   connected\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "--find", "devicectl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/devicectl\n", stderr="")
        if command == ["which", "dns-sd"]:
            return CommandResult(returncode=0, stdout="/usr/bin/dns-sd\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 Pro (2B89C11B-496C-43A0-852B-995D488187B6) (Shutdown)\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_preflight_report(command_runner=run)

    assert report["lan"]["ip"] == "192.0.2.10"
    assert report["tailscale"]["ip"] == "100.101.102.103"
    assert report["device"]["id"] == "00000000-0000-0000-0000-000000000000"
    assert report["tools"]["devicectl"]["ok"] is True
    assert report["tools"]["dns_sd"]["ok"] is True
    assert report["simulator"]["booted"]["id"] == "053743B2-A12B-4C6A-99CC-F46108333560"
    assert "xcrun simctl install booted" in report["simulator"]["commands"]["install"]
    assert "--gate-f-host 192.0.2.10" in report["simulator"]["commands"]["simulator_only_resume"]
    assert "--host 192.0.2.10" in report["commands"]["lan"]
    assert "--host 100.101.102.103" in report["commands"]["tailscale"]
    assert "--no-bonjour" in report["commands"]["tailscale"]
    assert calls == [
        ("ipconfig", "getifaddr", "en0"),
        ("which", "tailscale"),
        ("tailscale", "ip", "-4"),
        ("xcrun", "devicectl", "list", "devices"),
        ("xcrun", "--find", "devicectl"),
        ("which", "dns-sd"),
        ("xcrun", "simctl", "list", "devices", "available"),
        ("xcrun", "simctl", "list", "devices", "booted"),
        ("xcrun", "--find", "simctl"),
    ]


def test_build_preflight_report_uses_tailscale_cli_env_override():
    calls = []
    tailscale_cli = "/opt/homebrew/bin/tailscale"

    def run(command):
        calls.append(tuple(command))
        if command == ["ipconfig", "getifaddr", "en0"]:
            return CommandResult(returncode=0, stdout="192.0.2.10\n", stderr="")
        if command == [tailscale_cli, "version"]:
            return CommandResult(returncode=0, stdout="1.80.0\n", stderr="")
        if command == [tailscale_cli, "ip", "-4"]:
            return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["xcrun", "--find", "devicectl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/devicectl\n", stderr="")
        if command == ["which", "dns-sd"]:
            return CommandResult(returncode=0, stdout="/usr/bin/dns-sd\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_preflight_report(
        command_runner=run,
        env={"TAILSCALE_CLI": tailscale_cli},
    )

    assert report["tailscale"]["ip"] == "100.101.102.103"
    assert report["tailscale"]["cli"]["path"] == tailscale_cli
    assert report["tailscale"]["cli"]["configured_by"] == "TAILSCALE_CLI"
    assert (tailscale_cli, "version") in calls
    assert ("tailscale", "ip", "-4") not in calls
    assert (tailscale_cli, "ip", "-4") in calls


def test_build_preflight_report_reports_missing_tailscale_without_low_level_errno():
    def run(command):
        if command == ["ipconfig", "getifaddr", "en0"]:
            return CommandResult(returncode=0, stdout="192.0.2.10\n", stderr="")
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["xcrun", "--find", "devicectl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/devicectl\n", stderr="")
        if command == ["which", "dns-sd"]:
            return CommandResult(returncode=0, stdout="/usr/bin/dns-sd\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_preflight_report(command_runner=run)

    assert report["tailscale"]["ok"] is False
    assert report["tailscale"]["cli"]["error"] == "tailscale CLI not found in PATH"
    assert report["tailscale"]["ip_check"]["error"] == "Install or expose the tailscale CLI in PATH first."
    assert "[Errno" not in json.dumps(report)


def test_build_physical_device_preflight_reports_xcode_platform_blocker():
    def run(command):
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Name             Hostname                          Identifier                             State                Model\n"
                    "--------------   -------------------------------   ------------------------------------   ------------------   ---------------------------\n"
                    "iPhone 16 Plus   iPhone-16-Plus.coredevice.local   00000000-0000-0000-0000-000000000000   available (paired)   iPhone 16 Plus (iPhone17,4)\n"
                ),
                stderr="",
            )
        if command == ["xcodebuild", "-project", "ios/AgentPocket.xcodeproj", "-scheme", "AgentPocket", "-showdestinations"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Ineligible destinations for the \"AgentPocket\" scheme:\n"
                    "\t{ platform:iOS, arch:arm64e, id:00008140-000835003EEB001C, "
                    "name:iPhone 16 Plus, error:iOS 26.5 is not installed. "
                    "Please download and install the platform from Xcode > Settings > Components. }\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    report = build_physical_device_preflight_report(
        device_id="00000000-0000-0000-0000-000000000000",
        command_runner=run,
    )

    assert report["ok"] is False
    assert report["status"] == "blocked_by_xcode_device_support"
    assert report["device"]["ok"] is True
    assert report["device"]["id"] == "00000000-0000-0000-0000-000000000000"
    assert report["device"]["name"] == "iPhone 16 Plus"
    assert report["device"]["state"] == "available (paired)"
    assert report["xcode_destination"]["ok"] is False
    assert "iOS 26.5 is not installed" in report["xcode_destination"]["ineligible"][0]
    assert report["missing"] == ["Xcode iOS device platform support"]
    assert "Xcode > Settings > Components" in report["next_actions"][0]


def test_build_physical_device_preflight_marks_cli_ready_when_target_build_succeeds():
    def run(command):
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Name             Hostname                          Identifier                             State                Model\n"
                    "--------------   -------------------------------   ------------------------------------   ------------------   ---------------------------\n"
                    "iPhone 16 Plus   iPhone-16-Plus.coredevice.local   00000000-0000-0000-0000-000000000000   available (paired)   iPhone 16 Plus (iPhone17,4)\n"
                ),
                stderr="",
            )
        if command == ["xcodebuild", "-project", "ios/AgentPocket.xcodeproj", "-scheme", "AgentPocket", "-showdestinations"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Ineligible destinations for the \"AgentPocket\" scheme:\n"
                    "\t{ platform:iOS, arch:arm64e, id:00008140-000835003EEB001C, "
                    "name:iPhone 16 Plus, error:iOS 26.5 is not installed. "
                    "Please download and install the platform from Xcode > Settings > Components. }\n"
                ),
                stderr="",
            )
        if command == [
            "xcodebuild",
            "-project",
            "ios/AgentPocket.xcodeproj",
            "-target",
            "AgentPocket",
            "-configuration",
            "Debug",
            "-sdk",
            "iphoneos",
            "-allowProvisioningUpdates",
            "build",
        ]:
            return CommandResult(returncode=0, stdout="** BUILD SUCCEEDED **", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_physical_device_preflight_report(
        device_id="00000000-0000-0000-0000-000000000000",
        build_check=True,
        command_runner=run,
    )

    assert report["ok"] is True
    assert report["status"] == "ready_via_cli_build"
    assert report["missing"] == []
    assert report["xcode_destination"]["ok"] is False
    assert report["target_build"]["checked"] is True
    assert report["target_build"]["ok"] is True
    assert "Xcode Run button" in report["next_actions"][0]


def test_build_simulator_preflight_report_collects_booted_device_and_commands(tmp_path):
    app_path = tmp_path / "AgentPocket.app"
    app_path.mkdir()
    calls = []

    def run(command):
        calls.append(tuple(command))
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 Pro (2B89C11B-496C-43A0-852B-995D488187B6) (Shutdown)\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_simulator_preflight_report(
        app_path=str(app_path),
        port=8766,
        gate_f_host="192.0.2.10",
        command_runner=run,
    )

    assert report["ok"] is True
    assert report["app"]["exists"] is True
    assert report["booted"]["name"] == "iPhone 17"
    assert report["booted"]["id"] == "053743B2-A12B-4C6A-99CC-F46108333560"
    assert report["selected"]["id"] == "053743B2-A12B-4C6A-99CC-F46108333560"
    assert "xcodebuild -project ios/AgentPocket.xcodeproj" in report["commands"]["build"]
    assert report["commands"]["install"] == f"xcrun simctl install booted {app_path}"
    assert report["commands"]["launch"] == (
        "xcrun simctl launch --terminate-running-process booted com.kaka.AgentPocket"
    )
    assert "--host 127.0.0.1 --port 8766 --no-launch --connection-only" in report["commands"]["local_connection"]
    assert report["commands"]["capture_ready_smoke"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke "
        "--bundle-id com.kaka.AgentPocket "
        "--screenshot-file /tmp/agent-pocket-simulator-capture-ready.png "
        "--receipt-file docs/qa-receipts/simulator-capture-ready-latest.json"
    )
    assert report["commands"]["capture_completed_smoke"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke "
        "--bundle-id com.kaka.AgentPocket "
        "--screenshot-file /tmp/agent-pocket-simulator-capture-completed.png "
        "--receipt-file docs/qa-receipts/simulator-capture-completed-latest.json"
    )
    assert report["commands"]["result_gallery_smoke"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-smoke "
        "--bundle-id com.kaka.AgentPocket "
        "--screenshot-file /tmp/agent-pocket-simulator-result-gallery.png "
        "--receipt-file docs/qa-receipts/simulator-result-gallery-latest.json"
    )
    assert report["commands"]["share_sheet_smoke"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-share-sheet-smoke "
        "--bundle-id com.kaka.AgentPocket "
        "--screenshot-file /tmp/agent-pocket-simulator-share-sheet.png "
        "--receipt-file docs/qa-receipts/share-sheet-flow-latest.json"
    )
    assert report["commands"]["picker_ui_smoke"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-picker-ui-smoke "
        "--bundle-id com.kaka.AgentPocket "
        "--screenshot-file /tmp/agent-pocket-simulator-picker-ui-smoke.png"
    )
    assert report["commands"]["ui_test_preflight"] == (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight "
        "--receipt-file docs/qa-receipts/simulator-ui-test-preflight-latest.json"
    )
    assert "--gate-f-host 192.0.2.10" in report["commands"]["simulator_only_resume"]
    assert calls == [
        ("xcrun", "simctl", "list", "devices", "available"),
        ("xcrun", "simctl", "list", "devices", "booted"),
        ("xcrun", "--find", "simctl"),
    ]


def test_build_simulator_ui_test_preflight_report_detects_sdk_runtime_mismatch():
    calls = []

    def run(command):
        calls.append(command)
        if command == ["xcodebuild", "-showsdks"]:
            return CommandResult(
                returncode=0,
                stdout="iOS Simulator SDKs:\n\tSimulator - iOS 26.5          \t-sdk iphonesimulator26.5\n",
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "runtimes"]:
            return CommandResult(
                returncode=0,
                stdout="== Runtimes ==\niOS 26.1 (26.1 - 23B86) - com.apple.CoreSimulator.SimRuntime.iOS-26-1\n",
                stderr="",
            )
        if command == [
            "xcodebuild",
            "-showdestinations",
            "-project",
            "ios/AgentPocket.xcodeproj",
            "-scheme",
            "AgentPocket",
            "-sdk",
            "iphonesimulator",
        ]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Ineligible destinations for the \"AgentPocket\" scheme:\n"
                    "\t{ platform:iOS, id:dvtdevice-DVTiPhonePlaceholder-iphoneos:placeholder, "
                    "name:Any iOS Device, error:iOS 26.5 is not installed. Please download and install "
                    "the platform from Xcode > Settings > Components. }\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    report = build_simulator_ui_test_preflight_report(command_runner=run)

    assert report["ok"] is False
    assert report["sdk"]["latest"] == "26.5"
    assert report["runtime"]["latest"] == "26.1"
    assert report["mismatch"]["ok"] is False
    assert report["mismatch"]["sdk_latest"] == "26.5"
    assert report["mismatch"]["runtime_latest"] == "26.1"
    assert "runtime does not match" in report["mismatch"]["reason"]
    assert report["destinations"]["ok"] is False
    assert "iOS 26.5 is not installed" in report["destinations"]["ineligible"][0]
    assert "AgentPocketPickerUITests" in report["commands"]["build_ui_test_bundle"]
    assert "simulator-picker-ui-smoke" in report["commands"]["launch_picker_ui_smoke"]
    assert calls == [
        ["xcodebuild", "-showsdks"],
        ["xcrun", "simctl", "list", "runtimes"],
        [
            "xcodebuild",
            "-showdestinations",
            "-project",
            "ios/AgentPocket.xcodeproj",
            "-scheme",
            "AgentPocket",
            "-sdk",
            "iphonesimulator",
        ],
    ]


def test_build_simulator_ui_test_preflight_report_accepts_matching_runtime_and_destination():
    def run(command):
        if command == ["xcodebuild", "-showsdks"]:
            return CommandResult(
                returncode=0,
                stdout="iOS Simulator SDKs:\n\tSimulator - iOS 26.5          \t-sdk iphonesimulator26.5\n",
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "runtimes"]:
            return CommandResult(
                returncode=0,
                stdout="== Runtimes ==\niOS 26.5 (26.5 - 23F66) - com.apple.CoreSimulator.SimRuntime.iOS-26-5\n",
                stderr="",
            )
        if command == [
            "xcodebuild",
            "-showdestinations",
            "-project",
            "ios/AgentPocket.xcodeproj",
            "-scheme",
            "AgentPocket",
            "-sdk",
            "iphonesimulator",
        ]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Available destinations for the \"AgentPocket\" scheme:\n"
                    "\t{ platform:iOS Simulator, arch:arm64, id:053743B2-A12B-4C6A-99CC-F46108333560, "
                    "OS:26.5, name:iPhone 17 }\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    report = build_simulator_ui_test_preflight_report(command_runner=run)

    assert report["ok"] is True
    assert report["mismatch"]["ok"] is True
    assert report["destinations"]["ok"] is True
    assert report["destinations"]["available"][0]["name"] == "iPhone 17"
    assert report["destinations"]["available"][0]["os"] == "26.5"


def test_build_simulator_preflight_report_surfaces_boot_requirement_and_app_gap(tmp_path):
    app_path = tmp_path / "Missing.app"

    def run(command):
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 Pro (2B89C11B-496C-43A0-852B-995D488187B6) (Shutdown)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_simulator_preflight_report(app_path=str(app_path), command_runner=run)

    assert report["ok"] is False
    assert report["app"]["exists"] is False
    assert report["booted"]["ok"] is False
    assert report["selected"]["state"] == "Shutdown"
    assert report["commands"]["boot"] == (
        "xcrun simctl boot 2B89C11B-496C-43A0-852B-995D488187B6 && "
        "xcrun simctl bootstatus 2B89C11B-496C-43A0-852B-995D488187B6 -b"
    )


def test_build_preflight_report_accepts_available_paired_coredevice_state():
    def run(command):
        if command == ["ipconfig", "getifaddr", "en0"]:
            return CommandResult(returncode=0, stdout="192.0.2.10\n", stderr="")
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Name             Hostname                          Identifier                             State\n"
                    "--------------   -------------------------------   ------------------------------------   ------------------\n"
                    "iPhone 16 Plus   iPhone-16-Plus.coredevice.local   00000000-0000-0000-0000-000000000000   available (paired)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "--find", "devicectl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/devicectl\n", stderr="")
        if command == ["which", "dns-sd"]:
            return CommandResult(returncode=0, stdout="/usr/bin/dns-sd\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_preflight_report(command_runner=run)

    assert report["device"]["ok"] is True
    assert report["device"]["id"] == "00000000-0000-0000-0000-000000000000"
    assert "--device-id 00000000-0000-0000-0000-000000000000" in report["commands"]["lan"]


def test_run_lan_qa_session_launches_bridge_bonjour_app_and_waits_for_receipts():
    launched_apps = []
    bonjour_commands = []
    fetches = []
    process = FakeProcess()
    statuses = [
        {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {},
            "tasks": {},
        },
        {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1},
        },
    ]

    def launch_app(device_id, bundle_id):
        launched_apps.append((device_id, bundle_id))

    def launch_bonjour(command):
        bonjour_commands.append(command)
        return process

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        fetches.append((base_url, token, timeout))
        return statuses.pop(0)

    exit_code = run_lan_qa_session(
        host="192.0.2.10",
        port=0,
        device_id="device-1",
        app_launcher=launch_app,
        bonjour_launcher=launch_bonjour,
        status_fetcher=fetch_status,
        connection_timeout=1,
        photo_timeout=1,
        interval=0,
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert launched_apps == [("device-1", "com.kaka.AgentPocket")]
    assert any("endpoint=http://192.0.2.10:" in item for item in bonjour_commands[0])
    assert fetches[0][0].startswith("http://192.0.2.10:")
    assert fetches[0][1] == "dev-mobile-token"
    assert process.terminated is True
    assert process.wait_timeout == 2


def test_run_lan_qa_session_writes_final_photo_flow_receipt(tmp_path):
    receipt_path = tmp_path / "lan-photo-receipt.json"
    process = FakeProcess()
    statuses = [
        {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {},
            "tasks": {},
        },
        {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1},
        },
    ]

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return statuses.pop(0)

    exit_code = run_lan_qa_session(
        host="192.0.2.10",
        port=0,
        device_id="device-1",
        app_launcher=lambda device_id, bundle_id: None,
        bonjour_launcher=lambda command: process,
        status_fetcher=fetch_status,
        connection_timeout=1,
        photo_timeout=1,
        interval=0,
        receipt_file=str(receipt_path),
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert receipt["phase"] == "photo-flow"
    assert receipt["ok"] is True
    assert receipt["base_url"].startswith("http://192.0.2.10:")
    assert receipt["status"]["assets"]["download_request_count"] == 1


def test_run_lan_qa_session_writes_connection_failure_receipt(tmp_path):
    receipt_path = tmp_path / "lan-connection-receipt.json"

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return {
            "requests": {"health": 1, "capabilities": 0},
            "assets": {},
            "tasks": {},
        }

    exit_code = run_lan_qa_session(
        host="192.0.2.10",
        port=0,
        device_id="",
        launch_app=False,
        advertise_bonjour=False,
        status_fetcher=fetch_status,
        connection_timeout=0,
        interval=0,
        receipt_file=str(receipt_path),
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 1
    assert receipt["phase"] == "connection"
    assert receipt["ok"] is False
    assert receipt["missing"] == ["capabilities request"]


def test_run_simulator_connection_session_launches_app_and_writes_receipt(tmp_path):
    receipt_path = tmp_path / "simulator-connection.json"
    launched_apps = []
    bonjour_commands = []
    process = FakeProcess()

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {},
            "tasks": {},
        }

    exit_code = run_simulator_connection_session(
        host="127.0.0.1",
        port=0,
        bundle_id="com.kaka.AgentPocket",
        simulator_launcher=lambda bundle_id: launched_apps.append(bundle_id),
        bonjour_launcher=lambda command: (bonjour_commands.append(command) or process),
        status_fetcher=fetch_status,
        connection_timeout=1,
        interval=0,
        receipt_file=str(receipt_path),
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert launched_apps == ["com.kaka.AgentPocket"]
    assert any("endpoint=http://127.0.0.1:" in item for item in bonjour_commands[0])
    assert receipt["phase"] == "connection"
    assert receipt["ok"] is True
    assert receipt["base_url"].startswith("http://127.0.0.1:")
    assert process.terminated is True


def test_run_simulator_discovery_refresh_session_launches_no_payload_smoke_and_writes_receipt(tmp_path):
    receipt_path = tmp_path / "discovery-refresh.json"
    screenshot_path = tmp_path / "discovery-refresh.png"
    launches = []
    screenshots = []

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "pairing_dev": 1,
                "pairing_exchange": 1,
            },
            "assets": {},
            "tasks": {},
        }

    exit_code = qa_module.run_simulator_discovery_refresh_session(
        host="127.0.0.1",
        port=0,
        bundle_id="com.kaka.AgentPocket",
        simulator_launcher=lambda bundle_id, base_url: launches.append((bundle_id, base_url)),
        simulator_screenshotter=lambda path: screenshots.append(path),
        status_fetcher=fetch_status,
        connection_timeout=1,
        interval=0,
        receipt_file=str(receipt_path),
        screenshot_file=str(screenshot_path),
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert receipt["phase"] == "discovery-refresh"
    assert receipt["ok"] is True
    assert receipt["missing"] == []
    assert launches[0][0] == "com.kaka.AgentPocket"
    assert launches[0][1].startswith("http://127.0.0.1:")
    assert screenshots == [str(screenshot_path)]


def test_run_openai_compatible_simulator_session_launches_smoke_and_writes_receipts(tmp_path, monkeypatch):
    receipt_path = tmp_path / "simulator-openai-photo-flow.json"
    fake_status_path = tmp_path / "fake-openai-status.json"
    screenshot_path = tmp_path / "simulator-smoke.png"
    launched = []
    screenshots = []
    statuses = [
        {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {},
            "tasks": {},
            "provider": {"name": "openai"},
        },
        {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "openai"}},
            "provider": {"name": "openai"},
        },
    ]

    monkeypatch.setenv("OPENAI_API_KEY", "real-user-value")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_IMAGE_OUTPUT_FORMAT", raising=False)

    def launch_simulator(bundle_id, base_url, token):
        launched.append((bundle_id, base_url, token))

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return statuses.pop(0)

    def take_screenshot(path):
        screenshots.append(path)

    exit_code = run_openai_compatible_simulator_session(
        host="127.0.0.1",
        bridge_port=0,
        fake_openai_port=0,
        bundle_id="com.kaka.AgentPocket",
        token="dev-mobile-token",
        connection_timeout=1,
        photo_timeout=1,
        interval=0,
        receipt_file=str(receipt_path),
        fake_openai_status_file=str(fake_status_path),
        screenshot_file=str(screenshot_path),
        simulator_launcher=launch_simulator,
        simulator_screenshotter=take_screenshot,
        status_fetcher=fetch_status,
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    fake_status = json.loads(fake_status_path.read_text())
    assert exit_code == 0
    assert launched == [
        (
            "com.kaka.AgentPocket",
            receipt["base_url"],
            "dev-mobile-token",
        )
    ]
    assert screenshots == [str(screenshot_path)]
    assert receipt["phase"] == "photo-flow"
    assert receipt["ok"] is True
    assert receipt["status"]["provider"]["name"] == "openai"
    assert fake_status["request_count"] == 0
    assert os.environ["OPENAI_API_KEY"] == "real-user-value"
    assert "OPENAI_BASE_URL" not in os.environ
    assert "OPENAI_IMAGE_OUTPUT_FORMAT" not in os.environ


def test_run_local_recipe_simulator_session_launches_smoke_and_writes_receipt(tmp_path):
    receipt_path = tmp_path / "simulator-local-recipe-photo-flow.json"
    screenshot_path = tmp_path / "simulator-local-recipe.png"
    launched = []
    screenshots = []
    statuses = [
        {
            "requests": {"health": 1, "capabilities": 1},
            "assets": {},
            "tasks": {},
            "provider": {"name": "recipe_local"},
        },
        {
            "requests": {
                "health": 1,
                "capabilities": 1,
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {
                "completed": 1,
                "last_task": {
                    "provider": "recipe_local",
                    "variant_count": 2,
                    "renderer": "local_parametric",
                    "composition": {
                        "selected_aspect_ratio": "original",
                        "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                    },
                    "qa": {
                        "master_difference_score": 0.18,
                        "social_difference_score": 0.31,
                    },
                },
            },
            "provider": {"name": "recipe_local"},
        },
    ]

    def launch_simulator(bundle_id, base_url, token):
        launched.append((bundle_id, base_url, token))

    def fetch_status(base_url, token="dev-mobile-token", timeout=5.0):
        return statuses.pop(0)

    def take_screenshot(path):
        screenshots.append(path)

    exit_code = qa_module.run_local_recipe_simulator_session(
        host="127.0.0.1",
        bridge_port=0,
        bundle_id="com.kaka.AgentPocket",
        token="dev-mobile-token",
        connection_timeout=1,
        photo_timeout=1,
        interval=0,
        receipt_file=str(receipt_path),
        screenshot_file=str(screenshot_path),
        simulator_launcher=launch_simulator,
        simulator_screenshotter=take_screenshot,
        status_fetcher=fetch_status,
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert launched == [
        (
            "com.kaka.AgentPocket",
            receipt["base_url"],
            "dev-mobile-token",
        )
    ]
    assert screenshots == [str(screenshot_path)]
    assert receipt["phase"] == "photo-flow"
    assert receipt["ok"] is True
    assert receipt["status"]["provider"]["name"] == "recipe_local"


def test_cli_simulator_local_recipe_smoke_dispatches(monkeypatch, tmp_path, capsys):
    receipt_path = tmp_path / "local-recipe.json"
    screenshot_path = tmp_path / "local-recipe.png"
    calls = []

    def run_local_recipe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_local_recipe_simulator_session", run_local_recipe)

    exit_code = main([
        "simulator-local-recipe-smoke",
        "--host",
        "127.0.0.1",
        "--port",
        "8769",
        "--receipt-file",
        str(receipt_path),
        "--screenshot-file",
        str(screenshot_path),
        "--no-launch",
    ])

    assert exit_code == 0
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["bridge_port"] == 8769
    assert calls[0]["launch_app"] is False
    assert calls[0]["receipt_file"] == str(receipt_path)
    assert calls[0]["screenshot_file"] == str(screenshot_path)


def test_run_simulator_capture_ready_session_launches_debug_ready_view_and_screenshots(tmp_path):
    screenshot_path = tmp_path / "capture-ready.png"
    receipt_path = tmp_path / "capture-ready.json"
    app_receipt = {
        "phase": "capture-ready",
        "ok": True,
        "state": "ready",
        "file_name": "library.jpg",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": True,
        "send_to_local_agent_enabled": True,
        "send_to_hermes_enabled": True,
        "selection_source": "library_fixture",
        "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage",
        "primary_action": "Send to Local Agent",
        "ready_status_accessibility_identifier": "selectedPhotoReadyStatus",
        "send_button_accessibility_identifier": "sendToLocalAgentButton",
    }
    launched = []
    screenshots = []
    slept = []
    cleaned = []

    exit_code = run_simulator_capture_ready_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        simulator_receipt_cleaner=lambda bundle_id: cleaned.append(bundle_id),
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert cleaned == ["com.kaka.AgentPocket"]
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [1.0, 0.25]
    assert screenshots == [str(screenshot_path)]
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_capture_ready_session_waits_for_ready_receipt_before_screenshot(tmp_path):
    screenshot_path = tmp_path / "capture-ready.png"
    receipt_path = tmp_path / "capture-ready.json"
    app_receipt = {
        "phase": "capture-ready",
        "ok": True,
        "state": "ready",
        "file_name": "library.jpg",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": True,
        "send_to_local_agent_enabled": True,
        "send_to_hermes_enabled": True,
        "selection_source": "library_fixture",
        "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage",
        "primary_action": "Send to Local Agent",
        "ready_status_accessibility_identifier": "selectedPhotoReadyStatus",
        "send_button_accessibility_identifier": "sendToLocalAgentButton",
    }
    read_results = [FileNotFoundError("receipt not written yet"), app_receipt]
    calls = []

    def read_receipt(bundle_id):
        calls.append("read")
        result = read_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    exit_code = run_simulator_capture_ready_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        settle_seconds=0,
        simulator_launcher=lambda bundle_id: calls.append("launch"),
        simulator_screenshotter=lambda path: calls.append("screenshot"),
        simulator_receipt_cleaner=lambda bundle_id: calls.append("clean"),
        simulator_receipt_reader=read_receipt,
        sleeper=lambda seconds: calls.append(("sleep", seconds)),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert calls[:3] == ["clean", "launch", "read"]
    assert calls.count("read") == 2
    assert calls.index("screenshot") > calls.index("read")
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_capture_completed_session_launches_debug_completed_view_and_screenshots(tmp_path):
    screenshot_path = tmp_path / "capture-completed.png"
    receipt_path = tmp_path / "capture-completed.json"
    app_receipt = {
        "phase": "capture-completed",
        "ok": True,
        "state": "completed",
        "task_id": "task_123",
        "variants_count": 2,
        "review_results_enabled": True,
        "review_results_primary": True,
        "send_to_local_agent_enabled": False,
        "send_to_hermes_enabled": False,
    }
    launched = []
    screenshots = []
    slept = []
    cleaned = []

    exit_code = qa_module.run_simulator_capture_completed_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        simulator_receipt_cleaner=lambda bundle_id: cleaned.append(bundle_id),
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert cleaned == ["com.kaka.AgentPocket"]
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [3.0]
    assert screenshots == [str(screenshot_path)]
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_result_gallery_session_launches_debug_result_view_and_screenshots(tmp_path):
    screenshot_path = tmp_path / "result-gallery.png"
    receipt_path = tmp_path / "result-gallery.json"
    app_receipt = {
        "phase": "result-gallery",
        "ok": True,
        "state": "ready",
        "task_status": "completed",
        "variants_count": 2,
        "selected_variant_id": "variant_1",
        "selected_asset_id": "asset_1",
        "has_explanation": True,
        "download_selected_enabled": True,
        "save_enabled": False,
        "share_enabled": False,
    }
    launched = []
    screenshots = []
    slept = []
    cleaned = []

    exit_code = run_simulator_result_gallery_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        simulator_receipt_cleaner=lambda bundle_id: cleaned.append(bundle_id),
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert cleaned == ["com.kaka.AgentPocket"]
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [2.0]
    assert screenshots == [str(screenshot_path)]
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_result_gallery_downloaded_session_launches_debug_downloaded_view_and_screenshots(tmp_path):
    screenshot_path = tmp_path / "result-gallery-downloaded.png"
    receipt_path = tmp_path / "result-gallery-downloaded.json"
    app_receipt = {
        "phase": "result-gallery-downloaded",
        "ok": True,
        "state": "downloaded",
        "task_status": "completed",
        "variants_count": 2,
        "selected_variant_id": "variant_1",
        "selected_asset_id": "asset_1",
        "downloaded_asset_bytes": 68,
        "downloaded_mime_type": "image/png",
        "recipe_summary": "Balanced exposure while preserving the original frame.",
        "share_caption": "Shot polished locally with Pocket Agent.",
        "download_selected_enabled": False,
        "save_enabled": True,
        "share_enabled": True,
    }
    launched = []
    screenshots = []
    slept = []
    cleaned = []

    exit_code = run_simulator_result_gallery_downloaded_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        simulator_receipt_cleaner=lambda bundle_id: cleaned.append(bundle_id),
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert cleaned == ["com.kaka.AgentPocket"]
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [2.0]
    assert screenshots == [str(screenshot_path)]
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_result_gallery_downloaded_session_requires_share_caption(tmp_path):
    receipt_path = tmp_path / "result-gallery-downloaded.json"
    app_receipt = {
        "phase": "result-gallery-downloaded",
        "ok": True,
        "state": "downloaded",
        "task_status": "completed",
        "variants_count": 2,
        "selected_variant_id": "variant_1",
        "selected_asset_id": "asset_1",
        "downloaded_asset_bytes": 68,
        "downloaded_mime_type": "image/png",
        "download_selected_enabled": False,
        "save_enabled": True,
        "share_enabled": True,
    }

    exit_code = run_simulator_result_gallery_downloaded_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file="",
        receipt_file=str(receipt_path),
        launch_app=False,
        settle_seconds=0,
        simulator_receipt_cleaner=lambda bundle_id: None,
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 1


def test_run_simulator_share_sheet_session_launches_debug_share_sheet_and_writes_receipt(tmp_path):
    screenshot_path = tmp_path / "share-sheet.png"
    receipt_path = tmp_path / "share-sheet.json"
    app_receipt = {
        "phase": "share-sheet-handoff",
        "ok": True,
        "state": "presented",
        "selected_variant_id": "variant_clean_pro",
        "selected_asset_id": "asset_1",
        "downloaded_asset_bytes": 68,
        "downloaded_mime_type": "image/png",
        "share_items_count": 2,
        "share_caption": "Shot polished locally with Pocket Agent.",
        "handoff_attempted": True,
        "share_sheet_presented": True,
        "presenter": "UIActivityViewController",
    }
    launched = []
    screenshots = []
    slept = []
    cleaned = []

    exit_code = run_simulator_share_sheet_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        receipt_file=str(receipt_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        simulator_receipt_cleaner=lambda bundle_id: cleaned.append(bundle_id),
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert cleaned == ["com.kaka.AgentPocket"]
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [2.0]
    assert screenshots == [str(screenshot_path)]
    assert json.loads(receipt_path.read_text()) == app_receipt


def test_run_simulator_share_sheet_session_requires_presented_share_sheet(tmp_path):
    receipt_path = tmp_path / "share-sheet.json"
    app_receipt = {
        "phase": "share-sheet-handoff",
        "ok": True,
        "state": "prepared",
        "selected_variant_id": "variant_clean_pro",
        "selected_asset_id": "asset_1",
        "downloaded_asset_bytes": 68,
        "downloaded_mime_type": "image/png",
        "share_items_count": 2,
        "share_caption": "Shot polished locally with Pocket Agent.",
        "handoff_attempted": True,
        "share_sheet_presented": False,
    }

    exit_code = run_simulator_share_sheet_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file="",
        receipt_file=str(receipt_path),
        launch_app=False,
        settle_seconds=0,
        simulator_receipt_cleaner=lambda bundle_id: None,
        simulator_receipt_reader=lambda bundle_id: app_receipt,
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 1


def test_run_simulator_picker_ui_session_launches_debug_picker_view_and_screenshots(tmp_path):
    screenshot_path = tmp_path / "picker-ui.png"
    launched = []
    screenshots = []
    slept = []

    exit_code = run_simulator_picker_ui_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        simulator_launcher=lambda bundle_id: launched.append(bundle_id),
        simulator_screenshotter=lambda path: screenshots.append(path),
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert launched == ["com.kaka.AgentPocket"]
    assert slept == [1.0]
    assert screenshots == [str(screenshot_path)]


def test_run_simulator_picker_ui_session_retries_blank_screenshot_until_visible(tmp_path):
    screenshot_path = tmp_path / "picker-ui.png"
    attempts = []
    slept = []

    def screenshotter(path):
        attempts.append(path)
        if len(attempts) < 3:
            raise RuntimeError(f"Simulator screenshot has a blank content area: {path}")

    exit_code = run_simulator_picker_ui_session(
        bundle_id="com.kaka.AgentPocket",
        screenshot_file=str(screenshot_path),
        settle_seconds=0,
        screenshot_attempts=3,
        screenshot_retry_interval=0.2,
        simulator_launcher=lambda bundle_id: None,
        simulator_screenshotter=screenshotter,
        sleeper=lambda seconds: slept.append(seconds),
        out=StringIO(),
        err=StringIO(),
    )

    assert exit_code == 0
    assert attempts == [str(screenshot_path), str(screenshot_path), str(screenshot_path)]
    assert slept == [0.2, 0.2]


def test_run_simulator_seed_photo_library_writes_fixture_and_adds_media(tmp_path):
    image_path = tmp_path / "library-fixture.png"
    calls = []

    def run(command):
        calls.append(command)
        return CommandResult(returncode=0, stdout="", stderr="")

    report = run_simulator_seed_photo_library(
        device="booted",
        image_file=str(image_path),
        command_runner=run,
    )

    assert report["ok"] is True
    assert report["image_file"] == str(image_path)
    assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert calls == [["xcrun", "simctl", "addmedia", "booted", str(image_path)]]


def test_run_simulator_seed_photo_library_reports_addmedia_failure(tmp_path):
    image_path = tmp_path / "library-fixture.png"

    report = run_simulator_seed_photo_library(
        device="booted",
        image_file=str(image_path),
        command_runner=lambda command: CommandResult(returncode=1, stdout="", stderr="no booted simulator"),
    )

    assert report["ok"] is False
    assert report["error"] == "no booted simulator"
    assert image_path.exists()


def test_run_simulator_suite_refreshes_local_evidence_without_requiring_ui_test_runtime(tmp_path):
    suite_receipt = tmp_path / "suite.json"
    ui_preflight_receipt = tmp_path / "ui-preflight.json"
    connection_receipt = tmp_path / "connection.json"
    discovery_refresh_receipt = tmp_path / "discovery-refresh.json"
    discovery_refresh_screenshot = tmp_path / "discovery-refresh.png"
    picker_screenshot = tmp_path / "picker.png"
    capture_screenshot = tmp_path / "capture.png"
    capture_receipt = tmp_path / "capture.json"
    capture_completed_screenshot = tmp_path / "capture-completed.png"
    capture_completed_receipt = tmp_path / "capture-completed.json"
    result_gallery_screenshot = tmp_path / "result-gallery.png"
    result_gallery_receipt = tmp_path / "result-gallery.json"
    result_gallery_downloaded_screenshot = tmp_path / "result-gallery-downloaded.png"
    result_gallery_downloaded_receipt = tmp_path / "result-gallery-downloaded.json"
    library_fixture = tmp_path / "library.png"
    openai_receipt = tmp_path / "openai.json"
    fake_openai_status = tmp_path / "fake-openai.json"
    openai_screenshot = tmp_path / "openai.png"
    calls = []

    def build_ui_preflight():
        calls.append("ui_preflight")
        return {
            "ok": False,
            "mismatch": {
                "ok": False,
                "reason": "Installed iOS Simulator runtime does not match the active iOS Simulator SDK.",
                "sdk_latest": "26.5",
                "runtime_latest": "26.1",
            },
            "destinations": {
                "ok": False,
                "ineligible": ["{ platform:iOS, name:Any iOS Device, error:iOS 26.5 is not installed. }"],
            },
            "sdk": {"latest": "26.5"},
            "runtime": {"latest": "26.1"},
        }

    def seed_photo_library(device, image_file):
        calls.append(("seed", device, image_file))
        return {"ok": True, "image_file": image_file, "device": device}

    def run_connection(**kwargs):
        calls.append(("connection", kwargs["receipt_file"], kwargs["port"]))
        return 0

    def run_discovery_refresh(**kwargs):
        calls.append(("discovery_refresh", kwargs["receipt_file"], kwargs["screenshot_file"], kwargs["port"]))
        return 0

    def run_picker(**kwargs):
        calls.append(("picker", kwargs["screenshot_file"]))
        return 0

    def run_capture(**kwargs):
        calls.append(("capture", kwargs["screenshot_file"], kwargs["receipt_file"]))
        return 0

    def run_capture_completed(**kwargs):
        calls.append(("capture_completed", kwargs["screenshot_file"], kwargs["receipt_file"]))
        return 0

    def run_result_gallery(**kwargs):
        calls.append(("result_gallery", kwargs["screenshot_file"], kwargs["receipt_file"]))
        return 0

    def run_result_gallery_downloaded(**kwargs):
        calls.append(("result_gallery_downloaded", kwargs["screenshot_file"], kwargs["receipt_file"]))
        return 0

    def run_openai(**kwargs):
        calls.append(("openai", kwargs["receipt_file"], kwargs["fake_openai_status_file"], kwargs["screenshot_file"]))
        return 0

    report = run_simulator_suite(
        host="127.0.0.1",
        bundle_id="com.kaka.AgentPocket",
        connection_port=8766,
        discovery_refresh_port=8767,
        openai_bridge_port=8769,
        fake_openai_port=8781,
        simulator_ui_test_preflight_receipt=str(ui_preflight_receipt),
        simulator_connection_receipt=str(connection_receipt),
        discovery_refresh_receipt=str(discovery_refresh_receipt),
        discovery_refresh_screenshot=str(discovery_refresh_screenshot),
        library_fixture=str(library_fixture),
        picker_ui_screenshot=str(picker_screenshot),
        capture_ready_screenshot=str(capture_screenshot),
        capture_ready_receipt=str(capture_receipt),
        capture_completed_screenshot=str(capture_completed_screenshot),
        capture_completed_receipt=str(capture_completed_receipt),
        result_gallery_screenshot=str(result_gallery_screenshot),
        result_gallery_receipt=str(result_gallery_receipt),
        result_gallery_downloaded_screenshot=str(result_gallery_downloaded_screenshot),
        result_gallery_downloaded_receipt=str(result_gallery_downloaded_receipt),
        openai_receipt=str(openai_receipt),
        fake_openai_status_file=str(fake_openai_status),
        openai_screenshot=str(openai_screenshot),
        suite_receipt_file=str(suite_receipt),
        ui_test_preflight_builder=build_ui_preflight,
        seed_photo_library_runner=seed_photo_library,
        connection_session_runner=run_connection,
        discovery_refresh_session_runner=run_discovery_refresh,
        picker_ui_session_runner=run_picker,
        capture_ready_session_runner=run_capture,
        capture_completed_session_runner=run_capture_completed,
        result_gallery_session_runner=run_result_gallery,
        result_gallery_downloaded_session_runner=run_result_gallery_downloaded,
        openai_session_runner=run_openai,
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(suite_receipt.read_text())
    ui_receipt = json.loads(ui_preflight_receipt.read_text())
    assert report["ok"] is True
    assert receipt == report
    assert ui_receipt["mismatch"]["sdk_latest"] == "26.5"
    assert report["steps"]["ui_test_preflight"]["required"] is False
    assert report["steps"]["ui_test_preflight"]["runnable"] is False
    assert report["steps"]["ui_test_preflight"]["status"] == "blocked_by_local_xcode_runtime"
    assert report["steps"]["connection_smoke"]["ok"] is True
    assert report["steps"]["discovery_refresh_smoke"]["ok"] is True
    assert report["steps"]["discovery_refresh_smoke"]["receipt"] == str(discovery_refresh_receipt)
    assert report["steps"]["discovery_refresh_smoke"]["screenshot"] == str(discovery_refresh_screenshot)
    assert report["steps"]["picker_ui_smoke"]["ok"] is True
    assert report["steps"]["capture_ready_smoke"]["ok"] is True
    assert report["steps"]["capture_ready_smoke"]["receipt"] == str(capture_receipt)
    assert report["steps"]["capture_ready_smoke"]["screenshot"] == str(capture_screenshot)
    assert report["steps"]["capture_completed_smoke"]["ok"] is True
    assert report["steps"]["capture_completed_smoke"]["receipt"] == str(capture_completed_receipt)
    assert report["steps"]["capture_completed_smoke"]["screenshot"] == str(capture_completed_screenshot)
    assert report["steps"]["result_gallery_smoke"]["ok"] is True
    assert report["steps"]["result_gallery_smoke"]["receipt"] == str(result_gallery_receipt)
    assert report["steps"]["result_gallery_smoke"]["screenshot"] == str(result_gallery_screenshot)
    assert report["steps"]["result_gallery_downloaded_smoke"]["ok"] is True
    assert report["steps"]["result_gallery_downloaded_smoke"]["receipt"] == str(result_gallery_downloaded_receipt)
    assert report["steps"]["result_gallery_downloaded_smoke"]["screenshot"] == str(result_gallery_downloaded_screenshot)
    assert report["steps"]["openai_smoke"]["ok"] is True
    assert calls == [
        "ui_preflight",
        ("seed", "booted", str(library_fixture)),
        ("connection", str(connection_receipt), 8766),
        ("discovery_refresh", str(discovery_refresh_receipt), str(discovery_refresh_screenshot), 8767),
        ("picker", str(picker_screenshot)),
        ("capture", str(capture_screenshot), str(capture_receipt)),
        ("capture_completed", str(capture_completed_screenshot), str(capture_completed_receipt)),
        ("result_gallery", str(result_gallery_screenshot), str(result_gallery_receipt)),
        ("result_gallery_downloaded", str(result_gallery_downloaded_screenshot), str(result_gallery_downloaded_receipt)),
        ("openai", str(openai_receipt), str(fake_openai_status), str(openai_screenshot)),
    ]


def test_run_simulator_suite_fails_when_required_smoke_step_fails(tmp_path):
    report = run_simulator_suite(
        suite_receipt_file=str(tmp_path / "suite.json"),
        simulator_ui_test_preflight_receipt=str(tmp_path / "ui-preflight.json"),
        ui_test_preflight_builder=lambda: {"ok": True, "mismatch": {"ok": True}, "destinations": {"ok": True}},
        seed_photo_library_runner=lambda device, image_file: {"ok": True},
        connection_session_runner=lambda **kwargs: 0,
        discovery_refresh_session_runner=lambda **kwargs: 0,
        picker_ui_session_runner=lambda **kwargs: 1,
        capture_ready_session_runner=lambda **kwargs: 0,
        capture_completed_session_runner=lambda **kwargs: 0,
        result_gallery_session_runner=lambda **kwargs: 0,
        result_gallery_downloaded_session_runner=lambda **kwargs: 0,
        openai_session_runner=lambda **kwargs: 0,
        out=StringIO(),
        err=StringIO(),
    )

    assert report["ok"] is False
    assert report["steps"]["picker_ui_smoke"]["ok"] is False
    assert report["failed_required_steps"] == ["picker_ui_smoke"]


def test_cli_simulator_seed_photo_library_prints_json(monkeypatch, tmp_path, capsys):
    image_path = tmp_path / "library-fixture.png"
    calls = []

    def run(command):
        calls.append(command)
        return CommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main(["simulator-seed-photo-library", "--image-file", str(image_path)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["image_file"] == str(image_path)
    assert calls == [["xcrun", "simctl", "addmedia", "booted", str(image_path)]]


def test_cli_commands_prints_shell_sequence(capsys):
    exit_code = main(
        [
            "commands",
            "--host",
            "192.0.2.10",
            "--device-id",
            "00000000-0000-0000-0000-000000000000",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "# 1. Start the LAN mock Hermes bridge" in output
    assert "http://192.0.2.10:8765" in output
    assert "wait-photo-flow" in output


def test_cli_preflight_prints_json(monkeypatch, capsys):
    def run(command):
        if command == ["ipconfig", "getifaddr", "en0"]:
            return CommandResult(returncode=0, stdout="192.0.2.10\n", stderr="")
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        if command == ["xcrun", "devicectl", "list", "devices"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["xcrun", "--find", "devicectl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/devicectl\n", stderr="")
        if command == ["which", "dns-sd"]:
            return CommandResult(returncode=0, stdout="/usr/bin/dns-sd\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(returncode=0, stdout="== Devices ==\n", stderr="")
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main(["preflight"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["lan"]["ip"] == "192.0.2.10"
    assert output["tailscale"]["ok"] is False
    assert output["simulator"]["simctl"]["ok"] is True
    assert output["commands"]["lan"].startswith("PYTHONPATH=mock_bridge")
    assert "--gate-f-host 192.0.2.10" in output["simulator"]["commands"]["simulator_only_resume"]


def test_build_provider_preflight_report_is_available_from_qa_module(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_preflight_report("openai", photo_pack_root="photo-pack")

    assert report["ok"] is False
    assert report["provider"] == "openai"
    assert report["env"]["OPENAI_API_KEY"] == "missing"
    assert report["config"]["OPENAI_BASE_URL"] == {
        "state": "default",
        "value": "https://api.openai.com/v1",
        "redacted": False,
    }


def test_build_provider_preflight_report_redacts_custom_openai_base_url():
    report = build_provider_preflight_report(
        "openai",
        photo_pack_root="photo-pack",
        env={
            "OPENAI_API_KEY": "secret-value-that-must-not-leak",
            "OPENAI_BASE_URL": "http://proxy-user:proxy-pass@127.0.0.1:8781/v1?token=abc#frag",
        },
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["env"]["OPENAI_API_KEY"] == "set"
    assert report["config"]["OPENAI_BASE_URL"] == {
        "state": "custom",
        "value": "http://127.0.0.1:8781/v1",
        "redacted": True,
    }
    assert "secret-value-that-must-not-leak" not in serialized
    assert "proxy-pass" not in serialized
    assert "token=abc" not in serialized


def test_cli_provider_preflight_prints_json(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(["provider-preflight", "--photo-provider", "openai"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["provider"] == "openai"
    assert output["env"]["OPENAI_API_KEY"] == "missing"


def test_cli_provider_preflight_reads_env_file_without_leaking_secret(monkeypatch, tmp_path, capsys):
    env_file = tmp_path / "hermes.env"
    env_file.write_text('OPENAI_API_KEY="secret-from-hermes-env"\n', encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--env-file",
        str(env_file),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert "secret-from-hermes-env" not in output_text


def test_cli_provider_preflight_reads_hermes_force_env_without_leaking_secret(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("_HERMES_FORCE_OPENAI_API_KEY", "secret-from-hermes-force")

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert os.environ.get("OPENAI_API_KEY") is None
    assert "secret-from-hermes-force" not in output_text


def test_cli_provider_preflight_writes_receipt_without_leaking_secret(monkeypatch, tmp_path, capsys):
    env_file = tmp_path / "hermes.env"
    env_file.write_text("OPENAI_API_KEY=secret-from-hermes-env\n", encoding="utf-8")
    receipt_file = tmp_path / "provider-preflight.json"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--env-file",
        str(env_file),
        "--receipt-file",
        str(receipt_file),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    serialized = output_text + receipt_file.read_text(encoding="utf-8")
    assert exit_code == 0
    assert receipt == output
    assert receipt["ok"] is True
    assert receipt["env"]["OPENAI_API_KEY"] == "set"
    assert "secret-from-hermes-env" not in serialized


def test_cli_provider_preflight_reads_hermes_profile_env_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="OPENAI_API_KEY=secret-from-hermes-profile\n",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["profile"] == "dev-lead"
    assert output["hermes"]["env_file"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["auth"]["openai_codex"]["compatible_with_photo_provider"] is False
    assert "--hermes-profile dev-lead" in output["commands"]["server"]
    assert "--hermes-profile dev-lead" in output["commands"]["qa"]
    assert "--env-file" not in output["commands"]["server"]
    assert "secret-from-hermes-profile" not in output_text
    assert "codex-token-that-must-not-leak" not in output_text


def test_cli_provider_preflight_reads_hermes_openai_auth_api_key_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="",
        auth={
            "version": 1,
            "credential_pool": {
                "openai": [
                    {
                        "label": "images-key",
                        "auth_type": "api_key",
                        "access_token": "secret-from-hermes-auth",
                        "base_url": "http://proxy-user:proxy-pass@127.0.0.1:7788/v1?token=abc",
                    }
                ],
                "openai-codex": [
                    {
                        "label": "codex-oauth",
                        "auth_type": "oauth",
                        "access_token": "codex-token-that-must-not-leak",
                    }
                ],
            },
        },
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["env_file"]["OPENAI_API_KEY"] == "missing"
    assert output["hermes"]["auth"]["openai"]["credential_pool"] == "set"
    assert output["hermes"]["auth_env"] == {
        "source": "hermes_auth_openai_api_key",
        "used": True,
        "OPENAI_API_KEY": "set",
        "OPENAI_BASE_URL": "set",
    }
    assert output["hermes"]["effective_env"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["effective_env"]["OPENAI_BASE_URL"] == "set"
    assert output["config"]["OPENAI_BASE_URL"] == {
        "state": "custom",
        "value": "http://127.0.0.1:7788/v1",
        "redacted": True,
    }
    assert "secret-from-hermes-auth" not in output_text
    assert "codex-token-that-must-not-leak" not in output_text
    assert "proxy-pass" not in output_text
    assert "token=abc" not in output_text


def test_cli_provider_preflight_reads_hermes_shared_auth_api_key_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    _write_hermes_shared_auth(
        hermes_home,
        {
            "version": 1,
            "credential_pool": {
                "openai": [
                    {
                        "label": "shared-images-key",
                        "auth_type": "api_key",
                        "access_token": "secret-from-shared-hermes-auth",
                        "base_url": "http://proxy-user:proxy-pass@127.0.0.1:7788/v1?token=abc",
                    }
                ],
                "openai-codex": [
                    {
                        "label": "codex-oauth",
                        "auth_type": "oauth",
                        "access_token": "codex-token-that-must-not-leak",
                    }
                ],
            },
        },
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["auth"]["openai"]["credential_pool"] == "missing"
    assert output["hermes"]["shared_auth"]["openai"]["credential_pool"] == "set"
    assert output["hermes"]["auth_env"]["used"] is False
    assert output["hermes"]["shared_auth_env"] == {
        "source": "hermes_shared_auth_openai_api_key",
        "used": True,
        "OPENAI_API_KEY": "set",
        "OPENAI_BASE_URL": "set",
    }
    assert output["config"]["OPENAI_BASE_URL"] == {
        "state": "custom",
        "value": "http://127.0.0.1:7788/v1",
        "redacted": True,
    }
    assert "secret-from-shared-hermes-auth" not in output_text
    assert "codex-token-that-must-not-leak" not in output_text
    assert "proxy-pass" not in output_text
    assert "token=abc" not in output_text


def test_cli_hermes_openai_auth_import_writes_profile_auth_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    profile_root = _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    receipt_file = tmp_path / "import-receipt.json"
    monkeypatch.setenv("OPENAI_API_KEY", "secret-from-import-env")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://proxy-user:proxy-pass@127.0.0.1:7788/v1?token=abc")

    exit_code = main([
        "hermes-openai-auth-import",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
        "--label",
        "agent-pocket-images",
        "--receipt-file",
        str(receipt_file),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    auth = json.loads((profile_root / "auth.json").read_text(encoding="utf-8"))
    serialized_receipts = output_text + receipt_file.read_text(encoding="utf-8")
    assert exit_code == 0
    assert output == receipt
    assert output["ok"] is True
    assert output["scope"] == "profile"
    assert output["auth_file"]["path"] == str(profile_root / "auth.json")
    assert output["auth_file"]["written"] is True
    assert output["env"] == {
        "OPENAI_API_KEY": "set",
        "OPENAI_BASE_URL": "set",
    }
    assert output["credential"]["base_url"] == {
        "state": "custom",
        "value": "http://127.0.0.1:7788/v1",
        "redacted": True,
    }
    openai_entry = auth["credential_pool"]["openai"][0]
    assert openai_entry["label"] == "agent-pocket-images"
    assert openai_entry["auth_type"] == "api_key"
    assert openai_entry["access_token"] == "secret-from-import-env"
    assert openai_entry["base_url"] == "http://proxy-user:proxy-pass@127.0.0.1:7788/v1?token=abc"
    assert auth["credential_pool"]["openai-codex"][0]["access_token"] == "codex-token-that-must-not-leak"
    assert "secret-from-import-env" not in serialized_receipts
    assert "proxy-pass" not in serialized_receipts
    assert "token=abc" not in serialized_receipts
    assert "codex-token-that-must-not-leak" not in serialized_receipts


def test_cli_hermes_openai_auth_import_writes_shared_auth_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    shared_auth_file = _write_hermes_shared_auth(
        hermes_home,
        {
            "version": 1,
            "credential_pool": {
                "openai-codex": [
                    {
                        "label": "codex-oauth",
                        "auth_type": "oauth",
                        "access_token": "codex-token-that-must-not-leak",
                    }
                ],
            },
        },
    )
    monkeypatch.setenv("OPENAI_API_KEY", "secret-from-shared-import")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = main([
        "hermes-openai-auth-import",
        "--scope",
        "shared",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    auth = json.loads(shared_auth_file.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert output["ok"] is True
    assert output["scope"] == "shared"
    assert output["auth_file"]["path"] == str(shared_auth_file)
    assert output["credential"]["base_url"] == {
        "state": "default",
        "value": "https://api.openai.com/v1",
        "redacted": False,
    }
    assert auth["credential_pool"]["openai"][0]["access_token"] == "secret-from-shared-import"
    assert "secret-from-shared-import" not in output_text
    assert "codex-token-that-must-not-leak" not in output_text


def test_cli_hermes_openai_auth_import_missing_key_does_not_write_auth(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    profile_root = _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    before = (profile_root / "auth.json").read_text(encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = main([
        "hermes-openai-auth-import",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output = json.loads(capsys.readouterr().err)
    after = (profile_root / "auth.json").read_text(encoding="utf-8")
    assert exit_code == 1
    assert output["ok"] is False
    assert output["missing"] == ["OPENAI_API_KEY"]
    assert output["auth_file"]["written"] is False
    assert before == after


def test_cli_provider_preflight_reads_hermes_profile_base_url_without_leaking_credentials(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text=(
            "OPENAI_API_KEY=secret-from-hermes-profile\n"
            "OPENAI_BASE_URL=http://proxy-user:proxy-pass@127.0.0.1:7788/v1?token=abc\n"
        ),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["config"]["OPENAI_BASE_URL"] == {
        "state": "custom",
        "value": "http://127.0.0.1:7788/v1",
        "redacted": True,
    }
    assert output["hermes"]["env_file"]["OPENAI_BASE_URL"] == "set"
    assert output["hermes"]["effective_env"]["OPENAI_BASE_URL"] == "set"
    assert "secret-from-hermes-profile" not in output_text
    assert "proxy-pass" not in output_text
    assert "token=abc" not in output_text


def test_cli_provider_preflight_marks_codex_oauth_as_not_images_key(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is False
    assert output["env"]["OPENAI_API_KEY"] == "missing"
    assert output["hermes"]["auth"]["openai_codex"]["credential_pool"] == "set"
    assert output["hermes"]["auth"]["openai_codex"]["compatible_with_photo_provider"] is False
    assert "OpenAI Codex OAuth is not an Images API key" in output["hermes"]["missing"]


def test_cli_provider_preflight_reads_hermes_home_env_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("OPENAI_API_KEY=secret-from-hermes-home\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-preflight",
        "--photo-provider",
        "openai",
        "--photo-pack-root",
        "photo-pack",
        "--hermes-home",
        str(hermes_home),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["env"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["home_env_file"]["OPENAI_API_KEY"] == "set"
    assert output["hermes"]["effective_env"]["OPENAI_API_KEY"] == "set"
    assert "--hermes-home" in output["commands"]["server"]
    assert "secret-from-hermes-home" not in output_text


def test_build_provider_env_sources_report_checks_hermes_profiles_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "cfo", env_text="")
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="OPENAI_API_KEY=secret-from-hermes-profile\n",
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["env"]["OPENAI_API_KEY"] == "set"
    assert report["hermes"]["selected_profile"] == "dev-lead"
    assert report["hermes"]["selected_profile_state"] == "set"
    assert any(source["source"] == "hermes_profile" and source["profile"] == "dev-lead" for source in report["set_sources"])
    assert report["next_actions"] == [
        "Run provider_preflight with the same server-side key source, then rerun gate_f_preflight."
    ]
    assert "provider-env-sources --hermes-home" in report["commands"]["provider_env_sources"]
    assert "--hermes-profile dev-lead" in report["commands"]["provider_preflight"]
    assert "secret-from-hermes-profile" not in serialized


def test_build_provider_env_sources_report_checks_hermes_home_env_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("OPENAI_API_KEY=secret-from-hermes-home\n", encoding="utf-8")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["hermes"]["home_env_file"]["OPENAI_API_KEY"] == "set"
    assert any(source["source"] == "hermes_home_env" for source in report["set_sources"])
    assert "--hermes-home" in report["commands"]["provider_preflight"]
    assert "secret-from-hermes-home" not in serialized


def test_build_provider_env_sources_report_checks_hermes_force_current_process_without_leaking_secret(monkeypatch):
    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_provider_env_sources_report(
        env={"_HERMES_FORCE_OPENAI_API_KEY": "secret-from-hermes-force"},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["env"]["OPENAI_API_KEY"] == "set"
    assert report["current_process"]["OPENAI_API_KEY"] == "set"
    assert any(source["source"] == "hermes_force_current_process" for source in report["set_sources"])
    assert "secret-from-hermes-force" not in serialized


def test_build_provider_env_sources_report_checks_running_hermes_gateway_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    ps_output = (
        "1234 /Users/example/.hermes/hermes-agent/venv/bin/python "
        "-m hermes_cli.main --profile dev-lead gateway run --replace "
        "OPENAI_API_KEY=secret-from-process\n"
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout=ps_output, stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["hermes"]["gateway_process_probe"]["ok"] is True
    assert report["hermes"]["gateway_processes"] == [{
        "source": "hermes_gateway_process",
        "pid": "1234",
        "profile": "dev-lead",
        "selected": True,
        "OPENAI_API_KEY": "set",
        "force_env": "missing",
    }]
    assert any(
        source["source"] == "hermes_gateway_process"
        and source["profile"] == "dev-lead"
        and source["pid"] == "1234"
        for source in report["set_sources"]
    )
    assert "secret-from-process" not in serialized


def test_build_provider_env_sources_report_checks_forced_running_hermes_gateway_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    ps_output = (
        "1234 /Users/example/.hermes/hermes-agent/venv/bin/python "
        "-m hermes_cli.main --profile dev-lead gateway run --replace "
        "_HERMES_FORCE_OPENAI_API_KEY=secret-from-forced-process\n"
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout=ps_output, stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["hermes"]["gateway_processes"] == [{
        "source": "hermes_gateway_process",
        "pid": "1234",
        "profile": "dev-lead",
        "selected": True,
        "OPENAI_API_KEY": "set",
        "force_env": "set",
    }]
    assert any(
        source["source"] == "hermes_gateway_process"
        and source["profile"] == "dev-lead"
        and source["pid"] == "1234"
        for source in report["set_sources"]
    )
    assert "secret-from-forced-process" not in serialized


def test_build_provider_env_sources_report_checks_selected_hermes_auth_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="",
        auth={
            "version": 1,
            "credential_pool": {
                "openai": [
                    {
                        "label": "images-key",
                        "auth_type": "api_key",
                        "access_token": "secret-from-hermes-auth",
                        "base_url": "http://127.0.0.1:7788/v1",
                    }
                ]
            },
        },
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["hermes"]["profile_auths"][0]["OPENAI_API_KEY"] == "set"
    assert report["hermes"]["profile_auths"][0]["OPENAI_BASE_URL"] == "set"
    assert any(
        source["source"] == "hermes_profile_auth"
        and source["profile"] == "dev-lead"
        for source in report["set_sources"]
    )
    assert "secret-from-hermes-auth" not in serialized


def test_build_provider_env_sources_report_checks_hermes_shared_auth_without_leaking_secret(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    _write_hermes_shared_auth(
        hermes_home,
        {
            "version": 1,
            "credential_pool": {
                "openai": [
                    {
                        "label": "shared-images-key",
                        "auth_type": "api_key",
                        "access_token": "secret-from-shared-auth",
                        "base_url": "http://127.0.0.1:7788/v1",
                    }
                ]
            },
        },
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["hermes"]["shared_auth_file"]["OPENAI_API_KEY"] == "set"
    assert report["hermes"]["shared_auth_file"]["OPENAI_BASE_URL"] == "set"
    assert any(source["source"] == "hermes_shared_auth" for source in report["set_sources"])
    assert "secret-from-shared-auth" not in serialized


def test_build_provider_env_sources_report_does_not_count_nonselected_hermes_auth(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "cfo",
        env_text="",
        auth={
            "version": 1,
            "credential_pool": {
                "openai": [
                    {
                        "label": "images-key",
                        "auth_type": "api_key",
                        "access_token": "secret-from-cfo-auth",
                    }
                ]
            },
        },
    )
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is False
    assert report["set_sources"] == []
    assert any(
        auth_source["profile"] == "cfo"
        and auth_source["OPENAI_API_KEY"] == "set"
        for auth_source in report["hermes"]["profile_auths"]
    )
    assert "secret-from-cfo-auth" not in serialized


def test_build_provider_env_sources_report_records_hermes_process_diagnostics_without_counting_unrelated_process_key(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    profile_root = _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    (profile_root / "config.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: gpt-5.5\n",
        encoding="utf-8",
    )
    ps_output = (
        "2222 /Users/example/.hermes/hermes-agent/venv/bin/python "
        "-m hermes_cli.main --profile dev-lead chat OPENAI_API_KEY=secret-from-chat-process "
        "OPENAI_BASE_URL=http://proxy-user:proxy-pass@127.0.0.1:7788/v1\n"
    )

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout=ps_output, stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is False
    assert report["env"]["OPENAI_API_KEY"] == "missing"
    assert report["hermes"]["gateway_processes"] == []
    assert report["hermes"]["processes"] == [{
        "source": "hermes_process",
        "pid": "2222",
        "kind": "hermes_cli",
        "profile": "dev-lead",
        "selected": True,
        "gateway_run": False,
        "OPENAI_API_KEY": "set",
        "OPENAI_BASE_URL": "set",
        "force_env": "missing",
    }]
    selected_refs = [
        reference
        for reference in report["hermes"]["provider_references"]
        if reference.get("selected") and reference.get("path", "").endswith("config.yaml")
    ]
    assert selected_refs
    assert selected_refs[0]["openai_reference"] == "present"
    assert selected_refs[0]["OPENAI_API_KEY"] == "absent"
    assert "secret-from-chat-process" not in serialized
    assert "proxy-pass" not in serialized


def test_build_provider_env_sources_report_explains_missing_selected_hermes_profile_key(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    profile_root = _write_hermes_profile(hermes_home, "dev-lead", env_text="")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    assert report["ok"] is False
    assert report["missing"] == ["OPENAI_API_KEY"]
    assert report["hermes"]["selected_profile_state"] == "missing"
    assert "hermes --profile dev-lead auth add openai --type api-key" in report["next_actions"][0]
    assert str(profile_root / ".env") in report["next_actions"][1]
    assert "iPhone app never stores or calls this key" in report["next_actions"][2]
    assert report["commands"]["launchd_setenv_template"] == "launchctl setenv OPENAI_API_KEY <redacted-openai-api-key>"
    assert report["commands"]["hermes_auth_add_openai"] == (
        f"HERMES_HOME={hermes_home} hermes --profile dev-lead auth add openai "
        "--type api-key --label agent-pocket-openai-images"
    )
    assert report["commands"]["hermes_openai_auth_import"] == (
        "OPENAI_API_KEY=<server-side-openai-api-key> "
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa hermes-openai-auth-import "
        f"--hermes-home {hermes_home} --hermes-profile dev-lead "
        "--receipt-file docs/qa-receipts/hermes-openai-auth-import-latest.json"
    )


def test_build_provider_env_sources_report_records_shell_startup_key_without_counting_it(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")
    (tmp_path / ".zshrc").write_text("export OPENAI_API_KEY=secret-from-shell-startup\n", encoding="utf-8")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is False
    assert report["env"]["OPENAI_API_KEY"] == "missing"
    assert report["set_sources"] == []
    assert report["shell_startup_files"]["state"] == "declared_not_active"
    assert report["shell_startup_files"]["counts_for_provider_readiness"] is False
    assert report["shell_startup_files"]["set_files"] == [{
        "source": "shell_startup_file",
        "path": str(tmp_path / ".zshrc"),
    }]
    assert "secret-from-shell-startup" not in serialized


def test_build_provider_env_sources_report_records_hermes_cli_auth_status_without_leaking_labels(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["hermes", "--profile", "dev-lead", "auth", "list"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "openai-codex (1 credentials):\n"
                    "  #1  secret-from-cli-label  oauth   device_code <-\n"
                ),
                stderr="",
            )
        if command == ["hermes", "--profile", "dev-lead", "auth", "status", "openai"]:
            return CommandResult(returncode=0, stdout="openai: logged out\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
        include_hermes_cli_auth=True,
    )

    cli_auth = report["hermes"]["cli_auth"]
    serialized = json.dumps(report)
    assert cli_auth["auth_list"]["providers"]["openai-codex"]["auth_types"] == ["oauth"]
    assert cli_auth["openai_status"]["state"] == "logged_out"
    assert cli_auth["openai_images_api_key_auth"] == "missing"
    assert "secret-from-cli-label" not in serialized


def test_build_provider_env_sources_report_counts_hermes_cli_openai_status_as_key_source(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(hermes_home, "dev-lead", env_text="")

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["hermes", "--profile", "dev-lead", "auth", "list"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "openai (1 credentials):\n"
                    "  #1  secret-from-cli-label  api_key manual <-\n"
                ),
                stderr="",
            )
        if command == ["hermes", "--profile", "dev-lead", "auth", "status", "openai"]:
            return CommandResult(returncode=0, stdout="openai: logged in\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = build_provider_env_sources_report(
        hermes_home=str(hermes_home),
        hermes_profile="dev-lead",
        env={},
        command_runner=run,
        include_hermes_cli_auth=True,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["env"]["OPENAI_API_KEY"] == "set"
    assert report["set_sources"] == [{
        "source": "hermes_cli_auth",
        "profile": "dev-lead",
        "path": "",
        "pid": "",
    }]
    assert report["hermes"]["cli_auth"]["openai_status"]["state"] == "logged_in"
    assert report["hermes"]["cli_auth"]["openai_images_api_key_auth"] == "set"
    assert "secret-from-cli-label" not in serialized


def test_cli_provider_env_sources_writes_receipt_without_leaking_launchd_secret(monkeypatch, tmp_path, capsys):
    receipt_file = tmp_path / "provider-env-sources.json"

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="secret-from-launchd\n", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "provider-env-sources",
        "--receipt-file",
        str(receipt_file),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    serialized = output_text + receipt_file.read_text(encoding="utf-8")
    assert exit_code == 0
    assert receipt == output
    assert output["ok"] is True
    assert output["launchd"]["OPENAI_API_KEY"] == "set"
    assert output["set_sources"][0]["source"] == "launchd"
    assert output["commands"]["launchd_setenv_template"] == "launchctl setenv OPENAI_API_KEY <redacted-openai-api-key>"
    assert "secret-from-launchd" not in serialized


def test_build_gate_audit_report_marks_simulator_evidence_and_external_gaps(tmp_path):
    (tmp_path / "docs/superpowers/specs").mkdir(parents=True)
    (tmp_path / "docs/mobile-bridge-api.md").write_text("# API\n")
    (tmp_path / "docs/superpowers/specs/2026-05-30-agent-pocket-photo-mvp-design.md").write_text("# Spec\n")
    simulator_connection = tmp_path / "connection.json"
    fixture_receipt = tmp_path / "fixture.json"
    script_receipt = tmp_path / "script.json"
    openai_receipt = tmp_path / "openai.json"
    fake_openai_status = tmp_path / "fake-openai.json"
    python_tests = tmp_path / "python-tests.json"
    swift_tests = tmp_path / "swift-tests.json"
    ui_test_preflight = tmp_path / "ui-test-preflight.json"
    simulator_suite = tmp_path / "simulator-suite.json"
    simulator_only_resume = tmp_path / "simulator-only-resume.json"
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    discovery_refresh_receipt = tmp_path / "discovery-refresh.json"
    discovery_refresh_screenshot = tmp_path / "discovery-refresh.png"
    picker_ui_screenshot = tmp_path / "picker-ui.png"
    capture_ready_receipt = tmp_path / "capture-ready.json"
    capture_ready_screenshot = tmp_path / "capture-ready.png"
    capture_completed_receipt = tmp_path / "capture-completed.json"
    capture_completed_screenshot = tmp_path / "capture-completed.png"
    result_gallery_receipt = tmp_path / "result-gallery.json"
    result_gallery_screenshot = tmp_path / "result-gallery.png"
    result_gallery_downloaded_receipt = tmp_path / "result-gallery-downloaded.json"
    result_gallery_downloaded_screenshot = tmp_path / "result-gallery-downloaded.png"
    result_gallery_downloaded_receipt = tmp_path / "result-gallery-downloaded.json"
    result_gallery_downloaded_screenshot = tmp_path / "result-gallery-downloaded.png"
    screenshot = tmp_path / "simulator.png"
    _write_connection_receipt(simulator_connection)
    _write_photo_flow_receipt(fixture_receipt, provider="fixture")
    _write_photo_flow_receipt(script_receipt, provider="script")
    _write_photo_flow_receipt(openai_receipt, provider="openai")
    _write_fake_openai_status(fake_openai_status)
    _write_test_receipt(
        python_tests,
        "python",
        ["python3", "-m", "pytest", "mock_bridge/tests", "photo-pack/tests", "ios/tests", "-q"],
        stdout_tail="166 passed in 153.27s (0:02:33)",
    )
    _write_test_receipt(
        swift_tests,
        "swift",
        ["swift", "test"],
        stdout_tail="Test Suite 'All tests' passed.\n\t Executed 130 tests, with 0 failures (0 unexpected)",
    )
    _write_ui_test_preflight_receipt(ui_test_preflight, ok=False)
    _write_simulator_suite_receipt(simulator_suite, ok=True)
    _write_simulator_only_resume_receipt(simulator_only_resume, ok=True)
    _write_gate_f_preflight_receipt(gate_f_preflight, ready_to_run=False)
    _write_discovery_refresh_receipt(discovery_refresh_receipt, ok=True)
    _write_capture_ready_receipt(capture_ready_receipt, ok=True)
    _write_capture_completed_receipt(capture_completed_receipt, ok=True)
    _write_result_gallery_receipt(result_gallery_receipt, ok=True)
    _write_result_gallery_downloaded_receipt(result_gallery_downloaded_receipt, ok=True)
    _write_visible_simulator_screenshot(discovery_refresh_screenshot)
    _write_visible_simulator_screenshot(picker_ui_screenshot)
    _write_visible_simulator_screenshot(capture_ready_screenshot)
    _write_visible_simulator_screenshot(capture_completed_screenshot)
    _write_visible_simulator_screenshot(result_gallery_screenshot)
    _write_visible_simulator_screenshot(result_gallery_downloaded_screenshot)
    _write_visible_simulator_screenshot(screenshot)

    calls = []

    def run(command):
        calls.append(command)
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        simulator_connection_receipt="connection.json",
        fixture_receipt="fixture.json",
        script_receipt="script.json",
        openai_receipt="openai.json",
        fake_openai_status_file="fake-openai.json",
        python_test_receipt="python-tests.json",
        swift_test_receipt="swift-tests.json",
        simulator_ui_test_preflight_receipt="ui-test-preflight.json",
        simulator_suite_receipt="simulator-suite.json",
        simulator_only_resume_receipt="simulator-only-resume.json",
        gate_f_preflight_receipt="gate-f-preflight.json",
        screenshot_file="simulator.png",
        discovery_refresh_receipt_file="discovery-refresh.json",
        discovery_refresh_screenshot_file="discovery-refresh.png",
        picker_ui_screenshot_file="picker-ui.png",
        capture_ready_receipt_file="capture-ready.json",
        capture_ready_screenshot_file="capture-ready.png",
        capture_completed_receipt_file="capture-completed.json",
        capture_completed_screenshot_file="capture-completed.png",
        result_gallery_receipt_file="result-gallery.json",
        result_gallery_screenshot_file="result-gallery.png",
        result_gallery_downloaded_receipt_file="result-gallery-downloaded.json",
        result_gallery_downloaded_screenshot_file="result-gallery-downloaded.png",
        physical_openai_receipt="physical-openai.json",
        env={},
        command_runner=run,
    )

    assert report["summary"]["simulator_evidence_ok"] is True
    assert report["summary"]["gate_f_ok"] is False
    assert report["gates"]["A"]["status"] == "passed"
    assert report["gates"]["B"]["status"] == "passed"
    assert report["gates"]["B"]["evidence"][1]["summary"] == "166 passed"
    assert report["gates"]["C"]["status"] == "passed"
    assert report["gates"]["C"]["evidence"][0]["summary"] == "130 tests, 0 failures"
    assert report["gates"]["D"]["status"] == "passed"
    assert report["gates"]["D"]["evidence"][0]["path"] == "connection.json"
    assert report["gates"]["D"]["evidence"][1]["path"] == "fixture.json"
    assert report["gates"]["D"]["evidence"][2]["path"] == "discovery-refresh.json"
    assert report["gates"]["D"]["evidence"][2]["ok"] is True
    assert report["gates"]["D"]["evidence"][3]["path"] == "discovery-refresh.png"
    assert report["gates"]["D"]["evidence"][3]["exists"] is True
    assert report["gates"]["D"]["evidence"][4]["path"] == "picker-ui.png"
    assert report["gates"]["D"]["evidence"][4]["exists"] is True
    assert report["gates"]["D"]["evidence"][5]["path"] == "capture-ready.json"
    assert report["gates"]["D"]["evidence"][5]["ok"] is True
    assert report["gates"]["D"]["evidence"][6]["path"] == "capture-ready.png"
    assert report["gates"]["D"]["evidence"][6]["exists"] is True
    assert report["gates"]["D"]["evidence"][7]["path"] == "capture-completed.json"
    assert report["gates"]["D"]["evidence"][7]["ok"] is True
    assert report["gates"]["D"]["evidence"][8]["path"] == "capture-completed.png"
    assert report["gates"]["D"]["evidence"][8]["exists"] is True
    assert report["gates"]["E"]["status"] == "passed"
    assert report["gates"]["E"]["evidence"][4]["path"] == "result-gallery.json"
    assert report["gates"]["E"]["evidence"][4]["ok"] is True
    assert report["gates"]["E"]["evidence"][5]["path"] == "result-gallery.png"
    assert report["gates"]["E"]["evidence"][5]["exists"] is True
    assert report["gates"]["E"]["evidence"][6]["path"] == "result-gallery-downloaded.json"
    assert report["gates"]["E"]["evidence"][6]["ok"] is True
    assert report["gates"]["E"]["evidence"][7]["path"] == "result-gallery-downloaded.png"
    assert report["gates"]["E"]["evidence"][7]["exists"] is True
    assert report["gates"]["F"]["status"] == "missing_external_evidence"
    assert report["gates"]["F"]["missing"] == [
        "real iPhone OpenAI photo-flow receipt",
        "OPENAI_API_KEY",
        "Tailscale endpoint evidence",
    ]
    assert report["external"]["openai_api_key"] == "missing"
    assert report["external"]["tailscale"]["ok"] is False
    assert report["external"]["tailscale"]["cli"]["error"] == "tailscale CLI not found in PATH"
    assert report["external"]["tailscale"]["ip_check"]["error"] == "Install or expose the tailscale CLI in PATH first."
    assert report["external"]["gate_f_preflight"]["status"] == "blocked_to_start"
    assert report["external"]["gate_f_preflight"]["missing_to_start"] == [
        "OPENAI_API_KEY",
        "Tailscale endpoint evidence",
    ]
    assert report["local"]["simulator_ui_test_preflight"]["status"] == "blocked_by_local_xcode_runtime"
    assert report["local"]["simulator_ui_test_preflight"]["sdk_latest"] == "26.5"
    assert report["local"]["simulator_ui_test_preflight"]["runtime_latest"] == "26.1"
    assert "iOS 26.5 is not installed" in report["local"]["simulator_ui_test_preflight"]["ineligible"][0]
    assert report["local"]["simulator_suite"]["status"] == "passed"
    assert report["local"]["simulator_suite"]["required_steps"] == [
        "seed_photo_library",
        "connection_smoke",
        "discovery_refresh_smoke",
        "picker_ui_smoke",
        "capture_ready_smoke",
        "capture_completed_smoke",
        "result_gallery_smoke",
        "result_gallery_downloaded_smoke",
        "openai_smoke",
    ]
    assert report["local"]["simulator_only_resume"]["path"] == "simulator-only-resume.json"
    assert report["local"]["simulator_only_resume"]["ok"] is True
    assert report["local"]["simulator_only_resume"]["execution_mode"] == "local-mac-simulator-only"
    assert report["local"]["simulator_only_resume"]["physical_iphone_used"] is False
    assert report["local"]["simulator_only_resume"]["physical_device_launch_attempted"] is False
    assert report["local"]["simulator_only_resume"]["real_device_commands_executed"] == []
    artifacts = report["local"]["simulator_artifacts"]
    assert artifacts["discovery_refresh_receipt"]["path"] == "discovery-refresh.json"
    assert artifacts["discovery_refresh_receipt"]["ok"] is True
    assert artifacts["discovery_refresh_screenshot"]["path"] == "discovery-refresh.png"
    assert artifacts["discovery_refresh_screenshot"]["exists"] is True
    assert artifacts["picker_ui_screenshot"]["path"] == "picker-ui.png"
    assert artifacts["picker_ui_screenshot"]["exists"] is True
    assert artifacts["capture_ready_screenshot"]["path"] == "capture-ready.png"
    assert artifacts["capture_ready_screenshot"]["exists"] is True
    assert artifacts["capture_ready_receipt"]["path"] == "capture-ready.json"
    assert artifacts["capture_ready_receipt"]["ok"] is True
    assert artifacts["capture_completed_screenshot"]["path"] == "capture-completed.png"
    assert artifacts["capture_completed_screenshot"]["exists"] is True
    assert artifacts["capture_completed_receipt"]["path"] == "capture-completed.json"
    assert artifacts["capture_completed_receipt"]["ok"] is True
    assert artifacts["result_gallery_screenshot"]["path"] == "result-gallery.png"
    assert artifacts["result_gallery_screenshot"]["exists"] is True
    assert artifacts["result_gallery_receipt"]["path"] == "result-gallery.json"
    assert artifacts["result_gallery_receipt"]["ok"] is True
    assert artifacts["result_gallery_downloaded_screenshot"]["path"] == "result-gallery-downloaded.png"
    assert artifacts["result_gallery_downloaded_screenshot"]["exists"] is True
    assert artifacts["result_gallery_downloaded_receipt"]["path"] == "result-gallery-downloaded.json"
    assert artifacts["result_gallery_downloaded_receipt"]["ok"] is True
    assert artifacts["openai_photo_flow_receipt"]["path"] == "openai.json"
    assert artifacts["openai_photo_flow_receipt"]["ok"] is True
    assert artifacts["fake_openai_status"]["path"] == "fake-openai.json"
    assert artifacts["fake_openai_status"]["ok"] is True
    assert report["commands"]["simulator_ui_test_preflight"].endswith(
        "simulator-ui-test-preflight --receipt-file ui-test-preflight.json"
    )
    assert report["commands"]["simulator_suite"].endswith(
        "simulator-suite --suite-receipt-file simulator-suite.json"
    )
    assert calls == [["which", "tailscale"]]


def test_build_gate_audit_report_accepts_explicit_preflight_endpoint_evidence(tmp_path):
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    gate_f_preflight.write_text(json.dumps({
        "ok": False,
        "ready_to_run": False,
        "missing_to_start": ["OPENAI_API_KEY"],
        "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
        "checks": {
            "endpoint": {
                "ok": True,
                "source": "explicit_host",
                "host": "192.0.2.10",
                "missing": [],
            },
        },
        "commands": {},
    }))

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        gate_f_preflight_receipt="gate-f-preflight.json",
        env={},
        command_runner=run,
        provider_source_args="--hermes-profile dev-lead",
    )

    assert report["gates"]["F"]["missing"] == [
        "real iPhone OpenAI photo-flow receipt",
        "OPENAI_API_KEY",
    ]
    assert report["external"]["gate_f_preflight"]["endpoint"] == {
        "ok": True,
        "source": "explicit_host",
        "host": "192.0.2.10",
        "missing": [],
    }
    assert "--host 192.0.2.10" in report["commands"]["gate_f_preflight"]
    assert "--gate-f-host 192.0.2.10" in report["commands"]["simulator_only_resume"]
    assert "--hermes-profile dev-lead" in report["commands"]["simulator_only_resume"]
    assert "hermes --profile dev-lead auth add openai --type api-key" in report["commands"]["hermes_auth_add_openai"]
    assert "hermes-openai-auth-import --hermes-profile dev-lead" in report["commands"]["hermes_openai_auth_import"]
    assert "--resume-receipt-file docs/qa-receipts/simulator-only-resume-latest.json" in report["commands"]["simulator_only_resume"]


def test_build_gate_audit_report_accepts_redacted_provider_preflight_key_evidence(tmp_path):
    provider_preflight = tmp_path / "provider-openai.json"
    _write_provider_preflight_receipt(provider_preflight, key_state="set")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        provider_preflight_receipt="provider-openai.json",
        physical_openai_receipt="physical-openai.json",
        env={},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["external"]["openai_api_key"] == "set"
    assert report["external"]["provider_preflight"]["ok"] is True
    assert "OPENAI_API_KEY" not in report["gates"]["F"]["missing"]
    assert "real iPhone OpenAI photo-flow receipt" in report["gates"]["F"]["missing"]
    assert "secret" not in serialized


def test_build_gate_audit_report_accepts_redacted_provider_env_source_evidence(tmp_path):
    provider_env_sources = tmp_path / "provider-env-sources.json"
    provider_env_sources.write_text(json.dumps({
        "ok": True,
        "key": "OPENAI_API_KEY",
        "env": {"OPENAI_API_KEY": "set"},
        "set_sources": [
            {"source": "hermes_profile", "profile": "dev-lead", "path": "/Users/example/.hermes/profiles/dev-lead/.env"}
        ],
        "hermes": {
            "selected_profile": "dev-lead",
            "selected_profile_state": "set",
            "profiles": [],
        },
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        provider_env_sources_receipt="provider-env-sources.json",
        physical_openai_receipt="physical-openai.json",
        env={},
        command_runner=run,
    )

    assert report["external"]["openai_api_key"] == "set"
    assert report["external"]["provider_env_sources"]["ok"] is True
    assert report["external"]["provider_env_sources"]["set_sources"][0]["profile"] == "dev-lead"
    assert "OPENAI_API_KEY" not in report["gates"]["F"]["missing"]


def test_build_gate_audit_report_keeps_all_profile_env_source_sweep_diagnostic(tmp_path):
    selected_provider_env_sources = tmp_path / "selected-provider-env-sources.json"
    selected_provider_env_sources.write_text(json.dumps({
        "ok": False,
        "key": "OPENAI_API_KEY",
        "env": {"OPENAI_API_KEY": "missing"},
        "set_sources": [],
        "hermes": {
            "selected_profile": "dev-lead",
            "selected_profile_state": "missing",
            "profiles": [{"profile": "dev-lead", "selected": True, "OPENAI_API_KEY": "missing"}],
        },
    }), encoding="utf-8")
    all_profile_provider_env_sources = tmp_path / "all-provider-env-sources.json"
    all_profile_provider_env_sources.write_text(json.dumps({
        "ok": True,
        "key": "OPENAI_API_KEY",
        "env": {"OPENAI_API_KEY": "set"},
        "set_sources": [
            {"source": "hermes_profile_auth", "profile": "other", "path": "/Users/example/.hermes/profiles/other/auth.json"}
        ],
        "hermes": {
            "selected_profile": "",
            "profiles": [
                {"profile": "dev-lead", "selected": False, "OPENAI_API_KEY": "missing"},
                {"profile": "other", "selected": False, "OPENAI_API_KEY": "missing"},
            ],
        },
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        provider_env_sources_receipt="selected-provider-env-sources.json",
        provider_env_sources_all_profiles_receipt="all-provider-env-sources.json",
        physical_openai_receipt="physical-openai.json",
        env={},
        command_runner=run,
    )

    assert report["external"]["openai_api_key"] == "missing"
    assert report["external"]["provider_env_sources_all_profiles"]["ok"] is True
    assert report["external"]["provider_env_sources_all_profiles"]["set_sources"][0]["profile"] == "other"
    assert "OPENAI_API_KEY" in report["gates"]["F"]["missing"]


def test_build_gate_audit_report_rejects_blank_simulator_screenshot_evidence(tmp_path):
    (tmp_path / "docs/superpowers/specs").mkdir(parents=True)
    (tmp_path / "docs/mobile-bridge-api.md").write_text("# API\n")
    (tmp_path / "docs/superpowers/specs/2026-05-30-agent-pocket-photo-mvp-design.md").write_text("# Spec\n")
    simulator_connection = tmp_path / "connection.json"
    fixture_receipt = tmp_path / "fixture.json"
    discovery_refresh_receipt = tmp_path / "discovery-refresh.json"
    discovery_refresh_screenshot = tmp_path / "discovery-refresh.png"
    picker_ui_screenshot = tmp_path / "picker-ui.png"
    capture_ready_receipt = tmp_path / "capture-ready.json"
    capture_ready_screenshot = tmp_path / "capture-ready.png"
    capture_completed_receipt = tmp_path / "capture-completed.json"
    capture_completed_screenshot = tmp_path / "capture-completed.png"
    _write_connection_receipt(simulator_connection)
    _write_photo_flow_receipt(fixture_receipt, provider="fixture")
    _write_discovery_refresh_receipt(discovery_refresh_receipt, ok=True)
    _write_capture_ready_receipt(capture_ready_receipt, ok=True)
    _write_capture_completed_receipt(capture_completed_receipt, ok=True)
    _write_visible_simulator_screenshot(discovery_refresh_screenshot)
    _write_visible_simulator_screenshot(picker_ui_screenshot)
    _write_visible_simulator_screenshot(capture_ready_screenshot)
    _write_status_bar_only_simulator_screenshot(capture_completed_screenshot)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        simulator_connection_receipt="connection.json",
        fixture_receipt="fixture.json",
        discovery_refresh_receipt_file="discovery-refresh.json",
        discovery_refresh_screenshot_file="discovery-refresh.png",
        picker_ui_screenshot_file="picker-ui.png",
        capture_ready_receipt_file="capture-ready.json",
        capture_ready_screenshot_file="capture-ready.png",
        capture_completed_receipt_file="capture-completed.json",
        capture_completed_screenshot_file="capture-completed.png",
        env={},
        command_runner=run,
    )

    screenshot_evidence = report["local"]["simulator_artifacts"]["capture_completed_screenshot"]
    assert screenshot_evidence["exists"] is True
    assert screenshot_evidence["ok"] is False
    assert screenshot_evidence["missing"] == ["visible Simulator screenshot content"]
    assert report["gates"]["D"]["status"] == "missing_evidence"
    assert "visible Simulator screenshot content" in report["gates"]["D"]["missing"]


def test_audit_capture_ready_receipt_requires_library_selection_preprocessing_path(tmp_path):
    receipt = tmp_path / "capture-ready.json"
    receipt.write_text(json.dumps({
        "phase": "capture-ready",
        "ok": True,
        "state": "ready",
        "file_name": "library.jpg",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": True,
        "send_to_hermes_enabled": True,
    }), encoding="utf-8")

    report = qa_module._audit_capture_ready_receipt(str(tmp_path), "capture-ready.json")

    assert report["ok"] is False
    assert "library selection source" in report["missing"]
    assert "prepareSelectedImage preprocessing path" in report["missing"]
    assert "Send to Pocket Agent primary action" in report["missing"]


def test_audit_capture_ready_receipt_reports_selection_source_and_action(tmp_path):
    receipt = tmp_path / "capture-ready.json"
    payload = {
        "phase": "capture-ready",
        "ok": True,
        "state": "ready",
        "file_name": "library.jpg",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": True,
        "send_to_local_agent_enabled": True,
        "send_to_hermes_enabled": True,
        "selection_source": "library_fixture",
        "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage",
        "primary_action": "Send to Local Agent",
        "ready_status_accessibility_identifier": "selectedPhotoReadyStatus",
        "send_button_accessibility_identifier": "sendToLocalAgentButton",
    }
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    report = qa_module._audit_capture_ready_receipt(str(tmp_path), "capture-ready.json")

    assert report["ok"] is True
    assert report["selection_source"] == "library_fixture"
    assert report["preprocessing_path"] == "CaptureFlowViewModel.prepareSelectedImage"
    assert report["primary_action"] == "Send to Local Agent"
    assert report["ready_status_accessibility_identifier"] == "selectedPhotoReadyStatus"
    assert report["send_button_accessibility_identifier"] == "sendToLocalAgentButton"


def test_audit_capture_ready_receipt_accepts_runtime_neutral_send_fields(tmp_path):
    receipt = tmp_path / "capture-ready.json"
    payload = {
        "phase": "capture-ready",
        "ok": True,
        "state": "ready",
        "file_name": "library.jpg",
        "intent_title": "Natural Enhance",
        "has_prepared_upload": True,
        "send_to_local_agent_enabled": True,
        "selection_source": "library_fixture",
        "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage",
        "primary_action": "Send to Local Agent",
        "ready_status_accessibility_identifier": "selectedPhotoReadyStatus",
        "send_button_accessibility_identifier": "sendToLocalAgentButton",
    }
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    report = qa_module._audit_capture_ready_receipt(str(tmp_path), "capture-ready.json")

    assert report["ok"] is True
    assert report["send_to_local_agent_enabled"] is True
    assert report["send_button_accessibility_identifier"] == "sendToLocalAgentButton"


def test_build_gate_audit_report_never_prints_openai_secret_and_can_pass_gate_f(tmp_path):
    physical_receipt = tmp_path / "physical-openai.json"
    _write_photo_flow_receipt(physical_receipt, provider="openai")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")

    report = build_gate_audit_report(
        root=str(tmp_path),
        physical_openai_receipt="physical-openai.json",
        env={"OPENAI_API_KEY": "secret-value-that-must-not-leak"},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["external"]["openai_api_key"] == "set"
    assert report["external"]["tailscale"]["ip"] == "100.101.102.103"
    assert report["gates"]["F"]["status"] == "passed"
    assert "secret-value-that-must-not-leak" not in serialized


def test_build_gate_audit_report_marks_missing_test_receipts_as_fresh_verification_needed(tmp_path):
    fixture_receipt = tmp_path / "fixture.json"
    _write_photo_flow_receipt(fixture_receipt, provider="fixture")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=1, stdout="", stderr="not running")

    report = build_gate_audit_report(
        root=str(tmp_path),
        fixture_receipt="fixture.json",
        python_test_receipt="python-tests.json",
        swift_test_receipt="swift-tests.json",
        env={},
        command_runner=run,
    )

    assert report["gates"]["B"]["status"] == "needs_fresh_verification"
    assert report["gates"]["B"]["missing"] == ["python test receipt file"]
    assert report["gates"]["C"]["status"] == "needs_fresh_verification"
    assert report["gates"]["C"]["missing"] == ["swift test receipt file"]


def test_build_readiness_markdown_summarizes_gates_skills_and_next_commands():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": [
                "real iPhone OpenAI photo-flow receipt",
                "OPENAI_API_KEY",
            ],
        },
        "gates": {
            "A": {"title": "Bridge API and engineering spec", "status": "passed", "missing": []},
            "B": {
                "title": "Mock bridge tests and simulator fake task",
                "status": "passed",
                "missing": [],
                "evidence": [
                    {"path": "fixture.json", "ok": True},
                    {
                        "path": "docs/qa-receipts/python-tests-latest.json",
                        "name": "python",
                        "ok": True,
                        "summary": "166 passed",
                    },
                ],
            },
            "C": {
                "title": "Swift core tests and connection parsing",
                "status": "passed",
                "missing": [],
                "evidence": [
                    {
                        "path": "docs/qa-receipts/swift-test-latest.json",
                        "name": "swift",
                        "ok": True,
                        "summary": "130 tests, 0 failures",
                    },
                ],
            },
            "D": {"title": "SwiftUI simulator app fixture photo flow", "status": "passed", "missing": []},
            "E": {"title": "Photo Pack adapter chain and downloadable result", "status": "passed", "missing": []},
            "F": {
                "title": "Real Photo Pack adapter returns variants to a real iPhone",
                "status": "missing_external_evidence",
                "missing": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "provider_preflight": {
                "path": "docs/qa-receipts/provider-openai-preflight-latest.json",
                "exists": True,
                "ok": False,
                "status": "missing_provider_evidence",
                "env": {"OPENAI_API_KEY": "missing"},
                "hermes": {
                    "profile": "dev-lead",
                    "env_file": {
                        "path": "/Users/example/.hermes/profiles/dev-lead/.env",
                        "exists": True,
                        "OPENAI_API_KEY": "missing",
                    },
                    "auth": {
                        "openai_codex": {
                            "credential_pool": "set",
                            "compatible_with_photo_provider": False,
                        },
                    },
                },
            },
            "tailscale": {
                "ok": False,
                "ip": "",
                "error": "tailscale CLI not found in PATH",
                "cli": {
                    "ok": False,
                    "path": "",
                    "error": "tailscale CLI not found in PATH",
                },
                "ip_check": {
                    "ok": False,
                    "value": "",
                    "error": "Install or expose the tailscale CLI in PATH first.",
                },
            },
            "gate_f_preflight": {
                "path": "docs/qa-receipts/gate-f-preflight-latest.json",
                "exists": True,
                "ok": False,
                "ready_to_run": False,
                "status": "blocked_to_start",
                "missing_to_start": ["OPENAI_API_KEY", "Tailscale endpoint evidence"],
                "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
                "commands": {
                    "provider_preflight": (
                        "OPENAI_API_KEY=<set-in-hermes-process> PYTHONPATH=mock_bridge "
                        "python3 -m agent_pocket_mock_bridge.qa provider-preflight --photo-provider openai"
                    ),
                    "run_real_iphone_openai": (
                        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
                        "--photo-provider openai --receipt-file docs/qa-receipts/openai-photo-flow.json"
                    ),
                    "verify_real_iphone_openai": (
                        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt "
                        "--file docs/qa-receipts/openai-photo-flow.json --phase photo-flow --photo-provider openai"
                    ),
                    "gate_f_resume": (
                        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
                        "--photo-provider openai --receipt-file docs/qa-receipts/openai-photo-flow.json && "
                        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt "
                        "--file docs/qa-receipts/openai-photo-flow.json --phase photo-flow --photo-provider openai"
                    ),
                },
            },
        },
        "local": {
            "iphone_credential_boundary": {
                "path": "docs/qa-receipts/iphone-credential-boundary-latest.json",
                "exists": True,
                "ok": True,
                "scanned_files": 57,
            },
            "simulator_only_resume": {
                "path": "docs/qa-receipts/simulator-only-resume-latest.json",
                "exists": True,
                "ok": True,
                "execution_mode": "local-mac-simulator-only",
                "physical_iphone_used": False,
                "physical_device_launch_attempted": False,
                "real_device_commands_executed": [],
            },
            "simulator_suite": {
                "path": "docs/qa-receipts/simulator-suite-latest.json",
                "exists": True,
                "ok": True,
                "status": "passed",
                "required_steps": [
                    "seed_photo_library",
                    "connection_smoke",
                    "picker_ui_smoke",
                    "capture_ready_smoke",
                    "capture_completed_smoke",
                    "result_gallery_smoke",
                    "result_gallery_downloaded_smoke",
                    "openai_smoke",
                ],
                "failed_required_steps": [],
            },
            "simulator_ui_test_preflight": {
                "path": "docs/qa-receipts/simulator-ui-test-preflight-latest.json",
                "exists": True,
                "ok": False,
                "status": "blocked_by_local_xcode_runtime",
                "sdk_latest": "26.5",
                "runtime_latest": "26.1",
                "reason": "Installed iOS Simulator runtime does not match the active iOS Simulator SDK.",
                "ineligible": [
                    "{ platform:iOS, arch:arm64e, name:iPhone 16 Plus, error:iOS 26.5 is not installed. }",
                    "{ platform:iOS, name:Any iOS Device, error:iOS 26.5 is not installed. }",
                ],
            },
            "simulator_artifacts": {
                "picker_ui_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-picker-ui-smoke.png",
                    "exists": True,
                },
                "capture_ready_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-capture-ready.png",
                    "exists": True,
                },
                "capture_ready_receipt": {
                    "path": "docs/qa-receipts/simulator-capture-ready-latest.json",
                    "exists": True,
                    "ok": True,
                },
                "capture_completed_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-capture-completed.png",
                    "exists": True,
                },
                "capture_completed_receipt": {
                    "path": "docs/qa-receipts/simulator-capture-completed-latest.json",
                    "exists": True,
                    "ok": True,
                },
                "result_gallery_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-result-gallery.png",
                    "exists": True,
                },
                "result_gallery_receipt": {
                    "path": "docs/qa-receipts/simulator-result-gallery-latest.json",
                    "exists": True,
                    "ok": True,
                },
                "result_gallery_downloaded_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-result-gallery-downloaded.png",
                    "exists": True,
                },
                "result_gallery_downloaded_receipt": {
                    "path": "docs/qa-receipts/simulator-result-gallery-downloaded-latest.json",
                    "exists": True,
                    "ok": True,
                },
                "openai_photo_flow_receipt": {
                    "path": "docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
                    "exists": True,
                    "ok": True,
                },
                "fake_openai_status": {
                    "path": "docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
                    "exists": True,
                    "ok": True,
                },
                "openai_screenshot": {
                    "path": "/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
                    "exists": True,
                },
            },
        },
        "commands": {
            "gate_audit": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-audit",
            "gate_f_real_iphone": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan --photo-provider openai",
            "simulator_connection_smoke": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-connection-smoke",
            "simulator_seed_photo_library": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library",
            "simulator_capture_ready_smoke": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke",
            "simulator_capture_completed_smoke": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke",
            "simulator_result_gallery_smoke": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-smoke",
            "simulator_result_gallery_downloaded_smoke": "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-downloaded-smoke",
            "simulator_ui_test_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight "
                "--receipt-file docs/qa-receipts/simulator-ui-test-preflight-latest.json"
            ),
        },
    }

    markdown = build_readiness_markdown(report)

    assert "# Pocket Agent MVP Readiness" in markdown
    assert "- Gate F remains open until required external evidence is available: real iPhone OpenAI photo-flow receipt, server-side OpenAI key proof (Hermes/provider runtime), and Tailscale endpoint evidence." in markdown
    assert "@superpowers" in markdown
    assert "@build-ios-apps: unavailable in this session; Xcode/SwiftPM fallback used" in markdown
    assert "## Completion Audit" in markdown
    assert "- Overall objective: not complete" in markdown
    assert "- Proven locally: Gates A, B, C, D, and E" in markdown
    assert "- Current test lane: local Mac Simulator only" in markdown
    assert "- Not yet proven: Gate F real iPhone OpenAI provider flow" in markdown
    assert "- Required external evidence: real iPhone OpenAI photo-flow receipt, server-side OpenAI key proof (Hermes/provider runtime), and Tailscale endpoint evidence" in markdown
    assert "## Completion Evidence Matrix" in markdown
    assert "| Local simulator MVP gates | passed | Gates A, B, C, D, and E |" in markdown
    assert "| iPhone credential boundary | passed | OpenAI key/API use absent from client; receipt docs/qa-receipts/iphone-credential-boundary-latest.json |" in markdown
    assert "| Server-side OpenAI key proof | not proven | Hermes/provider runtime owns `OPENAI_API_KEY`; iPhone credential required: false |" in markdown
    assert "| Physical iPhone launch path | not checked | CLI/CoreDevice route; Xcode GUI platform support is optional for this proof |" in markdown
    assert "| Real iPhone OpenAI photo flow | not proven | Requires docs/qa-receipts/openai-photo-flow.json from a real iPhone run |" in markdown
    assert "| A | passed | Bridge API and engineering spec |  |" in markdown
    assert "| F | missing_external_evidence | Real Photo Pack adapter returns variants to a real iPhone | real iPhone OpenAI photo-flow receipt, server-side OpenAI key proof (Hermes/provider runtime) |" in markdown
    assert "## Fresh Verification" in markdown
    assert "- Python tests: passed (docs/qa-receipts/python-tests-latest.json; 166 passed)" in markdown
    assert "- Swift tests: passed (docs/qa-receipts/swift-test-latest.json; 130 tests, 0 failures)" in markdown
    assert (
        "- Provider preflight receipt: failed "
        "(docs/qa-receipts/provider-openai-preflight-latest.json; missing provider evidence)"
    ) in markdown
    assert "- Hermes profile provider check: dev-lead, profile OPENAI_API_KEY missing, /Users/example/.hermes/profiles/dev-lead/.env" in markdown
    assert "- OpenAI Codex OAuth: present, but not an OpenAI Images API key" in markdown
    assert "- Tailscale CLI: missing (tailscale CLI not found in PATH)" in markdown
    assert "- Tailscale IP: missing (Install or expose the tailscale CLI in PATH first.)" in markdown
    assert "## Gate F External Preflight" in markdown
    assert "- Receipt: docs/qa-receipts/gate-f-preflight-latest.json" in markdown
    assert "- Start readiness: blocked_to_start" in markdown
    assert "- Missing to start: server-side OpenAI key proof (Hermes/provider runtime), Tailscale endpoint evidence" in markdown
    assert "- Missing to close: real iPhone OpenAI photo-flow receipt" in markdown
    assert "### provider_preflight" in markdown
    assert "OPENAI_API_KEY=<set-in-hermes-process> PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight --photo-provider openai" in markdown
    assert "### run_real_iphone_openai" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan --photo-provider openai --receipt-file docs/qa-receipts/openai-photo-flow.json" in markdown
    assert "### verify_real_iphone_openai" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt --file docs/qa-receipts/openai-photo-flow.json --phase photo-flow --photo-provider openai" in markdown
    assert "### gate_f_resume" in markdown
    assert "## Gate F Resume Checklist" in markdown
    assert "1. Confirm `OPENAI_API_KEY` is available to the Hermes/mock bridge process, then rerun `provider_preflight`; the iPhone app never stores or calls this key." in markdown
    assert "2. Install or start Tailscale, or set `TAILSCALE_CLI=/path/to/tailscale`, until preflight reports a Mac tailnet endpoint." in markdown
    assert "3. When the iPhone and external start conditions are available, run `gate_f_resume`." in markdown
    assert "run `run_real_iphone_openai`" not in markdown
    assert "with `verify_real_iphone_openai`." not in markdown
    assert "## Local Simulator UI Test Readiness" in markdown
    assert "## Local Simulator Suite" in markdown
    assert "## Local Simulator Resume Evidence" in markdown
    assert "- Resume receipt: docs/qa-receipts/simulator-only-resume-latest.json" in markdown
    assert "- Execution mode: local-mac-simulator-only" in markdown
    assert "- Physical iPhone used: false" in markdown
    assert "- Physical device launch attempted: false" in markdown
    assert "- Real-device commands executed: none" in markdown
    assert "- Suite status: passed" in markdown
    assert "- Required steps: seed_photo_library, connection_smoke, picker_ui_smoke, capture_ready_smoke, capture_completed_smoke, result_gallery_smoke, result_gallery_downloaded_smoke, openai_smoke" in markdown
    assert "## Local Simulator Artifacts" in markdown
    assert "- PhotosPicker entry screenshot: /tmp/agent-pocket-simulator-picker-ui-smoke.png" in markdown
    assert "- Selected-photo ready receipt: docs/qa-receipts/simulator-capture-ready-latest.json" in markdown
    assert "- Selected-photo ready screenshot: /tmp/agent-pocket-simulator-capture-ready.png" in markdown
    assert "- Completed capture receipt: docs/qa-receipts/simulator-capture-completed-latest.json" in markdown
    assert "- Completed capture screenshot: /tmp/agent-pocket-simulator-capture-completed.png" in markdown
    assert "- Result gallery receipt: docs/qa-receipts/simulator-result-gallery-latest.json" in markdown
    assert "- Result gallery screenshot: /tmp/agent-pocket-simulator-result-gallery.png" in markdown
    assert "- Result gallery downloaded receipt: docs/qa-receipts/simulator-result-gallery-downloaded-latest.json" in markdown
    assert "- Result gallery downloaded screenshot: /tmp/agent-pocket-simulator-result-gallery-downloaded.png" in markdown
    assert "- OpenAI-compatible photo-flow receipt: docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json" in markdown
    assert "- Fake OpenAI status receipt: docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json" in markdown
    assert "- Xcode UI test destination: blocked_by_local_xcode_runtime" in markdown
    assert "- iOS Simulator SDK: 26.5" in markdown
    assert "- Installed iOS Simulator runtime: 26.1" in markdown
    assert "iOS 26.5 is not installed" in markdown
    assert "Xcode destination note: { platform:iOS, name:Any iOS Device" in markdown
    assert "Xcode destination note: { platform:iOS, arch:arm64e, name:iPhone 16 Plus" not in markdown
    assert "[Errno" not in markdown
    assert "- real iPhone OpenAI photo-flow receipt" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-audit" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-connection-smoke" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke" in markdown
    assert "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight" in markdown


def test_build_readiness_markdown_summarizes_openai_base_url_without_credentials():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["real iPhone OpenAI photo-flow receipt"],
        },
        "gates": {
            "A": {"title": "A", "status": "passed", "missing": []},
            "B": {"title": "B", "status": "passed", "missing": []},
            "C": {"title": "C", "status": "passed", "missing": []},
            "D": {"title": "D", "status": "passed", "missing": []},
            "E": {"title": "E", "status": "passed", "missing": []},
            "F": {
                "title": "Real Photo Pack adapter returns variants to a real iPhone",
                "status": "missing_external_evidence",
                "missing": ["real iPhone OpenAI photo-flow receipt"],
            },
        },
        "external": {
            "openai_api_key": "set",
            "provider_preflight": {
                "path": "docs/qa-receipts/provider-openai-preflight-latest.json",
                "exists": True,
                "ok": True,
                "env": {"OPENAI_API_KEY": "set"},
                "config": {
                    "OPENAI_BASE_URL": {
                        "state": "custom",
                        "value": "http://127.0.0.1:7788/v1",
                        "redacted": True,
                    },
                },
                "hermes": {
                    "profile": "dev-lead",
                    "env_file": {
                        "path": "/Users/example/.hermes/profiles/dev-lead/.env",
                        "OPENAI_API_KEY": "set",
                    },
                    "effective_env": {
                        "OPENAI_API_KEY": "set",
                        "OPENAI_BASE_URL": "set",
                    },
                    "shared_auth_env": {
                        "OPENAI_API_KEY": "missing",
                        "OPENAI_BASE_URL": "missing",
                        "used": False,
                    },
                    "shared_auth_file": {
                        "path": "/Users/example/.hermes/shared-auth/auth.json",
                    },
                },
            },
        },
    }

    markdown = build_readiness_markdown(report)

    assert "- OpenAI base URL: custom http://127.0.0.1:7788/v1, credentials redacted" in markdown
    assert "- Hermes profile provider check: dev-lead, effective OPENAI_API_KEY set, effective OPENAI_BASE_URL set, profile OPENAI_API_KEY set, /Users/example/.hermes/profiles/dev-lead/.env" in markdown
    assert "- Hermes shared auth OpenAI API-key source: OPENAI_API_KEY missing, OPENAI_BASE_URL missing, /Users/example/.hermes/shared-auth/auth.json" in markdown
    assert "proxy-pass" not in markdown


def test_build_readiness_markdown_summarizes_hermes_diagnostics_without_treating_them_as_iphone_key():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"title": "A", "status": "passed", "missing": []},
            "B": {"title": "B", "status": "passed", "missing": []},
            "C": {"title": "C", "status": "passed", "missing": []},
            "D": {"title": "D", "status": "passed", "missing": []},
            "E": {"title": "E", "status": "passed", "missing": []},
            "F": {
                "title": "Real Photo Pack adapter returns variants to a real iPhone",
                "status": "missing_external_evidence",
                "missing": ["OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "provider_env_sources": {
                "path": "docs/qa-receipts/provider-env-sources-latest.json",
                "exists": True,
                "ok": False,
                "sources": [
                    {
                        "source": "hermes_force_current_process",
                        "force_env": "_HERMES_FORCE_OPENAI_API_KEY",
                        "OPENAI_API_KEY": "missing",
                    }
                ],
                "shell_startup_files": {
                    "state": "declared_not_active",
                    "counts_for_provider_readiness": False,
                    "files": [
                        {
                            "source": "shell_startup_file",
                            "path": "/Users/kartz/.zshrc",
                            "OPENAI_API_KEY": "set",
                            "counts_for_provider_readiness": False,
                        }
                    ],
                    "set_files": [
                        {
                            "source": "shell_startup_file",
                            "path": "/Users/kartz/.zshrc",
                        }
                    ],
                },
                "hermes": {
                    "shared_auth_file": {
                        "OPENAI_API_KEY": "set",
                        "OPENAI_BASE_URL": "set",
                        "path": "/Users/example/.hermes/shared-auth/auth.json",
                    },
                    "processes": [
                        {
                            "profile": "dev-lead",
                            "pid": "2222",
                            "selected": True,
                            "OPENAI_API_KEY": "set",
                            "OPENAI_BASE_URL": "set",
                            "force_env": "set",
                        }
                    ],
                    "provider_references": [
                        {
                            "profile": "dev-lead",
                            "selected": True,
                            "path": "/Users/example/.hermes/profiles/dev-lead/config.yaml",
                            "openai_reference": "present",
                            "OPENAI_API_KEY": "absent",
                            "OPENAI_BASE_URL": "absent",
                        }
                    ],
                    "cli_auth": {
                        "profile": "dev-lead",
                        "auth_list": {
                            "providers": {
                                "openai-codex": {
                                    "credential_count": 1,
                                    "auth_types": ["oauth"],
                                    "source_types": ["device_code"],
                                }
                            },
                        },
                        "openai_status": {
                            "state": "logged_out",
                        },
                        "openai_images_api_key_auth": "missing",
                    },
                },
            },
            "provider_env_sources_all_profiles": {
                "path": "docs/qa-receipts/provider-env-sources-all-profiles-latest.json",
                "exists": True,
                "ok": False,
                "status": "missing_provider_env_source",
                "missing": ["OPENAI_API_KEY"],
                "set_sources": [],
                "hermes": {
                    "profiles": [
                        {"profile": "dev-lead", "OPENAI_API_KEY": "missing"},
                        {"profile": "prod", "OPENAI_API_KEY": "missing"},
                    ],
                },
            },
        },
    }

    markdown = build_readiness_markdown(report)

    assert "- Server-side OpenAI key proof: not proven (Hermes/provider runtime only; iPhone never stores or calls this key)" in markdown
    assert "- Hermes force env source: _HERMES_FORCE_OPENAI_API_KEY missing" in markdown
    assert "- Shell startup key declaration: /Users/kartz/.zshrc (diagnostic only; not active Hermes/provider evidence)" in markdown
    assert "- Hermes shared auth source: OPENAI_API_KEY set, OPENAI_BASE_URL set, /Users/example/.hermes/shared-auth/auth.json" in markdown
    assert "- Hermes process diagnostics: dev-lead pid 2222 OPENAI_API_KEY set OPENAI_BASE_URL set force env set" in markdown
    assert "- Hermes selected config references: dev-lead, openai reference present, OPENAI_API_KEY token absent, OPENAI_BASE_URL token absent, /Users/example/.hermes/profiles/dev-lead/config.yaml" in markdown
    assert "- Hermes CLI auth: dev-lead, openai logged_out, Images API key missing, openai-codex oauth present" in markdown
    assert "- Hermes all-profile key sweep: no compatible OpenAI Images API key found (failed; docs/qa-receipts/provider-env-sources-all-profiles-latest.json; missing OPENAI_API_KEY; scanned profiles 2)" in markdown


def test_build_readiness_markdown_reports_all_profile_key_sweep_as_diagnostic():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"title": "A", "status": "passed", "missing": []},
            "B": {"title": "B", "status": "passed", "missing": []},
            "C": {"title": "C", "status": "passed", "missing": []},
            "D": {"title": "D", "status": "passed", "missing": []},
            "E": {"title": "E", "status": "passed", "missing": []},
            "F": {
                "title": "Real Photo Pack adapter returns variants to a real iPhone",
                "status": "missing_external_evidence",
                "missing": ["OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "provider_env_sources": {
                "path": "docs/qa-receipts/provider-env-sources-latest.json",
                "exists": True,
                "ok": False,
                "missing": ["OPENAI_API_KEY"],
            },
            "provider_env_sources_all_profiles": {
                "path": "docs/qa-receipts/provider-env-sources-all-profiles-latest.json",
                "exists": True,
                "ok": True,
                "set_sources": [
                    {
                        "source": "hermes_profile_auth",
                        "profile": "other",
                        "path": "/Users/example/.hermes/profiles/other/auth.json",
                    },
                ],
            },
        },
    }

    markdown = build_readiness_markdown(report)

    assert "- Hermes all-profile key sweep: found compatible OpenAI Images API-key source(s) hermes_profile_auth:other /Users/example/.hermes/profiles/other/auth.json (docs/qa-receipts/provider-env-sources-all-profiles-latest.json; selected profile probe still governs Gate F)" in markdown


def test_build_readiness_markdown_shows_explicit_gate_f_endpoint_evidence():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": [
                "real iPhone OpenAI photo-flow receipt",
                "OPENAI_API_KEY",
            ],
        },
        "gates": {
            "A": {"title": "Bridge API and engineering spec", "status": "passed", "missing": []},
            "B": {"title": "Mock bridge tests and simulator fake task", "status": "passed", "missing": []},
            "C": {"title": "Swift core tests and connection parsing", "status": "passed", "missing": []},
            "D": {"title": "SwiftUI simulator app fixture photo flow", "status": "passed", "missing": []},
            "E": {"title": "Photo Pack adapter chain and downloadable result", "status": "passed", "missing": []},
            "F": {
                "title": "Real Photo Pack adapter returns variants to a real iPhone",
                "status": "missing_external_evidence",
                "missing": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "tailscale": {
                "ok": False,
                "error": "tailscale CLI not found in PATH",
            },
            "gate_f_preflight": {
                "path": "docs/qa-receipts/gate-f-preflight-latest.json",
                "exists": True,
                "ok": False,
                "ready_to_run": False,
                "status": "blocked_to_start",
                "missing_to_start": ["OPENAI_API_KEY"],
                "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
                "endpoint": {
                    "ok": True,
                    "source": "explicit_host",
                    "host": "192.0.2.10",
                    "missing": [],
                },
                "commands": {
                    "provider_preflight": "provider-preflight",
                    "hermes_auth_add_openai": (
                        "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
                    ),
                    "gate_f_resume": "gate-f-resume --host 192.0.2.10",
                },
                "start_blockers": [
                    {
                        "missing": "OPENAI_API_KEY",
                        "label": "server-side OpenAI key proof (Hermes/provider runtime)",
                        "scope": "Hermes/mock bridge server process",
                        "iphone_required": False,
                        "message": (
                            "Pocket Agent on iPhone never stores or calls OPENAI_API_KEY; "
                            "the runtime that performs the photo edit must prove it can read the key."
                        ),
                        "remediation_command": (
                            "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
                        ),
                        "evidence_command": "provider-preflight",
                    }
                ],
            },
        },
        "local": {},
        "commands": {},
    }

    markdown = build_readiness_markdown(report)

    assert "- Gate F remains open until required external evidence is available: real iPhone OpenAI photo-flow receipt and server-side OpenAI key proof (Hermes/provider runtime)." in markdown
    assert "endpoint evidence are available" not in markdown
    assert "- Endpoint evidence: ready (explicit_host: 192.0.2.10)" in markdown
    assert "Install or start Tailscale" not in markdown
    assert "Remediation command: `hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images`" in markdown
    assert "1. Add the OpenAI Images API key with `hermes_auth_add_openai`, then rerun `provider_preflight`; the iPhone app never stores or calls this key." in markdown
    assert "2. When the iPhone and external start conditions are available, run `gate_f_resume`." in markdown


def test_build_readiness_markdown_shows_no_device_gate_f_handoff():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"status": "passed", "title": "A", "missing": []},
            "B": {"status": "passed", "title": "B", "missing": []},
            "C": {"status": "passed", "title": "C", "missing": []},
            "D": {"status": "passed", "title": "D", "missing": []},
            "E": {"status": "passed", "title": "E", "missing": []},
            "F": {
                "status": "missing_external_evidence",
                "title": "F",
                "missing": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "tailscale": {},
            "gate_f_handoff": {
                "exists": True,
                "ok": True,
                "status": "handoff_ready_with_external_blockers",
                "path": "docs/qa-receipts/gate-f-handoff-latest.json",
                "execution_mode": "local-mac-simulator-only",
                "physical_iphone_used": False,
                "physical_device_launch_attempted": False,
                "remaining_to_start": ["OPENAI_API_KEY"],
                "remaining_to_close": ["real iPhone OpenAI photo-flow receipt"],
                "endpoint": {"ok": True, "source": "explicit_host", "host": "192.0.2.10", "missing": []},
                "next_actions": [
                    "Add the OpenAI Images API key with hermes_auth_add_openai, then rerun provider_preflight.",
                    "When the physical iPhone is available again, run gate_f_resume.",
                ],
            },
        },
        "local": {},
        "commands": {
            "gate_f_handoff": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-handoff "
                "--receipt-file docs/qa-receipts/gate-f-handoff-latest.json"
            ),
        },
    }

    markdown = build_readiness_markdown(report)

    assert "## Gate F No-Device Handoff" in markdown
    assert "- Handoff status: handoff_ready_with_external_blockers" in markdown
    assert "- Physical iPhone used: false" in markdown
    assert "- Physical device launch attempted: false" in markdown
    assert "- Remaining to start: server-side OpenAI key proof (Hermes/provider runtime)" in markdown
    assert "- Remaining to close: real iPhone OpenAI photo-flow receipt" in markdown
    assert "- Endpoint evidence: ready (explicit_host: 192.0.2.10)" in markdown
    assert "1. Add the OpenAI Images API key with hermes_auth_add_openai, then rerun provider_preflight." in markdown
    assert "### gate_f_handoff" in markdown


def test_build_readiness_markdown_shows_physical_device_preflight_blocker():
    report = {
        "summary": {
            "simulator_evidence_ok": True,
            "gate_f_ok": False,
            "remaining_external": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
        },
        "gates": {
            "A": {"status": "passed", "title": "A", "missing": []},
            "B": {"status": "passed", "title": "B", "missing": []},
            "C": {"status": "passed", "title": "C", "missing": []},
            "D": {"status": "passed", "title": "D", "missing": []},
            "E": {"status": "passed", "title": "E", "missing": []},
            "F": {
                "status": "missing_external_evidence",
                "title": "F",
                "missing": ["real iPhone OpenAI photo-flow receipt", "OPENAI_API_KEY"],
            },
        },
        "external": {
            "openai_api_key": "missing",
            "tailscale": {},
            "physical_device_preflight": {
                "exists": True,
                "ok": False,
                "status": "blocked_by_xcode_device_support",
                "path": "docs/qa-receipts/physical-device-preflight-latest.json",
                "device": {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "name": "iPhone 16 Plus",
                    "state": "available (paired)",
                },
                "missing": ["Xcode iOS device platform support"],
                "ineligible": [
                    "{ platform:iOS, name:iPhone 16 Plus, error:iOS 26.5 is not installed. Please download and install the platform from Xcode > Settings > Components. }"
                ],
                "next_actions": [
                    "Install the matching iOS platform from Xcode > Settings > Components, then rerun physical-device-preflight."
                ],
            },
        },
        "local": {},
        "commands": {
            "physical_device_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa physical-device-preflight "
                "--receipt-file docs/qa-receipts/physical-device-preflight-latest.json"
            ),
        },
    }

    markdown = build_readiness_markdown(report)

    assert "## Physical Device Preflight" in markdown
    assert "- Device: iPhone 16 Plus (00000000-0000-0000-0000-000000000000, available (paired))" in markdown
    assert "- Xcode destination: blocked_by_xcode_device_support" in markdown
    assert "- Missing: Xcode iOS device platform support" in markdown
    assert "iOS 26.5 is not installed" in markdown
    assert "### physical_device_preflight" in markdown


def test_build_gate_f_preflight_report_tracks_external_start_and_close_gaps(tmp_path):
    _write_openai_adapter(tmp_path)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={},
        command_runner=run,
    )

    assert report["ok"] is False
    assert report["ready_to_run"] is False
    assert report["checks"]["openai_api_key"] == "missing"
    assert report["checks"]["openai_provider"]["adapter"]["exists"] is True
    assert report["checks"]["tailscale"]["ok"] is False
    assert report["checks"]["tailscale"]["cli"]["ok"] is False
    assert report["checks"]["tailscale"]["cli"]["error"] == "tailscale CLI not found in PATH"
    assert report["checks"]["tailscale"]["ip_check"]["ok"] is False
    assert report["checks"]["tailscale"]["ip_check"]["error"] == "Install or expose the tailscale CLI in PATH first."
    assert report["checks"]["physical_openai_receipt"]["exists"] is False
    assert report["missing_to_start"] == ["OPENAI_API_KEY", "Tailscale endpoint evidence"]
    assert report["missing_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert "--photo-provider openai" in report["commands"]["run_real_iphone_openai"]
    assert "OPENAI_API_KEY" in report["commands"]["provider_preflight"]
    assert "--receipt-file docs/qa-receipts/provider-openai-preflight-latest.json" in report["commands"]["provider_preflight"]


def test_build_gate_f_preflight_report_accepts_explicit_host_as_endpoint_evidence(tmp_path):
    _write_openai_adapter(tmp_path)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={"OPENAI_API_KEY": "super-secret"},
        command_runner=run,
        host="192.0.2.10",
    )

    serialized = json.dumps(report)
    assert report["ready_to_run"] is True
    assert report["missing_to_start"] == []
    assert report["missing_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert report["checks"]["tailscale"]["ok"] is False
    assert report["checks"]["endpoint"] == {
        "ok": True,
        "source": "explicit_host",
        "host": "192.0.2.10",
        "missing": [],
    }
    assert "--host 192.0.2.10" in report["commands"]["run_real_iphone_openai"]
    assert "--host 192.0.2.10" in report["commands"]["gate_f_resume"]
    assert "super-secret" not in serialized


def test_build_gate_f_preflight_report_accepts_hermes_force_env_as_server_key_evidence(tmp_path):
    _write_openai_adapter(tmp_path)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={"_HERMES_FORCE_OPENAI_API_KEY": "secret-from-hermes-force"},
        command_runner=run,
        host="192.0.2.10",
    )

    serialized = json.dumps(report)
    assert report["ready_to_run"] is True
    assert report["missing_to_start"] == []
    assert report["checks"]["server_env"]["openai_api_key"] == "set"
    assert report["checks"]["server_env"]["key_evidence"] == "environment"
    assert "secret-from-hermes-force" not in serialized


def test_build_gate_f_preflight_report_preserves_env_file_in_resume_commands(tmp_path):
    _write_openai_adapter(tmp_path)
    env_file = tmp_path / "hermes-openai.local.env"
    env_file.write_text("OPENAI_API_KEY=secret-from-hermes-env\n", encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env=qa_module._env_with_file(env_file=str(env_file)),
        env_file=str(env_file),
        command_runner=run,
        host="192.0.2.10",
    )

    serialized = json.dumps(report)
    assert report["ready_to_run"] is True
    assert report["checks"]["server_env"]["env_file"] == str(env_file)
    assert report["checks"]["server_env"]["openai_api_key"] == "set"
    assert f"--env-file {env_file}" in report["commands"]["provider_preflight"]
    assert f"--env-file {env_file}" in report["commands"]["run_real_iphone_openai"]
    assert f"--env-file {env_file}" in report["commands"]["gate_f_resume"]
    assert "secret-from-hermes-env" not in serialized


def test_build_gate_f_preflight_report_accepts_redacted_provider_preflight_key_evidence(tmp_path):
    _write_openai_adapter(tmp_path)
    provider_preflight = tmp_path / "provider-openai.json"
    _write_provider_preflight_receipt(provider_preflight, key_state="set")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        provider_preflight_receipt="provider-openai.json",
        env={},
        command_runner=run,
        host="192.0.2.10",
    )

    serialized = json.dumps(report)
    assert report["ready_to_run"] is True
    assert report["missing_to_start"] == []
    assert report["missing_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert report["checks"]["server_env"]["openai_api_key"] == "set"
    assert report["checks"]["server_env"]["key_evidence"] == "provider_preflight_receipt"
    assert report["checks"]["provider_preflight_receipt"]["ok"] is True
    assert "secret" not in serialized


def test_build_gate_f_preflight_report_uses_physical_device_preflight_device_id(tmp_path):
    _write_openai_adapter(tmp_path)
    physical_device = tmp_path / "physical-device.json"
    physical_device.write_text(json.dumps({
        "ok": True,
        "status": "ready_via_cli_build",
        "device": {
            "ok": True,
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "iPhone 16 Plus",
            "state": "available (paired)",
        },
        "target_build": {
            "checked": True,
            "ok": True,
            "target": "AgentPocket",
            "configuration": "Debug",
            "sdk": "iphoneos",
        },
        "missing": [],
        "next_actions": [],
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        physical_device_preflight_receipt="physical-device.json",
        env={"OPENAI_API_KEY": "super-secret"},
        command_runner=run,
        host="192.0.2.10",
    )

    assert report["checks"]["physical_device_preflight"]["device"]["id"] == "00000000-0000-0000-0000-000000000000"
    assert "--device-id 00000000-0000-0000-0000-000000000000" in report["commands"]["run_real_iphone_openai"]
    assert "--device-id 00000000-0000-0000-0000-000000000000" in report["commands"]["gate_f_resume"]
    assert "<coredevice-id>" not in report["commands"]["run_real_iphone_openai"]


def test_build_gate_f_handoff_report_keeps_no_device_resume_actionable(tmp_path):
    simulator_only_resume = tmp_path / "simulator-only-resume.json"
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    _write_simulator_only_resume_receipt(simulator_only_resume, ok=True)
    gate_f_preflight.write_text(json.dumps({
        "ok": False,
        "ready_to_run": False,
        "missing_to_start": ["OPENAI_API_KEY"],
        "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
        "checks": {
            "endpoint": {
                "ok": True,
                "source": "explicit_host",
                "host": "192.0.2.10",
                "missing": [],
            },
        },
        "commands": {
            "hermes_auth_add_openai": (
                "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
            ),
            "provider_preflight": "provider-preflight --photo-provider openai",
            "gate_f_resume": "gate-f-resume --host 192.0.2.10",
            "verify_real_iphone_openai": "verify-receipt --file openai-photo-flow.json",
        },
        "start_blockers": [
            {
                "missing": "OPENAI_API_KEY",
                "label": "server-side OpenAI key proof (Hermes/provider runtime)",
                "iphone_required": False,
                "evidence_command": "provider-preflight --photo-provider openai",
            }
        ],
        "server_diagnostics": {
            "server_env": {
                "openai_api_key": "missing",
                "provider_source_args": "--hermes-profile dev-lead",
            },
            "provider_env_sources_receipt": {
                "selected_profile_state": "missing",
                "selected_gateway_processes": [
                    {
                        "source": "hermes_gateway_process",
                        "profile": "dev-lead",
                        "selected": True,
                        "pid": "87946",
                        "OPENAI_API_KEY": "missing",
                    }
                ],
            },
        },
    }), encoding="utf-8")

    report = build_gate_f_handoff_report(
        root=str(tmp_path),
        simulator_only_resume_receipt="simulator-only-resume.json",
        gate_f_preflight_receipt="gate-f-preflight.json",
    )

    assert report["phase"] == "gate-f-handoff"
    assert report["ok"] is True
    assert report["status"] == "handoff_ready_with_external_blockers"
    assert report["gate_f_closed"] is False
    assert report["gate_f_ready_to_run"] is False
    assert report["execution_mode"] == "local-mac-simulator-only"
    assert report["safe_without_physical_iphone"] is True
    assert report["physical_iphone_used"] is False
    assert report["physical_device_launch_attempted"] is False
    assert report["real_device_commands_executed"] == []
    assert report["remaining_to_start"] == ["OPENAI_API_KEY"]
    assert report["remaining_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert report["endpoint"] == {
        "ok": True,
        "source": "explicit_host",
        "host": "192.0.2.10",
        "missing": [],
    }
    assert report["start_blockers"][0]["iphone_required"] is False
    assert report["start_blockers"][0]["remediation_command"] == (
        "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
    )
    assert report["server_diagnostics"]["server_env"]["provider_source_args"] == "--hermes-profile dev-lead"
    assert report["server_diagnostics"]["provider_env_sources_receipt"]["selected_gateway_processes"][0]["pid"] == "87946"
    assert report["commands"]["gate_f_resume"] == "gate-f-resume --host 192.0.2.10"
    assert report["commands"]["hermes_auth_add_openai"] == (
        "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
    )
    assert report["next_actions"] == [
        "Add the OpenAI Images API key with hermes_auth_add_openai, then rerun provider_preflight.",
        "When the physical iPhone is available again, run gate_f_resume.",
    ]


def test_build_gate_audit_report_reads_gate_f_handoff_receipt(tmp_path):
    handoff = tmp_path / "gate-f-handoff.json"
    handoff.write_text(json.dumps({
        "phase": "gate-f-handoff",
        "ok": True,
        "status": "handoff_ready_with_external_blockers",
        "gate_f_closed": False,
        "gate_f_ready_to_run": False,
        "execution_mode": "local-mac-simulator-only",
        "safe_without_physical_iphone": True,
        "physical_iphone_used": False,
        "physical_device_launch_attempted": False,
        "real_device_commands_executed": [],
        "remaining_to_start": ["OPENAI_API_KEY"],
        "remaining_to_close": ["real iPhone OpenAI photo-flow receipt"],
        "endpoint": {"ok": True, "source": "explicit_host", "host": "192.0.2.10", "missing": []},
        "next_actions": [
            "Confirm OPENAI_API_KEY is available to the Hermes/mock bridge process and rerun provider_preflight."
        ],
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        gate_f_handoff_receipt="gate-f-handoff.json",
        env={},
        command_runner=run,
    )

    audit = report["external"]["gate_f_handoff"]
    assert audit["path"] == "gate-f-handoff.json"
    assert audit["ok"] is True
    assert audit["status"] == "handoff_ready_with_external_blockers"
    assert audit["execution_mode"] == "local-mac-simulator-only"
    assert audit["physical_iphone_used"] is False
    assert audit["physical_device_launch_attempted"] is False
    assert audit["remaining_to_start"] == ["OPENAI_API_KEY"]
    assert audit["remaining_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert report["commands"]["gate_f_handoff"].endswith("--receipt-file gate-f-handoff.json")


def test_build_gate_audit_report_reads_physical_device_preflight_receipt(tmp_path):
    receipt = tmp_path / "physical-device.json"
    receipt.write_text(json.dumps({
        "ok": False,
        "status": "blocked_by_xcode_device_support",
        "device": {
            "ok": True,
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "iPhone 16 Plus",
            "state": "available (paired)",
        },
        "xcode_destination": {
            "ok": False,
            "ineligible": [
                "{ platform:iOS, name:iPhone 16 Plus, error:iOS 26.5 is not installed. Please download and install the platform from Xcode > Settings > Components. }"
            ],
        },
        "missing": ["Xcode iOS device platform support"],
        "next_actions": [
            "Install the matching iOS platform from Xcode > Settings > Components, then rerun physical-device-preflight."
        ],
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        physical_device_preflight_receipt="physical-device.json",
        env={},
        command_runner=run,
    )

    audit = report["external"]["physical_device_preflight"]
    assert audit["path"] == "physical-device.json"
    assert audit["status"] == "blocked_by_xcode_device_support"
    assert audit["device"]["name"] == "iPhone 16 Plus"
    assert audit["missing"] == ["Xcode iOS device platform support"]
    assert "iOS 26.5 is not installed" in audit["ineligible"][0]
    assert report["commands"]["physical_device_preflight"].endswith("--receipt-file physical-device.json")


def test_build_gate_audit_report_does_not_block_gate_f_when_cli_physical_build_is_ready(tmp_path):
    receipt = tmp_path / "physical-device.json"
    receipt.write_text(json.dumps({
        "ok": True,
        "status": "ready_via_cli_build",
        "device": {
            "ok": True,
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "iPhone 16 Plus",
            "state": "available (paired)",
        },
        "xcode_destination": {
            "ok": False,
            "ineligible": [
                "{ platform:iOS, name:iPhone 16 Plus, error:iOS 26.5 is not installed. Please download and install the platform from Xcode > Settings > Components. }"
            ],
        },
        "target_build": {
            "checked": True,
            "ok": True,
            "configuration": "Debug",
            "sdk": "iphoneos",
        },
        "missing": [],
        "next_actions": [
            "Use the CLI run-lan or gate-f-resume path for real-device QA; install Xcode platform support only if you need the Xcode Run button."
        ],
    }), encoding="utf-8")

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_audit_report(
        root=str(tmp_path),
        physical_device_preflight_receipt="physical-device.json",
        env={},
        command_runner=run,
    )

    audit = report["external"]["physical_device_preflight"]
    assert audit["ok"] is True
    assert audit["status"] == "ready_via_cli_build"
    assert audit["target_build"]["ok"] is True
    assert "Xcode iOS device platform support" not in report["gates"]["F"]["missing"]


def test_build_gate_f_preflight_report_can_be_ready_to_run_without_leaking_secret(tmp_path):
    physical_receipt = tmp_path / "openai-photo-flow.json"
    _write_photo_flow_receipt(physical_receipt, provider="openai")
    _write_openai_adapter(tmp_path)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={"OPENAI_API_KEY": "super-secret"},
        command_runner=run,
    )

    serialized = json.dumps(report)
    assert report["ok"] is True
    assert report["ready_to_run"] is True
    assert report["missing_to_start"] == []
    assert report["missing_to_close"] == []
    assert report["checks"]["tailscale"]["cli"]["path"] == "/usr/local/bin/tailscale"
    assert report["checks"]["tailscale"]["ip_check"]["value"] == "100.101.102.103"
    assert "100.101.102.103" in report["commands"]["run_real_iphone_openai"]
    assert "gate-f-resume --port 8765 --device-id <coredevice-id>" in report["commands"]["gate_f_resume"]
    assert "--physical-openai-receipt openai-photo-flow.json" in report["commands"]["gate_f_resume"]
    assert "super-secret" not in serialized


def test_build_gate_f_preflight_report_uses_tailscale_cli_env_override(tmp_path):
    physical_receipt = tmp_path / "openai-photo-flow.json"
    _write_photo_flow_receipt(physical_receipt, provider="openai")
    _write_openai_adapter(tmp_path)
    calls = []
    tailscale_cli = "/Applications/Tailscale.app/Contents/MacOS/tailscale"

    def run(command):
        calls.append(tuple(command))
        if command == [tailscale_cli, "version"]:
            return CommandResult(returncode=0, stdout="1.80.0\n", stderr="")
        if command == [tailscale_cli, "ip", "-4"]:
            return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={
            "OPENAI_API_KEY": "super-secret",
            "TAILSCALE_CLI": tailscale_cli,
        },
        command_runner=run,
    )

    assert report["ok"] is True
    assert report["checks"]["tailscale"]["cli"]["path"] == tailscale_cli
    assert report["checks"]["tailscale"]["cli"]["configured_by"] == "TAILSCALE_CLI"
    assert report["checks"]["tailscale"]["ip_check"]["value"] == "100.101.102.103"
    assert ("which", "tailscale") not in calls
    assert (tailscale_cli, "version") in calls
    assert (tailscale_cli, "ip", "-4") in calls


def test_build_gate_f_preflight_report_requires_openai_adapter_file(tmp_path):
    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=0, stdout="100.101.102.103\n", stderr="")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={"OPENAI_API_KEY": "set"},
        command_runner=run,
    )

    assert report["ready_to_run"] is False
    assert report["checks"]["openai_provider"]["adapter"]["exists"] is False
    assert report["missing_to_start"] == ["OpenAI Photo Pack adapter"]


def test_build_gate_f_preflight_report_distinguishes_installed_tailscale_without_ip(tmp_path):
    _write_openai_adapter(tmp_path)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=0, stdout="/usr/local/bin/tailscale\n", stderr="")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=1, stdout="", stderr="not logged in")

    report = build_gate_f_preflight_report(
        root=str(tmp_path),
        physical_openai_receipt="openai-photo-flow.json",
        env={"OPENAI_API_KEY": "set"},
        command_runner=run,
    )

    assert report["checks"]["tailscale"]["cli"]["ok"] is True
    assert report["checks"]["tailscale"]["ip_check"]["ok"] is False
    assert report["checks"]["tailscale"]["ip_check"]["error"] == "not logged in"
    assert report["missing_to_start"] == ["Tailscale endpoint evidence"]


def test_cli_readiness_report_prints_and_writes_markdown(monkeypatch, tmp_path, capsys):
    (tmp_path / "docs/superpowers/specs").mkdir(parents=True)
    (tmp_path / "docs/mobile-bridge-api.md").write_text("# API\n")
    (tmp_path / "docs/superpowers/specs/2026-05-30-agent-pocket-photo-mvp-design.md").write_text("# Spec\n")
    simulator_connection = tmp_path / "connection.json"
    fixture_receipt = tmp_path / "fixture.json"
    script_receipt = tmp_path / "script.json"
    openai_receipt = tmp_path / "openai.json"
    fake_openai_status = tmp_path / "fake-openai.json"
    python_tests = tmp_path / "python-tests.json"
    swift_tests = tmp_path / "swift-tests.json"
    ui_test_preflight = tmp_path / "ui-test-preflight.json"
    simulator_suite = tmp_path / "simulator-suite.json"
    simulator_only_resume = tmp_path / "simulator-only-resume.json"
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    discovery_refresh_receipt = tmp_path / "discovery-refresh.json"
    discovery_refresh_screenshot = tmp_path / "discovery-refresh.png"
    picker_ui_screenshot = tmp_path / "picker-ui.png"
    capture_ready_receipt = tmp_path / "capture-ready.json"
    capture_ready_screenshot = tmp_path / "capture-ready.png"
    capture_completed_receipt = tmp_path / "capture-completed.json"
    capture_completed_screenshot = tmp_path / "capture-completed.png"
    result_gallery_receipt = tmp_path / "result-gallery.json"
    result_gallery_screenshot = tmp_path / "result-gallery.png"
    result_gallery_downloaded_receipt = tmp_path / "result-gallery-downloaded.json"
    result_gallery_downloaded_screenshot = tmp_path / "result-gallery-downloaded.png"
    output_file = tmp_path / "readiness.md"
    _write_connection_receipt(simulator_connection)
    _write_photo_flow_receipt(fixture_receipt, provider="fixture")
    _write_photo_flow_receipt(script_receipt, provider="script")
    _write_photo_flow_receipt(openai_receipt, provider="openai")
    _write_fake_openai_status(fake_openai_status)
    _write_test_receipt(python_tests, "python", ["python3", "-m", "pytest", "-q"])
    _write_test_receipt(swift_tests, "swift", ["swift", "test"])
    _write_ui_test_preflight_receipt(ui_test_preflight, ok=False)
    _write_simulator_suite_receipt(simulator_suite, ok=True)
    _write_simulator_only_resume_receipt(simulator_only_resume, ok=True)
    _write_gate_f_preflight_receipt(gate_f_preflight, ready_to_run=False)
    _write_discovery_refresh_receipt(discovery_refresh_receipt, ok=True)
    _write_capture_ready_receipt(capture_ready_receipt, ok=True)
    _write_capture_completed_receipt(capture_completed_receipt, ok=True)
    _write_result_gallery_receipt(result_gallery_receipt, ok=True)
    _write_result_gallery_downloaded_receipt(result_gallery_downloaded_receipt, ok=True)
    _write_visible_simulator_screenshot(discovery_refresh_screenshot)
    _write_visible_simulator_screenshot(picker_ui_screenshot)
    _write_visible_simulator_screenshot(capture_ready_screenshot)
    _write_visible_simulator_screenshot(capture_completed_screenshot)
    _write_visible_simulator_screenshot(result_gallery_screenshot)
    _write_visible_simulator_screenshot(result_gallery_downloaded_screenshot)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")
        return CommandResult(returncode=1, stdout="", stderr="not running")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "readiness-report",
        "--root",
        str(tmp_path),
        "--fixture-receipt",
        "fixture.json",
        "--script-receipt",
        "script.json",
        "--openai-receipt",
        "openai.json",
        "--fake-openai-status-file",
        "fake-openai.json",
        "--python-test-receipt",
        "python-tests.json",
        "--swift-test-receipt",
        "swift-tests.json",
        "--simulator-ui-test-preflight-receipt",
        "ui-test-preflight.json",
        "--simulator-suite-receipt",
        "simulator-suite.json",
        "--simulator-only-resume-receipt",
        "simulator-only-resume.json",
        "--gate-f-preflight-receipt",
        "gate-f-preflight.json",
        "--simulator-connection-receipt",
        "connection.json",
        "--discovery-refresh-receipt-file",
        "discovery-refresh.json",
        "--discovery-refresh-screenshot-file",
        "discovery-refresh.png",
        "--picker-ui-screenshot-file",
        "picker-ui.png",
        "--capture-ready-receipt-file",
        "capture-ready.json",
        "--capture-ready-screenshot-file",
        "capture-ready.png",
        "--capture-completed-receipt-file",
        "capture-completed.json",
        "--capture-completed-screenshot-file",
        "capture-completed.png",
        "--result-gallery-receipt-file",
        "result-gallery.json",
        "--result-gallery-screenshot-file",
        "result-gallery.png",
        "--result-gallery-downloaded-receipt-file",
        "result-gallery-downloaded.json",
        "--result-gallery-downloaded-screenshot-file",
        "result-gallery-downloaded.png",
        "--physical-openai-receipt",
        "physical-openai.json",
        "--output-file",
        str(output_file),
    ])

    printed = capsys.readouterr().out
    written = output_file.read_text()
    assert exit_code == 0
    assert "# Pocket Agent MVP Readiness" in printed
    assert "simulator_picker_ui_smoke" in printed
    assert printed == written
    assert "| C | passed | Swift core tests and connection parsing |  |" in written
    assert "Local Simulator UI Test Readiness" in written
    assert "Local Simulator Resume Evidence" in written
    assert "simulator-only-resume.json" in written
    assert "Physical device launch attempted: false" in written
    assert "Local Simulator Suite" in written
    assert "Local Simulator Artifacts" in written
    assert "Gate F External Preflight" in written
    assert "gate-f-preflight.json" in written
    assert "Suite status: passed" in written
    assert "capture-ready.png" in written
    assert "capture-completed.png" in written
    assert "result-gallery.png" in written
    assert "result-gallery-downloaded.png" in written
    assert "blocked_by_local_xcode_runtime" in written
    assert "- Tailscale CLI: missing (tailscale CLI not found in PATH)" in written
    assert "Gate F remains open" in written


def test_cli_gate_f_preflight_prints_json(monkeypatch, tmp_path, capsys):
    _write_openai_adapter(tmp_path)
    receipt_path = tmp_path / "gate-f-preflight.json"

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        assert command == ["tailscale", "ip", "-4"]
        return CommandResult(returncode=1, stdout="", stderr="not running")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "gate-f-preflight",
        "--root",
        str(tmp_path),
        "--physical-openai-receipt",
        "openai-photo-flow.json",
        "--receipt-file",
        str(receipt_path),
    ])

    output = json.loads(capsys.readouterr().out)
    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert output["ready_to_run"] is False
    assert output["missing_to_start"] == ["OPENAI_API_KEY", "Tailscale endpoint evidence"]
    assert receipt == output


def test_cli_gate_f_preflight_reads_env_file_without_leaking_secret(monkeypatch, tmp_path, capsys):
    _write_openai_adapter(tmp_path)
    env_file = tmp_path / "hermes.env"
    env_file.write_text("OPENAI_API_KEY=secret-from-hermes-env\n", encoding="utf-8")
    receipt_path = tmp_path / "gate-f-preflight.json"

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "gate-f-preflight",
        "--root",
        str(tmp_path),
        "--host",
        "192.0.2.10",
        "--physical-openai-receipt",
        "openai-photo-flow.json",
        "--env-file",
        str(env_file),
        "--receipt-file",
        str(receipt_path),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ready_to_run"] is True
    assert output["checks"]["openai_api_key"] == "set"
    assert output["missing_to_start"] == []
    assert "secret-from-hermes-env" not in output_text
    assert "secret-from-hermes-env" not in receipt_path.read_text()


def test_cli_gate_f_provider_check_refreshes_provider_receipts_without_leaking_secret(monkeypatch, tmp_path, capsys):
    _write_openai_adapter(tmp_path)
    hermes_home = tmp_path / "hermes"
    profile_root = hermes_home / "profiles" / "dev-lead"
    profile_root.mkdir(parents=True)
    (profile_root / ".env").write_text(
        "OPENAI_API_KEY=secret-from-hermes-profile\n"
        "OPENAI_BASE_URL=https://api.example.test/v1\n",
        encoding="utf-8",
    )
    provider_env_sources_receipt = tmp_path / "provider-env-sources.json"
    provider_env_sources_all_receipt = tmp_path / "provider-env-sources-all.json"
    provider_preflight_receipt = tmp_path / "provider-preflight.json"
    gate_f_receipt = tmp_path / "gate-f-preflight.json"
    readiness = tmp_path / "readiness.md"

    def run(command):
        if command == ["launchctl", "getenv", "OPENAI_API_KEY"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["ps", "eww", "-axo", "pid=,args="]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["hermes", "--profile", "dev-lead", "auth", "list"]:
            return CommandResult(returncode=0, stdout="", stderr="")
        if command == ["hermes", "--profile", "dev-lead", "auth", "status", "openai"]:
            return CommandResult(returncode=0, stdout="openai: logged out\n", stderr="")
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main([
        "gate-f-provider-check",
        "--root",
        str(tmp_path),
        "--host",
        "192.0.2.10",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
        "--provider-env-sources-receipt",
        str(provider_env_sources_receipt),
        "--provider-env-sources-all-profiles-receipt",
        str(provider_env_sources_all_receipt),
        "--provider-preflight-receipt",
        str(provider_preflight_receipt),
        "--gate-f-preflight-receipt",
        str(gate_f_receipt),
        "--readiness-output-file",
        str(readiness),
    ])

    stdout = capsys.readouterr().out
    output = json.loads(stdout)
    assert exit_code == 0
    assert output["phase"] == "gate-f-provider-check"
    assert output["status"] == "ready_to_run"
    assert output["provider_ready"] is True
    assert output["ready_to_run"] is True
    assert output["provider_env_sources"]["env"]["OPENAI_API_KEY"] == "set"
    assert output["provider_preflight"]["env"]["OPENAI_API_KEY"] == "set"
    assert output["gate_f_preflight"]["missing_to_start"] == []
    assert output["gate_f_preflight"]["missing_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert output["receipts"]["provider_preflight"] == str(provider_preflight_receipt)
    assert output["receipts"]["readiness_report"] == str(readiness)
    assert "gate-f-resume --host 192.0.2.10" in output["commands"]["gate_f_resume"]
    combined = "\n".join([
        stdout,
        provider_env_sources_receipt.read_text(),
        provider_env_sources_all_receipt.read_text(),
        provider_preflight_receipt.read_text(),
        gate_f_receipt.read_text(),
        readiness.read_text(),
    ])
    assert "secret-from-hermes-profile" not in combined
    assert "https://api.example.test/v1" in combined


def test_cli_gate_f_preflight_reads_hermes_profile_env_without_leaking_secret(monkeypatch, tmp_path, capsys):
    _write_openai_adapter(tmp_path)
    hermes_home = tmp_path / ".hermes"
    profile_root = _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="OPENAI_API_KEY=secret-from-hermes-profile\n",
    )
    receipt_path = tmp_path / "gate-f-preflight.json"

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "gate-f-preflight",
        "--root",
        str(tmp_path),
        "--host",
        "192.0.2.10",
        "--photo-pack-root",
        str(tmp_path / "photo-pack"),
        "--physical-openai-receipt",
        "openai-photo-flow.json",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
        "--receipt-file",
        str(receipt_path),
    ])

    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert exit_code == 0
    assert output["ready_to_run"] is True
    assert output["checks"]["openai_api_key"] == "set"
    assert output["checks"]["server_env"]["env_file"] == str(profile_root / ".env")
    assert output["checks"]["server_env"]["key_evidence"] == "environment"
    assert output["missing_to_start"] == []
    assert "--hermes-profile dev-lead" in output["commands"]["provider_preflight"]
    assert "--hermes-profile dev-lead" in output["commands"]["run_real_iphone_openai"]
    assert "--hermes-profile dev-lead" in output["commands"]["gate_f_resume"]
    assert "secret-from-hermes-profile" not in output_text
    assert "secret-from-hermes-profile" not in receipt_path.read_text(encoding="utf-8")


def test_run_test_receipt_command_runs_command_and_writes_redacted_receipt(tmp_path):
    receipt_path = tmp_path / "test-receipt.json"
    calls = []

    def run(command):
        calls.append(command)
        return CommandResult(
            returncode=0,
            stdout="line 1\nall tests passed\n",
            stderr="",
        )

    exit_code = run_test_receipt_command(
        name="swift",
        command=["swift", "test"],
        receipt_file=str(receipt_path),
        command_runner=run,
        out=StringIO(),
        err=StringIO(),
    )

    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert calls == [["swift", "test"]]
    assert receipt["phase"] == "test-command"
    assert receipt["name"] == "swift"
    assert receipt["command"] == ["swift", "test"]
    assert receipt["ok"] is True
    assert receipt["returncode"] == 0
    assert receipt["stdout_tail"] == "line 1\nall tests passed\n"


def test_cli_gate_audit_prints_json(monkeypatch, tmp_path, capsys):
    (tmp_path / "docs/superpowers/specs").mkdir(parents=True)
    (tmp_path / "docs/mobile-bridge-api.md").write_text("# API\n")
    (tmp_path / "docs/superpowers/specs/2026-05-30-agent-pocket-photo-mvp-design.md").write_text("# Spec\n")
    simulator_connection = tmp_path / "connection.json"
    fixture_receipt = tmp_path / "fixture.json"
    script_receipt = tmp_path / "script.json"
    openai_receipt = tmp_path / "openai.json"
    fake_openai_status = tmp_path / "fake-openai.json"
    python_tests = tmp_path / "python-tests.json"
    swift_tests = tmp_path / "swift-tests.json"
    ui_test_preflight = tmp_path / "ui-test-preflight.json"
    simulator_suite = tmp_path / "simulator-suite.json"
    simulator_only_resume = tmp_path / "simulator-only-resume.json"
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    discovery_refresh_receipt = tmp_path / "discovery-refresh.json"
    discovery_refresh_screenshot = tmp_path / "discovery-refresh.png"
    picker_ui_screenshot = tmp_path / "picker-ui.png"
    capture_ready_receipt = tmp_path / "capture-ready.json"
    capture_ready_screenshot = tmp_path / "capture-ready.png"
    capture_completed_receipt = tmp_path / "capture-completed.json"
    capture_completed_screenshot = tmp_path / "capture-completed.png"
    result_gallery_receipt = tmp_path / "result-gallery.json"
    result_gallery_screenshot = tmp_path / "result-gallery.png"
    result_gallery_downloaded_receipt = tmp_path / "result-gallery-downloaded.json"
    result_gallery_downloaded_screenshot = tmp_path / "result-gallery-downloaded.png"
    _write_connection_receipt(simulator_connection)
    _write_photo_flow_receipt(fixture_receipt, provider="fixture")
    _write_photo_flow_receipt(script_receipt, provider="script")
    _write_photo_flow_receipt(openai_receipt, provider="openai")
    _write_fake_openai_status(fake_openai_status)
    _write_test_receipt(
        python_tests,
        "python",
        ["python3", "-m", "pytest", "mock_bridge/tests", "photo-pack/tests", "ios/tests", "-q"],
    )
    _write_test_receipt(swift_tests, "swift", ["swift", "test"])
    _write_ui_test_preflight_receipt(ui_test_preflight, ok=False)
    _write_simulator_suite_receipt(simulator_suite, ok=True)
    _write_simulator_only_resume_receipt(simulator_only_resume, ok=True)
    _write_gate_f_preflight_receipt(gate_f_preflight, ready_to_run=False)
    _write_discovery_refresh_receipt(discovery_refresh_receipt, ok=True)
    _write_capture_ready_receipt(capture_ready_receipt, ok=True)
    _write_capture_completed_receipt(capture_completed_receipt, ok=True)
    _write_result_gallery_receipt(result_gallery_receipt, ok=True)
    _write_result_gallery_downloaded_receipt(result_gallery_downloaded_receipt, ok=True)
    _write_visible_simulator_screenshot(discovery_refresh_screenshot)
    _write_visible_simulator_screenshot(picker_ui_screenshot)
    _write_visible_simulator_screenshot(capture_ready_screenshot)
    _write_visible_simulator_screenshot(capture_completed_screenshot)
    _write_visible_simulator_screenshot(result_gallery_screenshot)
    _write_visible_simulator_screenshot(result_gallery_downloaded_screenshot)

    def run(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")
        return CommandResult(returncode=1, stdout="", stderr="not running")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "gate-audit",
        "--root",
        str(tmp_path),
        "--simulator-connection-receipt",
        "connection.json",
        "--fixture-receipt",
        "fixture.json",
        "--script-receipt",
        "script.json",
        "--openai-receipt",
        "openai.json",
        "--fake-openai-status-file",
        "fake-openai.json",
        "--python-test-receipt",
        "python-tests.json",
        "--swift-test-receipt",
        "swift-tests.json",
        "--simulator-ui-test-preflight-receipt",
        "ui-test-preflight.json",
        "--simulator-suite-receipt",
        "simulator-suite.json",
        "--simulator-only-resume-receipt",
        "simulator-only-resume.json",
        "--gate-f-preflight-receipt",
        "gate-f-preflight.json",
        "--discovery-refresh-receipt-file",
        "discovery-refresh.json",
        "--discovery-refresh-screenshot-file",
        "discovery-refresh.png",
        "--picker-ui-screenshot-file",
        "picker-ui.png",
        "--capture-ready-receipt-file",
        "capture-ready.json",
        "--capture-ready-screenshot-file",
        "capture-ready.png",
        "--capture-completed-receipt-file",
        "capture-completed.json",
        "--capture-completed-screenshot-file",
        "capture-completed.png",
        "--result-gallery-receipt-file",
        "result-gallery.json",
        "--result-gallery-screenshot-file",
        "result-gallery.png",
        "--result-gallery-downloaded-receipt-file",
        "result-gallery-downloaded.json",
        "--result-gallery-downloaded-screenshot-file",
        "result-gallery-downloaded.png",
        "--physical-openai-receipt",
        "physical-openai.json",
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["summary"]["simulator_evidence_ok"] is True
    assert output["gates"]["F"]["status"] == "missing_external_evidence"
    assert output["gates"]["C"]["status"] == "passed"
    assert output["external"]["gate_f_preflight"]["status"] == "blocked_to_start"
    assert output["local"]["simulator_suite"]["status"] == "passed"
    assert output["local"]["simulator_only_resume"]["path"] == "simulator-only-resume.json"
    assert output["local"]["simulator_only_resume"]["ok"] is True
    assert output["local"]["simulator_only_resume"]["physical_device_launch_attempted"] is False
    assert output["local"]["simulator_artifacts"]["discovery_refresh_receipt"]["ok"] is True
    assert output["local"]["simulator_artifacts"]["discovery_refresh_screenshot"]["exists"] is True
    assert output["local"]["simulator_artifacts"]["capture_ready_receipt"]["ok"] is True
    assert output["local"]["simulator_artifacts"]["capture_ready_screenshot"]["exists"] is True
    assert output["local"]["simulator_artifacts"]["capture_completed_receipt"]["ok"] is True
    assert output["local"]["simulator_artifacts"]["capture_completed_screenshot"]["exists"] is True
    assert output["local"]["simulator_artifacts"]["result_gallery_receipt"]["ok"] is True
    assert output["local"]["simulator_artifacts"]["result_gallery_screenshot"]["exists"] is True
    assert output["local"]["simulator_artifacts"]["result_gallery_downloaded_receipt"]["ok"] is True
    assert output["local"]["simulator_artifacts"]["result_gallery_downloaded_screenshot"]["exists"] is True
    assert output["local"]["simulator_ui_test_preflight"]["status"] == "blocked_by_local_xcode_runtime"


def test_cli_test_receipt_writes_json(monkeypatch, tmp_path, capsys):
    receipt_path = tmp_path / "python-tests.json"

    def run(command, timeout_seconds=10):
        assert command == ["python3", "-m", "pytest", "-q"]
        assert timeout_seconds == 300
        return CommandResult(returncode=0, stdout="passed\n", stderr="")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main([
        "test-receipt",
        "--name",
        "python",
        "--receipt-file",
        str(receipt_path),
        "--",
        "python3",
        "-m",
        "pytest",
        "-q",
    ])

    output = json.loads(capsys.readouterr().out)
    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert output["ok"] is True
    assert receipt["command"] == ["python3", "-m", "pytest", "-q"]


def test_cli_verify_receipt_accepts_expected_photo_provider(tmp_path, capsys):
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps({
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://127.0.0.1:8766",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "script"}},
            "provider": {"name": "script"},
        },
    }))

    exit_code = main([
        "verify-receipt",
        "--file",
        str(receipt_path),
        "--phase",
        "photo-flow",
        "--photo-provider",
        "script",
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True


def test_cli_simulator_preflight_prints_json(monkeypatch, tmp_path, capsys):
    app_path = tmp_path / "AgentPocket.app"
    app_path.mkdir()

    def run(command):
        if command == ["xcrun", "simctl", "list", "devices", "available"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "devices", "booted"]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "== Devices ==\n"
                    "-- iOS 26.1 --\n"
                    "    iPhone 17 (053743B2-A12B-4C6A-99CC-F46108333560) (Booted)\n"
                ),
                stderr="",
            )
        if command == ["xcrun", "--find", "simctl"]:
            return CommandResult(returncode=0, stdout="/usr/bin/simctl\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main([
        "simulator-preflight",
        "--app-path",
        str(app_path),
        "--port",
        "8766",
        "--gate-f-host",
        "192.0.2.10",
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["booted"]["id"] == "053743B2-A12B-4C6A-99CC-F46108333560"
    assert "CODE_SIGNING_ALLOWED=NO" not in output["commands"]["build"]
    assert "--port 8766" in output["commands"]["local_connection"]
    assert "simulator-connection-smoke" in output["commands"]["connection_smoke_session"]
    assert "simulator-connection-latest.json" in output["commands"]["connection_smoke_session"]
    assert "--agent-pocket-simulator-smoke" in output["commands"]["smoke_launch"]
    assert "simulator-photo-flow-smoke.json" in output["commands"]["smoke_session"]
    assert "simulator-openai-smoke" in output["commands"]["openai_smoke_session"]
    assert "--screenshot-file /tmp/agent-pocket-simulator-openai-provider-smoke.png" in output["commands"]["openai_smoke_session"]
    assert "simulator-seed-photo-library" in output["commands"]["seed_photo_library"]
    assert "/tmp/agent-pocket-simulator-library-fixture.png" in output["commands"]["seed_photo_library"]
    assert "simulator-picker-ui-smoke" in output["commands"]["picker_ui_smoke"]
    assert "/tmp/agent-pocket-simulator-picker-ui-smoke.png" in output["commands"]["picker_ui_smoke"]
    assert "simulator-result-gallery-downloaded-smoke" in output["commands"]["result_gallery_downloaded_smoke"]
    assert "/tmp/agent-pocket-simulator-result-gallery-downloaded.png" in output["commands"]["result_gallery_downloaded_smoke"]
    assert "simulator-capture-completed-smoke" in output["commands"]["capture_completed_smoke"]
    assert "/tmp/agent-pocket-simulator-capture-completed.png" in output["commands"]["capture_completed_smoke"]
    assert output["commands"]["ui_test_preflight"].endswith(
        "simulator-ui-test-preflight --receipt-file docs/qa-receipts/simulator-ui-test-preflight-latest.json"
    )
    assert output["commands"]["simulator_only_resume"].endswith(
        "simulator-only-resume --suite-receipt-file docs/qa-receipts/simulator-suite-latest.json "
        "--gate-f-preflight-receipt docs/qa-receipts/gate-f-preflight-latest.json "
        "--gate-f-host 192.0.2.10 "
        "--resume-receipt-file docs/qa-receipts/simulator-only-resume-latest.json "
        "--readiness-output-file docs/agent-pocket-readiness.md"
    )


def test_cli_simulator_ui_test_preflight_prints_json_and_writes_receipt(monkeypatch, tmp_path, capsys):
    receipt_path = tmp_path / "ui-test-preflight.json"

    def run(command):
        if command == ["xcodebuild", "-showsdks"]:
            return CommandResult(
                returncode=0,
                stdout="iOS Simulator SDKs:\n\tSimulator - iOS 26.5          \t-sdk iphonesimulator26.5\n",
                stderr="",
            )
        if command == ["xcrun", "simctl", "list", "runtimes"]:
            return CommandResult(
                returncode=0,
                stdout="== Runtimes ==\niOS 26.1 (26.1 - 23B86) - com.apple.CoreSimulator.SimRuntime.iOS-26-1\n",
                stderr="",
            )
        if command == [
            "xcodebuild",
            "-showdestinations",
            "-project",
            "ios/AgentPocket.xcodeproj",
            "-scheme",
            "AgentPocket",
            "-sdk",
            "iphonesimulator",
        ]:
            return CommandResult(
                returncode=0,
                stdout=(
                    "Ineligible destinations for the \"AgentPocket\" scheme:\n"
                    "\t{ platform:iOS, name:Any iOS Device, error:iOS 26.5 is not installed. }\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run)

    exit_code = main(["simulator-ui-test-preflight", "--receipt-file", str(receipt_path)])

    output = json.loads(capsys.readouterr().out)
    receipt = json.loads(receipt_path.read_text())
    assert exit_code == 0
    assert output["ok"] is False
    assert output["sdk"]["latest"] == "26.5"
    assert output["runtime"]["latest"] == "26.1"
    assert "iOS 26.5 is not installed" in output["destinations"]["ineligible"][0]
    assert receipt == output


def test_cli_simulator_suite_prints_json(monkeypatch, tmp_path, capsys):
    suite_receipt = tmp_path / "suite.json"
    ui_preflight_receipt = tmp_path / "ui-preflight.json"

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.build_simulator_ui_test_preflight_report",
        lambda **kwargs: {"ok": True, "mismatch": {"ok": True}, "destinations": {"ok": True}},
    )
    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_seed_photo_library",
        lambda device, image_file: {"ok": True, "device": device, "image_file": image_file},
    )
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_connection_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_discovery_refresh_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_picker_ui_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_capture_ready_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_capture_completed_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_result_gallery_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_result_gallery_downloaded_session", lambda **kwargs: 0)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_openai_compatible_simulator_session", lambda **kwargs: 0)

    exit_code = main([
        "simulator-suite",
        "--suite-receipt-file",
        str(suite_receipt),
        "--simulator-ui-test-preflight-receipt",
        str(ui_preflight_receipt),
        "--connection-port",
        "8766",
        "--openai-port",
        "8769",
        "--fake-openai-port",
        "8781",
    ])

    output = json.loads(capsys.readouterr().out)
    receipt = json.loads(suite_receipt.read_text())
    ui_receipt = json.loads(ui_preflight_receipt.read_text())
    assert exit_code == 0
    assert output["ok"] is True
    assert output["steps"]["connection_smoke"]["ok"] is True
    assert output["steps"]["discovery_refresh_smoke"]["ok"] is True
    assert output["steps"]["capture_completed_smoke"]["ok"] is True
    assert output["steps"]["result_gallery_smoke"]["ok"] is True
    assert output["steps"]["result_gallery_downloaded_smoke"]["ok"] is True
    assert output == receipt
    assert ui_receipt["ok"] is True


def test_cli_simulator_only_resume_refreshes_suite_gate_f_and_readiness(monkeypatch, tmp_path, capsys):
    suite_receipt = tmp_path / "suite.json"
    gate_f_receipt = tmp_path / "gate-f.json"
    resume_receipt = tmp_path / "simulator-only-resume.json"
    readiness_report = tmp_path / "readiness.md"
    hermes_home = tmp_path / "hermes"
    hermes_profile_root = hermes_home / "profiles" / "dev-lead"
    hermes_profile_root.mkdir(parents=True)
    (hermes_profile_root / ".env").write_text(
        "OPENAI_API_KEY=secret-from-simulator-resume\n"
        "OPENAI_BASE_URL=https://api.example.test/v1\n",
        encoding="utf-8",
    )
    calls = {}

    def run_suite(**kwargs):
        calls["suite"] = kwargs
        return {
            "ok": True,
            "phase": "simulator-suite",
            "failed_required_steps": [],
            "steps": {"connection_smoke": {"ok": True, "required": True}},
        }

    def build_gate_f(**kwargs):
        calls["gate_f"] = kwargs
        return {
            "ok": False,
            "ready_to_run": False,
            "missing_to_start": ["OPENAI_API_KEY"],
            "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
        }

    def build_audit(**kwargs):
        calls["audit"] = kwargs
        return {
            "summary": {
                "simulator_evidence_ok": True,
                "gate_f_ok": False,
                "remaining_external": ["OPENAI_API_KEY"],
            }
        }

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_simulator_suite", run_suite)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_gate_f_preflight_report", build_gate_f)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_gate_audit_report", build_audit)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_readiness_markdown", lambda report: "# Readiness\n")

    exit_code = main([
        "simulator-only-resume",
        "--suite-receipt-file",
        str(suite_receipt),
        "--gate-f-preflight-receipt",
        str(gate_f_receipt),
        "--resume-receipt-file",
        str(resume_receipt),
        "--readiness-output-file",
        str(readiness_report),
        "--connection-port",
        "8766",
        "--gate-f-port",
        "8765",
        "--gate-f-host",
        "192.0.2.10",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    stdout = capsys.readouterr().out
    assert "secret-from-simulator-resume" not in stdout
    output = json.loads(stdout)
    gate_f = json.loads(gate_f_receipt.read_text())
    resume = json.loads(resume_receipt.read_text())
    assert exit_code == 0
    assert output["ok"] is True
    assert output["phase"] == "simulator-only-resume"
    assert output["execution_mode"] == "local-mac-simulator-only"
    assert output["physical_iphone_used"] is False
    assert output["physical_device_launch_attempted"] is False
    assert output["real_device_commands_executed"] == []
    assert output["resume_receipt"]["path"] == str(resume_receipt)
    assert output["resume_receipt"]["written"] is True
    assert output["gate_f_preflight"]["missing_to_start"] == ["OPENAI_API_KEY"]
    assert resume == output
    assert output["readiness_report"]["path"] == str(readiness_report)
    assert gate_f["missing_to_close"] == ["real iPhone OpenAI photo-flow receipt"]
    assert readiness_report.read_text() == "# Readiness\n"
    assert calls["suite"]["connection_port"] == 8766
    assert calls["gate_f"]["port"] == 8765
    assert calls["gate_f"]["host"] == "192.0.2.10"
    assert calls["gate_f"]["env"]["OPENAI_API_KEY"] == "secret-from-simulator-resume"
    assert calls["gate_f"]["env"]["OPENAI_BASE_URL"] == "https://api.example.test/v1"
    assert calls["gate_f"]["env_file"] == str(hermes_profile_root / ".env")
    assert f"--hermes-home {hermes_home}" in calls["gate_f"]["provider_source_args"]
    assert "--hermes-profile dev-lead" in calls["gate_f"]["provider_source_args"]
    assert calls["audit"]["simulator_suite_receipt"] == str(suite_receipt)
    assert calls["audit"]["gate_f_preflight_receipt"] == str(gate_f_receipt)
    assert calls["audit"]["env"]["OPENAI_API_KEY"] == "secret-from-simulator-resume"
    assert calls["audit"]["provider_source_args"] == calls["gate_f"]["provider_source_args"]
    assert output["provider_source"]["args"] == calls["gate_f"]["provider_source_args"]
    assert output["provider_source"]["hermes"]["profile"] == "dev-lead"


def test_cli_gate_f_resume_stops_before_launch_when_external_preflight_missing(monkeypatch, tmp_path, capsys):
    gate_f_receipt = tmp_path / "gate-f.json"
    physical_receipt = tmp_path / "openai-photo-flow.json"
    calls = []
    preflight_calls = {}

    def build_gate_f(**kwargs):
        preflight_calls.update(kwargs)
        return {
            "ok": False,
            "ready_to_run": False,
            "missing_to_start": ["OPENAI_API_KEY", "Tailscale endpoint evidence"],
            "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
            "checks": {
                "tailscale": {"ip": ""},
                "server_env": {
                    "openai_api_key": "missing",
                    "provider_source_args": "--hermes-profile dev-lead",
                },
                "provider_preflight_receipt": {
                    "exists": True,
                    "ok": False,
                    "status": "missing_provider_evidence",
                    "env": {"OPENAI_API_KEY": "missing"},
                },
                "provider_env_sources_receipt": {
                    "exists": True,
                    "ok": False,
                    "status": "missing_provider_env_source",
                    "hermes": {
                        "selected_profile_state": "missing",
                        "gateway_processes": [
                            {
                                "profile": "dev-lead",
                                "pid": "87946",
                                "selected": True,
                                "OPENAI_API_KEY": "missing",
                            }
                        ],
                    },
                },
            },
            "commands": {
                "provider_preflight": "provider-preflight --photo-provider openai --hermes-profile dev-lead",
                "hermes_auth_add_openai": (
                    "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
                ),
            },
        }

    def run_lan(**kwargs):
        calls.append(kwargs)
        raise AssertionError("gate-f-resume must not launch before preflight is ready")

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_gate_f_preflight_report", build_gate_f)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_lan_qa_session", run_lan)

    exit_code = main([
        "gate-f-resume",
        "--device-id",
        "coredevice-id",
        "--gate-f-preflight-receipt",
        str(gate_f_receipt),
        "--physical-openai-receipt",
        str(physical_receipt),
        "--hermes-profile",
        "dev-lead",
    ])

    output = json.loads(capsys.readouterr().err)
    saved_preflight = json.loads(gate_f_receipt.read_text())
    assert exit_code == 1
    assert output["phase"] == "gate-f-resume"
    assert output["ok"] is False
    assert output["status"] == "blocked_to_start"
    assert output["launched"] is False
    assert output["verified"] is False
    assert output["provider_source"]["args"] == "--hermes-profile dev-lead"
    assert output["provider_source"]["hermes"]["profile"] == "dev-lead"
    assert preflight_calls["provider_source_args"] == "--hermes-profile dev-lead"
    assert output["missing_to_start"] == ["OPENAI_API_KEY", "Tailscale endpoint evidence"]
    assert output["start_blockers"][0]["label"] == "server-side OpenAI key proof (Hermes/provider runtime)"
    assert output["start_blockers"][0]["iphone_required"] is False
    assert "iPhone never stores or calls OPENAI_API_KEY" in output["start_blockers"][0]["message"]
    assert output["start_blockers"][0]["remediation_command"] == (
        "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
    )
    assert output["start_blockers"][0]["evidence_command"] == "provider-preflight --photo-provider openai --hermes-profile dev-lead"
    assert output["commands"]["hermes_auth_add_openai"] == (
        "hermes --profile dev-lead auth add openai --type api-key --label agent-pocket-openai-images"
    )
    assert output["commands"]["provider_preflight"] == "provider-preflight --photo-provider openai --hermes-profile dev-lead"
    assert output["next_actions"] == [
        "Add the OpenAI Images API key with hermes_auth_add_openai, then rerun provider_preflight.",
        "Provide a reachable Mac LAN host or Tailscale endpoint, then rerun gate_f_preflight.",
    ]
    assert output["server_diagnostics"]["server_env"]["openai_api_key"] == "missing"
    assert output["server_diagnostics"]["provider_env_sources_receipt"]["selected_profile_state"] == "missing"
    assert output["server_diagnostics"]["provider_env_sources_receipt"]["selected_gateway_processes"][0]["pid"] == "87946"
    assert saved_preflight["ready_to_run"] is False
    assert calls == []


def test_cli_gate_f_handoff_writes_receipt_without_physical_iphone(tmp_path, capsys):
    simulator_only_resume = tmp_path / "simulator-only-resume.json"
    gate_f_preflight = tmp_path / "gate-f-preflight.json"
    handoff_receipt = tmp_path / "gate-f-handoff.json"
    _write_simulator_only_resume_receipt(simulator_only_resume, ok=True)
    gate_f_preflight.write_text(json.dumps({
        "ok": False,
        "ready_to_run": False,
        "missing_to_start": ["OPENAI_API_KEY"],
        "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
        "checks": {
            "endpoint": {
                "ok": True,
                "source": "explicit_host",
                "host": "192.0.2.10",
                "missing": [],
            },
        },
        "commands": {
            "provider_preflight": "provider-preflight --photo-provider openai",
            "gate_f_resume": "gate-f-resume --host 192.0.2.10",
        },
    }), encoding="utf-8")

    exit_code = main([
        "gate-f-handoff",
        "--root",
        str(tmp_path),
        "--simulator-only-resume-receipt",
        "simulator-only-resume.json",
        "--gate-f-preflight-receipt",
        "gate-f-preflight.json",
        "--receipt-file",
        str(handoff_receipt),
    ])

    output = json.loads(capsys.readouterr().out)
    saved = json.loads(handoff_receipt.read_text())
    assert exit_code == 0
    assert output["ok"] is True
    assert output["physical_iphone_used"] is False
    assert output["physical_device_launch_attempted"] is False
    assert output["real_device_commands_executed"] == []
    assert saved == output


def test_cli_gate_f_resume_runs_real_openai_flow_and_verifies_receipt(monkeypatch, tmp_path, capsys):
    gate_f_receipt = tmp_path / "gate-f.json"
    physical_receipt = tmp_path / "openai-photo-flow.json"
    calls = []

    def build_gate_f(**kwargs):
        return {
            "ok": False,
            "ready_to_run": True,
            "missing_to_start": [],
            "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
            "checks": {"tailscale": {"ip": "100.101.102.103"}},
        }

    def run_lan(**kwargs):
        calls.append(kwargs)
        status = {
            "requests": {"asset_upload": 1, "photo_task_create": 1, "asset_download": 1},
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "openai"}},
            "provider": {"name": "openai"},
        }
        with open(kwargs["receipt_file"], "w", encoding="utf-8") as handle:
            json.dump({
                "phase": "photo-flow",
                "ok": True,
                "missing": [],
                "base_url": "http://100.101.102.103:8765",
                "status": status,
            }, handle)
        return 0

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_gate_f_preflight_report", build_gate_f)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_lan_qa_session", run_lan)

    exit_code = main([
        "gate-f-resume",
        "--device-id",
        "coredevice-id",
        "--gate-f-preflight-receipt",
        str(gate_f_receipt),
        "--physical-openai-receipt",
        str(physical_receipt),
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["phase"] == "gate-f-resume"
    assert output["status"] == "verified"
    assert output["host"] == "100.101.102.103"
    assert output["launched"] is True
    assert output["verified"] is True
    assert output["verification"]["ok"] is True
    assert calls[0]["host"] == "100.101.102.103"
    assert calls[0]["device_id"] == "coredevice-id"
    assert calls[0]["advertise_bonjour"] is False
    assert calls[0]["photo_provider"] == "openai"
    assert calls[0]["receipt_file"] == str(physical_receipt)


def test_run_gate_f_resume_loads_env_file_for_openai_bridge_without_leaking_secret(monkeypatch, tmp_path):
    _write_openai_adapter(tmp_path)
    env_file = tmp_path / "hermes.env"
    env_file.write_text("OPENAI_API_KEY=secret-from-hermes-env\n", encoding="utf-8")
    gate_f_receipt = tmp_path / "gate-f.json"
    physical_receipt = tmp_path / "openai-photo-flow.json"
    calls = []

    def run_command(command):
        if command == ["which", "tailscale"]:
            return CommandResult(returncode=1, stdout="", stderr="not installed")
        raise AssertionError(f"unexpected command: {command}")

    def run_lan(**kwargs):
        calls.append({
            "kwargs": kwargs,
            "env_key_visible": os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-env",
        })
        status = {
            "requests": {"asset_upload": 1, "photo_task_create": 1, "asset_download": 1},
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "openai"}},
            "provider": {"name": "openai"},
        }
        with open(kwargs["receipt_file"], "w", encoding="utf-8") as handle:
            json.dump({
                "phase": "photo-flow",
                "ok": True,
                "missing": [],
                "base_url": "http://192.0.2.10:8765",
                "status": status,
            }, handle)
        return 0

    monkeypatch.setattr("agent_pocket_mock_bridge.qa._run_command", run_command)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_lan_qa_session", run_lan)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = run_gate_f_resume(
        root=str(tmp_path),
        host="192.0.2.10",
        device_id="coredevice-id",
        gate_f_preflight_receipt=str(gate_f_receipt),
        physical_openai_receipt=str(physical_receipt),
        env_file=str(env_file),
    )

    serialized = json.dumps(report) + gate_f_receipt.read_text() + physical_receipt.read_text()
    assert report["ok"] is True
    assert report["status"] == "verified"
    assert calls[0]["env_key_visible"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert "secret-from-hermes-env" not in serialized


def test_cli_gate_f_resume_allows_explicit_host_as_endpoint_evidence(monkeypatch, tmp_path, capsys):
    gate_f_receipt = tmp_path / "gate-f.json"
    physical_receipt = tmp_path / "openai-photo-flow.json"
    calls = []

    def build_gate_f(**kwargs):
        return {
            "ok": False,
            "ready_to_run": False,
            "missing_to_start": ["Tailscale endpoint evidence"],
            "missing_to_close": ["real iPhone OpenAI photo-flow receipt"],
            "checks": {"tailscale": {"ip": ""}},
        }

    def run_lan(**kwargs):
        calls.append(kwargs)
        status = {
            "requests": {"asset_upload": 1, "photo_task_create": 1, "asset_download": 1},
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1, "last_task": {"provider": "openai"}},
            "provider": {"name": "openai"},
        }
        with open(kwargs["receipt_file"], "w", encoding="utf-8") as handle:
            json.dump({
                "phase": "photo-flow",
                "ok": True,
                "missing": [],
                "base_url": "http://192.0.2.10:8765",
                "status": status,
            }, handle)
        return 0

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.build_gate_f_preflight_report", build_gate_f)
    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_lan_qa_session", run_lan)

    exit_code = main([
        "gate-f-resume",
        "--host",
        "192.0.2.10",
        "--device-id",
        "coredevice-id",
        "--gate-f-preflight-receipt",
        str(gate_f_receipt),
        "--physical-openai-receipt",
        str(physical_receipt),
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["host"] == "192.0.2.10"
    assert output["endpoint_evidence"] == "explicit_host"
    assert output["missing_to_start"] == []
    assert calls[0]["host"] == "192.0.2.10"


def test_cli_simulator_capture_ready_smoke_forwards_receipt_file(monkeypatch, tmp_path):
    calls = []

    def run_capture_ready(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_capture_ready_session",
        run_capture_ready,
    )

    exit_code = main([
        "simulator-capture-ready-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--screenshot-file",
        str(tmp_path / "capture.png"),
        "--receipt-file",
        str(tmp_path / "capture.json"),
        "--settle-seconds",
        "0.2",
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["screenshot_file"].endswith("capture.png")
    assert calls[0]["receipt_file"].endswith("capture.json")
    assert calls[0]["settle_seconds"] == 0.2


def test_cli_simulator_discovery_refresh_smoke_forwards_receipt_and_screenshot(monkeypatch, tmp_path):
    calls = []

    def run_discovery_refresh(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_discovery_refresh_session",
        run_discovery_refresh,
    )

    exit_code = main([
        "simulator-discovery-refresh-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--host",
        "127.0.0.1",
        "--port",
        "8767",
        "--screenshot-file",
        str(tmp_path / "discovery-refresh.png"),
        "--receipt-file",
        str(tmp_path / "discovery-refresh.json"),
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 8767
    assert calls[0]["screenshot_file"].endswith("discovery-refresh.png")
    assert calls[0]["receipt_file"].endswith("discovery-refresh.json")


def test_cli_simulator_capture_completed_smoke_forwards_receipt_file(monkeypatch, tmp_path):
    calls = []

    def run_capture_completed(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_capture_completed_session",
        run_capture_completed,
    )

    exit_code = main([
        "simulator-capture-completed-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--screenshot-file",
        str(tmp_path / "capture-completed.png"),
        "--receipt-file",
        str(tmp_path / "capture-completed.json"),
        "--settle-seconds",
        "0.2",
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["screenshot_file"].endswith("capture-completed.png")
    assert calls[0]["receipt_file"].endswith("capture-completed.json")
    assert calls[0]["settle_seconds"] == 0.2


def test_cli_simulator_result_gallery_smoke_forwards_receipt_file(monkeypatch, tmp_path):
    calls = []

    def run_result_gallery(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_result_gallery_session",
        run_result_gallery,
    )

    exit_code = main([
        "simulator-result-gallery-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--screenshot-file",
        str(tmp_path / "result-gallery.png"),
        "--receipt-file",
        str(tmp_path / "result-gallery.json"),
        "--settle-seconds",
        "0.2",
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["screenshot_file"].endswith("result-gallery.png")
    assert calls[0]["receipt_file"].endswith("result-gallery.json")
    assert calls[0]["settle_seconds"] == 0.2


def test_cli_simulator_result_gallery_downloaded_smoke_forwards_receipt_file(monkeypatch, tmp_path):
    calls = []

    def run_result_gallery_downloaded(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_result_gallery_downloaded_session",
        run_result_gallery_downloaded,
    )

    exit_code = main([
        "simulator-result-gallery-downloaded-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--screenshot-file",
        str(tmp_path / "result-gallery-downloaded.png"),
        "--receipt-file",
        str(tmp_path / "result-gallery-downloaded.json"),
        "--settle-seconds",
        "0.2",
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["screenshot_file"].endswith("result-gallery-downloaded.png")
    assert calls[0]["receipt_file"].endswith("result-gallery-downloaded.json")
    assert calls[0]["settle_seconds"] == 0.2


def test_cli_simulator_share_sheet_smoke_forwards_receipt_file(monkeypatch, tmp_path):
    calls = []

    def run_share_sheet(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "agent_pocket_mock_bridge.qa.run_simulator_share_sheet_session",
        run_share_sheet,
    )

    exit_code = main([
        "simulator-share-sheet-smoke",
        "--bundle-id",
        "com.kaka.AgentPocket",
        "--screenshot-file",
        str(tmp_path / "share-sheet.png"),
        "--receipt-file",
        str(tmp_path / "share-sheet.json"),
        "--settle-seconds",
        "0.2",
    ])

    assert exit_code == 0
    assert calls[0]["bundle_id"] == "com.kaka.AgentPocket"
    assert calls[0]["screenshot_file"].endswith("share-sheet.png")
    assert calls[0]["receipt_file"].endswith("share-sheet.json")
    assert calls[0]["settle_seconds"] == 0.2


def test_simulator_tool_helpers_suppress_stdout_from_xcrun(monkeypatch, tmp_path):
    calls = []
    screenshot_path = tmp_path / "screenshot.png"

    def run(command, check=True, stdout=None):
        calls.append((command, check, stdout))
        if command[:5] == ["xcrun", "simctl", "io", "booted", "screenshot"]:
            _write_rgb_png(
                screenshot_path,
                40,
                80,
                lambda x, y: (0, 122, 255) if 36 <= y < 52 and 6 <= x < 34 else (255, 255, 255),
            )

    monkeypatch.setattr(qa_module.subprocess, "run", run)

    qa_module._launch_simulator_app("com.kaka.AgentPocket")
    qa_module._launch_simulator_discovery_refresh_smoke("com.kaka.AgentPocket", "http://127.0.0.1:8766")
    qa_module._launch_simulator_picker_ui_smoke("com.kaka.AgentPocket")
    qa_module._launch_simulator_capture_ready_smoke("com.kaka.AgentPocket")
    qa_module._launch_simulator_capture_completed_smoke("com.kaka.AgentPocket")
    qa_module._launch_simulator_result_gallery_smoke("com.kaka.AgentPocket")
    qa_module._launch_simulator_result_gallery_downloaded_smoke("com.kaka.AgentPocket")
    qa_module._take_simulator_screenshot(str(screenshot_path))

    assert all(call[1] is True for call in calls)
    assert all(call[2] is subprocess.DEVNULL for call in calls)
    assert any("--agent-pocket-simulator-discovery-refresh-smoke" in call[0] for call in calls)
    assert any("http://127.0.0.1:8766" in call[0] for call in calls)


def test_simulator_screenshot_visible_content_rejects_status_bar_only_blank_body(tmp_path):
    screenshot_path = tmp_path / "blank-body.png"
    _write_rgb_png(
        screenshot_path,
        40,
        80,
        lambda x, y: (0, 0, 0) if y < 8 else (255, 255, 255),
    )

    assert qa_module._simulator_screenshot_has_visible_content(str(screenshot_path)) is False


def test_simulator_screenshot_visible_content_accepts_body_controls(tmp_path):
    screenshot_path = tmp_path / "body-controls.png"
    _write_rgb_png(
        screenshot_path,
        40,
        80,
        lambda x, y: (0, 122, 255) if 36 <= y < 52 and 6 <= x < 34 else (255, 255, 255),
    )

    assert qa_module._simulator_screenshot_has_visible_content(str(screenshot_path)) is True


def test_take_simulator_screenshot_rejects_blank_content_area(monkeypatch, tmp_path):
    screenshot_path = tmp_path / "blank-body.png"

    def run(command, check=True, stdout=None):
        _write_rgb_png(
            screenshot_path,
            40,
            80,
            lambda x, y: (0, 0, 0) if y < 8 else (255, 255, 255),
        )

    monkeypatch.setattr(qa_module.subprocess, "run", run)

    try:
        qa_module._take_simulator_screenshot(str(screenshot_path))
    except RuntimeError as error:
        assert "blank content area" in str(error)
    else:
        raise AssertionError("blank Simulator screenshot should fail")


def test_cli_verify_receipt_accepts_complete_photo_flow_file(tmp_path, capsys):
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps({
        "phase": "photo-flow",
        "ok": True,
        "missing": [],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 1,
            },
            "assets": {"download_request_count": 1},
            "tasks": {"completed": 1},
        },
    }))

    exit_code = main(["verify-receipt", "--file", str(receipt_file), "--phase", "photo-flow"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {"missing": [], "ok": True, "phase": "photo-flow"}


def test_cli_verify_receipt_rejects_incomplete_photo_flow_file(tmp_path, capsys):
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps({
        "phase": "photo-flow",
        "ok": False,
        "missing": ["asset_download request"],
        "base_url": "http://192.0.2.10:8765",
        "status": {
            "requests": {
                "asset_upload": 1,
                "photo_task_create": 1,
                "asset_download": 0,
            },
            "assets": {"download_request_count": 0},
            "tasks": {"completed": 1},
        },
    }))

    exit_code = main(["verify-receipt", "--file", str(receipt_file), "--phase", "photo-flow"])

    output = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert output["ok"] is False
    assert output["missing"] == ["ok receipt flag", "asset_download request", "result download"]


def test_cli_run_lan_accepts_manual_launch_connection_only_mode(capsys):
    exit_code = main(
        [
            "run-lan",
            "--host",
            "192.0.2.10",
            "--connection-only",
            "--no-launch",
            "--connection-timeout",
            "0",
            "--interval",
            "0",
            "--no-bonjour",
        ]
    )

    assert exit_code == 1


def test_cli_run_lan_reads_hermes_profile_env_without_leaking_secret(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    _write_hermes_profile(
        hermes_home,
        "dev-lead",
        env_text="OPENAI_API_KEY=secret-from-hermes-profile\n",
    )
    calls = []

    def run_lan(**kwargs):
        calls.append({
            "kwargs": kwargs,
            "env_key_visible": os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-profile",
        })
        return 0

    monkeypatch.setattr("agent_pocket_mock_bridge.qa.run_lan_qa_session", run_lan)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([
        "run-lan",
        "--host",
        "192.0.2.10",
        "--photo-provider",
        "openai",
        "--no-launch",
        "--no-bonjour",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls[0]["env_key_visible"] is True
    assert calls[0]["kwargs"]["photo_provider"] == "openai"
    assert os.environ.get("OPENAI_API_KEY") is None
    assert "secret-from-hermes-profile" not in output


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.wait_timeout = None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_timeout = timeout
