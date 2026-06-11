from __future__ import annotations

import json
from typing import Any, Mapping

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.connection_qa import build_connection_qa_preview


def test_connection_qa_preview_reports_schema_surface_and_summary():
    report = build_connection_qa_preview(
        BridgeConfig(
            runtime="hermes",
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            pairing_mode="production",
            runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
        ),
        bridge_enabled=True,
    )

    assert report["schema_version"] == "kaka.connection_qa_preview.v1"
    assert report["surface"] == "ordinary_user_connection_qa"
    assert report["summary"] == {
        "runtime": "hermes",
        "phone_api_path": "/mobile/v1",
        "bridge_url": "http://192.168.1.10:8765/mobile/v1",
        "pairing_mode": "production",
        "lan_discovery": "bonjour",
        "bonjour_status": "advertised_preview",
        "bridge_enabled": True,
        "runtime_side_only": True,
        "private_api_called": False,
    }


def test_connection_qa_preview_includes_expected_first_run_steps():
    report = build_connection_qa_preview(
        BridgeConfig(
            runtime="hermes",
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            pairing_mode="production",
        ),
        bridge_enabled=True,
    )

    steps = report["first_run_steps"]
    assert [step["id"] for step in steps] == [
        "package_preview",
        "host_package_preview",
        "install_runtime_package",
        "enable_start_with_runtime",
        "start_bridge",
        "production_qr_pairing",
        "bonjour_lan_discovery",
        "health_check",
        "token_revocation",
        "saved_token_reconnect",
    ]
    assert all(
        set(step) >= {"id", "title", "status", "owner", "requires_user_action"}
        for step in steps
    )
    assert steps[0]["command_ref"]["command"] == "package-preview"
    assert steps[1]["command_ref"]["command"] == "host-package-preview"
    assert steps[2]["action_ref"]["action_id"] == "install_runtime_package"
    assert steps[4]["command_ref"]["command"] == "start_bridge"
    assert steps[5]["phone_api_ref"] == "/mobile/v1/pairing/qr.html"
    assert steps[8]["phone_api_ref"] == "/mobile/v1/pairing/revoke"


def test_connection_qa_preview_includes_expected_recovery_fixtures():
    report = build_connection_qa_preview(BridgeConfig(pairing_mode="production"), bridge_enabled=False)

    fixtures = report["failure_fixtures"]
    assert [fixture["id"] for fixture in fixtures] == [
        "expired_pairing_qr",
        "revoked_mobile_token",
        "bridge_unavailable",
        "missing_bonjour_host",
        "port_conflict",
        "disabled_host_action",
        "missing_runtime_store_path",
        "private_host_adapter_unavailable",
    ]
    assert all(
        set(fixture) >= {
            "id",
            "source",
            "user_message",
            "recommended_action",
            "phone_state_hint",
        }
        for fixture in fixtures
    )
    by_id = {fixture["id"]: fixture for fixture in fixtures}
    assert by_id["port_conflict"]["host_action_id"] == "repair_port_conflict"
    assert by_id["disabled_host_action"]["host_action_id"] == "enable_start_with_runtime"
    assert by_id["private_host_adapter_unavailable"]["source"] == "host_private_api"


def test_connection_qa_preview_declares_private_api_readiness_without_calling_it():
    report = build_connection_qa_preview(BridgeConfig(runtime="openclaw"), bridge_enabled=True)
    readiness = report["readiness_report"]

    assert readiness["private_api_called"] is False
    assert readiness["p3_0_ready"] is True
    assert readiness["p3_1_private_api_ready"] is False
    assert readiness["p3_1_private_capabilities_required"] == [
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
    assert readiness["mobile_bridge_api_changed"] is False
    assert readiness["phone_owned_host_settings"] is False


def test_connection_qa_preview_is_deterministic_for_same_input():
    config = BridgeConfig(
        runtime="hermes",
        lan=True,
        bonjour=True,
        bonjour_host="192.168.1.10",
        pairing_mode="production",
        installed=True,
        process_state="running",
        health_status="healthy",
    )

    assert build_connection_qa_preview(config, bridge_enabled=True) == build_connection_qa_preview(
        config,
        bridge_enabled=True,
    )


def test_connection_qa_phone_safe_sections_do_not_leak_runtime_or_secret_values():
    config = BridgeConfig(
        runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
        recall_search_provider="runtime_http",
        recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        env_file="/Users/kartz/.config/hermes/openai.env",
        pairing_code="raw-mobile-token-secret",
        tls_private_key_path="/Users/kartz/.config/kaka/private.key",
        hermes_profile="hidden prompt profile",
    )

    report = build_connection_qa_preview(config, bridge_enabled=True)

    phone_safe_rendered = json.dumps(
        _phone_safe_sections(report),
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden_values = [
        "/Users/kartz/.kaka/mobile-runtime.sqlite3",
        "http://127.0.0.1:8788/kaka/recall/search",
        "openai.env",
        "raw-mobile-token-secret",
        "/Users/kartz/.config/kaka/private.key",
        "hidden prompt profile",
    ]

    for value in forbidden_values:
        assert value not in phone_safe_rendered

    assert report["safety"]["forbidden_phone_safe_fields"] == [
        "runtime_store_path",
        "recall_search_endpoint",
        "env_file",
        "auth_file",
        "auth_files",
        "provider_credentials",
        "provider_keys",
        "auth_env_files",
        "mobile_bearer_token",
        "mobile_tokens",
        "tls_private_key_path",
        "tls_private_key_paths",
        "hidden_prompt",
        "hidden_prompts",
        "raw_embeddings",
        "index_rows",
        "retrieval_index_rows",
        "task_logs",
        "raw_provider_responses",
        "process_ids",
        "host_log_paths",
    ]
    assert report["safety"]["does_not_start_processes"] is True
    assert report["safety"]["does_not_mutate_host_os"] is True
    assert report["safety"]["phone_api_unchanged"] is True
    assert report["safety"]["mock_adapter_only"] is True


def test_connection_qa_preview_cli_outputs_json_without_spawning_bridge(monkeypatch, capsys):
    def fail_if_called(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("connection-qa-preview must not start a bridge process")

    monkeypatch.setattr("kaka_mobile_runtime_kit.cli.subprocess.call", fail_if_called)

    exit_code = main(
        [
            "connection-qa-preview",
            "--runtime",
            "hermes",
            "--bridge-enabled",
            "--lan",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.10",
            "--pairing-mode",
            "production",
            "--runtime-store-path",
            "/Users/kartz/.kaka/mobile-runtime.sqlite3",
            "--recall-search-provider",
            "fixture",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["schema_version"] == "kaka.connection_qa_preview.v1"
    assert report["surface"] == "ordinary_user_connection_qa"
    assert report["summary"]["runtime"] == "hermes"


def _phone_safe_sections(report: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "summary": report["summary"],
        "first_run_steps": report["first_run_steps"],
        "failure_fixtures": report["failure_fixtures"],
        "readiness_report": report["readiness_report"],
        "safety": report["safety"],
    }
