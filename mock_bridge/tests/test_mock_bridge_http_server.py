import json
import os
import threading
import urllib.request

from agent_pocket_mock_bridge import server as server_module
from agent_pocket_mock_bridge.server import BonjourAdvertisement, build_app_for_provider, create_http_server


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

    def build_app(photo_provider, photo_pack_root):
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

    def build_app(photo_provider, photo_pack_root):
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

    def build_app(photo_provider, photo_pack_root):
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

    def build_app(photo_provider, photo_pack_root):
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

    def build_app(photo_provider, photo_pack_root):
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

    def build_app(photo_provider, photo_pack_root):
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
