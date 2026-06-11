import io
import html as html_lib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from agent_pocket_mock_bridge import app as app_module
from agent_pocket_mock_bridge.app import RuntimeHTTPVisionProvider, create_app
from kaka_mobile_runtime_kit.pairing import (
    InMemoryPairingStore,
    PairingManager,
    PairingSecurityConfig,
    StaticPairingClock,
)
from kaka_mobile_runtime_kit.recall_search import RecallSearchResult


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


def test_runtime_settings_and_capabilities_use_configured_retention_policy():
    client = create_app(
        input_assets_days=3,
        output_assets_days=14,
        task_history_days=60,
    ).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    capabilities = client.get("/mobile/v1/capabilities", headers=headers).get_json()
    settings = client.get("/mobile/v1/runtime/settings", headers=headers).get_json()

    expected = {
        "input_assets_days": 3,
        "output_assets_days": 14,
        "task_history_days": 60,
    }
    assert capabilities["retention"] == expected
    assert settings["retention"] == expected
    assert set(settings["retention"]) == set(expected)


def test_mock_bridge_retention_purge_helper_skips_untimestamped_assets_and_has_no_mobile_route():
    app = app_module.MockBridgeApp(input_assets_days=7, output_assets_days=30, task_history_days=30)
    app.assets["asset_old_input"] = {
        "id": "asset_old_input",
        "role": "input",
        "bytes": b"input",
        "mime_type": "image/png",
    }
    app.assets["asset_result_old_output"] = {
        "id": "asset_result_old_output",
        "role": "output",
        "bytes": b"output",
        "mime_type": "image/png",
    }

    dry_run = app.purge_retention(now_iso="2026-06-07T00:00:00Z", dry_run=True)
    apply_receipt = app.purge_retention(now_iso="2026-06-07T00:00:00Z", dry_run=False)
    mobile_route = app.test_client().post(
        "/mobile/v1/runtime/purge",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    assert dry_run["mode"] == "dry_run"
    assert apply_receipt["mode"] == "apply"
    assert apply_receipt["applied"] is True
    assert apply_receipt["deleted"]["input_asset_ids"] == []
    assert apply_receipt["deleted"]["output_asset_ids"] == []
    assert apply_receipt["preserved"]["asset_purge_status"] == "skipped_missing_asset_timestamps"
    assert apply_receipt["preserved"]["untracked_asset_ids"] == ["asset_old_input", "asset_result_old_output"]
    assert sorted(app.assets) == ["asset_old_input", "asset_result_old_output"]
    assert mobile_route.status_code == 404


def test_mock_bridge_asset_retention_metadata_enables_explicit_purge():
    app = app_module.create_app()
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={
            "file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg"),
        },
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    status = client.get(f"/mobile/v1/tasks/{created.get_json()['task_id']}", headers=headers)
    source_asset_id = upload.get_json()["asset_id"]
    result_asset_id = status.get_json()["variants"][0]["asset_id"]

    assert app.assets[source_asset_id]["role"] == "input"
    assert app.assets[result_asset_id]["role"] == "output"
    assert app.assets[source_asset_id]["created_at"].endswith("Z")
    assert app.assets[result_asset_id]["created_at"].endswith("Z")

    qa_status = client.get("/mobile/v1/qa/status", headers=headers).get_json()
    rendered_qa = json.dumps(qa_status, sort_keys=True)
    assert "source-image" not in rendered_qa
    assert "iVBOR" not in rendered_qa

    app.assets[source_asset_id]["created_at"] = "2026-05-01T00:00:00Z"
    app.assets[result_asset_id]["created_at"] = "2026-05-01T00:00:00Z"
    apply_receipt = app.purge_retention(now_iso="2026-06-07T00:00:00Z", dry_run=False)
    mobile_route = client.post("/mobile/v1/runtime/purge", headers=headers)

    assert apply_receipt["deleted"]["input_asset_ids"] == [source_asset_id]
    assert apply_receipt["deleted"]["output_asset_ids"] == [result_asset_id]
    assert apply_receipt["preserved"]["asset_purge_status"] == "complete"
    assert source_asset_id not in app.assets
    assert result_asset_id not in app.assets
    assert mobile_route.status_code == 404


def test_assets_persist_download_and_purge_when_app_uses_runtime_store(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeAssetRecord, SQLiteRuntimeStore

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    app = app_module.create_app(runtime_store=store, runtime_store_path=str(db_path))
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
    )
    assert upload.status_code == 200
    source_asset_id = upload.get_json()["asset_id"]
    assert source_asset_id not in app.assets

    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": source_asset_id,
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    assert created.status_code == 200
    task_id = created.get_json()["task_id"]
    result_asset_id = f"asset_result_{task_id.removeprefix('task_')}_1"
    assert result_asset_id not in app.assets

    stored_status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)
    assert stored_status.status_code == 200
    stored_body = stored_status.get_json()
    assert stored_body["status"] == "completed"
    assert stored_body["variants"][0]["asset_id"] == result_asset_id
    assert stored_body["variants"][0]["download_url"].endswith("/download")

    source_download = client.get(f"/mobile/v1/assets/{source_asset_id}/download", headers=headers)
    result_download = client.get(f"/mobile/v1/assets/{result_asset_id}/download", headers=headers)
    assert source_download.status_code == 200
    assert source_download.data == b"source-image"
    assert result_download.status_code == 200
    assert result_download.content_type == "image/png"
    assert result_download.data.startswith(b"\x89PNG")

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()
    reopened_app = app_module.create_app(runtime_store=reopened, runtime_store_path=str(db_path))
    reopened_client = reopened_app.test_client()
    reopened_source_download = reopened_client.get(
        f"/mobile/v1/assets/{source_asset_id}/download",
        headers=headers,
    )
    reopened_result_download = reopened_client.get(
        f"/mobile/v1/assets/{result_asset_id}/download",
        headers=headers,
    )
    assert reopened_source_download.status_code == 200
    assert reopened_source_download.data == b"source-image"
    assert reopened_result_download.status_code == 200
    assert reopened_result_download.data.startswith(b"\x89PNG")

    for asset_id in (source_asset_id, result_asset_id):
        existing = reopened.get_asset(asset_id)
        assert existing is not None
        reopened.upsert_asset(
            RuntimeAssetRecord(
                asset_id=existing.asset_id,
                role=existing.role,
                created_at="2026-05-01T00:00:00Z",
                filename=existing.filename,
                mime_type=existing.mime_type,
                size_bytes=existing.size_bytes,
                sha256=existing.sha256,
                body=existing.body,
                metadata=existing.metadata,
            )
        )

    apply_receipt = reopened_app.purge_retention(now_iso="2026-06-07T00:00:00Z", dry_run=False)
    mobile_route = reopened_client.post("/mobile/v1/runtime/purge", headers=headers)
    assert apply_receipt["deleted"]["input_asset_ids"] == [source_asset_id]
    assert apply_receipt["deleted"]["output_asset_ids"] == [result_asset_id]
    assert apply_receipt["preserved"]["asset_purge_status"] == "complete"
    assert reopened.get_asset(source_asset_id) is None
    assert reopened.get_asset(result_asset_id) is None
    assert mobile_route.status_code == 404


def test_store_backed_photo_task_status_preserves_variants_after_reopen(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    app = app_module.create_app(runtime_store=store, runtime_store_path=str(db_path))
    client = app.test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 2,
        },
    )
    task_id = created.get_json()["task_id"]

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()
    reopened_client = app_module.create_app(runtime_store=reopened, runtime_store_path=str(db_path)).test_client()

    status = reopened_client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)

    assert status.status_code == 200
    body = status.get_json()
    assert body["task_id"] == task_id
    assert body["status"] == "completed"
    assert [variant["label"] for variant in body["variants"]] == ["Master", "Social"]
    assert body["variants"][0]["asset_id"].startswith("asset_result_")
    assert body["variants"][0]["download_url"].endswith("/download")
    assert body["explanation"]

    stored_task = reopened.get_task(task_id)
    assert stored_task is not None
    stored_variants = stored_task.metadata["variants"]
    assert [set(variant) for variant in stored_variants] == [
        {"id", "label", "asset_id"},
        {"id", "label", "asset_id"},
    ]
    assert "download_url" not in json.dumps(stored_task.metadata, sort_keys=True)

    rendered = json.dumps(body, sort_keys=True)
    assert "source-image" not in rendered
    assert str(db_path) not in rendered
    assert "runtime_store_path" not in rendered
    assert "provider_endpoint" not in rendered
    assert "mobile_token" not in rendered

    download = reopened_client.get(body["variants"][0]["download_url"], headers=headers)
    assert download.status_code == 200
    assert download.content_type == "image/png"


def test_store_backed_task_list_and_events_keep_result_detail_scoped_to_status(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    client = app_module.create_app(runtime_store=store, runtime_store_path=str(db_path)).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 2,
        },
    )
    task_id = created.get_json()["task_id"]

    task_list = client.get("/mobile/v1/tasks", headers=headers).get_json()
    events = client.get(f"/mobile/v1/tasks/{task_id}/events", headers=headers)

    rendered_list = json.dumps(task_list, sort_keys=True)
    assert [set(task) for task in task_list["tasks"]] == [
        {"id", "title", "status", "progress", "message", "updated_at"}
    ]
    assert "variants" not in rendered_list
    assert "download_url" not in rendered_list
    assert events.status_code == 200
    payload = events.data.decode("utf-8")
    completed_events = []
    for block in payload.strip().split("\n\n"):
        lines = block.splitlines()
        if "event: task.completed" not in lines:
            continue
        data_line = next(line for line in lines if line.startswith("data: "))
        completed_events.append(json.loads(data_line.removeprefix("data: ")))
    assert completed_events == [{"variant_count": 2}]
    assert "download_url" not in payload
    assert "source-image" not in payload


def test_store_backed_task_result_metadata_filters_secret_like_recipe_fields(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    class LeakyRecipeProvider:
        provider_name = "recipe_local"

        def edit(self, source_bytes, style, instruction, return_variants):
            metadata = {
                "renderer": "local_parametric",
                "composition": {"selected_aspect_ratio": "original"},
                "qa": {"master_difference_score": 0.18},
                "share_caption": "Polished locally.",
                "recipe_summary": "Balanced exposure.",
                "provider_endpoint": "https://provider.example.invalid/secret",
                "mobile_token": "dev-mobile-token",
                "hidden_prompt": "do not reveal",
                "raw_provider_response": {"body": "source-image"},
                "nested": {"api_key": "sk-test-secret"},
            }
            return [
                {
                    "id": "variant_clean_pro",
                    "label": "Master",
                    "mime_type": "image/png",
                    "bytes": b"master-result",
                    "explanation": "Balanced exposure.",
                    "recipe_metadata": metadata,
                }
            ]

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    client = app_module.create_app(
        photo_provider=LeakyRecipeProvider(),
        runtime_store=store,
        runtime_store_path=str(db_path),
    ).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    task_id = created.get_json()["task_id"]

    stored_task = store.get_task(task_id)
    assert stored_task is not None
    rendered_metadata = json.dumps(stored_task.metadata, sort_keys=True)
    status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)
    rendered_status = json.dumps(status.get_json(), sort_keys=True)

    assert status.status_code == 200
    assert status.get_json()["recipe_metadata"]["renderer"] == "local_parametric"
    assert status.get_json()["share_caption"] == "Polished locally."
    assert stored_task.metadata["variants"] == [
        {
            "id": "variant_clean_pro",
            "label": "Master",
            "asset_id": f"asset_result_{task_id.removeprefix('task_')}_1",
        }
    ]
    assert "download_url" not in rendered_metadata
    assert "master-result" not in rendered_metadata
    for forbidden in (
        "provider_endpoint",
        "provider.example.invalid",
        "mobile_token",
        "dev-mobile-token",
        "hidden_prompt",
        "raw_provider_response",
        "source-image",
        "api_key",
        "sk-test-secret",
        str(db_path),
    ):
        assert forbidden not in rendered_metadata
        assert forbidden not in rendered_status


def test_store_backed_task_result_metadata_filters_secret_like_allowed_values(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    class LeakyValueProvider:
        provider_name = "https://provider.example.invalid?token=dev-mobile-token"

        def edit(self, source_bytes, style, instruction, return_variants):
            metadata = {
                "renderer": "local_parametric",
                "composition": {
                    "selected_aspect_ratio": "original",
                    "note": "data:image/png;base64,iVBORw0KGgo=",
                },
                "qa": {"diagnostic": "/Users/kartz/.kaka/mobile-runtime.sqlite3"},
                "share_caption": "token=dev-mobile-token",
                "recipe_summary": "https://provider.example.invalid/raw",
            }
            return [
                {
                    "id": "variant_clean_pro",
                    "label": "Master",
                    "mime_type": "image/png",
                    "bytes": b"master-result",
                    "explanation": "Bearer dev-mobile-token",
                    "recipe_metadata": metadata,
                }
            ]

    db_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    client = app_module.create_app(
        photo_provider=LeakyValueProvider(),
        runtime_store=store,
        runtime_store_path=str(db_path),
    ).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
    )
    created = client.post(
        "/mobile/v1/tasks/photo-edit",
        headers=headers,
        json={
            "asset_id": upload.get_json()["asset_id"],
            "style": "natural_enhance",
            "instruction": "Keep it realistic.",
            "return_variants": 1,
        },
    )
    task_id = created.get_json()["task_id"]

    stored_task = store.get_task(task_id)
    assert stored_task is not None
    status = client.get(f"/mobile/v1/tasks/{task_id}", headers=headers)
    rendered_metadata = json.dumps(stored_task.metadata, sort_keys=True)
    rendered_status = json.dumps(status.get_json(), sort_keys=True)

    assert status.status_code == 200
    assert stored_task.metadata["recipe_metadata"]["renderer"] == "local_parametric"
    assert stored_task.metadata["variants"] == [
        {
            "id": "variant_clean_pro",
            "label": "Master",
            "asset_id": f"asset_result_{task_id.removeprefix('task_')}_1",
        }
    ]
    for forbidden in (
        "https://provider.example.invalid",
        "token=",
        "dev-mobile-token",
        "Bearer",
        "/Users/",
        ".sqlite3",
        "data:image",
        "iVBOR",
        "source-image",
        str(db_path),
    ):
        assert forbidden not in rendered_metadata
        assert forbidden not in rendered_status


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
    assert intake["supports_voice_followup"] is True
    assert intake["supports_sse"] is False


def test_recall_semantic_search_returns_ranked_results_without_raw_index_ids():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_launch",
            "user_visible_summary": "Launch summary language should prefer concise Chinese answers.",
        },
    )

    response = client.post(
        "/mobile/v1/recall/search",
        headers=headers,
        json={"query": "launch summary language", "limit": 5},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["query"] == "launch summary language"
    assert payload["mode"] == "semantic"
    assert payload["items"][0]["item"]["summary"] == "Launch summary language should prefer concise Chinese answers."
    assert payload["items"][0]["score"] > 0
    assert "embedding_" not in rendered


def test_runtime_settings_advertise_store_and_semantic_recall_status(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    store_path = tmp_path / "kaka-runtime.sqlite3"
    store = SQLiteRuntimeStore(store_path)
    store.initialize()
    client = create_app(runtime_store=store, runtime_store_path=str(store_path)).test_client()

    response = client.get(
        "/mobile/v1/runtime/settings",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["recall_store"]["enabled"] is True
    assert payload["recall_store"]["owner"] == "runtime"
    assert payload["recall_store"]["label"] == "Local Kaka Recall and task store"
    assert payload["recall_store"]["phone_can_change"] is False
    assert payload["semantic_recall"]["available"] is True
    assert payload["semantic_recall"]["mode"] == "local_deterministic"
    assert payload["retention"]["task_history_days"] == 30
    assert "provider_keys" not in rendered
    assert "kaka-runtime.sqlite3" not in rendered


def test_runtime_settings_advertise_provider_backed_recall_without_endpoint_leak():
    client = create_app(
        recall_search_provider="runtime_http",
        recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
    ).test_client()

    response = client.get(
        "/mobile/v1/runtime/settings",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["semantic_recall"]["available"] is True
    assert payload["semantic_recall"]["owner"] == "runtime"
    assert payload["semantic_recall"]["mode"] == "provider_backed"
    assert payload["semantic_recall"]["provider_label"] == "Runtime provider"
    assert "127.0.0.1:8788" not in rendered
    assert "kaka-runtime.sqlite3" not in rendered
    assert "provider_keys" not in rendered


def test_runtime_settings_do_not_expose_runtime_side_ui_values(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    store_path = tmp_path / "runtime_store_path-openai_api_key.sqlite3"
    store = SQLiteRuntimeStore(store_path)
    store.initialize()
    endpoint = "http://127.0.0.1:8788/kaka/recall/search?hidden_prompt=never"
    client = create_app(
        runtime_store=store,
        runtime_store_path=str(store_path),
        recall_search_provider="runtime_http",
        recall_search_endpoint=endpoint,
    ).test_client()

    response = client.get(
        "/mobile/v1/runtime/settings",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert set(payload.keys()) == {"recall_store", "semantic_recall", "retention", "connection_security"}
    assert set(payload["recall_store"].keys()) == {"enabled", "owner", "label", "phone_can_change"}
    assert set(payload["semantic_recall"].keys()) == {"available", "owner", "mode", "provider_label"}
    assert set(payload["retention"].keys()) == {"input_assets_days", "output_assets_days", "task_history_days"}
    assert set(payload["connection_security"].keys()) == {
        "pairing_code_ttl_seconds",
        "mobile_token_ttl_seconds",
        "mobile_token_revocation_supported",
        "trusted_local_tls_required",
        "tls_trust_state",
        "tls_certificate_label",
    }
    assert payload["recall_store"]["enabled"] is True
    assert payload["semantic_recall"]["mode"] == "provider_backed"
    assert payload["connection_security"]["mobile_token_revocation_supported"] is False
    assert payload["connection_security"]["tls_trust_state"] == "development_http"
    for forbidden in (
        str(store_path),
        "runtime_store_path",
        "openai_api_key",
        "127.0.0.1:8788",
        "hidden_prompt",
        "recall_search_endpoint",
    ):
        assert forbidden not in rendered


def test_provider_backed_recall_search_keeps_semantic_response_shape():
    client = create_app(recall_search_provider="fixture").test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_provider_search",
            "user_visible_summary": "Provider launch summary language preference.",
        },
    )

    response = client.post(
        "/mobile/v1/recall/search",
        headers=headers,
        json={"query": "launch summary language", "limit": 5},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["query"] == "launch summary language"
    assert payload["mode"] == "semantic"
    assert payload["retrieval_mode"] == "provider_backed"
    assert payload["items"][0]["item"]["summary"] == "Provider launch summary language preference."
    assert "embedding_" not in rendered


def test_recall_search_allowlists_runtime_store_results():
    class LeakyRuntimeStore:
        recall_search_provider = type("Provider", (), {"provider_mode": "provider_backed"})()

        def search_recall_semantic(self, query, limit):
            return [
                {
                    "item": {
                        "item_id": "recall_0001",
                        "summary": "Provider launch summary language preference.",
                        "created_at": "2026-06-05T09:30:00Z",
                        "provenance": {
                            "source_surface": "voice",
                            "provider_endpoint": "http://127.0.0.1:8788/kaka/recall/search",
                            "raw_provider_response": "never leak",
                        },
                        "provider_key": "secret-provider-key",
                        "sqlite_path": "/tmp/kaka-runtime.sqlite3",
                        "raw_embedding": [0.1, 0.2],
                    },
                    "score": 0.91,
                    "match_reason": "Matched http://127.0.0.1:8788 hidden_prompt raw_embedding.",
                    "provider_endpoint": "http://127.0.0.1:8788/kaka/recall/search",
                    "raw_provider_response": {"hidden_prompt": "never leak"},
                    "index_rows": ["embedding_recall_0001"],
                }
            ]

    client = create_app(runtime_store=LeakyRuntimeStore()).test_client()

    response = client.post(
        "/mobile/v1/recall/search",
        headers={"Authorization": "Bearer dev-mobile-token"},
        json={"query": "launch summary language", "limit": 5},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["items"] == [
        {
            "item": {
                "item_id": "recall_0001",
                "summary": "Provider launch summary language preference.",
                "created_at": "2026-06-05T09:30:00Z",
                "provenance": {"source_surface": "voice"},
            },
            "score": 0.91,
            "match_reason": "Matched runtime Recall provider.",
        }
    ]
    for forbidden in (
        "secret-provider-key",
        "127.0.0.1:8788",
        "kaka-runtime.sqlite3",
        "raw_embedding",
        "hidden_prompt",
        "embedding_recall_0001",
        "index_rows",
    ):
        assert forbidden not in rendered


def test_recall_search_allowlists_in_memory_provider_results():
    class LeakyProvider:
        provider_mode = "provider_backed"

        def search(self, query, items, limit):
            return [
                RecallSearchResult(
                    item=items[0],
                    score=0.87,
                    match_reason="Matched provider_endpoint http://127.0.0.1:8788 hidden_prompt.",
                    provider_mode="provider_backed",
                )
            ]

    client = create_app(recall_search_provider=LeakyProvider()).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_safe",
            "user_visible_summary": "Safe visible summary.",
        },
    )

    response = client.post(
        "/mobile/v1/recall/search",
        headers=headers,
        json={"query": "safe", "limit": 5},
    )

    payload = response.get_json()
    rendered = str(payload)
    assert response.status_code == 200
    assert payload["items"][0]["match_reason"] == "Matched runtime Recall provider."
    assert payload["items"][0]["item"]["provenance"] == {"source_task_id": "task_safe"}
    assert "127.0.0.1:8788" not in rendered
    assert "hidden_prompt" not in rendered


def test_recall_semantic_search_requires_non_empty_query():
    client = create_app().test_client()

    response = client.post(
        "/mobile/v1/recall/search",
        headers={"Authorization": "Bearer dev-mobile-token"},
        json={"query": "   ", "limit": 5},
    )

    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "invalid_recall_payload"


def test_capabilities_advertise_runtime_neutral_local_recipe_contract():
    client = create_app().test_client()

    response = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": "Bearer dev-mobile-token"},
    )

    tasks = response.get_json()["tasks"]
    photo_edit = tasks["photo_edit"]
    vision = tasks["vision"]
    image_intake = tasks["image_intake"]
    assert response.status_code == 200
    assert photo_edit["provider"] == "recipe_local"
    assert photo_edit["renderer"] == "local_parametric"
    assert photo_edit["accepted_mime_types"] == ["image/jpeg"]
    assert vision["accepted_mime_types"] == ["image/jpeg", "image/heic", "image/png"]
    assert image_intake["accepted_mime_types"] == [
        "image/jpeg",
        "image/heic",
        "image/png",
    ]
    assert photo_edit["variant_labels"] == ["Master", "Social"]
    assert photo_edit["variant_ids"] == ["variant_clean_pro", "variant_social_pop"]
    assert photo_edit["crop_aspects"] == ["original"]
    assert photo_edit["supports_crop_candidates"] is False
    assert photo_edit["supports_upscale_policy"] is True
    assert photo_edit["return_variants_max"] == 2


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


def test_development_pairing_payload_includes_configured_tls_pin_metadata():
    client = create_app(
        advertised_endpoint="https://macbook-pro.local:8765",
        trusted_local_tls_required=True,
        tls_certificate_label="Kaka Local Runtime",
        tls_public_key_sha256="a" * 64,
    ).test_client()

    payload = client.get("/mobile/v1/pairing/dev").get_json()
    rendered = str(payload)

    assert payload["endpoint"] == "https://macbook-pro.local:8765"
    assert payload["trusted_local_tls_required"] is True
    assert payload["tls_certificate_label"] == "Kaka Local Runtime"
    assert payload["tls_public_key_sha256"] == "a" * 64
    assert "private_key" not in rendered


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


def _production_pairing_manager() -> tuple[PairingManager, StaticPairingClock]:
    clock = StaticPairingClock(datetime(2026, 6, 5, 8, 0, 0, tzinfo=timezone.utc))
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=clock,
        config=PairingSecurityConfig(code_ttl_seconds=120),
    )
    return manager, clock


def test_production_pairing_payload_exchanges_once_and_authorizes_capabilities():
    manager, _ = _production_pairing_manager()
    app = create_app(pairing_manager=manager, advertised_endpoint="https://macbook-pro.local:8765")
    client = app.test_client()

    payload_response = client.get("/mobile/v1/pairing/qr")
    payload = payload_response.get_json()
    first = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": payload["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )
    replay = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": payload["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )
    capabilities = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": f"Bearer {first.get_json()['mobile_token']}"},
    )

    assert payload_response.status_code == 200
    assert payload["endpoint"] == "https://macbook-pro.local:8765"
    assert payload["expires_at"] == "2026-06-05T08:02:00Z"
    assert first.status_code == 200
    assert first.get_json()["mobile_token"].startswith("mobile_")
    assert replay.status_code == 409
    assert replay.get_json()["error"]["code"] == "pairing_already_used"
    assert capabilities.status_code == 200


def test_production_pairing_payload_includes_configured_tls_pin_metadata():
    manager, _ = _production_pairing_manager()
    manager.config = PairingSecurityConfig(
        code_ttl_seconds=120,
        trusted_local_tls_required=True,
        tls_trust_state="configured",
        tls_certificate_label="Kaka Local Runtime",
        tls_public_key_sha256="b" * 64,
        tls_private_key_path="/Users/kartz/.kaka/private/key.pem",
    )
    client = create_app(pairing_manager=manager, advertised_endpoint="https://macbook-pro.local:8765").test_client()

    payload = client.get("/mobile/v1/pairing/qr").get_json()
    rendered = str(payload)

    assert payload["trusted_local_tls_required"] is True
    assert payload["tls_certificate_label"] == "Kaka Local Runtime"
    assert payload["tls_public_key_sha256"] == "b" * 64
    assert "key.pem" not in rendered


def test_production_pairing_payload_uses_configured_runtime_display_name_and_scheme():
    manager, _ = _production_pairing_manager()
    client = create_app(
        pairing_manager=manager,
        runtime_id="openclaw",
        runtime_display_name="Agent Pocket Mock OpenClaw",
        pairing_scheme="http",
    ).test_client()

    payload = client.get(
        "/mobile/v1/pairing/qr",
        headers={"Host": "192.168.1.10:8765"},
    ).get_json()

    assert payload["endpoint"] == "http://192.168.1.10:8765"
    assert payload["runtime"] == "openclaw"
    assert payload["display_name"] == "Agent Pocket Mock OpenClaw"


def test_production_pairing_rejects_expired_code():
    manager, clock = _production_pairing_manager()
    client = create_app(pairing_manager=manager, advertised_endpoint="https://macbook-pro.local:8765").test_client()
    payload = client.get("/mobile/v1/pairing/qr").get_json()

    clock.advance(timedelta(seconds=121))
    response = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": payload["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "pairing_expired"


def test_revoked_mobile_token_is_rejected_by_every_protected_endpoint():
    manager, _ = _production_pairing_manager()
    client = create_app(pairing_manager=manager, advertised_endpoint="https://macbook-pro.local:8765").test_client()
    payload = client.get("/mobile/v1/pairing/qr").get_json()
    exchange = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": payload["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    ).get_json()
    token = exchange["mobile_token"]

    revoke = client.post(
        "/mobile/v1/pairing/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    capabilities = client.get(
        "/mobile/v1/capabilities",
        headers={"Authorization": f"Bearer {token}"},
    )
    tasks = client.get(
        "/mobile/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert revoke.status_code == 200
    assert revoke.get_json() == {"status": "revoked"}
    assert capabilities.status_code == 401
    assert tasks.status_code == 401


def test_runtime_settings_security_summary_does_not_expose_raw_tokens_or_private_paths():
    manager, _ = _production_pairing_manager()
    manager.config = PairingSecurityConfig(
        code_ttl_seconds=120,
        trusted_local_tls_required=True,
        tls_trust_state="configured",
        tls_certificate_label="Kaka Local Runtime",
        tls_private_key_path="/Users/kartz/.kaka/private/key.pem",
    )
    client = create_app(pairing_manager=manager, advertised_endpoint="https://macbook-pro.local:8765").test_client()
    payload = client.get("/mobile/v1/pairing/qr").get_json()
    token = client.post(
        "/mobile/v1/pairing/exchange",
        json={
            "pairing_code": payload["pairing_code"],
            "device_name": "Kartz iPhone",
            "device_public_id": "device_abc",
        },
    ).get_json()["mobile_token"]

    response = client.get(
        "/mobile/v1/runtime/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.get_json()
    rendered = str(body)

    assert response.status_code == 200
    assert body["connection_security"]["pairing_code_ttl_seconds"] == 120
    assert body["connection_security"]["mobile_token_revocation_supported"] is True
    assert body["connection_security"]["trusted_local_tls_required"] is True
    assert body["connection_security"]["tls_trust_state"] == "configured"
    assert body["connection_security"]["tls_certificate_label"] == "Kaka Local Runtime"
    assert token not in rendered
    assert "key.pem" not in rendered


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


def test_universal_intake_context_snapshot_allows_motion_calendar_busy_labels():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "text",
            "text": "Prep a short note before the next meeting.",
            "context_snapshot": {
                "timestamp": "2026-06-05T09:30:00Z",
                "timezone": "Asia/Shanghai",
                "source_surface": "share_extension",
                "network": "wifi",
                "motion": "walking",
                "calendar_availability": "busy_soon",
            },
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)

    snapshot = status.get_json()["intake"]["metadata"]["context_snapshot"]
    assert created.status_code == 200
    assert snapshot == {
        "timestamp": "2026-06-05T09:30:00Z",
        "timezone": "Asia/Shanghai",
        "source_surface": "share_extension",
        "network": "wifi",
        "motion": "walking",
        "calendar_availability": "busy_soon",
    }


def test_universal_intake_context_snapshot_filters_private_fields():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    created = client.post(
        "/mobile/v1/tasks/intake",
        headers=headers,
        json={
            "type": "text",
            "text": "Summarize this without keeping private context.",
            "context_snapshot": {
                "timestamp": "2026-06-05T09:30:00Z",
                "timezone": "Asia/Shanghai",
                "source_surface": "share_extension",
                "motion": "driving",
                "calendar_availability": "busy",
                "ssid": "HomeWiFiSecret",
                "bssid": "aa:bb:cc:dd:ee:ff",
                "ip_address": "192.168.1.44",
                "latitude": "31.2304",
                "longitude": "121.4737",
                "calendar_event_title": "Private board review",
                "attendees": ["ceo@example.com"],
                "calendar_notes": "Do not leak this note.",
                "calendar_body": "Sensitive event body.",
            },
        },
    )
    status = client.get(created.get_json()["status_url"], headers=headers)
    task_list = client.get("/mobile/v1/tasks", headers=headers)

    snapshot = status.get_json()["intake"]["metadata"]["context_snapshot"]
    rendered = json.dumps([status.get_json(), task_list.get_json()], sort_keys=True)
    assert created.status_code == 200
    assert snapshot == {
        "timestamp": "2026-06-05T09:30:00Z",
        "timezone": "Asia/Shanghai",
        "source_surface": "share_extension",
        "motion": "driving",
        "calendar_availability": "busy",
    }
    for forbidden in (
        "ssid",
        "HomeWiFiSecret",
        "bssid",
        "aa:bb:cc:dd:ee:ff",
        "ip_address",
        "192.168.1.44",
        "latitude",
        "31.2304",
        "longitude",
        "121.4737",
        "calendar_event_title",
        "Private board review",
        "attendees",
        "ceo@example.com",
        "calendar_notes",
        "Do not leak this note.",
        "calendar_body",
        "Sensitive event body.",
    ):
        assert forbidden not in rendered


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


def test_vision_task_sanitizes_runtime_provider_payload_before_mobile_status():
    class LeakyVisionProvider:
        provider_name = "leaky_vision"

        def analyze(self, source_bytes, mode, instruction, locale):
            return {
                "mode": mode,
                "title": "Recorded",
                "summary": "Provider handled vision.",
                "items": [
                    {
                        "title": "Object",
                        "value": "Notebook",
                        "provider_endpoint": "http://127.0.0.1:7788/vision",
                        "raw_provider_response": {"OPENAI_API_KEY": "sk-vision-secret"},
                    }
                ],
                "sections": [
                    {
                        "title": "Findings",
                        "kind": "candidates",
                        "hidden_prompt": "never expose hidden prompt",
                        "items": [
                            {
                                "title": "Subject",
                                "value": "Desk",
                                "subtitle": "hidden_prompt raw_provider_response task_logs",
                                "task_logs": ["OPENAI_API_KEY=sk-vision-secret"],
                            }
                        ],
                    }
                ],
                "provider_endpoint": "http://127.0.0.1:7788/vision",
                "raw_provider_response": {"hidden_prompt": "never expose", "token": "sk-vision-secret"},
                "hidden_prompt": "never expose hidden prompt",
                "task_logs": ["OPENAI_API_KEY=sk-vision-secret"],
            }

    client = create_app(vision_provider=LeakyVisionProvider()).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    upload = client.post(
        "/mobile/v1/assets",
        headers=headers,
        data={"file": (io.BytesIO(b"source-image"), "photo.jpg", "image/jpeg")},
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
    body = status.get_json()
    rendered = str(body)

    assert body["vision"]["items"][0]["value"] == "Notebook"
    assert body["vision"]["sections"][0]["items"][0]["value"] == "Desk"
    assert "provider_endpoint" not in rendered
    assert "raw_provider_response" not in rendered
    assert "hidden_prompt" not in rendered
    assert "task_logs" not in rendered
    assert "OPENAI_API_KEY" not in rendered
    assert "sk-vision-secret" not in rendered


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
        "deleted_index_ids": [],
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
        "deleted_index_ids": ["embedding_recall_0001"],
    }
    assert second.status_code == 200
    assert second.get_json() == {
        "action": "forget",
        "status": "forgotten",
        "item": None,
        "deleted_item_ids": [],
        "deleted_index_ids": [],
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


def test_recall_items_supports_query_and_limit():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    for summary in [
        "Remember Chinese summaries.",
        "Keep the PDF upload limit visible.",
        "Prefer concise Chinese answers.",
    ]:
        client.post(
            "/mobile/v1/recall/actions",
            headers=headers,
            json={
                "action": "remember",
                "source_task_id": f"task_{summary[:4].lower()}",
                "user_visible_summary": summary,
            },
        )

    listed = client.get("/mobile/v1/recall/items?query=Chinese&limit=1", headers=headers)

    assert listed.status_code == 200
    assert [item["item_id"] for item in listed.get_json()["items"]] == ["recall_0003"]


def test_recall_items_clips_negative_limit_to_zero():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "user_visible_summary": "Remember the launch preference.",
        },
    )

    listed = client.get("/mobile/v1/recall/items?limit=-5", headers=headers)

    assert listed.status_code == 200
    assert listed.get_json()["items"] == []


def test_recall_export_returns_json_items_with_generated_at():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    remembered = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "user_visible_summary": "Remember Chinese summaries.",
        },
    )

    exported = client.get("/mobile/v1/recall/export", headers=headers)

    assert exported.status_code == 200
    payload = exported.get_json()
    assert payload == {
        "schema_version": "kaka.recall_export.v1",
        "format": "json",
        "generated_at": "2026-06-05T00:00:00Z",
        "artifact_policy": {
            "classification": "user_recall_export",
            "artifact_kind": "recall_export_json",
            "runtime_owned_source": True,
            "database_dump": False,
            "phone_safe": True,
            "item_fields": ["item_id", "summary", "created_at", "provenance"],
            "provenance_fields": ["source_task_id", "source_inbox_item_id", "source_surface"],
            "forbidden_fields": [
                "raw_embeddings",
                "embeddings",
                "retrieval_index_rows",
                "provider_keys",
                "provider_endpoints",
                "bearer_tokens",
                "mobile_tokens",
                "runtime_store_path",
                "sqlite_path",
                "hidden_prompts",
                "raw_provider_responses",
                "unrelated_task_logs",
            ],
        },
        "items": [remembered.get_json()["item"]],
    }
    rendered_items = json.dumps(payload["items"], ensure_ascii=False, sort_keys=True)
    assert "embedding_" not in rendered_items
    assert "runtime_store_path" not in rendered_items


def test_recall_delete_returns_index_deletion_receipt():
    client = create_app().test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}
    remembered = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "user_visible_summary": "Remember Chinese summaries.",
        },
    )
    item_id = remembered.get_json()["item"]["item_id"]

    deleted = client.delete(f"/mobile/v1/recall/items/{item_id}", headers=headers)

    assert deleted.status_code == 200
    assert deleted.get_json()["deleted_item_ids"] == [item_id]
    assert deleted.get_json()["deleted_index_ids"] == [f"embedding_{item_id}"]


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
    assert first.get_json() == {
        "status": "forgotten",
        "deleted_item_ids": [item_id],
        "deleted_index_ids": [f"embedding_{item_id}"],
    }
    assert second.status_code == 200
    assert second.get_json() == {
        "status": "forgotten",
        "deleted_item_ids": [],
        "deleted_index_ids": [],
    }
    assert listed.get_json()["items"] == []


def test_recall_persists_when_app_uses_runtime_store(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    first_store = SQLiteRuntimeStore(db_path)
    first_store.initialize()
    first_client = create_app(runtime_store=first_store).test_client()

    response = first_client.post(
        "/mobile/v1/recall/actions",
        headers={"Authorization": "Bearer dev-mobile-token"},
        json={
            "action": "remember",
            "source_task_id": "task_0001",
            "user_visible_summary": "Keep restart-safe Recall.",
        },
    )
    assert response.status_code == 200

    second_store = SQLiteRuntimeStore(db_path)
    second_store.initialize()
    second_client = create_app(runtime_store=second_store).test_client()

    items = second_client.get(
        "/mobile/v1/recall/items?query=restart",
        headers={"Authorization": "Bearer dev-mobile-token"},
    ).get_json()

    assert [item["summary"] for item in items["items"]] == ["Keep restart-safe Recall."]


def test_persistent_recall_export_forget_and_delete_receipts_survive_reopen(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    inbox_a = "12345678-1234-1234-1234-1234567890AB"
    inbox_b = "12345678-1234-1234-1234-1234567890AC"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    client = create_app(runtime_store=store).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    first = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "source_inbox_item_id": inbox_a,
            "user_visible_summary": "Forget only this stored item.",
        },
    ).get_json()
    second = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "remember",
            "source_task_id": "task_123",
            "source_inbox_item_id": inbox_b,
            "user_visible_summary": "Keep this stored item.",
        },
    ).get_json()

    exported = client.get("/mobile/v1/recall/export", headers=headers).get_json()
    forgotten = client.post(
        "/mobile/v1/recall/actions",
        headers=headers,
        json={
            "action": "forget",
            "source_task_id": "task_123",
            "source_inbox_item_id": inbox_a,
            "user_visible_summary": "Forget exact source.",
        },
    ).get_json()

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()
    reopened_client = create_app(runtime_store=reopened).test_client()
    listed = reopened_client.get("/mobile/v1/recall/items", headers=headers).get_json()
    deleted = reopened_client.delete(
        f"/mobile/v1/recall/items/{second['item']['item_id']}",
        headers=headers,
    ).get_json()

    assert exported["format"] == "json"
    assert [item["item_id"] for item in exported["items"]] == [second["item"]["item_id"], first["item"]["item_id"]]
    assert forgotten["deleted_item_ids"] == [first["item"]["item_id"]]
    assert forgotten["deleted_index_ids"] == [f"embedding_{first['item']['item_id']}"]
    assert [item["item_id"] for item in listed["items"]] == [second["item"]["item_id"]]
    assert deleted == {
        "status": "forgotten",
        "deleted_item_ids": [second["item"]["item_id"]],
        "deleted_index_ids": [f"embedding_{second['item']['item_id']}"],
    }
    assert reopened_client.get("/mobile/v1/recall/items", headers=headers).get_json()["items"] == []


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


def test_runtime_tasks_persist_when_app_uses_runtime_store(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    first_store = SQLiteRuntimeStore(db_path)
    first_store.initialize()
    first_client = create_app(runtime_store=first_store).test_client()

    created = first_client.post(
        "/mobile/v1/tasks/intake",
        headers={"Authorization": "Bearer dev-mobile-token"},
        json={"type": "text", "text": "Summarize this note."},
    )
    assert created.status_code == 200

    reopened_store = SQLiteRuntimeStore(db_path)
    reopened_store.initialize()
    second_client = create_app(runtime_store=reopened_store).test_client()
    tasks = second_client.get(
        "/mobile/v1/tasks",
        headers={"Authorization": "Bearer dev-mobile-token"},
    ).get_json()

    assert len(tasks["tasks"]) == 1
    assert tasks["tasks"][0]["status"] in {"completed", "waiting_for_approval", "running"}


def test_runtime_task_approval_cancel_and_events_persist_when_app_uses_runtime_store(tmp_path):
    from kaka_mobile_runtime_kit.runtime_store import RuntimeTaskEvent, RuntimeTaskRecord, SQLiteRuntimeStore

    db_path = tmp_path / "runtime.sqlite3"
    store = SQLiteRuntimeStore(db_path)
    store.initialize()
    store.upsert_task(
        RuntimeTaskRecord(
            task_id="task_waiting",
            title="Approve PDF summary",
            status="waiting_for_approval",
            updated_at="2026-06-05T09:32:00Z",
            detail="Needs approval.",
            approval_required=True,
            metadata={"progress": 0.0, "message": "Needs approval."},
        )
    )
    store.append_task_event(
        RuntimeTaskEvent(
            event_id="event_task_waiting_requested",
            task_id="task_waiting",
            type="approval_requested",
            message="Approve PDF summary.",
            created_at="2026-06-05T09:32:01Z",
        )
    )
    client = create_app(runtime_store=store).test_client()
    headers = {"Authorization": "Bearer dev-mobile-token"}

    approved = client.post(
        "/mobile/v1/tasks/task_waiting/approval",
        headers=headers,
        json={"action": "approve", "note": "Yes"},
    ).get_json()
    cancelled = client.post("/mobile/v1/tasks/task_waiting/cancel", headers=headers).get_json()
    events = client.get("/mobile/v1/tasks/task_waiting/events", headers=headers)
    events_text = events.data.decode("utf-8")

    reopened = SQLiteRuntimeStore(db_path)
    reopened.initialize()
    reopened_task = reopened.get_task("task_waiting")
    reopened_events = reopened.list_task_events("task_waiting")

    assert approved["status"] == "approved"
    assert approved["task"]["status"] == "running"
    assert cancelled["status"] == "cancelled"
    assert cancelled["task"]["status"] == "cancelled"
    assert reopened_task is not None
    assert reopened_task.status == "cancelled"
    assert {event.type for event in reopened_events} >= {"approval_requested", "task_approved", "task_cancelled"}
    assert events.content_type == "text/event-stream"
    assert "event: task.progress" in events_text
    assert "event: task.completed" in events_text
    assert "event: task_approved" not in events_text
