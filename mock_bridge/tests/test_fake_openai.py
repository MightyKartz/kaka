import json
import threading
import urllib.request

from agent_pocket_mock_bridge.fake_openai import create_fake_openai_server
from agent_pocket_mock_bridge.server import build_app_for_provider, create_http_server


def test_fake_openai_server_returns_b64_images_and_records_request_fields():
    server = create_fake_openai_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        body, content_type = _multipart_body(
            {
                "model": "gpt-image-1.5",
                "prompt": "Make the photo brighter.",
                "n": "2",
                "output_format": "png",
            },
            {
                "image": ("source.png", "image/png", b"source-image"),
            },
        )

        response = _json_request(
            f"{base_url}/images/edits",
            method="POST",
            body=body,
            headers={
                "Authorization": "Bearer test-key",
                "Content-Type": content_type,
            },
        )
        status = _json_request(f"{base_url}/status")

        assert len(response["data"]) == 2
        assert response["data"][0]["b64_json"]
        assert status["request_count"] == 1
        assert status["last_request"]["path"] == "/images/edits"
        assert status["last_request"]["authorization_present"] is True
        assert status["last_request"]["fields"]["model"] == "gpt-image-1.5"
        assert status["last_request"]["fields"]["n"] == "2"
        assert status["last_request"]["files"]["image"] == {
            "filename": "source.png",
            "mime_type": "image/png",
            "size_bytes": len(b"source-image"),
        }
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_openai_provider_runs_against_local_openai_compatible_server(monkeypatch):
    fake_openai = create_fake_openai_server(host="127.0.0.1", port=0)
    fake_thread = threading.Thread(target=fake_openai.serve_forever, daemon=True)
    fake_thread.start()
    fake_base_url = f"http://127.0.0.1:{fake_openai.server_address[1]}"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", fake_base_url)
    monkeypatch.setenv("OPENAI_IMAGE_OUTPUT_FORMAT", "png")

    app = build_app_for_provider("openai", photo_pack_root="photo-pack")
    bridge = create_http_server(host="127.0.0.1", port=0, app=app)
    bridge_thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    bridge_thread.start()
    bridge_base_url = f"http://127.0.0.1:{bridge.server_address[1]}"

    try:
        upload_body, upload_content_type = _multipart_body(
            {"metadata": '{"width":100,"height":100}'},
            {"file": ("photo.png", "image/png", b"source-image")},
        )
        upload = _json_request(
            f"{bridge_base_url}/mobile/v1/assets",
            method="POST",
            body=upload_body,
            headers={
                "Authorization": "Bearer dev-mobile-token",
                "Content-Type": upload_content_type,
            },
        )
        created = _json_request(
            f"{bridge_base_url}/mobile/v1/tasks/photo-edit",
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
        task = _json_request(
            f"{bridge_base_url}/mobile/v1/tasks/{created['task_id']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        download = _raw_request(
            f"{bridge_base_url}{task['variants'][0]['download_url']}",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        bridge_status = _json_request(
            f"{bridge_base_url}/mobile/v1/qa/status",
            headers={"Authorization": "Bearer dev-mobile-token"},
        )
        fake_status = _json_request(f"{fake_base_url}/status")

        assert task["status"] == "completed"
        assert task["provider"] == "openai"
        assert download.startswith(b"\x89PNG")
        assert bridge_status["provider"]["name"] == "openai"
        assert bridge_status["tasks"]["completed"] == 1
        assert bridge_status["assets"]["download_request_count"] == 1
        assert fake_status["request_count"] == 1
        assert fake_status["last_request"]["fields"]["output_format"] == "png"
        assert "Improve exposure" in fake_status["last_request"]["fields"]["prompt"]
    finally:
        bridge.shutdown()
        bridge_thread.join(timeout=2)
        bridge.server_close()
        fake_openai.shutdown()
        fake_thread.join(timeout=2)
        fake_openai.server_close()


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
