import io
import html as html_lib
import threading
from concurrent.futures import ThreadPoolExecutor

from agent_pocket_mock_bridge import app as app_module
from agent_pocket_mock_bridge.app import RuntimeHTTPVisionProvider, create_app


def test_health_reports_hermes_runtime():
    client = create_app().test_client()

    response = client.get("/mobile/v1/health")

    assert response.status_code == 200
    assert response.get_json()["runtime"] == "hermes"


def test_capabilities_requires_bearer_token():
    client = create_app().test_client()

    response = client.get("/mobile/v1/capabilities")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_capabilities_advertise_photo_edit_and_sse():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert "photo_edit" in body["tasks"]
    assert "image_intake" in body["tasks"]
    assert "intake" in body["tasks"]
    assert body["tasks"]["photo_edit"]["supports_sse"] is True
    assert body["tasks"]["vision"]["supports_sse"] is True
    assert body["tasks"]["image_intake"]["supports_sse"] is True
    assert body["retention"]["input_assets_days"] == 7


def test_capabilities_advertise_vision_modes():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["profiles"][0]["capabilities"] == ["photo_edit", "vision", "image_intake", "intake"]
    assert body["tasks"]["vision"]["modes"] == ["scan", "identify", "translate", "food"]
    assert body["tasks"]["vision"]["provider"] == "fixture_vision"


def test_capabilities_advertise_universal_intake_contract():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    intake = response.get_json()["tasks"]["intake"]
    assert response.status_code == 200
    assert intake["accepted_types"] == ["text", "url", "image", "pdf"]
    assert intake["supports_context_snapshot"] is True
    assert intake["supports_sse"] is False


def test_capabilities_advertise_runtime_neutral_local_recipe_contract():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    photo_edit = response.get_json()["tasks"]["photo_edit"]
    assert response.status_code == 200
    assert photo_edit["provider"] == "recipe_local"
    assert photo_edit["renderer"] == "local_parametric"
    assert photo_edit["variant_labels"] == ["Master", "Social"]
    assert photo_edit["variant_ids"] == ["variant_clean_pro", "variant_social_pop"]
    assert photo_edit["crop_aspects"] == ["original"]
    assert photo_edit["supports_crop_candidates"] is False
    assert photo_edit["supports_upscale_policy"] is True


def test_pairing_exchange_returns_mobile_token_once():
    app = create_app(pairing_codes={"pair_123": "Kartz MacBook Hermes"})
    client = app.test_client()

    first = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": "pair_123",
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )
    second = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": "pair_123",
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )

    assert first.status_code == 200
    assert first.get_json()["mobile_token"] == "dev-mobile-token"
    assert first.get_json()["display_name"] == "Kartz MacBook Hermes"
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "pairing_already_used"


def test_pairing_exchange_rejects_unknown_code():
    client = create_app(pairing_codes={"pair_123": "Kartz MacBook Hermes"}).test_client()

    response = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": "pair_missing",
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "pairing_expired"


def test_development_pairing_payload_uses_request_host():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/pairing/dev",
        headers={"Host": "192.168.1.42:8765"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body == {
        "version": 1,
        "endpoint": "http://192.168.1.42:8765",
        "runtime": "hermes",
        "display_name": "Agent Pocket Mock Hermes",
        "pairing_code": "pair_dev",
        "expires_at": "2099-01-01T00:00:00Z",
    }


def test_development_pairing_payload_prefers_advertised_endpoint_for_real_device():
    client = create_app(advertised_endpoint="http://192.168.1.104:8765").test_client()

    response = client.get(
        "/mobile/v1/pairing/dev",
        headers={"Host": "127.0.0.1:8765"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["endpoint"] == "http://192.168.1.104:8765"


def test_development_pairing_payload_refreshes_after_default_code_is_used():
    client = create_app().test_client()

    first = client.get(
        "/mobile/v1/pairing/dev",
        headers={"Host": "192.168.1.42:8765"},
    ).get_json()
    first_exchange = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": first["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )

    second = client.get(
        "/mobile/v1/pairing/dev",
        headers={"Host": "192.168.1.42:8765"},
    ).get_json()
    second_exchange = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": second["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_xyz",
        },
    )
    replay = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": second["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_xyz",
        },
    )

    assert first_exchange.status_code == 200
    assert first["pairing_code"] == "pair_dev"
    assert second["pairing_code"] != "pair_dev"
    assert second["pairing_code"].startswith("pair_dev_")
    assert second_exchange.status_code == 200
    assert second_exchange.get_json()["display_name"] == "Agent Pocket Mock Hermes"
    assert replay.status_code == 409
    assert replay.get_json()["error"]["code"] == "pairing_already_used"


def test_development_pairing_page_shows_copyable_payload_and_commands():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/pairing/dev.html",
        headers={"Host": "192.168.1.42:8765"},
    )

    html = response.data.decode("utf-8")
    visible_text = html_lib.unescape(html)
    assert response.status_code == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert "<title>Agent Pocket Mock Hermes Pairing</title>" in html
    assert "http://192.168.1.42:8765" in visible_text
    assert '"pairing_code": "pair_dev"' in visible_text
    assert "curl http://192.168.1.42:8765/mobile/v1/health" in visible_text
    assert "Authorization: Bearer dev-mobile-token" in visible_text


def test_development_pairing_page_shows_refreshed_code_after_default_is_used():
    client = create_app().test_client()

    client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": "pair_dev",
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )
    response = client.get(
        "/mobile/v1/pairing/dev.html",
        headers={"Host": "192.168.1.42:8765"},
    )

    html = response.data.decode("utf-8")
    visible_text = html_lib.unescape(html)
    assert response.status_code == 200
    assert '"pairing_code": "pair_dev"' not in visible_text
    assert '"pairing_code": "pair_dev_' in visible_text
    assert 'data-pairing-payload=' in html


def test_development_pairing_page_embeds_scannable_qr_without_external_service():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/pairing/dev.html",
        headers={"Host": "192.168.1.42:8765"},
    )

    html = response.data.decode("utf-8")
    visible_text = html_lib.unescape(html)
    assert response.status_code == 200
    assert '<img class="pairing-qr"' in html
    assert 'src="data:image/png;base64,' in html
    assert 'alt="Pairing QR code for Agent Pocket"' in html
    assert 'data-pairing-payload=' in html
    assert '"endpoint": "http://192.168.1.42:8765"' in visible_text
    assert "api.qrserver.com" not in html
    assert "chart.googleapis.com" not in html


def test_photo_edit_lifecycle_returns_downloadable_variant():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    assert upload.status_code == 200
    asset_id = upload.get_json()["asset_id"]

    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": asset_id,
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    assert created.status_code == 200
    task_id = created.get_json()["task_id"]

    status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)
    assert status.status_code == 200
    body = status.get_json()
    assert body["status"] == "completed"
    assert body["variants"][0]["download_url"].endswith("/download")

    download = client.get(body["variants"][0]["download_url"], headers=headers)
    assert download.status_code == 200
    assert download.content_type == "image/png"
    assert download.data.startswith(b"\x89PNG")


def test_vision_task_lifecycle_returns_structured_result():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/vision",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "mode": "identify",
            "instruction": "Identify the main object.",
            "locale": "zh-Hans",
        },
    )
    task_id = created.get_json()["task_id"]
    events = client.get(f"/mobile/v1/tasks/{task_id}/events", headers=headers)
    status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)

    body = status.get_json()
    assert upload.status_code == 200
    assert created.status_code == 200
    assert created.get_json()["status"] == "queued"
    assert events.status_code == 200
    assert events.content_type == "text/event-stream"
    assert '"result_type":"vision"' in events.data.decode("utf-8")
    assert body["status"] == "completed"
    assert body["result_type"] == "vision"
    assert body["vision"]["mode"] == "identify"
    assert body["vision"]["title"] == "识别结果"
    assert body["vision"]["sections"][0]["kind"] == "candidates"
    assert body["vision"]["sections"][0]["items"][0]["title"] == "候选主体"


def test_image_intake_lifecycle_returns_skill_suggestions():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/image-intake",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "locale": "zh-Hans",
        },
    )
    task_id = created.get_json()["task_id"]
    status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)

    body = status.get_json()
    assert created.status_code == 200
    assert body["status"] == "completed"
    assert body["result_type"] == "image_intake"
    assert body["image_intake"]["suggestions"][0]["skill"] in ["photo_enhance", "ocr"]


def test_image_intake_marks_unavailable_multimodal_skills():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/image-intake",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "locale": "zh-Hans",
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    suggestions = {
        item["skill"]: item
        for item in status.get_json()["image_intake"]["suggestions"]
    }
    assert suggestions["photo_enhance"]["is_available"] is True
    assert suggestions["identify_subject"]["is_available"] is False


def test_image_intake_marks_identify_available_for_runtime_http_vision_provider():
    class RuntimeHTTPLikeVisionProvider:
        provider_name = "runtime_http_vision"

        def analyze(self, source_bytes, mode, instruction, locale):
            return {"mode": mode, "title": "ok", "summary": "ok"}

    client = create_app(vision_provider=RuntimeHTTPLikeVisionProvider()).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/image-intake",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "locale": "zh-Hans",
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    suggestions = {
        item["skill"]: item
        for item in status.get_json()["image_intake"]["suggestions"]
    }
    assert suggestions["identify_subject"]["is_available"] is True


def test_universal_text_intake_lifecycle_returns_status_url_and_suggestions():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "text",
            "text": "Buy milk and send launch review notes",
            "note": "Extract next actions.",
            "locale": "en-US",
            "preferred_profile_id": "photo-agent",
            "source_app": "Notes",
            "received_at": "2026-06-05T09:00:00Z",
            "context_snapshot": {
                "timestamp": "2026-06-05T09:30:00Z",
                "timezone": "Asia/Shanghai",
                "source_surface": "share_extension",
                "network": "wifi",
            },
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)

    body = status.get_json()
    suggestions = {item["id"]: item for item in body["intake"]["suggestions"]}
    assert created.status_code == 200
    assert created.get_json() == {
        "task_id": "task_0001",
        "status": "queued",
        "status_url": "/mobile/v1/tasks/task_0001",
        "events_url": "/mobile/v1/tasks/task_0001/events",
    }
    assert body["status"] == "completed"
    assert body["result_type"] == "intake"
    assert body["intake"]["kind"] == "text"
    assert body["intake"]["type"] == "text"
    assert "37 characters" in body["intake"]["summary"]
    assert body["intake"]["metadata"]["source_app"] == "Notes"
    assert body["intake"]["metadata"]["context_snapshot"]["source_surface"] == "share_extension"
    assert body["intake"]["metadata"]["context_snapshot"]["network"] == "wifi"
    assert suggestions["summarize"]["is_available"] is True
    assert suggestions["extract_tasks"]["requires_confirmation"] is False


def test_universal_url_intake_lifecycle_returns_link_summary():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "url",
            "url": "https://example.com/launch-review",
            "note": "Summarize before standup.",
            "locale": "en-US",
            "source_app": "Safari",
            "received_at": "2026-06-05T10:00:00Z",
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)

    intake = status.get_json()["intake"]
    assert created.status_code == 200
    assert intake["kind"] == "url"
    assert intake["type"] == "url"
    assert "https://example.com/launch-review" in intake["summary"]
    assert intake["metadata"]["source_app"] == "Safari"
    assert [item["id"] for item in intake["suggestions"]] == ["summarize", "remember", "forget"]


def test_universal_image_intake_delegates_to_existing_image_result_builder(monkeypatch):
    calls = []

    def fake_build_image_intake_result(image_bytes, locale, recognized_lines):
        calls.append(
            {
                "image_bytes": image_bytes,
                "locale": locale,
                "recognized_lines": recognized_lines,
            }
        )
        return {
            "image_type": "document",
            "title": "Delegated image intake",
            "summary": "Delegated image summary.",
            "suggestions": [{"skill": "photo_enhance", "label": "Enhance"}],
        }

    monkeypatch.setattr(app_module, "build_image_intake_result", fake_build_image_intake_result)
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"shared-image-bytes"), "shared.png", "image/png"),
            "metadata": '{"width":200,"height":100}',
        },
    )

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "image",
            "source": {"asset_id": upload.get_json()["asset_id"]},
            "locale": "zh-Hans",
            "source_app": "Photos",
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)

    body = status.get_json()
    assert created.status_code == 200
    assert calls == [
        {
            "image_bytes": b"shared-image-bytes",
            "locale": "zh-Hans",
            "recognized_lines": [],
        }
    ]
    assert body["result_type"] == "intake"
    assert body["intake"]["kind"] == "image"
    assert body["intake"]["type"] == "image"
    assert body["intake"]["image_intake"]["title"] == "Delegated image intake"
    assert body["image_intake"]["title"] == "Delegated image intake"
    assert body["image_intake"]["suggestions"][0]["is_available"] is True


def test_universal_pdf_intake_preserves_source_metadata():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"%PDF-1.7 fake"), "brief.pdf", "application/pdf"),
            "metadata": '{"page_count":8,"title":"Launch Brief"}',
        },
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
                "page_count": 8,
            },
            "note": "Find risks.",
            "source_app": "Files",
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)

    intake = status.get_json()["intake"]
    assert created.status_code == 200
    assert intake["kind"] == "pdf"
    assert intake["type"] == "pdf"
    assert "brief.pdf" in intake["summary"]
    assert intake["metadata"]["asset_id"] == upload.get_json()["asset_id"]
    assert intake["metadata"]["filename"] == "brief.pdf"
    assert intake["metadata"]["mime_type"] == "application/pdf"
    assert intake["metadata"]["page_count"] == 8


def test_universal_intake_requires_auth_and_rejects_bad_payloads():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    unauthorized = client.post(
        "/mobile/v1/tasks/intake",
        json={"type": "text", "text": "hello"},
    )
    unknown_type = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={"type": "video", "text": "hello"},
    )
    missing_image = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={"type": "image", "source": {"asset_id": "asset_missing"}},
    )
    missing_text = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={"type": "text", "text": ""},
    )

    assert unauthorized.status_code == 401
    assert unauthorized.get_json()["error"]["code"] == "unauthorized"
    assert unknown_type.status_code == 400
    assert unknown_type.get_json()["error"]["code"] == "intake_unavailable"
    assert missing_image.status_code == 404
    assert missing_image.get_json()["error"]["code"] == "not_found"
    assert missing_text.status_code == 400
    assert missing_text.get_json()["error"]["code"] == "invalid_intake_payload"


def test_vision_task_uses_injected_fake_provider():
    class RecordingVisionProvider:
        provider_name = "recording_vision"

        def __init__(self):
            self.calls = []

        def analyze(self, source_bytes, mode, instruction, locale):
            self.calls.append(
                {
                    "source_bytes": source_bytes,
                    "mode": mode,
                    "instruction": instruction,
                    "locale": locale,
                }
            )
            return {
                "mode": mode,
                "title": "Recorded",
                "summary": "Provider handled vision.",
                "items": [{"title": "Object", "value": "Notebook"}],
            }

    provider = RecordingVisionProvider()
    client = create_app(vision_provider=provider).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )

    created = client.post(
        "/mobile/v1/tasks/vision",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "mode": "scan",
            "instruction": "Extract text.",
            "locale": "en",
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    assert provider.calls == [
        {
            "source_bytes": b"source-image",
            "mode": "scan",
            "instruction": "Extract text.",
            "locale": "en",
        }
    ]
    assert status.get_json()["provider"] == "recording_vision"
    assert status.get_json()["vision"]["items"][0]["value"] == "Notebook"


def test_concurrent_vision_tasks_receive_unique_task_ids():
    class SlowVisionProvider:
        provider_name = "slow_vision"

        def __init__(self):
            self.barrier = threading.Barrier(3)

        def analyze(self, source_bytes, mode, instruction, locale):
            self.barrier.wait(timeout=3)
            return {
                "mode": mode,
                "title": mode,
                "summary": f"{mode} completed.",
                "items": [],
            }

    app = create_app(vision_provider=SlowVisionProvider())
    headers = {"Authorization": "Bearer dev-mobile-token"}
    asset_response = app.test_client().post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"image"), "image.png", "image/png")},
    )
    asset_id = asset_response.get_json()["asset_id"]

    def create_task(mode: str) -> str:
        response = app.test_client().post(
            "/mobile/v1/tasks/vision",
            headers=headers,
            json={"asset_id": asset_id, "mode": mode, "instruction": mode, "locale": "zh-Hans"},
        )
        assert response.status_code == 200
        return response.get_json()["task_id"]

    with ThreadPoolExecutor(max_workers=3) as executor:
        task_ids = list(executor.map(create_task, ["scan", "identify", "translate"]))

    assert len(set(task_ids)) == 3
    assert sorted(task_ids) == ["task_0001", "task_0002", "task_0003"]
    modes_by_task = {
        task_id: app.test_client().get(f"/mobile/v1/tasks/{task_id}", headers=headers).get_json()["vision"]["mode"]
        for task_id in task_ids
    }
    assert sorted(modes_by_task.values()) == ["identify", "scan", "translate"]


def test_runtime_http_vision_provider_posts_image_payload(monkeypatch):
    observations = {}

    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"vision":{"mode":"identify","title":"Desk","summary":"A desk.","items":[]}}'

    def fake_urlopen(request, timeout):
        observations["url"] = request.full_url
        observations["timeout"] = timeout
        observations["headers"] = dict(request.header_items())
        observations["body"] = request.data
        return FakeHTTPResponse()

    monkeypatch.setattr(app_module.urllib_request, "urlopen", fake_urlopen)
    provider = RuntimeHTTPVisionProvider("http://127.0.0.1:7799/kaka/vision", timeout_seconds=5)

    result = provider.analyze(
        source_bytes=b"image-bytes",
        mode="identify",
        instruction="Identify this.",
        locale="zh-Hans",
    )
    payload = app_module.json.loads(observations["body"].decode("utf-8"))

    assert observations["url"] == "http://127.0.0.1:7799/kaka/vision"
    assert observations["timeout"] == 5
    assert observations["headers"]["Content-type"] == "application/json"
    assert payload["mode"] == "identify"
    assert payload["instruction"] == "Identify this."
    assert payload["locale"] == "zh-Hans"
    assert payload["image_base64"] == "aW1hZ2UtYnl0ZXM="
    assert result["title"] == "Desk"


def test_vision_task_rejects_unknown_mode():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    response = client.post(
        "/mobile/v1/tasks/vision",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "mode": "video",
            "instruction": "Do the thing.",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "vision_unavailable"


def test_qa_status_summarizes_pairing_photo_task_and_download_without_raw_bytes():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    client.get("/mobile/v1/capabilities", headers=headers)
    pairing = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": "pair_dev",
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)
    variant = status.get_json()["variants"][0]
    client.get(variant["download_url"], headers=headers)

    qa_status = client.get("/mobile/v1/qa/status", headers=headers)

    body = qa_status.get_json()
    assert pairing.status_code == 200
    assert qa_status.status_code == 200
    assert body["pairing"]["used_codes"] == ["pair_dev"]
    assert body["pairing"]["current_development_code"].startswith("pair_dev_")
    assert body["requests"]["capabilities"] == 1
    assert body["requests"]["pairing_exchange"] == 1
    assert body["requests"]["asset_upload"] == 1
    assert body["requests"]["photo_task_create"] == 1
    assert body["requests"]["task_status"] == 1
    assert body["requests"]["asset_download"] == 1
    assert body["assets"]["uploaded_count"] == 1
    assert body["assets"]["result_count"] == 1
    assert body["assets"]["download_request_count"] == 1
    assert body["assets"]["last_upload"] == {
        "asset_id": upload.get_json()["asset_id"],
        "filename": "photo.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": len(b"source-image"),
    }
    assert body["tasks"]["total"] == 1
    assert body["tasks"]["completed"] == 1
    assert body["tasks"]["failed"] == 0
    assert body["tasks"]["last_task"]["task_id"] == created.get_json()["task_id"]
    assert body["tasks"]["last_task"]["status"] == "completed"
    assert body["tasks"]["last_task"]["provider"] == "fixture"
    assert body["provider"]["name"] == "fixture"
    assert "source-image" not in str(body)


def test_photo_edit_task_uses_injected_fake_provider():
    class RecordingProvider:
        provider_name = "recording"

        def __init__(self):
            self.calls = []

        def edit(self, source_bytes, style, instruction, return_variants):
            self.calls.append(
                {
                    "source_bytes": source_bytes,
                    "style": style,
                    "instruction": instruction,
                    "return_variants": return_variants,
                }
            )
            return [
                {
                    "id": "variant_provider",
                    "label": "Provider Variant",
                    "mime_type": "image/png",
                    "bytes": b"provider-result",
                    "explanation": "Provider handled the edit.",
                }
            ]

    provider = RecordingProvider()
    client = create_app(photo_provider=provider).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "style": "social_cover",
            "instruction": "Preserve original framing.",
            "return_variants": 1,
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)
    variant = status.get_json()["variants"][0]
    download = client.get(variant["download_url"], headers=headers)

    assert provider.calls == [
        {
            "source_bytes": b"source-image",
            "style": "social_cover",
            "instruction": "Preserve original framing.",
            "return_variants": 1,
        }
    ]
    assert variant["label"] == "Provider Variant"
    assert status.get_json()["provider"] == "recording"
    assert status.get_json()["explanation"] == "Provider handled the edit."
    assert download.data == b"provider-result"


def test_photo_edit_task_preserves_recipe_metadata_for_status_and_qa():
    class RecipeProvider:
        provider_name = "recipe_local"

        def edit(self, source_bytes, style, instruction, return_variants):
            metadata = {
                "provider": "recipe_local",
                "renderer": "local_parametric",
                "composition": {
                    "selected_aspect_ratio": "original",
                    "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                },
                "qa": {
                    "master_difference_score": 0.18,
                    "social_difference_score": 0.31,
                },
                "share_caption": "Polished locally.",
                "recipe_summary": "Balanced exposure.",
            }
            return [
                {
                    "id": "variant_clean_pro",
                    "label": "Master",
                    "mime_type": "image/jpeg",
                    "bytes": b"master-result",
                    "explanation": "Balanced exposure.",
                    "recipe_metadata": metadata,
                },
                {
                    "id": "variant_social_pop",
                    "label": "Social",
                    "mime_type": "image/jpeg",
                    "bytes": b"social-result",
                    "explanation": "Social-ready polish.",
                    "recipe_metadata": metadata,
                },
            ]

    client = create_app(photo_provider=RecipeProvider()).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 2,
        },
    )

    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers).get_json()
    client.get(status["variants"][0]["download_url"], headers=headers)
    qa_status = client.get("/mobile/v1/qa/status", headers=headers).get_json()

    assert [variant["label"] for variant in status["variants"]] == ["Master", "Social"]
    assert status["renderer"] == "local_parametric"
    assert status["composition"]["selected_aspect_ratio"] == "original"
    assert status["qa"]["master_difference_score"] == 0.18
    assert status["qa"]["social_difference_score"] == 0.31
    assert status["share_caption"] == "Polished locally."
    assert qa_status["tasks"]["last_task"]["variant_count"] == 2
    assert qa_status["tasks"]["last_task"]["renderer"] == "local_parametric"
    assert qa_status["tasks"]["last_task"]["composition"]["crop"]["width"] == 1.0
    assert qa_status["tasks"]["last_task"]["qa"]["social_difference_score"] == 0.31


def test_photo_edit_provider_failure_becomes_failed_task_status():
    class FailingProvider:
        def edit(self, source_bytes, style, instruction, return_variants):
            raise RuntimeError("provider key missing: provider-secret-value")

    client = create_app(photo_provider=FailingProvider()).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
            "metadata": '{"width":100,"height":100}',
        },
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "profile_id": "photo-agent",
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)

    body = status.get_json()
    assert created.status_code == 200
    assert body["status"] == "failed"
    assert body["failure_code"] == "provider_failed"
    assert body["message"] == "The photo provider failed. Check Hermes provider credentials or logs."
    assert "provider-secret-value" not in body["message"]


def test_recall_remember_persists_visible_item():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    remembered = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "user_visible_summary": "Remember that launch summaries should be in Chinese.",
        },
    )
    listed = client.get("/mobile/v1/recall/items", headers=headers)

    body = remembered.get_json()
    assert remembered.status_code == 200
    assert body["action"] == "remember"
    assert body["status"] == "remembered"
    assert body["item"]["item_id"] == "recall_0001"
    assert body["item"]["summary"] == "Remember that launch summaries should be in Chinese."
    assert body["item"]["created_at"] == "2026-06-05T00:00:00Z"
    assert body["item"]["provenance"]["source_task_id"] == "task_123"
    assert listed.status_code == 200
    assert listed.get_json()["items"] == [body["item"]]


def test_recall_use_once_succeeds_without_persisting_item():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    used = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "use_once",
            "source_task_id": "task_123",
            "user_visible_summary": "Use this detail for the current answer only.",
        },
    )
    listed = client.get("/mobile/v1/recall/items", headers=headers)

    assert used.status_code == 200
    assert used.get_json() == {
        "action": "use_once",
        "status": "used_once",
        "item": None,
        "deleted_item_ids": [],
    }
    assert listed.status_code == 200
    assert listed.get_json()["items"] == []


def test_recall_forget_by_source_is_deterministic():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    inbox_item_id = "12345678-1234-1234-1234-1234567890AB"
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_inbox_item_id": inbox_item_id,
            "user_visible_summary": "Remember the launch preference.",
        },
    )

    first = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "forget",
            "source_inbox_item_id": inbox_item_id,
            "user_visible_summary": "Forget the launch preference.",
        },
    )
    second = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "forget",
            "source_inbox_item_id": inbox_item_id,
            "user_visible_summary": "Forget the launch preference.",
        },
    )

    assert first.status_code == 200
    assert first.get_json() == {
        "action": "forget",
        "status": "forgotten",
        "item": None,
        "deleted_item_ids": ["recall_0001"],
    }
    assert second.status_code == 200
    assert second.get_json() == {
        "action": "forget",
        "status": "forgotten",
        "item": None,
        "deleted_item_ids": [],
    }


def test_recall_forget_with_two_provenance_fields_requires_both_to_match():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    inbox_item_id = "12345678-1234-1234-1234-1234567890AB"
    other_inbox_item_id = "12345678-1234-1234-1234-1234567890AC"
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "source_inbox_item_id": inbox_item_id,
            "user_visible_summary": "Remember the matched launch preference.",
        },
    )
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "source_inbox_item_id": other_inbox_item_id,
            "user_visible_summary": "Remember the other launch preference.",
        },
    )

    deleted = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "forget",
            "source_task_id": "task_123",
            "source_inbox_item_id": inbox_item_id,
            "user_visible_summary": "Forget the matched launch preference.",
        },
    )
    listed = client.get("/mobile/v1/recall/items", headers=headers)

    assert deleted.status_code == 200
    assert deleted.get_json()["deleted_item_ids"] == ["recall_0001"]
    assert [item["item_id"] for item in listed.get_json()["items"]] == ["recall_0002"]


def test_recall_items_are_returned_newest_first():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    for summary in ["First", "Second"]:
        client.post(
            "/mobile/v1/recall/actions",
            headers=headers,
            json={
                "action": "remember",
                "source_task_id": f"task_{summary.lower()}",
                "user_visible_summary": summary,
            },
        )

    listed = client.get("/mobile/v1/recall/items", headers=headers)

    assert [item["item_id"] for item in listed.get_json()["items"]] == ["recall_0002", "recall_0001"]


def test_recall_delete_item_by_id_is_deterministic():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    remembered = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "user_visible_summary": "Remember the launch preference.",
        },
    )
    item_id = remembered.get_json()["item"]["item_id"]

    first = client.delete(f"/mobile/v1/recall/items/{item_id}", headers=headers)
    second = client.delete(f"/mobile/v1/recall/items/{item_id}", headers=headers)
    listed = client.get("/mobile/v1/recall/items", headers=headers)

    assert first.status_code == 200
    assert first.get_json() == {"status": "forgotten", "deleted_item_ids": [item_id]}
    assert second.status_code == 200
    assert second.get_json() == {"status": "forgotten", "deleted_item_ids": []}
    assert listed.get_json()["items"] == []


def test_runtime_task_list_returns_waiting_tasks_first():
    app = create_app()
    app.tasks["task_running"] = {
        "task_id": "task_running",
        "title": "Summarize PDF",
        "status": "running",
        "progress": 0.2,
        "updated_at": "2026-06-05T09:32:00Z",
    }
    app.tasks["task_waiting"] = {
        "task_id": "task_waiting",
        "title": "Approve Recall write",
        "status": "waiting_for_approval",
        "progress": 0.4,
        "message": "Review memory write",
        "updated_at": "2026-06-05T09:31:00Z",
    }
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    listed = client.get("/mobile/v1/tasks", headers=headers)

    assert listed.status_code == 200
    assert [task["id"] for task in listed.get_json()["tasks"]] == ["task_waiting", "task_running"]
    assert listed.get_json()["tasks"][0]["status"] == "waiting_for_approval"


def test_runtime_task_cancel_and_approval_update_task_summary():
    app = create_app()
    app.tasks["task_waiting"] = {
        "task_id": "task_waiting",
        "title": "Approve Recall write",
        "status": "waiting_for_approval",
        "progress": 0.4,
        "message": "Review memory write",
        "updated_at": "2026-06-05T09:31:00Z",
    }
    app.tasks["task_running"] = {
        "task_id": "task_running",
        "title": "Summarize PDF",
        "status": "running",
        "progress": 0.2,
        "updated_at": "2026-06-05T09:32:00Z",
    }
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    approved = client.post(
        "/mobile/v1/tasks/task_waiting/approval",
        headers=headers,
        json={"action": "approve", "note": "Looks safe."},
    )
    cancelled = client.post(
        "/mobile/v1/tasks/task_running/cancel",
        headers=headers,
    )

    assert approved.status_code == 200
    assert approved.get_json()["status"] == "approved"
    assert approved.get_json()["task"]["status"] == "running"
    assert approved.get_json()["task"]["message"] == "Approved."
    assert cancelled.status_code == 200
    assert cancelled.get_json()["status"] == "cancelled"
    assert cancelled.get_json()["task"]["status"] == "cancelled"
    assert cancelled.get_json()["task"]["progress"] == 1.0


def test_runtime_task_approval_requires_explicit_valid_action():
    app = create_app()
    app.tasks["task_waiting"] = {
        "task_id": "task_waiting",
        "title": "Approve Recall write",
        "status": "waiting_for_approval",
        "progress": 0.4,
        "message": "Review memory write",
        "updated_at": "2026-06-05T09:31:00Z",
    }
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    missing = client.post(
        "/mobile/v1/tasks/task_waiting/approval",
        headers=headers,
        json={},
    )
    invalid = client.post(
        "/mobile/v1/tasks/task_waiting/approval",
        headers=headers,
        json={"action": "maybe"},
    )

    assert missing.status_code == 400
    assert missing.get_json()["error"]["code"] == "invalid_task_approval"
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "invalid_task_approval"
    assert app.tasks["task_waiting"]["status"] == "waiting_for_approval"
