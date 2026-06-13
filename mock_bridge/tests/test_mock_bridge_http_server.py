import json
import os
import threading
import urllib.request

from agent_pocket_mock_bridge import server as server_module
from agent_pocket_mock_bridge.app import create_app
from agent_pocket_mock_bridge.server import BonjourAdvertisement, build_app_for_provider, create_http_server
from kaka_mobile_runtime_kit.pairing import PairingManager


def test_http_server_runs_photo_edit_lifecycle_over_real_requests():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        health = _json_request(f"{base_url}/mobile/v1/health")
        assert health["runtime"] == "hermes"

        upload_body, upload_content_type = _multipart_body(
            {
                "metadata": '{"width":100,"height":100}',
            },
            {
                "file": ("photo.jpg", "image/jpeg", b"source-image"),
            },
        )
        upload = _json_request(
            f"{base_url}/mobile/v1/assets",
            method="POST",
            body=upload_body,
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": upload_content_type,
            },
        )

        created = _json_request(
            f"{base_url}/mobile/v1/tasks/photo-edit",
            method="POST",
            body=json.dumps(
                {
                    "profile_id": "photo-agent",
                    "asset_id": upload["asset_id"],
                    "style": "natural_enhance",
                    "instruction": "Keep it realistic.",
                    "return_variants": 1,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": "application/json",
            },
        )

        status = _json_request(
            f"{base_url}/mobile/v1/tasks/{created['task_id']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        variant = status["variants"][0]
        download = _raw_request(
            f"{base_url}{variant['download_url']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        qa_status = _json_request(
            f"{base_url}/mobile/v1/qa/status",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert status["status"] == "completed"
        assert download.startswith(b"\x89PNG")
        assert qa_status["assets"]["uploaded_count"] == 1
        assert qa_status["assets"]["download_request_count"] == 1
        assert qa_status["tasks"]["completed"] == 1
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_server_serves_development_pairing_payload():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        payload = _json_request(f"{base_url}/mobile/v1/pairing/dev")

        assert payload["endpoint"] == base_url
        assert payload["pairing_code"] == "pair_dev"
        assert payload["runtime"] == "hermes"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_server_supports_recall_delete():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    headers = {
        "Authorization": "Bearer dev-mobile-token",
        "Content-Type": "application/json",
    }

    try:
        remembered = _json_request(
            f"{base_url}/mobile/v1/recall/actions",
            method="POST",
            body=json.dumps(
                {
                    "action": "remember",
                    "source_task_id": "task_123",
                    "user_visible_summary": "Remember this through the HTTP server.",
                }
            ).encode("utf-8"),
            headers=headers,
        )
        item_id = remembered["item"]["item_id"]

        deleted = _json_request(
            f"{base_url}/mobile/v1/recall/items/{item_id}",
            method="DELETE",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert deleted == {
            "status": "forgotten",
            "deleted_item_ids": [item_id],
            "deleted_index_ids": [f"embedding_{item_id}"],
        }
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_server_supports_recall_query_and_limit():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    headers = {
        "Authorization": "Bearer dev-mobile-token",
        "Content-Type": "application/json",
    }

    try:
        for summary in [
            "Remember Chinese summaries.",
            "Keep the PDF upload limit visible.",
            "Prefer concise Chinese answers.",
        ]:
            _json_request(
                f"{base_url}/mobile/v1/recall/actions",
                method="POST",
                body=json.dumps(
                    {
                        "action": "remember",
                        "source_task_id": f"task_{summary[:4].lower()}",
                        "user_visible_summary": summary,
                    }
                ).encode("utf-8"),
                headers=headers,
            )

        listed = _json_request(
            f"{base_url}/mobile/v1/recall/items?query=Chinese&limit=1",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert [item["item_id"] for item in listed["items"]] == ["recall_0003"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_server_supports_recall_semantic_search():
    server = create_http_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    headers = {
        "Authorization": "Bearer dev-mobile-token",
        "Content-Type": "application/json",
    }

    try:
        _json_request(
            f"{base_url}/mobile/v1/recall/actions",
            method="POST",
            body=json.dumps(
                {
                    "action": "remember",
                    "source_task_id": "task_http_search",
                    "user_visible_summary": "HTTP launch summary language preference.",
                }
            ).encode("utf-8"),
            headers=headers,
        )

        searched = _json_request(
            f"{base_url}/mobile/v1/recall/search",
            method="POST",
            body=json.dumps({"query": "launch summary language", "limit": 5}).encode("utf-8"),
            headers=headers,
        )

        assert searched["query"] == "launch summary language"
        assert searched["mode"] == "semantic"
        assert searched["items"][0]["item"]["summary"] == "HTTP launch summary language preference."
        assert searched["items"][0]["score"] > 0
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_server_runtime_store_path_preserves_recall_after_restart(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    first_store = SQLiteRuntimeStore(db_path)
    first_store.initialize()
    first_server = create_http_server("127.0.0.1", 0, app=create_app(runtime_store=first_store))
    first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
    first_thread.start()
    first_base_url = f"http://127.0.0.1:{first_server.server_address[1]}"
    headers = {
        "Authorization": "Bearer dev-mobile-token",
        "Content-Type": "application/json",
    }

    try:
        _json_request(
            f"{first_base_url}/mobile/v1/recall/actions",
            method="POST",
            body=json.dumps(
                {
                    "action": "remember",
                    "source_task_id": "task_http",
                    "user_visible_summary": "HTTP persistent Recall.",
                }
            ).encode("utf-8"),
            headers=headers,
        )
    finally:
        first_server.shutdown()
        first_thread.join(timeout=2)
        first_server.server_close()

    reopened_store = SQLiteRuntimeStore(db_path)
    reopened_store.initialize()
    second_server = create_http_server("127.0.0.1", 0, app=create_app(runtime_store=reopened_store))
    second_thread = threading.Thread(target=second_server.serve_forever, daemon=True)
    second_thread.start()
    second_base_url = f"http://127.0.0.1:{second_server.server_address[1]}"

    try:
        response = _json_request(
            f"{second_base_url}/mobile/v1/recall/items?query=HTTP",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert [item["summary"] for item in response["items"]] == ["HTTP persistent Recall."]
    finally:
        second_server.shutdown()
        second_thread.join(timeout=2)
        second_server.server_close()


def test_http_server_runtime_store_preserves_image_intake_result_after_restart(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    first_store = SQLiteRuntimeStore(db_path)
    first_store.initialize()
    first_server = create_http_server("127.0.0.1", 0, app=create_app(runtime_store=first_store))
    first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
    first_thread.start()
    first_base_url = f"http://127.0.0.1:{first_server.server_address[1]}"
    headers = {
        "Authorization": "Bearer dev-mobile-token",
        "Content-Type": "application/json",
    }

    try:
        upload_body, upload_content_type = _multipart_body(
            {"metadata": '{"width":100,"height":100}'},
            {"file": ("photo.jpg", "image/jpeg", b"source-image")},
        )
        upload = _json_request(
            f"{first_base_url}/mobile/v1/assets",
            method="POST",
            body=upload_body,
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": upload_content_type,
            },
        )
        created = _json_request(
            f"{first_base_url}/mobile/v1/tasks/image-intake",
            method="POST",
            body=json.dumps(
                {
                    "profile_id": "photo-agent",
                    "asset_id": upload["asset_id"],
                    "locale": "en",
                }
            ).encode("utf-8"),
            headers=headers,
        )
    finally:
        first_server.shutdown()
        first_thread.join(timeout=2)
        first_server.server_close()

    reopened_store = SQLiteRuntimeStore(db_path)
    reopened_store.initialize()
    second_server = create_http_server("127.0.0.1", 0, app=create_app(runtime_store=reopened_store))
    second_thread = threading.Thread(target=second_server.serve_forever, daemon=True)
    second_thread.start()
    second_base_url = f"http://127.0.0.1:{second_server.server_address[1]}"

    try:
        status = _json_request(
            f"{second_base_url}/mobile/v1/tasks/{created['task_id']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert status["status"] == "completed"
        assert status["result_type"] == "image_intake"
        assert status["image_intake"]["title"]
        assert status["image_intake"]["suggestions"]
    finally:
        second_server.shutdown()
        second_thread.join(timeout=2)
        second_server.server_close()


def test_bonjour_advertisement_publishes_discoverable_pairing_metadata():
    launched_commands = []
    process = FakeProcess()

    def launch(command):
        launched_commands.append(command)
        return process

    advertisement = BonjourAdvertisement(
        name="Agent Pocket Mock Hermes",
        host="192.168.1.42",
        port=8765,
        pairing_code="pair_dev",
        launcher=launch,
    )

    advertisement.start()
    advertisement.stop()

    assert launched_commands == [
        [
            "dns-sd",
            "-R",
            "Agent Pocket Mock Hermes",
            "_agent-pocket._tcp",
            "local",
            "8765",
            "display_name=Agent Pocket Mock Hermes",
            "runtime=hermes",
            "scheme=http",
            "endpoint=http://192.168.1.42:8765",
            "pairing_code=pair_dev",
            "expires_at=2099-01-01T00:00:00Z",
        ]
    ]
    assert process.terminated is True
    assert process.wait_timeout == 2


def test_server_builds_app_with_named_photo_provider():
    app = build_app_for_provider("script", photo_pack_root="photo-pack")

    assert app.photo_provider.adapter_path.name == "script.py"


def test_server_builds_app_with_recall_search_provider():
    app = build_app_for_provider(
        recall_search_provider="runtime_http",
        recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
    )

    settings = app.handle(
        "GET",
        "/mobile/v1/runtime/settings",
        headers={"Authorization": "Bearer dev-mobile-token"},
    ).get_json()
    rendered = str(settings)
    assert settings["semantic_recall"]["mode"] == "provider_backed"
    assert "127.0.0.1:8788" not in rendered


def test_server_cli_accepts_recall_search_provider_and_endpoint():
    args = server_module.build_parser().parse_args(
        [
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "http://127.0.0.1:8788/kaka/recall/search",
        ]
    )

    assert args.recall_search_provider == "runtime_http"
    assert args.recall_search_endpoint == "http://127.0.0.1:8788/kaka/recall/search"


def test_server_cli_accepts_explicit_anthropic_provider():
    args = server_module.build_parser().parse_args(["--provider", "anthropic"])

    assert args.provider == "anthropic"


def test_server_cli_accepts_explicit_hermes_provider():
    args = server_module.build_parser().parse_args(["--provider", "hermes"])

    assert args.provider == "hermes"


def test_server_cli_requires_anthropic_api_key_for_anthropic_provider(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    args = server_module.build_parser().parse_args(["--provider", "anthropic"])

    assert server_module.validate_server_config(args) == [
        "--provider anthropic requires ANTHROPIC_API_KEY in the runtime environment."
    ]


def test_server_cli_requires_hermes_api_key_for_hermes_provider(monkeypatch):
    monkeypatch.delenv("KAKA_HERMES_API_KEY", raising=False)
    args = server_module.build_parser().parse_args(["--provider", "hermes"])

    assert server_module.validate_server_config(args) == [
        "--provider hermes requires KAKA_HERMES_API_KEY in the runtime environment."
    ]


def test_server_builds_app_with_anthropic_provider(monkeypatch):
    class FakeAnthropicProvider:
        provider_name = "anthropic"

        def analyze(self, source_bytes, mode, instruction, locale):
            return {"mode": mode, "title": "ok", "summary": "ok"}

        def image_intake(self, source_bytes, mime_type, locale=None):
            return {
                "image_type": "photo",
                "title": "Photo",
                "summary": "Photo ready.",
                "suggestions": [],
            }

        def universal_intake(self, intake_type, payload, source_bytes=None, mime_type=""):
            return {"title": "Ready", "summary": "Ready.", "suggestions": []}

    monkeypatch.setattr(server_module, "build_anthropic_provider", lambda: FakeAnthropicProvider())

    app = build_app_for_provider(provider="anthropic")

    assert app.vision_provider.provider_name == "anthropic"
    assert app.intake_provider.provider_name == "anthropic"


def test_server_builds_app_with_hermes_provider(monkeypatch):
    class FakeHermesProvider:
        provider_name = "hermes"

        def analyze(self, source_bytes, mode, instruction, locale):
            return {"mode": mode, "title": "ok", "summary": "ok"}

        def image_intake(self, source_bytes, mime_type, locale=None):
            return {
                "image_type": "photo",
                "title": "Photo",
                "summary": "Photo ready.",
                "suggestions": [],
            }

        def universal_intake(self, intake_type, payload, source_bytes=None, mime_type=""):
            return {"title": "Ready", "summary": "Ready.", "suggestions": []}

    monkeypatch.setattr(server_module, "build_hermes_provider", lambda: FakeHermesProvider(), raising=False)

    app = build_app_for_provider(provider="hermes")

    assert app.vision_provider.provider_name == "hermes"
    assert app.intake_provider.provider_name == "hermes"


def test_server_cli_requires_recall_search_endpoint_for_runtime_http_provider():
    args = server_module.build_parser().parse_args(["--recall-search-provider", "runtime_http"])

    assert server_module.validate_server_config(args) == [
        "--recall-search-endpoint is required when --recall-search-provider runtime_http."
    ]


def test_server_cli_rejects_malformed_recall_search_endpoint_for_runtime_http_provider():
    args = server_module.build_parser().parse_args(
        [
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "not-a-url",
        ]
    )

    assert server_module.validate_server_config(args) == [
        "--recall-search-endpoint must be an http:// or https:// URL."
    ]


def test_server_cli_rejects_public_recall_search_endpoint_for_runtime_http_provider():
    args = server_module.build_parser().parse_args(
        [
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "https://api.example.com/kaka/recall/search",
        ]
    )

    assert server_module.validate_server_config(args) == [
        "--recall-search-endpoint must point to localhost, Tailscale, or a private LAN endpoint."
    ]


def test_server_cli_allows_tailscale_recall_search_endpoint_for_runtime_http_provider():
    args = server_module.build_parser().parse_args(
        [
            "--recall-search-provider",
            "runtime_http",
            "--recall-search-endpoint",
            "http://100.64.12.34:8788/kaka/recall/search",
        ]
    )

    assert server_module.validate_server_config(args) == []


def test_server_validation_rejects_invalid_retention_days():
    args = server_module.build_parser().parse_args(
        [
            "--input-assets-days",
            "0",
            "--output-assets-days",
            "3660",
            "--task-history-days",
            "-1",
        ]
    )

    assert server_module.validate_server_config(args) == [
        "--input-assets-days must be between 1 and 3650.",
        "--output-assets-days must be between 1 and 3650.",
        "--task-history-days must be between 1 and 3650.",
    ]


def test_server_validation_requires_certificate_files_for_trusted_local_tls():
    args = server_module.build_parser().parse_args(["--trusted-local-tls"])

    assert server_module.validate_server_config(args) == [
        "--tls-certificate-chain-path is required when --trusted-local-tls starts the bridge.",
        "--tls-private-key-path is required when --trusted-local-tls starts the bridge.",
    ]


def test_server_parser_accepts_production_pairing_security_flags():
    args = server_module.build_parser().parse_args(
        [
            "--pairing-mode",
            "production",
            "--pairing-code-ttl-seconds",
            "120",
            "--token-ttl-seconds",
            "3600",
            "--trusted-local-tls",
            "--tls-trust-state",
            "configured",
            "--tls-certificate-label",
            "Kaka Local Runtime",
            "--tls-public-key-sha256",
            "c" * 64,
        ]
    )

    assert args.pairing_mode == "production"
    assert args.pairing_code_ttl_seconds == 120
    assert args.token_ttl_seconds == 3600
    assert args.trusted_local_tls is True
    assert args.tls_trust_state == "configured"
    assert args.tls_certificate_label == "Kaka Local Runtime"
    assert args.tls_public_key_sha256 == "c" * 64


def test_build_app_for_production_pairing_uses_runtime_store_when_available(tmp_path):
    args = server_module.build_parser().parse_args(
        [
            "--pairing-mode",
            "production",
            "--runtime-store-path",
            str(tmp_path / "runtime.sqlite3"),
        ]
    )

    app = server_module._build_app_with_optional_vision(args)

    assert isinstance(app.pairing_manager, PairingManager)
    assert app.runtime_store is not None
    assert app.pairing_manager.store is app.runtime_store


def test_build_app_for_production_pairing_passes_runtime_name_and_http_scheme():
    args = server_module.build_parser().parse_args(
        [
            "--pairing-mode",
            "production",
            "--runtime",
            "openclaw",
            "--bonjour-name",
            "Agent Pocket Mock OpenClaw",
        ]
    )

    app = server_module._build_app_with_optional_vision(args)
    payload = app.test_client().get(
        "/mobile/v1/pairing/qr",
        headers={"Host": "127.0.0.1:8765"},
    ).get_json()

    assert payload["endpoint"] == "http://127.0.0.1:8765"
    assert payload["runtime"] == "openclaw"
    assert payload["display_name"] == "Agent Pocket Mock OpenClaw"


def test_create_http_server_wraps_socket_when_tls_paths_are_supplied(monkeypatch):
    calls = {}

    class FakeContext:
        def load_cert_chain(self, *, certfile, keyfile):
            calls["certfile"] = certfile
            calls["keyfile"] = keyfile

        def wrap_socket(self, socket, *, server_side):
            calls["server_side"] = server_side
            calls["socket_wrapped"] = True
            return socket

    monkeypatch.setattr(server_module.ssl, "create_default_context", lambda purpose: FakeContext())

    server = create_http_server(
        host="127.0.0.1",
        port=0,
        tls_certificate_chain_path="/tmp/kaka-local-runtime.crt",
        tls_private_key_path="/tmp/kaka-local-runtime.key",
    )
    try:
        assert calls == {
            "certfile": "/tmp/kaka-local-runtime.crt",
            "keyfile": "/tmp/kaka-local-runtime.key",
            "server_side": True,
            "socket_wrapped": True,
        }
    finally:
        server.server_close()


def test_production_bonjour_advertisement_uses_https_scheme_without_static_pair_dev():
    command = BonjourAdvertisement(
        name="Kaka Mobile Bridge",
        host="192.168.1.10",
        port=8765,
        pairing_code="",
        runtime="hermes",
        scheme="https",
        pairing_page="https://192.168.1.10:8765/mobile/v1/pairing/qr.html",
        expires_at="",
    ).command()
    rendered = " ".join(command)

    assert "scheme=https" in command
    assert "pairing_page=https://192.168.1.10:8765/mobile/v1/pairing/qr.html" in command
    assert "pairing_code=pair_dev" not in rendered
    assert "expires_at=2099-01-01T00:00:00Z" not in rendered


def test_server_cli_loads_env_file_only_for_provider_process_without_leaking(monkeypatch, tmp_path, capsys):
    env_file = tmp_path / "hermes-openai.env"
    env_file.write_text(
        "OPENAI_API_KEY=secret-from-hermes-env\n"
        "OPENAI_BASE_URL=http://127.0.0.1:7788/v1\n",
        encoding="utf-8",
    )
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-env"
            observations["base_url_during_serve"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["photo_pack_root"] = photo_pack_root
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-env"
        observations["base_url_during_build"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
        "--env-file",
        str(env_file),
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["base_url_during_build"] is True
    assert observations["during_serve"] is True
    assert observations["base_url_during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("OPENAI_BASE_URL") is None
    assert "secret-from-hermes-env" not in output


def test_server_cli_loads_hermes_force_env_without_leaking(monkeypatch, capsys):
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-force"
            observations["base_url_during_serve"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-force"
        observations["base_url_during_build"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("_HERMES_FORCE_OPENAI_API_KEY", "secret-from-hermes-force")
    monkeypatch.setenv("_HERMES_FORCE_OPENAI_BASE_URL", "http://127.0.0.1:7788/v1")

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["base_url_during_build"] is True
    assert observations["during_serve"] is True
    assert observations["base_url_during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("OPENAI_BASE_URL") is None
    assert "secret-from-hermes-force" not in output


def test_server_cli_loads_hermes_profile_env_without_leaking(monkeypatch, tmp_path, capsys):
    profile_root = tmp_path / ".hermes" / "profiles" / "dev-lead"
    profile_root.mkdir(parents=True)
    (profile_root / ".env").write_text("OPENAI_API_KEY=secret-from-hermes-profile\n", encoding="utf-8")
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-profile"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["photo_pack_root"] = photo_pack_root
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-profile"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
        "--hermes-home",
        str(tmp_path / ".hermes"),
        "--hermes-profile",
        "dev-lead",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert "secret-from-hermes-profile" not in output


def test_server_cli_loads_hermes_home_env_without_leaking(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("OPENAI_API_KEY=secret-from-hermes-home\n", encoding="utf-8")
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-home"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-home"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
        "--hermes-home",
        str(hermes_home),
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert "secret-from-hermes-home" not in output


def test_server_cli_loads_hermes_openai_auth_api_key_without_leaking(monkeypatch, tmp_path, capsys):
    profile_root = tmp_path / ".hermes" / "profiles" / "dev-lead"
    profile_root.mkdir(parents=True)
    (profile_root / ".env").write_text("", encoding="utf-8")
    (profile_root / "auth.json").write_text(json.dumps({
        "version": 1,
        "credential_pool": {
            "openai": [
                {
                    "label": "images-key",
                    "auth_type": "api_key",
                    "access_token": "secret-from-hermes-auth",
                    "base_url": "http://127.0.0.1:7788/v1",
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
    }), encoding="utf-8")
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-auth"
            observations["base_url_during_serve"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-hermes-auth"
        observations["base_url_during_build"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
        "--hermes-home",
        str(tmp_path / ".hermes"),
        "--hermes-profile",
        "dev-lead",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["base_url_during_build"] is True
    assert observations["during_serve"] is True
    assert observations["base_url_during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("OPENAI_BASE_URL") is None
    assert "secret-from-hermes-auth" not in output
    assert "codex-token-that-must-not-leak" not in output


def test_server_cli_loads_hermes_shared_auth_api_key_without_leaking(monkeypatch, tmp_path, capsys):
    hermes_home = tmp_path / ".hermes"
    profile_root = hermes_home / "profiles" / "dev-lead"
    profile_root.mkdir(parents=True)
    (profile_root / ".env").write_text("", encoding="utf-8")
    (profile_root / "auth.json").write_text(json.dumps({
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
    }), encoding="utf-8")
    shared_auth_root = hermes_home / "shared-auth"
    shared_auth_root.mkdir(parents=True)
    (shared_auth_root / "auth.json").write_text(json.dumps({
        "version": 1,
        "credential_pool": {
            "openai": [
                {
                    "label": "shared-images-key",
                    "auth_type": "api_key",
                    "access_token": "secret-from-shared-hermes-auth",
                    "base_url": "http://127.0.0.1:7788/v1",
                }
            ],
        },
    }), encoding="utf-8")
    observations = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            observations["during_serve"] = os.environ.get("OPENAI_API_KEY") == "secret-from-shared-hermes-auth"
            observations["base_url_during_serve"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"

        def server_close(self):
            observations["closed"] = True

    def build_app(photo_provider, photo_pack_root, **kwargs):
        observations["photo_provider"] = photo_provider
        observations["during_build"] = os.environ.get("OPENAI_API_KEY") == "secret-from-shared-hermes-auth"
        observations["base_url_during_build"] = os.environ.get("OPENAI_BASE_URL") == "http://127.0.0.1:7788/v1"
        return object()

    def create_server(host, port, app):
        observations["host"] = host
        observations["port"] = port
        observations["app"] = app
        return FakeServer()

    monkeypatch.setattr(server_module, "build_app_for_provider", build_app)
    monkeypatch.setattr(server_module, "create_http_server", create_server)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code = server_module.main([
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
        "--photo-provider",
        "openai",
        "--hermes-home",
        str(hermes_home),
        "--hermes-profile",
        "dev-lead",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert observations["photo_provider"] == "openai"
    assert observations["during_build"] is True
    assert observations["base_url_during_build"] is True
    assert observations["during_serve"] is True
    assert observations["base_url_during_serve"] is True
    assert observations["closed"] is True
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("OPENAI_BASE_URL") is None
    assert "secret-from-shared-hermes-auth" not in output
    assert "codex-token-that-must-not-leak" not in output


def test_http_server_can_run_script_photo_pack_provider():
    app = build_app_for_provider("script", photo_pack_root="photo-pack")
    server = create_http_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        upload_body, upload_content_type = _multipart_body(
            {"metadata": '{"width":100,"height":100}'},
            {"file": ("photo.jpg", "image/jpeg", b"source-image")},
        )
        upload = _json_request(
            f"{base_url}/mobile/v1/assets",
            method="POST",
            body=upload_body,
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": upload_content_type,
            },
        )
        created = _json_request(
            f"{base_url}/mobile/v1/tasks/photo-edit",
            method="POST",
            body=json.dumps(
                {
                    "profile_id": "photo-agent",
                    "asset_id": upload["asset_id"],
                    "style": "natural_enhance",
                    "instruction": "Keep it realistic.",
                    "return_variants": 1,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": "application/json",
            },
        )
        status = _json_request(
            f"{base_url}/mobile/v1/tasks/{created['task_id']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        download = _raw_request(
            f"{base_url}{status['variants'][0]['download_url']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )

        assert status["status"] == "completed"
        assert status["variants"][0]["label"] == "Natural Enhance"
        assert download == b"source-image"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _json_request(url, method="GET", body=None, headers=None):
    raw = _raw_request(url, method=method, body=body, headers=headers)
    return json.loads(raw.decode("utf-8"))


def _raw_request(url, method="GET", body=None, headers=None):
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read()


def _multipart_body(fields, files):
    boundary = "agent-pocket-test-boundary"
    chunks = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, (filename, mime_type, data) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
                data,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.wait_timeout = None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_timeout = timeout
