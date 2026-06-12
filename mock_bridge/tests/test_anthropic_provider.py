import io
import json
from types import SimpleNamespace

from agent_pocket_mock_bridge import anthropic_provider as anthropic_module
from agent_pocket_mock_bridge.anthropic_provider import AnthropicProvider
from agent_pocket_mock_bridge.app import create_app


class FakeAnthropicMessages:
    def __init__(self, response_text=None, exception=None):
        self.response_text = response_text
        self.exception = exception
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text=self.response_text),
            ]
        )


class FakeAnthropicClient:
    def __init__(self, response_text=None, exception=None):
        self.messages = FakeAnthropicMessages(response_text=response_text, exception=exception)


def test_anthropic_provider_image_intake_posts_vision_block_and_parses_success(monkeypatch):
    monkeypatch.delenv("KAKA_MODEL", raising=False)
    client = FakeAnthropicClient(
        json.dumps(
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
    )
    provider = AnthropicProvider(client=client)

    result = provider.image_intake(b"image-bytes", "image/jpeg", locale="en")

    call = client.messages.calls[0]
    content = call["messages"][0]["content"]
    image_block = next(block for block in content if block["type"] == "image")
    assert call["model"] == "claude-opus-4-8"
    assert call["max_tokens"] == 16000
    assert image_block["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": "aW1hZ2UtYnl0ZXM=",
    }
    assert result["image_type"] == "text"
    assert result["suggestions"][0]["skill"] == "ocr"
    assert result["suggestions"][0]["is_available"] is True


def test_anthropic_api_status_error_becomes_failed_vision_task_status(monkeypatch):
    class FakeAPIStatusError(Exception):
        pass

    monkeypatch.setattr(
        anthropic_module,
        "anthropic",
        SimpleNamespace(
            APIStatusError=FakeAPIStatusError,
            APIConnectionError=RuntimeError,
            APITimeoutError=TimeoutError,
        ),
    )
    provider = AnthropicProvider(client=FakeAnthropicClient(exception=FakeAPIStatusError("provider unavailable")))
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
    assert body["provider"] == "anthropic"
    assert "provider unavailable" not in rendered
    assert "ANTHROPIC_API_KEY" not in rendered


def test_anthropic_json_parse_error_becomes_failed_image_intake_task_status():
    provider = AnthropicProvider(client=FakeAnthropicClient("not json"))
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
    assert body["provider"] == "anthropic"
    assert "not json" not in json.dumps(body, sort_keys=True)


def test_anthropic_universal_text_intake_success_path_uses_fake_sdk_response():
    provider = AnthropicProvider(
        client=FakeAnthropicClient(
            json.dumps(
                {
                    "title": "Shared note",
                    "summary": "The note asks for a launch checklist.",
                    "suggestions": [
                        {
                            "id": "extract_tasks",
                            "label": "Extract Tasks",
                            "requires_confirmation": False,
                        }
                    ],
                }
            )
        )
    )
    client = create_app(vision_provider=provider, intake_provider=provider).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "text",
            "text": "Please turn this into a launch checklist.",
            "source_app": "Notes",
            "locale": "en",
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)
    body = status.get_json()

    assert created.status_code == 200
    assert body["status"] == "completed"
    assert body["provider"] == "anthropic"
    assert body["intake"]["kind"] == "text"
    assert body["intake"]["type"] == "text"
    assert body["intake"]["title"] == "Shared note"
    assert body["intake"]["metadata"]["source_app"] == "Notes"
    assert body["intake"]["suggestions"][0]["id"] == "extract_tasks"
