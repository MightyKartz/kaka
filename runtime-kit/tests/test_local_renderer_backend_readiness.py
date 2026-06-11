import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.local_renderer_backend_readiness import (
    build_local_renderer_backend_readiness,
)


SCHEMA_PATH = Path("runtime-kit/packaging/local-renderer-backend-readiness.schema.json")


def test_local_renderer_backend_readiness_runs_recipe_local_probe() -> None:
    report = build_local_renderer_backend_readiness(
        repo_root=Path("."),
        photo_pack_root="photo-pack",
    )
    rendered = json.dumps(report, sort_keys=True)

    assert report["schema_version"] == "kaka.local_renderer_backend_readiness.v1"
    assert report["surface"] == "hermes_openclaw_local_renderer_backend_readiness"
    assert report["status"] == "ready_for_local_recipe_flow"
    assert report["ready_for_local_recipe_flow"] is True
    assert report["provider"] == "recipe_local"
    assert report["backend"]["provider"] == "recipe_local"
    assert report["backend"]["renderer"] == "local_parametric"
    assert report["backend"]["adapter"]["exists"] is True
    assert report["backend"]["adapter"]["loadable"] is True
    assert report["backend"]["pillow"]["available"] is True
    assert report["recipe_contract"]["schema_version"] == "photo_edit_recipe.v1"
    assert report["recipe_contract"]["max_return_variants"] == 2
    assert "natural_enhance" in report["recipe_contract"]["supported_styles"]
    assert report["probe"]["variant_count"] == 2
    assert report["probe"]["variant_ids"] == ["variant_clean_pro", "variant_social_pop"]
    assert report["probe"]["qa"]["master_difference_score"] > 0
    assert report["phone_api"]["mobile_bridge_endpoint_added"] is False
    assert report["gates"]["can_start_bridge"] is False
    assert report["safety"]["does_not_call_cloud_provider"] is True
    assert "source_image_base64" not in rendered
    assert "OPENAI_API_KEY" not in rendered


def test_local_renderer_backend_readiness_blocks_non_local_renderer_provider() -> None:
    report = build_local_renderer_backend_readiness(provider="openai")

    assert report["status"] == "blocked"
    assert report["ready_for_local_recipe_flow"] is False
    assert report["provider"] == "openai"
    assert report["missing_inputs"] == [
        {
            "id": "photo_provider",
            "label": "Use recipe_local for local parameterized renderer readiness.",
        }
    ]
    assert report["gates"]["can_call_cloud_provider"] is False


def test_local_renderer_backend_readiness_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)

    validator.validate(build_local_renderer_backend_readiness())
    validator.validate(build_local_renderer_backend_readiness(provider="openai"))


def test_local_renderer_backend_readiness_schema_rejects_drift() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    ready = json.loads(json.dumps(build_local_renderer_backend_readiness()))

    phone_api_drift = json.loads(json.dumps(ready))
    phone_api_drift["phone_api"]["mobile_bridge_endpoint_added"] = True
    assert not validator.is_valid(phone_api_drift)

    forged_provider = json.loads(json.dumps(ready))
    forged_provider["provider"] = "openai"
    forged_provider["backend"]["provider"] = "openai"
    assert not validator.is_valid(forged_provider)

    empty_checks = json.loads(json.dumps(ready))
    empty_checks["checks"] = []
    assert not validator.is_valid(empty_checks)

    empty_probe = json.loads(json.dumps(ready))
    empty_probe["probe"]["variant_count"] = 0
    empty_probe["probe"]["variant_ids"] = []
    empty_probe["probe"]["variant_labels"] = []
    empty_probe["probe"]["mime_types"] = []
    assert not validator.is_valid(empty_probe)

    cloud_drift = json.loads(json.dumps(ready))
    cloud_drift["gates"]["can_call_cloud_provider"] = True
    assert not validator.is_valid(cloud_drift)

    payload_drift = json.loads(json.dumps(ready))
    payload_drift["probe"]["source_image_base64"] = "abc"
    assert not validator.is_valid(payload_drift)

    false_ready = json.loads(json.dumps(build_local_renderer_backend_readiness(provider="openai")))
    false_ready["ready_for_local_recipe_flow"] = True
    assert not validator.is_valid(false_ready)
