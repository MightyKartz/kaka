from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import sys
import threading

import pytest

from agent_pocket_mock_bridge.server import (
    BonjourAdvertisement,
    build_parser as build_server_parser,
    resolve_pairing_advertised_endpoint,
)
from kaka_mobile_runtime_kit.cli import (
    BridgeConfig,
    build_bridge_environment,
    build_runtime_package_manifest,
    build_runtime_settings_preview,
    build_runtime_settings_preview_command,
    build_server_command,
    doctor_report,
    main,
    pairing_url,
    validate_start_config,
)
from kaka_mobile_runtime_kit import cli as runtime_cli
from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord, RuntimeTaskRecord, SQLiteRuntimeStore


def test_server_cli_accepts_recipe_local_provider():
    args = build_server_parser().parse_args(["--photo-provider", "recipe_local"])

    assert args.photo_provider == "recipe_local"


def test_server_cli_accepts_runtime_store_path():
    args = build_server_parser().parse_args(["--runtime-store-path", "/tmp/kaka-runtime.sqlite3"])

    assert args.runtime_store_path == "/tmp/kaka-runtime.sqlite3"


def test_bonjour_advertisement_can_publish_runtime_identifier():
    command = BonjourAdvertisement(
        name="Kaka Mobile Bridge",
        host="192.168.1.10",
        port=8765,
        pairing_code="pair_dev",
        runtime="openclaw",
    ).command()

    assert "runtime=openclaw" in command
    assert "endpoint=http://192.168.1.10:8765" in command


def test_server_lan_pairing_endpoint_uses_advertised_host_instead_of_request_host():
    args = build_server_parser().parse_args(
        [
            "--host",
            "0.0.0.0",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.104",
        ]
    )

    endpoint = resolve_pairing_advertised_endpoint(args, 8765)

    assert endpoint == "http://192.168.1.104:8765"


def test_runtime_bridge_default_command_is_loopback_recipe_local():
    command = build_server_command(BridgeConfig())

    assert "--host" in command
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--photo-provider") + 1] == "recipe_local"
    assert command[command.index("--vision-provider") + 1] == "fixture"
    assert "--bonjour" not in command


def test_runtime_bridge_can_route_vision_to_runtime_http_provider():
    command = build_server_command(
        BridgeConfig(
            vision_provider="runtime_http",
            vision_endpoint="http://127.0.0.1:7799/kaka/vision",
        )
    )

    assert command[command.index("--vision-provider") + 1] == "runtime_http"
    assert command[command.index("--vision-endpoint") + 1] == "http://127.0.0.1:7799/kaka/vision"


def test_runtime_bridge_can_route_recall_search_to_runtime_http_provider():
    command = build_server_command(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        )
    )

    assert command[command.index("--recall-search-provider") + 1] == "runtime_http"
    assert command[command.index("--recall-search-endpoint") + 1] == "http://127.0.0.1:8788/kaka/recall/search"


def test_runtime_bridge_anthropic_provider_lan_bonjour_sqlite_dry_run_command(tmp_path, capsys, monkeypatch):
    store_path = tmp_path / "kaka-runtime.sqlite3"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-runtime-key")

    exit_code = main(
        [
            "start",
            "--provider",
            "anthropic",
            "--runtime-store-path",
            str(store_path),
            "--lan",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.10",
            "--dry-run",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    command = summary["command"]
    rendered = json.dumps(summary, sort_keys=True)
    assert exit_code == 0
    assert summary["provider"] == "anthropic"
    assert command[command.index("--provider") + 1] == "anthropic"
    assert command[command.index("--runtime-store-path") + 1] == str(store_path)
    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert "--bonjour" in command
    assert command[command.index("--bonjour-host") + 1] == "192.168.1.10"
    assert summary["provider_environment"]["api_key_env_var"] == "ANTHROPIC_API_KEY"
    assert summary["provider_environment"]["api_key_state"] == "set"
    assert "secret-runtime-key" not in rendered


def test_runtime_bridge_hermes_provider_lan_bonjour_sqlite_dry_run_command(tmp_path, capsys, monkeypatch):
    store_path = tmp_path / "kaka-runtime.sqlite3"
    monkeypatch.setenv("KAKA_HERMES_API_KEY", "secret-runtime-key")
    monkeypatch.setenv("KAKA_HERMES_BASE_URL", "http://127.0.0.1:8642/v1")
    monkeypatch.setenv("KAKA_HERMES_MODEL", "jiqimao")

    exit_code = main(
        [
            "start",
            "--provider",
            "hermes",
            "--runtime-store-path",
            str(store_path),
            "--lan",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.10",
            "--dry-run",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    command = summary["command"]
    rendered = json.dumps(summary, sort_keys=True)
    assert exit_code == 0
    assert summary["provider"] == "hermes"
    assert command[command.index("--provider") + 1] == "hermes"
    assert command[command.index("--runtime-store-path") + 1] == str(store_path)
    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert "--bonjour" in command
    assert command[command.index("--bonjour-host") + 1] == "192.168.1.10"
    assert summary["provider_environment"]["api_key_env_var"] == "KAKA_HERMES_API_KEY"
    assert summary["provider_environment"]["api_key_state"] == "set"
    assert summary["provider_environment"]["base_url_env_var"] == "KAKA_HERMES_BASE_URL"
    assert summary["provider_environment"]["base_url"] == "http://127.0.0.1:8642/v1"
    assert summary["provider_environment"]["model_env_var"] == "KAKA_HERMES_MODEL"
    assert summary["provider_environment"]["model_state"] == "set"
    assert "secret-runtime-key" not in rendered


def test_runtime_start_requires_anthropic_key_outside_dry_run(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    exit_code = main(["start", "--provider", "anthropic"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ANTHROPIC_API_KEY" in captured.err
    assert "anthropic" in captured.err


def test_runtime_start_requires_hermes_key_outside_dry_run(capsys, monkeypatch):
    monkeypatch.delenv("KAKA_HERMES_API_KEY", raising=False)

    exit_code = main(["start", "--provider", "hermes"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "KAKA_HERMES_API_KEY" in captured.err
    assert "hermes" in captured.err


def test_runtime_start_dry_run_warns_without_anthropic_key(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    exit_code = main(["start", "--provider", "anthropic", "--dry-run"])

    summary = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert summary["provider"] == "anthropic"
    assert summary["provider_environment"]["api_key_env_var"] == "ANTHROPIC_API_KEY"
    assert summary["provider_environment"]["api_key_state"] == "missing"
    assert summary["warnings"] == [
        {
            "id": "missing_anthropic_api_key",
            "message": "Set ANTHROPIC_API_KEY in the runtime environment before starting without --dry-run.",
        }
    ]


def test_runtime_start_dry_run_warns_without_hermes_key(capsys, monkeypatch):
    monkeypatch.delenv("KAKA_HERMES_API_KEY", raising=False)

    exit_code = main(["start", "--provider", "hermes", "--dry-run"])

    summary = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert summary["provider"] == "hermes"
    assert summary["provider_environment"]["api_key_env_var"] == "KAKA_HERMES_API_KEY"
    assert summary["provider_environment"]["api_key_state"] == "missing"
    assert summary["provider_environment"]["base_url"] == "http://127.0.0.1:8642/v1"
    assert summary["warnings"] == [
        {
            "id": "missing_hermes_api_key",
            "message": "Set KAKA_HERMES_API_KEY in the runtime environment before starting without --dry-run.",
        }
    ]


def test_runtime_bridge_can_pass_runtime_store_path_to_bridge_server():
    command = build_server_command(
        BridgeConfig(runtime_store_path="/tmp/kaka-runtime.sqlite3")
    )

    assert "--runtime-store-path" in command
    assert command[command.index("--runtime-store-path") + 1] == "/tmp/kaka-runtime.sqlite3"


def test_runtime_server_command_passes_non_default_retention_policy():
    command = build_server_command(
        BridgeConfig(
            input_assets_days=3,
            output_assets_days=14,
            task_history_days=60,
        )
    )

    assert command[command.index("--input-assets-days") + 1] == "3"
    assert command[command.index("--output-assets-days") + 1] == "14"
    assert command[command.index("--task-history-days") + 1] == "60"


def test_runtime_server_command_passes_tls_certificate_chain_path():
    command = build_server_command(
        BridgeConfig(
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
            tls_public_key_sha256="d" * 64,
            tls_certificate_chain_path="/Users/kartz/.kaka/certs/kaka-local-runtime.crt",
            tls_private_key_path="/Users/kartz/.kaka/private/kaka-local-runtime.key",
        )
    )

    assert "--trusted-local-tls" in command
    assert "--tls-certificate-chain-path" in command
    assert command[command.index("--tls-public-key-sha256") + 1] == "d" * 64
    assert command[command.index("--tls-certificate-chain-path") + 1] == (
        "/Users/kartz/.kaka/certs/kaka-local-runtime.crt"
    )
    assert "--tls-private-key-path" in command


def test_runtime_bridge_dry_run_summarizes_recall_store_status(tmp_path, capsys):
    store_path = tmp_path / "kaka-runtime.sqlite3"

    exit_code = main(
        [
            "start",
            "--runtime-store-path",
            str(store_path),
            "--dry-run",
        ]
    )

    summary = __import__("json").loads(capsys.readouterr().out)
    assert exit_code == 0
    assert summary["recall_store_enabled"] is True
    assert summary["recall_store_owner"] == "runtime"
    assert summary["phone_safe_summary"]["recall_store_enabled"] is True
    assert "runtime_store_path" not in summary["phone_safe_summary"]


def test_runtime_bridge_dry_run_summarizes_recall_search_provider(capsys):
    exit_code = main(
        [
            "start",
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "http://127.0.0.1:8788/kaka/recall/search",
            "--dry-run",
        ]
    )

    summary = __import__("json").loads(capsys.readouterr().out)
    rendered = str(summary)
    assert exit_code == 0
    assert summary["recall_search_provider"] == "runtime_http"
    assert summary["semantic_recall_mode"] == "provider_backed"
    assert summary["phone_safe_summary"]["semantic_recall_mode"] == "provider_backed"
    assert "recall_search_endpoint" not in summary["phone_safe_summary"]
    assert "provider_keys" not in rendered


def test_runtime_bridge_dry_run_remains_developer_facing_with_phone_safe_nested_summary(tmp_path, capsys):
    store_path = tmp_path / "mobile-runtime.sqlite3"
    endpoint = "http://127.0.0.1:8788/kaka/recall/search"

    exit_code = main(
        [
            "start",
            "--runtime-store-path",
            str(store_path),
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            endpoint,
            "--dry-run",
        ]
    )

    summary = __import__("json").loads(capsys.readouterr().out)
    rendered_phone_safe = str(summary["phone_safe_summary"])
    assert exit_code == 0
    assert summary["runtime_store_path"] == str(store_path)
    assert "--runtime-store-path" in summary["command"]
    assert endpoint in summary["command"]
    assert str(store_path) not in rendered_phone_safe
    assert endpoint not in rendered_phone_safe


def test_runtime_settings_preview_describes_runtime_side_controls_and_start_command(tmp_path):
    store_path = tmp_path / "mobile-runtime.sqlite3"
    config = BridgeConfig(
        lan=True,
        bonjour=True,
        bonjour_host="192.168.1.10",
        runtime_store_path=str(store_path),
        recall_search_provider="runtime_http",
        recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        hermes_profile="dev-lead",
    )

    preview = build_runtime_settings_preview(config, bridge_enabled=True)

    controls = preview["runtime_side_ui"]["controls"]
    assert preview["bridge_enabled"] is True
    assert controls["bind_mode"]["value"] == "lan"
    assert controls["bonjour_enabled"]["value"] is True
    assert controls["runtime_store_path"]["kind"] == "path_picker"
    assert controls["runtime_store_path"]["value"] == str(store_path)
    assert controls["recall_search_provider"]["value"] == "runtime_http"
    assert controls["recall_search_endpoint"]["value"] == "http://127.0.0.1:8788/kaka/recall/search"
    assert preview["actions"]["start_bridge"] == build_server_command(config)
    assert preview["actions"]["show_qr"] == "http://192.168.1.10:8765/mobile/v1/pairing/dev.html"


def test_runtime_settings_preview_keeps_phone_safe_summary_free_of_runtime_only_values(tmp_path):
    store_path = tmp_path / "private-runtime.sqlite3"
    endpoint = "http://127.0.0.1:8788/kaka/recall/search"

    preview = build_runtime_settings_preview(
        BridgeConfig(
            runtime_store_path=str(store_path),
            recall_search_provider="runtime_http",
            recall_search_endpoint=endpoint,
            env_file="/Users/kartz/.config/hermes/openai.env",
        ),
        bridge_enabled=True,
    )

    phone_safe = preview["phone_safe_summary"]
    rendered_phone_safe = str(phone_safe)
    assert phone_safe["recall_store_enabled"] is True
    assert phone_safe["semantic_recall_mode"] == "provider_backed"
    assert "runtime_store_path" not in phone_safe
    assert "recall_search_endpoint" not in phone_safe
    assert str(store_path) not in rendered_phone_safe
    assert endpoint not in rendered_phone_safe
    assert "openai.env" not in rendered_phone_safe


def test_runtime_settings_preview_tls_bind_url_uses_config_scheme():
    preview = build_runtime_settings_preview(
        BridgeConfig(trusted_local_tls=True),
        bridge_enabled=True,
    )

    assert preview["bind_url"] == "https://127.0.0.1:8765"
    assert preview["pairing_page"].startswith("https://")


def test_runtime_settings_preview_command_allows_tls_metadata_without_serving_files(capsys):
    exit_code = main(
        [
            "settings-preview",
            "--trusted-local-tls",
            "--tls-trust-state",
            "configured",
            "--tls-certificate-label",
            "Kaka Local Runtime",
        ]
    )

    preview = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert preview["bind_url"] == "https://127.0.0.1:8765"
    assert preview["runtime_side_ui"]["controls"]["tls_certificate_chain_path"]["value"] == ""
    assert preview["runtime_side_ui"]["controls"]["tls_private_key_path"]["value"] == ""


def test_runtime_settings_preview_keeps_tls_serving_paths_runtime_side_only():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
            tls_certificate_chain_path="/Users/kartz/.kaka/certs/kaka-local-runtime.crt",
            tls_private_key_path="/Users/kartz/.kaka/private/kaka-local-runtime.key",
        )
    )

    rendered_phone_safe = json.dumps(preview["phone_safe_summary"])
    assert preview["runtime_side_ui"]["controls"]["tls_certificate_chain_path"] == {
        "kind": "path_picker",
        "enabled": True,
        "value": "/Users/kartz/.kaka/certs/kaka-local-runtime.crt",
    }
    assert preview["runtime_side_ui"]["controls"]["tls_private_key_path"] == {
        "kind": "path_picker",
        "enabled": True,
        "value": "/Users/kartz/.kaka/private/kaka-local-runtime.key",
    }
    assert "/Users/kartz/.kaka" not in rendered_phone_safe


def test_runtime_package_manifest_keeps_tls_serving_paths_runtime_side_only():
    manifest = build_runtime_package_manifest(
        BridgeConfig(
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
            tls_certificate_chain_path="/Users/kartz/.kaka/certs/kaka-local-runtime.crt",
            tls_private_key_path="/Users/kartz/.kaka/private/kaka-local-runtime.key",
        )
    )

    rendered_phone_safe = json.dumps(manifest["settings_preview"]["phone_safe_summary"])
    assert "tls_certificate_chain_path" in manifest["runtime_side_values"]
    assert "tls_private_key_path" in manifest["runtime_side_values"]
    assert "tls_certificate_chain_path" in manifest["forbidden_phone_safe_fields"]
    assert "tls_private_key_path" in manifest["forbidden_phone_safe_fields"]
    assert "/Users/kartz/.kaka" not in rendered_phone_safe


def test_runtime_settings_preview_exposes_retention_policy_controls():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            input_assets_days=3,
            output_assets_days=14,
            task_history_days=60,
        )
    )

    assert preview["retention"] == {
        "input_assets_days": 3,
        "output_assets_days": 14,
        "task_history_days": 60,
    }
    controls = preview["runtime_side_ui"]["controls"]
    assert controls["input_assets_days"] == {
        "kind": "stepper",
        "value": 3,
        "minimum": 1,
        "maximum": 3650,
    }
    assert controls["output_assets_days"]["value"] == 14
    assert controls["task_history_days"]["value"] == 60
    assert "retention" not in preview["phone_safe_summary"]


def test_runtime_settings_preview_command_preserves_non_default_retention_policy():
    command = build_runtime_settings_preview_command(
        BridgeConfig(
            input_assets_days=3,
            output_assets_days=14,
            task_history_days=60,
        )
    )

    assert command[command.index("--input-assets-days") + 1] == "3"
    assert command[command.index("--output-assets-days") + 1] == "14"
    assert command[command.index("--task-history-days") + 1] == "60"


def test_runtime_settings_preview_anthropic_provider_reports_env_name_without_secret(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-runtime-key")

    preview = build_runtime_settings_preview(BridgeConfig(provider="anthropic"))

    rendered = json.dumps(preview, sort_keys=True)
    controls = preview["runtime_side_ui"]["controls"]
    assert preview["provider"] == "anthropic"
    assert preview["provider_environment"]["api_key_env_var"] == "ANTHROPIC_API_KEY"
    assert preview["provider_environment"]["api_key_state"] == "set"
    assert controls["provider"]["value"] == "anthropic"
    assert controls["provider_environment"]["value"]["api_key_env_var"] == "ANTHROPIC_API_KEY"
    assert "--provider" in preview["actions"]["start_bridge"]
    assert "secret-runtime-key" not in rendered


def test_runtime_settings_preview_hermes_provider_reports_base_url_without_secret(monkeypatch):
    monkeypatch.setenv("KAKA_HERMES_API_KEY", "secret-runtime-key")
    monkeypatch.setenv("KAKA_HERMES_BASE_URL", "http://127.0.0.1:8642/v1/")

    preview = build_runtime_settings_preview(BridgeConfig(provider="hermes"))

    rendered = json.dumps(preview, sort_keys=True)
    controls = preview["runtime_side_ui"]["controls"]
    assert preview["provider"] == "hermes"
    assert preview["provider_environment"]["api_key_env_var"] == "KAKA_HERMES_API_KEY"
    assert preview["provider_environment"]["api_key_state"] == "set"
    assert preview["provider_environment"]["base_url_env_var"] == "KAKA_HERMES_BASE_URL"
    assert preview["provider_environment"]["base_url"] == "http://127.0.0.1:8642/v1"
    assert controls["provider"]["value"] == "hermes"
    assert controls["provider"]["options"] == ["fake", "anthropic", "hermes"]
    assert controls["provider_environment"]["value"]["base_url"] == "http://127.0.0.1:8642/v1"
    assert "--provider" in preview["actions"]["start_bridge"]
    assert "secret-runtime-key" not in rendered


def test_runtime_retention_purge_command_dry_run_outputs_receipt(tmp_path, capsys):
    store_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(store_path)
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_old_done",
            title="Old task",
            status="completed",
            updated_at="2026-05-01T00:00:00Z",
        )
    )

    exit_code = main(
        [
            "retention-purge",
            "--runtime",
            "hermes",
            "--runtime-store-path",
            str(store_path),
            "--now",
            "2026-06-07T00:00:00Z",
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == "kaka.runtime_retention_purge_receipt.v1"
    assert payload["surface"] == "hermes_openclaw_runtime_retention_purge"
    assert payload["mode"] == "dry_run"
    assert payload["applied"] is False
    assert payload["eligible"]["task_ids"] == ["task_old_done"]
    assert payload["deleted"]["task_ids"] == []
    reopened = SQLiteRuntimeStore(store_path)
    reopened.initialize()
    assert reopened.get_task("task_old_done") is not None


def test_runtime_retention_purge_command_apply_requires_existing_store(tmp_path, capsys):
    missing_store = tmp_path / "missing.sqlite3"

    exit_code = main(
        [
            "retention-purge",
            "--runtime-store-path",
            str(missing_store),
            "--now",
            "2026-06-07T00:00:00Z",
            "--apply",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "runtime store path must exist before --apply" in captured.err


def test_runtime_retention_purge_command_apply_deletes_old_terminal_tasks(tmp_path, capsys):
    store_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(store_path)
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_old_done",
            title="Old task",
            status="completed",
            updated_at="2026-05-01T00:00:00Z",
        )
    )

    exit_code = main(
        [
            "retention-purge",
            "--runtime-store-path",
            str(store_path),
            "--now",
            "2026-06-07T00:00:00Z",
            "--apply",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mode"] == "apply"
    assert payload["applied"] is True
    assert payload["eligible"]["task_ids"] == ["task_old_done"]
    assert payload["deleted"]["task_ids"] == ["task_old_done"]
    reopened = SQLiteRuntimeStore(store_path)
    reopened.initialize()
    assert reopened.get_task("task_old_done") is None


def test_runtime_retention_purge_command_apply_deletes_store_backed_assets(tmp_path, capsys):
    store_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(store_path)
    store.initialize()
    store.upsert_asset(
        RuntimeAssetRecord(
            asset_id="asset_old_input",
            role="input",
            created_at="2026-05-01T00:00:00Z",
            filename="old-input.png",
            mime_type="image/png",
            size_bytes=9,
            sha256="oldinput",
            body=b"old-input",
        )
    )

    exit_code = main(
        [
            "retention-purge",
            "--runtime-store-path",
            str(store_path),
            "--now",
            "2026-06-07T00:00:00Z",
            "--apply",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mode"] == "apply"
    assert payload["deleted"]["input_asset_ids"] == ["asset_old_input"]
    reopened = SQLiteRuntimeStore(store_path)
    reopened.initialize()
    assert reopened.get_asset("asset_old_input") is None


def test_runtime_settings_preview_command_validates_unsafe_bonjour(capsys):
    exit_code = main(["settings-preview", "--bonjour"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Bonjour discovery for iPhone requires --lan or --bonjour-host." in captured.err


def test_runtime_settings_preview_command_requires_recall_search_endpoint(capsys):
    exit_code = main(["settings-preview", "--recall-search-provider", "runtime_http"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--recall-search-endpoint is required when --recall-search-provider runtime_http." in captured.err


def test_runtime_settings_preview_command_rejects_malformed_recall_search_endpoint(capsys):
    exit_code = main(
        [
            "settings-preview",
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "not-a-url",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--recall-search-endpoint must be an http:// or https:// URL." in captured.err


def test_local_renderer_backend_readiness_command_outputs_local_probe_report(capsys):
    exit_code = main(["local-renderer-backend-readiness", "--photo-provider", "recipe_local"])

    report = json.loads(capsys.readouterr().out)
    rendered = json.dumps(report, sort_keys=True)
    assert exit_code == 0
    assert report["schema_version"] == "kaka.local_renderer_backend_readiness.v1"
    assert report["status"] == "ready_for_local_recipe_flow"
    assert report["provider"] == "recipe_local"
    assert report["probe"]["variant_count"] == 2
    assert "source_image_base64" not in rendered
    assert "OPENAI_API_KEY" not in rendered


def test_local_renderer_backend_readiness_command_returns_nonzero_for_blocked_provider(capsys):
    exit_code = main(["local-renderer-backend-readiness", "--photo-provider", "openai"])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["status"] == "blocked"
    assert report["missing_inputs"] == [
        {
            "id": "photo_provider",
            "label": "Use recipe_local for local parameterized renderer readiness.",
        }
    ]


def test_local_renderer_backend_readiness_cli_handles_missing_mock_bridge_import_path():
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": "runtime-kit",
    }

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "kaka_mobile_runtime_kit",
            "local-renderer-backend-readiness",
            "--repo-root",
            ".",
            "--photo-provider",
            "recipe_local",
        ],
        cwd=Path("."),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    report = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert report["status"] == "ready_for_local_recipe_flow"
    assert report["probe"]["variant_count"] == 2


def test_local_renderer_backend_capability_manifest_command_outputs_gate_manifest(capsys):
    exit_code = main(["local-renderer-backend-capability-manifest"])

    report = json.loads(capsys.readouterr().out)
    rendered = json.dumps(report, sort_keys=True).lower()
    assert exit_code == 0
    assert report["schema_version"] == "kaka.local_renderer_backend_capability_manifest.v1"
    assert report["status"] == "ready_for_backend_gate_planning"
    assert report["current_contract"]["renderer"] == "local_parametric"
    assert [candidate["backend_id"] for candidate in report["backend_candidates"]] == [
        "pillow",
        "core_image",
        "imagemagick",
        "opencv",
        "libvips",
    ]
    assert report["phone_api"]["capabilities_changed"] is False
    assert report["safety"]["does_not_import_future_backends"] is True
    assert "source_image_base64" not in rendered
    assert "api_key" not in rendered
    assert "subprocess" not in rendered


def test_runtime_settings_preview_command_outputs_plugin_shell(tmp_path, capsys):
    store_path = tmp_path / "mobile-runtime.sqlite3"

    exit_code = main(
        [
            "settings-preview",
            "--bridge-enabled",
            "--lan",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.10",
            "--runtime-store-path",
            str(store_path),
            "--recall-search-provider",
            "fixture",
            "--input-assets-days",
            "3",
            "--output-assets-days",
            "14",
            "--task-history-days",
            "60",
        ]
    )

    summary = __import__("json").loads(capsys.readouterr().out)
    assert exit_code == 0
    assert summary["bridge_enabled"] is True
    assert summary["runtime_side_ui"]["surface"] == "hermes_openclaw_settings"
    assert summary["runtime_side_ui"]["controls"]["runtime_store_path"]["value"] == str(store_path)
    assert summary["phone_safe_summary"]["semantic_recall_mode"] == "provider_backed"
    assert "--runtime-store-path" in summary["actions"]["start_bridge"]
    assert summary["retention"]["input_assets_days"] == 3
    assert "--input-assets-days" in summary["actions"]["start_bridge"]
    assert "--output-assets-days" in summary["actions"]["start_bridge"]
    assert "--task-history-days" in summary["actions"]["start_bridge"]


def test_runtime_settings_preview_schema_freezes_required_top_level_keys():
    preview = build_runtime_settings_preview(BridgeConfig())

    assert set(preview) == {
        "bridge",
        "surface",
        "bridge_enabled",
        "runtime",
        "provider",
        "provider_environment",
        "bind_url",
        "lan_exposed",
        "bonjour",
        "pairing_page",
        "pairing_mode",
        "runtime_store_path",
        "retention",
        "recall_search_provider",
        "recall_search_endpoint",
        "runtime_side_ui",
        "actions",
        "phone_safe_summary",
    }
    assert preview["surface"] == "runtime_side_settings_preview"
    assert preview["runtime_side_ui"]["surface"] == "hermes_openclaw_settings"


def test_runtime_settings_preview_freezes_control_contract_defaults():
    preview = build_runtime_settings_preview(BridgeConfig())
    controls = preview["runtime_side_ui"]["controls"]

    assert preview["retention"] == {
        "input_assets_days": 7,
        "output_assets_days": 30,
        "task_history_days": 30,
    }
    assert preview["bridge_enabled"] is False
    assert controls["bridge_enabled"]["kind"] == "toggle"
    assert controls["bridge_enabled"]["value"] is False
    assert controls["start_with_runtime"]["value"] is False
    assert controls["provider"] == {
        "kind": "menu",
        "value": "fake",
        "options": ["fake", "anthropic", "hermes"],
    }
    assert controls["provider_environment"]["kind"] == "status"
    assert controls["provider_environment"]["value"] == {
        "provider": "fake",
        "required_env_vars": [],
        "api_key_env_var": "",
        "api_key_state": "not_required",
        "model_env_var": "",
        "default_model": "",
    }
    assert controls["bind_mode"]["value"] == "loopback"
    assert controls["bind_mode"]["options"] == ["loopback", "lan"]
    assert controls["bonjour_enabled"]["value"] is False
    assert controls["local_store_enabled"]["value"] is False
    assert controls["runtime_store_path"]["enabled"] is False
    assert controls["recall_search_provider"]["options"] == ["local", "fixture", "runtime_http"]
    assert controls["recall_search_endpoint"]["enabled"] is False
    assert controls["input_assets_days"]["value"] == 7
    assert controls["output_assets_days"]["value"] == 30
    assert controls["task_history_days"]["value"] == 30
    assert controls["input_assets_days"]["minimum"] == 1
    assert controls["input_assets_days"]["maximum"] == 3650


def test_runtime_settings_preview_runtime_http_enables_endpoint_control():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        )
    )

    control = preview["runtime_side_ui"]["controls"]["recall_search_endpoint"]
    assert control["enabled"] is True
    assert control["value"] == "http://127.0.0.1:8788/kaka/recall/search"


def test_runtime_settings_preview_exposes_process_ownership_contract():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            runtime="hermes",
            installed=True,
            start_with_runtime=True,
            process_state="running",
            process_supervision="host_managed",
            health_status="healthy",
            port_conflict=False,
        ),
        bridge_enabled=True,
    )

    ownership = preview["runtime_side_ui"]["process_ownership"]

    assert ownership["schema_version"] == "kaka.runtime_process_ownership.v1"
    assert ownership["surface"] == "hermes_openclaw_process_ownership"
    assert ownership["owner"] == "hermes"
    assert ownership["state"] == {
        "installed": True,
        "running": True,
        "process_state": "running",
        "start_with_runtime": True,
        "supervision": "host_managed",
        "health": "healthy",
        "port": 8765,
        "port_conflict": False,
    }
    assert [action["id"] for action in ownership["actions"]] == [
        "install_runtime_package",
        "enable_start_with_runtime",
        "disable_start_with_runtime",
        "update_runtime_package",
        "uninstall_runtime_package",
        "open_runtime_logs",
        "run_health_check",
        "repair_port_conflict",
    ]
    assert ownership["actions"][0]["enabled"] is False
    assert ownership["actions"][2]["enabled"] is True
    assert ownership["actions"][6]["url"] == "http://127.0.0.1:8765/mobile/v1/health"
    assert ownership["warnings"] == [
        {
            "id": "start_with_runtime_enabled",
            "tone": "warning",
            "message": "Start with runtime is enabled. The bridge still starts only under this runtime host, not during package install.",
        }
    ]


def test_runtime_consumer_ui_adds_process_section_without_phone_only_values():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            installed=True,
            port_conflict=True,
            runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        )
    )

    consumer = preview["runtime_side_ui"]["consumer_ui"]

    assert [section["id"] for section in consumer["sections"]] == [
        "process",
        "connection",
        "pairing",
        "memory",
        "retrieval",
    ]
    assert consumer["sections"][0]["controls"] == [
        "install_runtime_package",
        "start_with_runtime",
        "update_runtime_package",
        "uninstall_runtime_package",
        "open_runtime_logs",
        "run_health_check",
        "repair_port_conflict",
    ]
    assert "runtime_store_path" not in str(consumer["safe_summary"])
    assert "recall_search_endpoint" not in str(consumer["safe_summary"])


def test_runtime_package_manifest_derives_process_ownership_from_settings_preview():
    manifest = build_runtime_package_manifest(
        BridgeConfig(
            runtime="openclaw",
            installed=True,
            process_supervision="host_managed",
            health_status="healthy",
        ),
        bridge_enabled=True,
    )

    assert manifest["process_ownership"] == manifest["settings_preview"]["runtime_side_ui"]["process_ownership"]
    assert manifest["process_ownership"]["owner"] == "openclaw"
    assert manifest["install"]["auto_start_on_install"] is False
    assert manifest["defaults"]["start_with_runtime"] is False


def test_process_preview_command_outputs_runtime_side_contract(capsys):
    exit_code = main(
        [
            "process-preview",
            "--runtime",
            "hermes",
            "--installed",
            "--start-with-runtime",
            "--process-state",
            "running",
            "--process-supervision",
            "host_managed",
            "--health-status",
            "healthy",
        ]
    )

    ownership = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ownership["surface"] == "hermes_openclaw_process_ownership"
    assert ownership["state"]["installed"] is True
    assert ownership["state"]["start_with_runtime"] is True
    assert ownership["state"]["health"] == "healthy"


def test_pairing_url_uses_production_qr_route_when_requested():
    assert pairing_url("192.168.1.10", 8765, mode="production", scheme="https") == (
        "https://192.168.1.10:8765/mobile/v1/pairing/qr.html"
    )


def test_runtime_settings_preview_exposes_production_pairing_controls_without_phone_secrets():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            pairing_mode="production",
            pairing_code_ttl_seconds=120,
            token_ttl_seconds=3600,
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
            tls_private_key_path="/Users/kartz/.kaka/private/key.pem",
        ),
        bridge_enabled=True,
    )

    controls = preview["runtime_side_ui"]["controls"]
    security = preview["runtime_side_ui"]["connection_security"]
    rendered_phone_safe = str(preview["phone_safe_summary"])

    assert preview["pairing_page"] == "https://192.168.1.10:8765/mobile/v1/pairing/qr.html"
    assert controls["pairing_mode"] == {
        "kind": "segmented_control",
        "value": "production",
        "options": ["development", "production"],
    }
    assert controls["qr_ttl_seconds"] == {
        "kind": "stepper",
        "value": 120,
        "minimum": 60,
        "maximum": 300,
    }
    assert controls["revoke_mobile_tokens"]["kind"] == "button"
    assert security == {
        "pairing_code_ttl_seconds": 120,
        "mobile_token_ttl_seconds": 3600,
        "mobile_token_revocation_supported": True,
        "trusted_local_tls_required": True,
        "tls_trust_state": "configured",
        "tls_certificate_label": "Kaka Local Runtime",
    }
    assert "mobile_token" not in preview["phone_safe_summary"]
    assert "key.pem" not in rendered_phone_safe


def test_runtime_settings_preview_exposes_consumer_ui_sections_and_primary_actions(tmp_path):
    store_path = tmp_path / "mobile-runtime.sqlite3"
    preview = build_runtime_settings_preview(
        BridgeConfig(
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            pairing_mode="production",
            pairing_code_ttl_seconds=120,
            token_ttl_seconds=3600,
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
            runtime_store_path=str(store_path),
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        ),
        bridge_enabled=True,
    )

    consumer = preview["runtime_side_ui"]["consumer_ui"]

    assert consumer["schema_version"] == "kaka.runtime_consumer_ui.v1"
    assert consumer["surface"] == "hermes_openclaw_consumer_runtime_ui"
    assert consumer["title"] == "Kaka Mobile Bridge"
    assert consumer["status_badges"] == [
        {"id": "bridge", "label": "Running", "tone": "success"},
        {"id": "network", "label": "LAN + Bonjour", "tone": "warning"},
        {"id": "pairing", "label": "Production QR", "tone": "success"},
        {"id": "trust", "label": "TLS configured", "tone": "success"},
    ]
    assert [action["id"] for action in consumer["primary_actions"]] == [
        "stop_bridge",
        "show_qr",
        "revoke_mobile_tokens",
    ]
    assert consumer["primary_actions"][0]["label"] == "Stop Bridge"
    assert consumer["primary_actions"][1]["label"] == "Show QR"
    assert consumer["primary_actions"][1]["url"] == "https://192.168.1.10:8765/mobile/v1/pairing/qr.html"
    assert consumer["primary_actions"][2]["style"] == "destructive"
    assert [section["id"] for section in consumer["sections"]] == [
        "process",
        "connection",
        "pairing",
        "memory",
        "retrieval",
    ]
    assert consumer["sections"][0]["controls"] == [
        "install_runtime_package",
        "start_with_runtime",
        "update_runtime_package",
        "uninstall_runtime_package",
        "open_runtime_logs",
        "run_health_check",
        "repair_port_conflict",
    ]
    assert consumer["sections"][1]["controls"] == [
        "bridge_enabled",
        "bind_mode",
        "bonjour_enabled",
        "trusted_local_tls",
    ]
    assert consumer["sections"][2]["controls"] == [
        "pairing_mode",
        "qr_ttl_seconds",
        "revoke_mobile_tokens",
    ]
    assert consumer["sections"][3]["controls"] == [
        "local_store_enabled",
        "runtime_store_path",
        "input_assets_days",
        "output_assets_days",
        "task_history_days",
    ]
    assert consumer["warnings"] == [
        {
            "id": "lan_visible",
            "tone": "warning",
            "message": "LAN and Bonjour make this runtime discoverable on the local network.",
        }
    ]
    assert "runtime_store_path" not in str(consumer["safe_summary"])
    assert "recall_search_endpoint" not in str(consumer["safe_summary"])


def test_runtime_settings_preview_consumer_ui_stopped_empty_state_is_loopback_first():
    preview = build_runtime_settings_preview(BridgeConfig(), bridge_enabled=False)

    consumer = preview["runtime_side_ui"]["consumer_ui"]

    assert consumer["status_badges"] == [
        {"id": "bridge", "label": "Stopped", "tone": "neutral"},
        {"id": "network", "label": "Loopback only", "tone": "neutral"},
        {"id": "pairing", "label": "Development pairing", "tone": "warning"},
        {"id": "trust", "label": "TLS not configured", "tone": "neutral"},
    ]
    assert consumer["empty_state"] == {
        "id": "bridge_stopped",
        "title": "Bridge is stopped",
        "message": "Start Kaka Mobile Bridge from this runtime before pairing an iPhone.",
        "primary_action": "start_bridge",
    }
    assert consumer["primary_actions"] == [
        {
            "id": "start_bridge",
            "label": "Start Bridge",
            "style": "primary",
            "enabled": True,
            "action": "start_bridge",
        }
    ]
    assert consumer["warnings"] == [
        {
            "id": "development_pairing",
            "tone": "warning",
            "message": "Development pairing is intended for local testing. Use production pairing for ordinary users.",
        }
    ]


def test_runtime_settings_preview_command_does_not_spawn_bridge_process(monkeypatch, capsys):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("settings-preview must not start a bridge process")

    monkeypatch.setattr("kaka_mobile_runtime_kit.cli.subprocess.call", fail_if_called)

    exit_code = main(["settings-preview"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["surface"] == "runtime_side_settings_preview"


def test_runtime_settings_preview_actions_are_spawnable_not_shell_strings(tmp_path):
    store_path = tmp_path / "mobile-runtime.sqlite3"
    config = BridgeConfig(
        lan=True,
        bonjour=True,
        bonjour_host="192.168.1.10",
        runtime="openclaw",
        runtime_store_path=str(store_path),
    )

    preview = build_runtime_settings_preview(config)

    start_action = preview["actions"]["start_bridge"]
    assert isinstance(start_action, list)
    assert "-m" in start_action
    assert "agent_pocket_mock_bridge.server" in start_action
    assert start_action[start_action.index("--runtime") + 1] == "openclaw"
    assert "--runtime-store-path" in start_action
    assert "--bonjour" in start_action
    assert preview["actions"]["show_qr"] == preview["pairing_page"]


def test_runtime_settings_preview_phone_safe_summary_is_exact_allowlist():
    preview = build_runtime_settings_preview(
        BridgeConfig(
            runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
            env_file="/Users/kartz/.config/hermes/openai.env",
        )
    )

    assert set(preview["phone_safe_summary"]) == {
        "recall_store_enabled",
        "recall_store_owner",
        "semantic_recall_mode",
    }


def test_runtime_package_manifest_wraps_settings_preview_for_native_shells(tmp_path):
    store_path = tmp_path / "mobile-runtime.sqlite3"
    endpoint = "http://127.0.0.1:8788/kaka/recall/search"
    config = BridgeConfig(
        lan=True,
        bonjour=True,
        bonjour_host="192.168.1.10",
        runtime="hermes",
        hermes_profile="dev-lead",
        runtime_store_path=str(store_path),
        recall_search_provider="runtime_http",
        recall_search_endpoint=endpoint,
    )

    manifest = build_runtime_package_manifest(config, bridge_enabled=True)

    assert manifest["schema_version"] == "kaka.runtime_package.v1"
    assert manifest["runtime"] == "hermes"
    assert manifest["install"]["enabled_by_default"] is False
    assert manifest["install"]["auto_start_on_install"] is False
    assert manifest["install"]["requires_explicit_start"] is True
    assert manifest["settings_preview"]["runtime_side_ui"]["surface"] == "hermes_openclaw_settings"
    controls = manifest["settings_preview"]["runtime_side_ui"]["controls"]
    assert controls["bridge_enabled"]["value"] is True
    assert controls["bind_mode"]["value"] == "lan"
    assert controls["bonjour_enabled"]["value"] is True
    assert controls["runtime_store_path"]["value"] == str(store_path)
    assert controls["recall_search_endpoint"]["value"] == endpoint
    assert manifest["actions"]["start_bridge"] == build_server_command(config)
    assert manifest["actions"]["show_qr"] == "http://192.168.1.10:8765/mobile/v1/pairing/dev.html"
    assert manifest["follow_up_security"]["short_lived_qr"] == "development_only"
    assert manifest["follow_up_security"]["token_revocation"] == "development_only"


def test_runtime_package_manifest_marks_security_followups_ready_in_production_mode():
    manifest = build_runtime_package_manifest(
        BridgeConfig(
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            pairing_mode="production",
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
        ),
        bridge_enabled=True,
    )

    assert manifest["follow_up_security"] == {
        "short_lived_qr": "implemented",
        "token_revocation": "implemented",
        "trusted_local_tls": "metadata_ready",
    }
    assert manifest["settings_preview"]["pairing_page"].endswith("/mobile/v1/pairing/qr.html")


def test_runtime_package_manifest_exposes_consumer_ui_without_duplicate_source_of_truth():
    manifest = build_runtime_package_manifest(
        BridgeConfig(
            runtime="openclaw",
            pairing_mode="production",
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
        ),
        bridge_enabled=True,
    )

    assert manifest["consumer_ui"] == manifest["settings_preview"]["runtime_side_ui"]["consumer_ui"]
    assert manifest["consumer_ui"]["surface"] == "hermes_openclaw_consumer_runtime_ui"
    assert manifest["consumer_ui"]["status_badges"][2]["label"] == "Production QR"


def test_runtime_package_manifest_phone_safe_summary_is_allowlisted(tmp_path):
    store_path = tmp_path / "private-runtime.sqlite3"
    endpoint = "http://127.0.0.1:8788/kaka/recall/search"
    manifest = build_runtime_package_manifest(
        BridgeConfig(
            runtime_store_path=str(store_path),
            recall_search_provider="runtime_http",
            recall_search_endpoint=endpoint,
            env_file="/Users/kartz/.config/hermes/openai.env",
        ),
        bridge_enabled=True,
    )

    phone_safe = manifest["settings_preview"]["phone_safe_summary"]
    rendered_phone_safe = str(phone_safe)
    assert set(phone_safe) == {
        "recall_store_enabled",
        "recall_store_owner",
        "semantic_recall_mode",
    }
    assert str(store_path) not in rendered_phone_safe
    assert endpoint not in rendered_phone_safe
    assert "openai.env" not in rendered_phone_safe
    assert "runtime_store_path" in manifest["runtime_side_values"]
    assert "recall_search_endpoint" in manifest["runtime_side_values"]
    assert "tls_private_key_path" in manifest["runtime_side_values"]
    assert "tls_private_key_path" in manifest["forbidden_phone_safe_fields"]


def test_runtime_package_preview_command_outputs_openclaw_shell_contract(tmp_path, capsys):
    store_path = tmp_path / "mobile-runtime.sqlite3"

    exit_code = main(
        [
            "package-preview",
            "--bridge-enabled",
            "--lan",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.10",
            "--runtime",
            "openclaw",
            "--runtime-store-path",
            str(store_path),
            "--recall-search-provider",
            "fixture",
        ]
    )

    manifest = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert manifest["runtime"] == "openclaw"
    assert manifest["install"]["auto_start_on_install"] is False
    assert manifest["settings_preview_command"][manifest["settings_preview_command"].index("--runtime") + 1] == "openclaw"
    assert manifest["settings_preview"]["runtime_side_ui"]["controls"]["runtime_store_path"]["value"] == str(store_path)
    assert manifest["settings_preview"]["phone_safe_summary"]["semantic_recall_mode"] == "provider_backed"


def test_runtime_host_package_preview_declares_distribution_and_native_handoff_actions():
    package = runtime_cli.build_runtime_host_package(
        BridgeConfig(
            runtime="hermes",
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            installed=True,
            process_state="running",
            process_supervision="host_managed",
            health_status="healthy",
        ),
        bridge_enabled=True,
        distribution_source="signed_download",
        distribution_channel="stable",
        package_version="1.2.3",
        host_api_level="preview",
    )

    assert package["schema_version"] == "kaka.runtime_host_package.v1"
    assert package["surface"] == "hermes_openclaw_host_package"
    assert package["runtime"] == "hermes"
    assert package["distribution"] == {
        "source": "signed_download",
        "channel": "stable",
        "version": "1.2.3",
        "update_policy": "explicit_user_approved",
    }
    assert package["install_policy"] == {
        "enabled_by_default": False,
        "auto_start_on_install": False,
        "requires_explicit_start": True,
        "login_item_default": False,
        "creates_login_item_on_install": False,
    }
    assert [action["id"] for action in package["host_actions"]] == [
        "install_runtime_package",
        "enable_start_with_runtime",
        "disable_start_with_runtime",
        "update_runtime_package",
        "uninstall_runtime_package",
        "open_runtime_logs",
        "run_health_check",
        "repair_port_conflict",
        "supervise_bridge",
    ]
    mutating = [
        action for action in package["host_actions"]
        if action["mutates_host_state"] is True
    ]
    assert mutating
    assert all(action["requires_explicit_user_approval"] is True for action in mutating)
    assert all(action["owner"] == "host_native_adapter" for action in package["host_actions"])
    assert all("adapter" in action for action in package["host_actions"])
    assert all(action["runtime_side_only"] is True for action in package["host_actions"])
    assert package["safety"]["runtime_side_only"] is True
    assert package["safety"]["phone_settings_owner"] is False
    assert package["safety"]["no_autostart_on_install"] is True
    assert package["safety"]["no_login_item_creation_by_runtime_kit"] is True
    assert package["safety"]["requires_host_native_adapter"] is True
    assert package["process_ownership"]["state"]["installed"] is True
    assert package["consumer_ui"]["sections"][0]["id"] == "process"


def test_host_package_preview_command_outputs_handoff_contract(capsys):
    exit_code = main(
        [
            "host-package-preview",
            "--runtime",
            "openclaw",
            "--distribution-source",
            "local_checkout",
            "--distribution-channel",
            "development",
            "--package-version",
            "development",
            "--installed",
            "--process-state",
            "running",
            "--process-supervision",
            "host_managed",
            "--health-status",
            "healthy",
        ]
    )

    package = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert package["surface"] == "hermes_openclaw_host_package"
    assert package["runtime"] == "openclaw"
    assert package["distribution"]["source"] == "local_checkout"
    assert package["host_actions"][-1]["id"] == "supervise_bridge"
    assert package["artifacts"]["process_preview_command"][2] == "kaka_mobile_runtime_kit"


def test_host_extension_preview_command_outputs_installable_runtime_contract(capsys):
    exit_code = main(["host-extension-preview", "--runtime", "openclaw"])

    preview = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert preview["surface"] == "hermes_openclaw_host_extension_preview"
    assert preview["runtime"] == "openclaw"
    assert preview["ordinary_user_install"]["install_shape"] == "openclaw_skill"
    assert preview["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert preview["ordinary_user_install"]["requires_environment_variable"] is False
    assert preview["adapter_command"]["visibility"] == "extension_internal"
    assert preview["phone_api"]["base_path"] == "/mobile/v1"
    assert preview["phone_api"]["phone_api_unchanged"] is True


def test_host_extension_readiness_command_outputs_blocked_report(capsys):
    exit_code = main(["host-extension-readiness", "--runtime", "hermes"])

    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["schema_version"] == "kaka.host_extension_readiness.v1"
    assert report["runtime"] == "hermes"
    assert report["status"] == "blocked"
    assert report["ready_for_external_install_drill"] is False
    assert report["missing_inputs"][0]["id"] == "install_command"
    assert report["ordinary_user_install"]["requires_manual_adapter_code"] is False
    assert report["ordinary_user_install"]["requires_environment_variable"] is False
    assert report["adapter_command"]["visibility"] == "extension_internal"
    assert report["phone_api"]["base_path"] == "/mobile/v1"


def test_host_extension_material_intake_command_outputs_review_report(tmp_path, capsys):
    manifest_path = tmp_path / "host-extension-materials.json"
    manifest = {
        "schema_version": "kaka.host_extension_materials.v1",
        "runtime": "hermes",
        "package_facts": {
            "install_command": "hermes plugins install example/kaka-mobile --no-enable",
            "update_channel": "Hermes stable plugin channel ref 2026-06-11",
            "adapter_command_location": "extension-internal:kaka-mobile-bridge/hermes-kaka-host-api",
            "host_ui_entrypoint": "Settings > Plugins > Kaka Mobile Bridge",
            "signed_package_ref": "artifact://hermes/kaka-mobile-bridge/1.0.0/package",
            "signature_ref": "artifact://hermes/kaka-mobile-bridge/1.0.0/signature",
            "conformance_report_ref": "artifact://hermes/kaka/p3.2/conformance.json",
            "evidence_manifest_ref": "artifact://hermes/kaka/p3.4/evidence-manifest.json",
        },
        "install_drill_refs": {
            "install_receipt_ref": "artifact://hermes/kaka/p3.7/install.json",
            "enable_receipt_ref": "artifact://hermes/kaka/p3.7/enable.json",
            "pairing_receipt_ref": "artifact://hermes/kaka/p3.7/pairing.json",
            "health_receipt_ref": "artifact://hermes/kaka/p3.7/health.json",
            "revoke_repair_receipt_ref": "artifact://hermes/kaka/p3.7/revoke-repair.json",
            "update_receipt_ref": "artifact://hermes/kaka/p3.7/update.json",
            "failure_recovery_receipt_ref": "artifact://hermes/kaka/p3.7/failure-recovery.json",
            "uninstall_receipt_ref": "artifact://hermes/kaka/p3.7/uninstall.json",
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    exit_code = main(
        [
            "host-extension-material-intake",
            "--manifest",
            str(manifest_path),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["schema_version"] == "kaka.host_extension_material_intake.v1"
    assert report["status"] == "accepted_for_external_install_drill_review"
    assert report["readiness"]["status"] == "ready_for_external_install_drill"
    assert report["safety"]["does_not_install_package"] is True


def test_host_extension_material_intake_command_returns_one_for_blocked_report(
    tmp_path,
    capsys,
):
    manifest_path = tmp_path / "host-extension-materials.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "kaka.host_extension_materials.v1",
                "runtime": "hermes",
                "package_facts": {},
                "install_drill_refs": {},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "host-extension-material-intake",
            "--manifest",
            str(manifest_path),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["schema_version"] == "kaka.host_extension_material_intake.v1"
    assert report["status"] == "blocked"
    assert "install_command" in report["missing_package_facts"]


def test_host_package_preview_command_rejects_non_host_package_runtime(capsys):
    with pytest.raises(SystemExit) as error:
        main(["host-package-preview", "--runtime", "sidecar"])

    assert error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_host_package_preview_keeps_private_runtime_fields_out_of_phone_summary():
    package = runtime_cli.build_runtime_host_package(
        BridgeConfig(
            runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
        ),
        bridge_enabled=False,
    )

    safe_summary = str(package["consumer_ui"]["safe_summary"])
    assert "runtime_store_path" not in safe_summary
    assert "recall_search_endpoint" not in safe_summary
    assert package["safety"]["forbidden_phone_safe_fields"] == [
        "runtime_store_path",
        "recall_search_endpoint",
        "provider_keys",
        "auth_env_files",
        "mobile_tokens",
        "tls_private_key_paths",
        "env_file",
        "auth_file",
        "auth_files",
        "provider_credentials",
        "mobile_bearer_token",
        "tls_private_key_path",
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


def test_host_package_preview_does_not_put_lifecycle_flags_in_start_command():
    package = runtime_cli.build_runtime_host_package(
        BridgeConfig(installed=True, start_with_runtime=True),
        bridge_enabled=True,
    )

    command = package["artifacts"]["start_bridge_command"]

    assert "--installed" not in command
    assert "--start-with-runtime" not in command
    assert package["install_policy"]["auto_start_on_install"] is False


def test_static_runtime_shell_manifests_are_disabled_by_default():
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    for manifest, runtime in ((hermes_manifest, "hermes"), (openclaw_manifest, "openclaw")):
        assert manifest["schema_version"] == "kaka.runtime_shell_manifest.v1"
        assert manifest["id"] == "kaka-mobile-bridge"
        assert manifest["runtime"] == runtime
        assert manifest["install"]["enabled_by_default"] is False
        assert manifest["install"]["auto_start_on_install"] is False
        assert manifest["install"]["requires_explicit_start"] is True
        assert manifest["defaults"]["lan_exposed"] is False
        assert manifest["defaults"]["bonjour"] is False
        assert manifest["consumer_ui"]["source"] == "settings_preview.runtime_side_ui.consumer_ui"
        assert "bridge_enabled" in manifest["controls"]
        for control in (
            "pairing_mode",
            "qr_ttl_seconds",
            "trusted_local_tls",
            "revoke_mobile_tokens",
        ):
            assert control in manifest["controls"]
        assert "runtime_store_path" in manifest["runtime_side_values"]
        assert "runtime_store_path" in manifest["forbidden_phone_safe_fields"]
        assert "recall_search_endpoint" in manifest["forbidden_phone_safe_fields"]
        assert "tls_private_key_path" in manifest["runtime_side_values"]
        assert "tls_private_key_path" in manifest["forbidden_phone_safe_fields"]


def test_runtime_bridge_lan_bonjour_command_is_explicit():
    command = build_server_command(
        BridgeConfig(
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            runtime="hermes",
            hermes_profile="dev-lead",
        )
    )

    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert "--bonjour" in command
    assert command[command.index("--bonjour-host") + 1] == "192.168.1.10"
    assert command[command.index("--runtime") + 1] == "hermes"
    assert command[command.index("--hermes-profile") + 1] == "dev-lead"


def test_runtime_bridge_rejects_iphone_bonjour_without_reachable_host():
    errors = validate_start_config(BridgeConfig(bonjour=True))

    assert errors == ["Bonjour discovery for iPhone requires --lan or --bonjour-host."]


def test_runtime_bridge_requires_vision_endpoint_for_runtime_http_provider():
    errors = validate_start_config(BridgeConfig(vision_provider="runtime_http"))

    assert errors == ["--vision-endpoint is required when --vision-provider runtime_http."]


def test_runtime_bridge_requires_recall_search_endpoint_for_runtime_http_provider():
    errors = validate_start_config(BridgeConfig(recall_search_provider="runtime_http"))

    assert errors == ["--recall-search-endpoint is required when --recall-search-provider runtime_http."]


def test_runtime_bridge_rejects_malformed_recall_search_endpoint_for_runtime_http_provider():
    errors = validate_start_config(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="not-a-url",
        )
    )

    assert errors == ["--recall-search-endpoint must be an http:// or https:// URL."]


def test_runtime_bridge_rejects_public_recall_search_endpoint_for_runtime_http_provider():
    errors = validate_start_config(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="https://api.example.com/kaka/recall/search",
        )
    )

    assert errors == ["--recall-search-endpoint must point to localhost, Tailscale, or a private LAN endpoint."]


def test_runtime_start_validation_rejects_invalid_retention_days():
    errors = validate_start_config(
        BridgeConfig(
            input_assets_days=0,
            output_assets_days=3660,
            task_history_days=-1,
        )
    )

    assert "--input-assets-days must be between 1 and 3650." in errors
    assert "--output-assets-days must be between 1 and 3650." in errors
    assert "--task-history-days must be between 1 and 3650." in errors


def test_runtime_start_requires_certificate_files_for_trusted_local_tls():
    errors = validate_start_config(
        BridgeConfig(
            trusted_local_tls=True,
            tls_trust_state="configured",
            tls_certificate_label="Kaka Local Runtime",
        )
    )

    assert "--tls-certificate-chain-path is required when --trusted-local-tls starts the bridge." in errors
    assert "--tls-private-key-path is required when --trusted-local-tls starts the bridge." in errors


def test_runtime_bridge_allows_private_recall_search_endpoint_for_runtime_http_provider():
    errors = validate_start_config(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://192.168.1.20:8788/kaka/recall/search",
        )
    )

    assert errors == []


def test_runtime_bridge_allows_tailscale_recall_search_endpoint_for_runtime_http_provider():
    errors = validate_start_config(
        BridgeConfig(
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://100.64.12.34:8788/kaka/recall/search",
        )
    )

    assert errors == []


def test_runtime_bridge_environment_prepends_mock_bridge_path():
    repo_root = Path("/tmp/kaka")
    env = build_bridge_environment(
        repo_root,
        base_env={"PYTHONPATH": "existing"},
    )

    assert env["PYTHONPATH"].split(":")[0] == str((repo_root / "mock_bridge").resolve())
    assert env["PYTHONPATH"].split(":")[1] == "existing"


def test_pairing_url_points_to_development_qr_page():
    assert pairing_url("192.168.1.10", 8765) == "http://192.168.1.10:8765/mobile/v1/pairing/dev.html"


def test_doctor_report_does_not_print_secret_values():
    report = doctor_report(Path("."), photo_pack_root="photo-pack")
    rendered = str(report)

    assert "sk-" not in rendered
    assert report["checks"]["recipe_local_adapter"]["ok"] is True


def test_doctor_report_checks_anthropic_provider_key_without_printing_secret():
    report = doctor_report(
        Path("."),
        photo_pack_root="photo-pack",
        provider="anthropic",
        env={"ANTHROPIC_API_KEY": "secret-runtime-key"},
    )
    rendered = json.dumps(report, sort_keys=True)

    assert report["checks"]["anthropic_provider"]["ok"] is True
    assert report["checks"]["anthropic_provider"]["env_var"] == "ANTHROPIC_API_KEY"
    assert "secret-runtime-key" not in rendered


def test_doctor_report_checks_hermes_health_with_bearer_without_printing_secret():
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            received["path"] = self.path
            received["authorization"] = self.headers.get("Authorization", "")
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}/v1"

    try:
        report = doctor_report(
            Path("."),
            photo_pack_root="photo-pack",
            provider="hermes",
            env={
                "KAKA_HERMES_API_KEY": "secret-runtime-key",
                "KAKA_HERMES_BASE_URL": base_url,
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    rendered = json.dumps(report, sort_keys=True)
    check = report["checks"]["hermes_provider"]
    assert report["ok"] is True
    assert check["ok"] is True
    assert check["env_var"] == "KAKA_HERMES_API_KEY"
    assert check["base_url"] == base_url
    assert check["health_url"] == f"{base_url.removesuffix('/v1')}/health"
    assert check["health_probe"] == "reachable"
    assert received == {
        "path": "/health",
        "authorization": "Bearer secret-runtime-key",
    }
    assert "secret-runtime-key" not in rendered


def test_doctor_report_hermes_unreachable_prompts_manual_api_server_enablement():
    report = doctor_report(
        Path("."),
        photo_pack_root="photo-pack",
        provider="hermes",
        env={
            "KAKA_HERMES_API_KEY": "secret-runtime-key",
            "KAKA_HERMES_BASE_URL": "http://127.0.0.1:9/v1",
        },
    )

    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    check = report["checks"]["hermes_provider"]
    assert report["ok"] is False
    assert check["ok"] is False
    assert check["health_probe"] == "unreachable"
    assert "需要手动启用 Hermes API server" in check["detail"]
    assert "docs/hermes-local-integration-notes.md" in check["detail"]
    assert "secret-runtime-key" not in rendered


def test_host_plugin_skill_devkit_command_prints_preview(capsys):
    exit_code = main(["host-plugin-skill-devkit", "--runtime", "hermes"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "kaka.host_plugin_skill_devkit.v1"
    assert output["surface"] == "hermes_openclaw_host_plugin_skill_devkit"
    assert output["runtime"] == "hermes"
    assert output["written"] is False
    assert output["developer_kit_only"] is True
    assert output["ordinary_user_install"] is False
    assert output["codex_automation"]["ordinary_user_install_surface"] is False
    assert output["phone_api"]["base_path"] == "/mobile/v1"


def test_host_plugin_skill_devkit_command_writes_output(tmp_path, capsys):
    exit_code = main(
        [
            "host-plugin-skill-devkit",
            "--runtime",
            "openclaw",
            "--output-dir",
            str(tmp_path),
            "--write",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["written"] is True
    assert Path(output["output_root"]).name == "kaka-mobile-bridge-openclaw-devkit"


def test_host_codex_developer_plugin_source_command_prints_preview(capsys):
    exit_code = main(["host-codex-developer-plugin-source", "--runtime", "hermes"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "kaka.host_codex_developer_plugin_source.v1"
    assert output["surface"] == "hermes_openclaw_host_codex_developer_plugin_source"
    assert output["runtime"] == "hermes"
    assert output["written"] is False
    assert output["developer_only"] is True
    assert output["ordinary_user_install"] is False
    assert output["codex_install"]["installs_codex_plugin"] is False
    assert output["codex_install"]["updates_marketplace"] is False
    assert output["codex_install"]["writes_user_home"] is False
    assert output["phone_api"]["base_path"] == "/mobile/v1"


def test_host_codex_developer_plugin_source_command_writes_output(tmp_path, capsys):
    exit_code = main(
        [
            "host-codex-developer-plugin-source",
            "--runtime",
            "openclaw",
            "--output-dir",
            str(tmp_path),
            "--write",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    root = Path(output["output_root"])
    assert exit_code == 0
    assert output["written"] is True
    assert root.name == "kaka-host-extension-developer-openclaw"
    assert (root / ".codex-plugin" / "plugin.json").exists()
    assert (root / "skills" / "kaka-host-extension-developer" / "SKILL.md").exists()
    assert not (root / ".agents" / "plugins" / "marketplace.json").exists()


def test_host_codex_developer_plugin_source_write_requires_explicit_output_dir():
    with pytest.raises(SystemExit) as error:
        main(["host-codex-developer-plugin-source", "--runtime", "hermes", "--write"])

    assert error.value.code == 2


@pytest.mark.parametrize(
    "forbidden",
    [
        Path.home() / "plugins",
        Path.home() / ".codex" / "skills",
        Path.home() / ".agents" / "plugins",
    ],
)
def test_host_codex_developer_plugin_source_rejects_user_install_roots(forbidden):
    with pytest.raises(ValueError, match="Refusing to write"):
        main(
            [
                "host-codex-developer-plugin-source",
                "--runtime",
                "hermes",
                "--output-dir",
                str(forbidden),
                "--write",
            ]
        )
