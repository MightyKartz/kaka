import base64
import importlib.util
import json
from pathlib import Path


def load_openai_adapter():
    adapter_path = Path(__file__).resolve().parents[1] / "adapters" / "openai_image.py"
    spec = importlib.util.spec_from_file_location("photo_pack_openai_image_adapter", adapter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openai_adapter_posts_image_edit_request_and_writes_variants(tmp_path):
    adapter = load_openai_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    input_path.write_bytes(b"source-image")
    calls = []

    def fake_post(url, headers, body, content_type, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "body": body,
                "content_type": content_type,
                "timeout": timeout,
            }
        )
        return {
            "data": [
                {"b64_json": base64.b64encode(b"edited-one").decode("ascii")},
                {"b64_json": base64.b64encode(b"edited-two").decode("ascii")},
            ]
        }

    result = adapter.run_edit(
        input_path=input_path,
        output_dir=output_dir,
        style="portrait_polish",
        instruction="Keep the person recognizable.",
        return_variants=2,
        api_key="test-key",
        model="gpt-image-1.5",
        http_post=fake_post,
    )

    assert calls[0]["url"] == "https://api.openai.com/v1/images/edits"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["content_type"].startswith("multipart/form-data; boundary=")
    assert b'name="image"; filename="input.jpg"' in calls[0]["body"]
    assert b'name="model"\r\n\r\ngpt-image-1.5' in calls[0]["body"]
    assert b'name="n"\r\n\r\n2' in calls[0]["body"]
    assert b"Keep the person recognizable." in calls[0]["body"]

    paths = [Path(variant["path"]) for variant in result["variants"]]
    assert result["status"] == "completed"
    assert result["provider"] == "openai"
    assert paths[0].read_bytes() == b"edited-one"
    assert paths[1].read_bytes() == b"edited-two"
    assert json.loads((output_dir / "manifest.json").read_text())["model"] == "gpt-image-1.5"


def test_openai_adapter_requires_api_key(tmp_path, monkeypatch):
    adapter = load_openai_adapter()
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"source-image")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        adapter.run_edit(
            input_path=input_path,
            output_dir=tmp_path / "out",
            style="natural_enhance",
            instruction="Keep it realistic.",
        )
    except adapter.OpenAIImageEditError as error:
        assert "OPENAI_API_KEY" in str(error)
    else:
        raise AssertionError("Expected OpenAIImageEditError")


def test_openai_adapter_wraps_provider_error(tmp_path):
    adapter = load_openai_adapter()
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"source-image")

    def fake_post(url, headers, body, content_type, timeout):
        raise adapter.OpenAIImageEditError("OpenAI image edit failed (400): policy rejection")

    try:
        adapter.run_edit(
            input_path=input_path,
            output_dir=tmp_path / "out",
            style="social_cover",
            instruction="Make it title-safe.",
            api_key="test-key",
            http_post=fake_post,
        )
    except adapter.OpenAIImageEditError as error:
        assert "policy rejection" in str(error)
    else:
        raise AssertionError("Expected OpenAIImageEditError")
