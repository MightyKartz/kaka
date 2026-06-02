import base64
import json
from pathlib import Path

from agent_pocket_mock_bridge.photo_providers import (
    PhotoPackAdapterProvider,
    build_photo_provider,
    build_provider_preflight_report,
)


def test_photo_pack_adapter_provider_loads_module_and_returns_variant_bytes(tmp_path):
    adapter_path = tmp_path / "fake_adapter.py"
    adapter_path.write_text(
        """
import json

def run_edit(input_path, output_dir, style, instruction, return_variants=1):
    assert input_path.read_bytes() == b"source-image"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "variant.png"
    output_path.write_bytes(b"edited-image")
    result = {
        "status": "completed",
        "variants": [{
            "id": "variant_fake",
            "label": "Fake Variant",
            "path": str(output_path),
            "mime_type": "image/png"
        }],
        "explanation": "Fake adapter completed."
    }
    (output_dir / "manifest.json").write_text(json.dumps(result))
    return result
""",
        encoding="utf-8",
    )

    provider = PhotoPackAdapterProvider(adapter_path=adapter_path)

    variants = provider.edit(
        source_bytes=b"source-image",
        style="natural_enhance",
        instruction="Keep it realistic.",
        return_variants=1,
    )

    assert variants == [
        {
            "id": "variant_fake",
            "label": "Fake Variant",
            "mime_type": "image/png",
            "bytes": b"edited-image",
            "explanation": "Fake adapter completed.",
        }
    ]


def test_photo_pack_adapter_provider_preserves_manifest_metadata(tmp_path):
    adapter_path = tmp_path / "fake_recipe_adapter.py"
    adapter_path.write_text(
        """
def run_edit(input_path, output_dir, style, instruction, return_variants=2):
    output_dir.mkdir(parents=True, exist_ok=True)
    first = output_dir / "master.jpg"
    second = output_dir / "social.jpg"
    first.write_bytes(b"master-image")
    second.write_bytes(b"social-image")
    return {
        "status": "completed",
        "provider": "recipe_local",
        "renderer": "local_parametric",
        "variants": [
            {"id": "variant_clean_pro", "label": "Master", "path": str(first), "mime_type": "image/jpeg"},
            {"id": "variant_social_pop", "label": "Social", "path": str(second), "mime_type": "image/jpeg"},
        ],
        "composition": {
            "selected_aspect_ratio": "4:5",
            "crop": {"x": 0.2, "y": 0.0, "width": 0.6, "height": 1.0}
        },
        "qa": {
            "master_difference_score": 0.18,
            "social_difference_score": 0.31
        },
        "share_caption": "Polished locally.",
        "recipe_summary": "Balanced exposure.",
        "explanation": "Balanced exposure."
    }
""",
        encoding="utf-8",
    )

    provider = PhotoPackAdapterProvider(adapter_path=adapter_path)

    variants = provider.edit(
        source_bytes=b"source-image",
        style="natural_enhance",
        instruction="Keep it realistic.",
        return_variants=2,
    )

    assert variants[0]["recipe_metadata"]["provider"] == "recipe_local"
    assert variants[0]["recipe_metadata"]["renderer"] == "local_parametric"
    assert variants[0]["recipe_metadata"]["composition"]["selected_aspect_ratio"] == "4:5"
    assert variants[0]["recipe_metadata"]["qa"]["master_difference_score"] == 0.18
    assert variants[0]["recipe_metadata"]["share_caption"] == "Polished locally."
    assert variants[1]["recipe_metadata"] == variants[0]["recipe_metadata"]


def test_build_photo_provider_returns_fixture_or_photo_pack_adapter():
    fixture = build_photo_provider("fixture", photo_pack_root=Path("missing"))
    script = build_photo_provider("script", photo_pack_root=Path("photo-pack"))
    recipe = build_photo_provider("recipe_local", photo_pack_root=Path("photo-pack"))

    assert fixture.edit(b"source", "natural_enhance", "Keep it realistic.", 1)[0]["bytes"].startswith(
        base64.b64decode("iVBORw0KGgo=")
    )
    assert isinstance(script, PhotoPackAdapterProvider)
    assert script.provider_name == "script"
    assert script.adapter_path.name == "script.py"
    assert isinstance(recipe, PhotoPackAdapterProvider)
    assert recipe.provider_name == "recipe_local"
    assert recipe.adapter_path.name == "recipe_local.py"


def test_provider_preflight_reports_recipe_local_without_provider_key():
    report = build_provider_preflight_report("recipe_local", photo_pack_root=Path("photo-pack"))

    assert report["ok"] is True
    assert report["provider"] == "recipe_local"
    assert report["adapter"]["exists"] is True
    assert "OPENAI_API_KEY" not in json.dumps(report)
    assert "--photo-provider recipe_local" in report["commands"]["server"]
    assert "--photo-provider recipe_local" in report["commands"]["qa"]


def test_provider_preflight_reports_openai_key_without_exposing_secret(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    missing = build_provider_preflight_report("openai", photo_pack_root=Path("photo-pack"))
    ready = build_provider_preflight_report(
        "openai",
        photo_pack_root=Path("photo-pack"),
        env={"OPENAI_API_KEY": "secret-value"},
    )

    assert missing["ok"] is False
    assert missing["provider"] == "openai"
    assert missing["adapter"]["exists"] is True
    assert missing["env"]["OPENAI_API_KEY"] == "missing"
    assert "--env-file /path/to/hermes-openai.env" in missing["commands"]["server"]
    assert "agent_pocket_mock_bridge.fake_openai" in missing["commands"]["fake_openai"]
    assert "simulator-openai-smoke" in missing["commands"]["simulator_openai_smoke"]
    assert "--screenshot-file /tmp/agent-pocket-simulator-openai-provider-smoke.png" in missing["commands"]["simulator_openai_smoke"]
    assert "secret-value" not in json.dumps(ready)
    assert ready["ok"] is True
    assert ready["env"]["OPENAI_API_KEY"] == "set"
