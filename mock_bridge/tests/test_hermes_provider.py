import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent_pocket_mock_bridge.app import create_app


class FakeHermesState:
    def __init__(self):
        self.api_key = "test-secret"
        self.model_id = "jiqimao"
        self.health_status = 200
        self.models_status = 200
        self.chat_status = 200
        self.chat_delay = 0.0
        self.chat_error_body = {"error": {"message": "provider rejected the request"}}
        self.chat_raw_response = None
        self.chat_responses = [
            _chat_completion(
                {
                    "image_type": "photo",
                    "title": "Image ready",
                    "summary": "Hermes inspected the image.",
                    "confidence": 0.91,
                    "suggestions": [],
                }
            )
        ]
        self.requests = []


class FakeHermesHandler(BaseHTTPRequestHandler):
    server: ThreadingHTTPServer

    def do_GET(self):
        state = self.server.state
        state.requests.append(
            {
                "method": "GET",
                "path": self.path,
                "authorized": self.headers.get("Authorization") == f"Bearer {state.api_key}",
            }
        )
        if self.path == "/health":
            self._send_json({"ok": state.health_status < 400}, status=state.health_status)
            return
        if self.path == "/v1/models":
            self._send_json(
                {"object": "list", "data": [{"id": state.model_id}]},
                status=state.models_status,
            )
            return
        self._send_json({"error": {"message": "not found"}}, status=404)

    def do_POST(self):
        state = self.server.state
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length > 0 else b""
        decoded = json.loads(body.decode("utf-8")) if body else {}
        state.requests.append(
            {
                "method": "POST",
                "path": self.path,
                "authorized": self.headers.get("Authorization") == f"Bearer {state.api_key}",
                "json": decoded,
            }
        )
        if state.chat_delay:
            time.sleep(state.chat_delay)
        if self.path != "/v1/chat/completions":
            self._send_json({"error": {"message": "not found"}}, status=404)
            return
        if state.chat_status >= 400:
            self._send_json(state.chat_error_body, status=state.chat_status)
            return
        if state.chat_raw_response is not None:
            self._send_raw(state.chat_raw_response, status=state.chat_status)
            return
        response = state.chat_responses.pop(0) if state.chat_responses else _chat_completion({})
        self._send_json(response, status=state.chat_status)

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, status=200):
        encoded = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_raw(self, payload, status=200):
        encoded = payload.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            return


class FakeHermesServer:
    def __init__(self, state=None):
        self.state = state or FakeHermesState()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHermesHandler)
        self.server.state = self.state
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def test_hermes_provider_discovers_model_posts_image_url_block_and_parses_image_intake(monkeypatch):
    state = FakeHermesState()
    state.chat_responses = [
        _chat_completion(
            {
                "image_type": "text",
                "title": "Receipt",
                "summary": "A receipt with readable totals.",
                "confidence": 0.91,
                "suggestions": [
                    {
                        "skill": "ocr",
                        "title": "Extract Text",
                        "reason": "The receipt has printed text.",
                        "confidence": 0.94,
                    }
                ],
            }
        )
    ]
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        monkeypatch.delenv("KAKA_HERMES_MODEL", raising=False)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        result = provider.image_intake(b"image-bytes", "image/png", locale="en")

    chat_request = next(request for request in state.requests if request["method"] == "POST")
    content = chat_request["json"]["messages"][0]["content"]
    image_block = next(block for block in content if block["type"] == "image_url")
    text_block = next(block for block in content if block["type"] == "text")

    assert [request["path"] for request in state.requests[:2]] == ["/health", "/v1/models"]
    assert all(request["authorized"] for request in state.requests)
    assert chat_request["json"]["model"] == "jiqimao"
    assert chat_request["json"]["stream"] is False
    assert image_block == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,aW1hZ2UtYnl0ZXM="},
    }
    assert "Respond with one JSON object only" in text_block["text"]
    assert result["image_type"] == "text"
    assert result["suggestions"][0]["skill"] == "ocr"
    assert result["suggestions"][0]["is_available"] is True


def test_hermes_provider_uses_explicit_model_after_model_probe_for_universal_url(monkeypatch):
    state = FakeHermesState()
    state.chat_responses = [
        _chat_completion(
            {
                "title": "Shared link",
                "summary": "The link asks Hermes to summarize a page.",
                "suggestions": [{"id": "summarize", "label": "Summarize"}],
            }
        )
    ]
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        monkeypatch.setenv("KAKA_HERMES_MODEL", "explicit-hermes-model")
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        result = provider.universal_intake(
            "url",
            {"type": "url", "url": "https://example.com/story", "source_app": "Safari"},
        )

    chat_request = next(request for request in state.requests if request["method"] == "POST")
    content = chat_request["json"]["messages"][0]["content"]

    assert "/v1/models" in [request["path"] for request in state.requests]
    assert chat_request["json"]["model"] == "explicit-hermes-model"
    assert [block["type"] for block in content] == ["text", "text"]
    assert "https://example.com/story" in "\n".join(block["text"] for block in content)
    assert result["title"] == "Shared link"
    assert result["suggestions"][0]["requires_confirmation"] is False


def test_hermes_vision_skill_posts_image_url_block_and_parses_result(monkeypatch):
    state = FakeHermesState()
    state.chat_responses = [
        _chat_completion(
            {
                "mode": "scan",
                "title": "OCR",
                "summary": "Visible text was extracted.",
                "text": "HELLO",
                "language": "en",
                "confidence": 0.88,
                "sections": [],
                "items": [],
            }
        )
    ]
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        result = provider.analyze(
            b"image-bytes",
            mode="scan",
            instruction="Read the sign.",
            locale="en",
            mime_type="image/jpeg",
        )

    chat_request = next(request for request in state.requests if request["method"] == "POST")
    content = chat_request["json"]["messages"][0]["content"]
    image_block = next(block for block in content if block["type"] == "image_url")

    assert result["mode"] == "scan"
    assert result["text"] == "HELLO"
    assert image_block["image_url"]["url"] == "data:image/jpeg;base64,aW1hZ2UtYnl0ZXM="


def test_hermes_universal_image_intake_posts_image_url_block(monkeypatch):
    state = FakeHermesState()
    state.chat_responses = [
        _chat_completion(
            {
                "title": "Screenshot",
                "summary": "The screenshot is ready for follow-up.",
                "suggestions": [{"id": "open_image_conversation", "label": "Open Image Conversation"}],
                "image_intake": {
                    "image_type": "screenshot",
                    "title": "Screenshot",
                    "summary": "A screenshot with visible UI.",
                    "confidence": 0.82,
                    "suggestions": [{"skill": "ocr", "title": "Extract Text", "reason": "UI text", "confidence": 0.9}],
                },
            }
        )
    ]
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        result = provider.universal_intake(
            "image",
            {"type": "image", "source_app": "Screenshots"},
            source_bytes=b"image-bytes",
            mime_type="image/png",
        )

    chat_request = next(request for request in state.requests if request["method"] == "POST")
    content = chat_request["json"]["messages"][0]["content"]
    image_block = next(block for block in content if block["type"] == "image_url")

    assert result["title"] == "Screenshot"
    assert result["image_intake"]["suggestions"][0]["is_available"] is True
    assert image_block["image_url"]["url"] == "data:image/png;base64,aW1hZ2UtYnl0ZXM="


def test_hermes_http_401_becomes_failed_vision_task_status_without_key_leak(monkeypatch):
    state = FakeHermesState()
    state.chat_status = 401
    state.chat_error_body = {"error": {"message": "bad key test-secret"}}
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        client = create_app(vision_provider=provider, intake_provider=provider).test_client()
        headers = {"Authorization": "Bearer dev-mobile-token"}
        upload = client.post(
            "/mobile/v1/assets",
            headers=headers,
            data={"file": (io.BytesIO(b"image-bytes"), "photo.jpg", "image/jpeg")},
        )

        created = client.post(
            "/mobile/v1/tasks/vision",
            headers=headers,
            json={
                "asset_id": upload.get_json()["asset_id"],
                "mode": "identify",
                "instruction": "Identify the subject.",
                "locale": "en",
            },
        )
        status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    body = status.get_json()
    rendered = json.dumps(body, sort_keys=True)

    assert created.status_code == 200
    assert body["status"] == "failed"
    assert body["failure_code"] == "vision_failed"
    assert body["provider"] == "hermes"
    assert "test-secret" not in rendered
    assert "KAKA_HERMES_API_KEY" not in rendered


def test_hermes_bad_json_becomes_failed_image_intake_task_status(monkeypatch):
    state = FakeHermesState()
    state.chat_responses = [_chat_completion_text("not json")]
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        client = create_app(vision_provider=provider, intake_provider=provider).test_client()
        headers = {"Authorization": "Bearer dev-mobile-token"}
        upload = client.post(
            "/mobile/v1/assets",
            headers=headers,
            data={"file": (io.BytesIO(b"image-bytes"), "photo.jpg", "image/jpeg")},
        )

        created = client.post(
            "/mobile/v1/tasks/image-intake",
            headers=headers,
            json={"asset_id": upload.get_json()["asset_id"], "locale": "en"},
        )
        status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    body = status.get_json()

    assert created.status_code == 200
    assert body["status"] == "failed"
    assert body["failure_code"] == "image_intake_failed"
    assert body["provider"] == "hermes"
    assert "not json" not in json.dumps(body, sort_keys=True)


def test_hermes_timeout_becomes_failed_universal_intake_task_status(monkeypatch):
    state = FakeHermesState()
    state.chat_delay = 0.2
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        monkeypatch.setenv("KAKA_HERMES_TIMEOUT_SECONDS", "0.05")
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        client = create_app(vision_provider=provider, intake_provider=provider).test_client()
        headers = {"Authorization": "Bearer dev-mobile-token"}

        created = client.post(
            "/mobile/v1/tasks/intake",
            headers=headers,
            json={
                "type": "text",
                "text": "Please summarize this launch note.",
                "source_app": "Notes",
            },
        )
        status = client.get(created.get_json()["status_url"], headers=headers)

    body = status.get_json()

    assert created.status_code == 200
    assert body["status"] == "failed"
    assert body["failure_code"] == "intake_failed"
    assert body["provider"] == "hermes"


def test_hermes_non_json_http_response_becomes_failed_universal_intake_task_status(monkeypatch):
    state = FakeHermesState()
    state.chat_raw_response = "this is not a JSON HTTP response"
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        client = create_app(vision_provider=provider, intake_provider=provider).test_client()
        headers = {"Authorization": "Bearer dev-mobile-token"}

        created = client.post(
            "/mobile/v1/tasks/intake",
            headers=headers,
            json={
                "type": "text",
                "text": "Please summarize this launch note.",
                "source_app": "Notes",
            },
        )
        status = client.get(created.get_json()["status_url"], headers=headers)

    body = status.get_json()

    assert body["status"] == "failed"
    assert body["failure_code"] == "intake_failed"
    assert body["provider"] == "hermes"
    assert "not a JSON" not in json.dumps(body, sort_keys=True)


def test_hermes_pdf_intake_returns_structured_failure_without_chat_request(monkeypatch):
    with FakeHermesServer() as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProvider

        provider = HermesProvider()
        client = create_app(vision_provider=provider, intake_provider=provider).test_client()
        headers = {"Authorization": "Bearer dev-mobile-token"}
        upload = client.post(
            "/mobile/v1/assets",
            headers=headers,
            data={"file": (io.BytesIO(b"%PDF-1.7 fake"), "brief.pdf", "application/pdf")},
        )

        created = client.post(
            "/mobile/v1/tasks/intake",
            headers=headers,
            json={
                "type": "pdf",
                "source": {
                    "asset_id": upload.get_json()["asset_id"],
                    "filename": "brief.pdf",
                    "mime_type": "application/pdf",
                },
                "source_app": "Files",
            },
        )
        status = client.get(created.get_json()["status_url"], headers=headers)

    body = status.get_json()

    assert body["status"] == "failed"
    assert body["failure_code"] == "pdf_not_supported_by_hermes_provider"
    assert body["provider"] == "hermes"
    assert not [request for request in server.state.requests if request["method"] == "POST"]


def test_hermes_health_probe_failure_is_configuration_error(monkeypatch):
    state = FakeHermesState()
    state.health_status = 503
    with FakeHermesServer(state) as server:
        _configure_hermes_env(monkeypatch, server.base_url)
        from agent_pocket_mock_bridge.hermes_provider import HermesProviderConfigurationError, HermesProvider

        with pytest.raises(HermesProviderConfigurationError, match="/health"):
            HermesProvider()


def _configure_hermes_env(monkeypatch, base_url):
    monkeypatch.setenv("KAKA_HERMES_BASE_URL", base_url)
    monkeypatch.setenv("KAKA_HERMES_API_KEY", "test-secret")
    monkeypatch.delenv("KAKA_HERMES_MODEL", raising=False)
    monkeypatch.delenv("KAKA_HERMES_TIMEOUT_SECONDS", raising=False)


def _chat_completion(payload):
    return _chat_completion_text(json.dumps(payload))


def _chat_completion_text(text):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
    }
