import io
import html as html_lib

from agent_pocket_mock_bridge.app import create_app


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
    assert body["tasks"]["photo_edit"]["supports_sse"] is True
    assert body["retention"]["input_assets_days"] == 7


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
    assert photo_edit["crop_aspects"] == ["original", "4:5", "1:1"]
    assert photo_edit["supports_crop_candidates"] is True
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
            "instruction": "Make it title-safe.",
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
            "instruction": "Make it title-safe.",
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
                    "selected_aspect_ratio": "4:5",
                    "crop": {"x": 0.2, "y": 0.0, "width": 0.6, "height": 1.0},
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
                    "explanation": "Stronger crop.",
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
    assert status["composition"]["selected_aspect_ratio"] == "4:5"
    assert status["qa"]["master_difference_score"] == 0.18
    assert status["qa"]["social_difference_score"] == 0.31
    assert status["share_caption"] == "Polished locally."
    assert qa_status["tasks"]["last_task"]["variant_count"] == 2
    assert qa_status["tasks"]["last_task"]["renderer"] == "local_parametric"
    assert qa_status["tasks"]["last_task"]["composition"]["crop"]["width"] == 0.6
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
