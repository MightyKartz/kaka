import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.local_renderer_backend_capability_manifest import (
    build_local_renderer_backend_capability_manifest,
)


SCHEMA_PATH = Path("runtime-kit/packaging/local-renderer-backend-capability-manifest.schema.json")


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def test_local_renderer_backend_capability_manifest_describes_current_and_future_backends() -> None:
    manifest = build_local_renderer_backend_capability_manifest()
    rendered = json.dumps(manifest, sort_keys=True).lower()

    assert manifest["schema_version"] == "kaka.local_renderer_backend_capability_manifest.v1"
    assert manifest["surface"] == "hermes_openclaw_local_renderer_backend_capability_manifest"
    assert manifest["status"] == "ready_for_backend_gate_planning"
    assert manifest["ready_for_backend_gate_planning"] is True
    assert manifest["provider"] == "recipe_local"
    assert manifest["source"]["adapter_constants_readable"] is True
    assert manifest["missing_inputs"] == []

    current = manifest["current_contract"]
    assert current["provider"] == "recipe_local"
    assert current["renderer"] == "local_parametric"
    assert current["recipe_schema_version"] == "photo_edit_recipe.v1"
    assert current["return_variants_max"] == 2
    assert current["output_mime_types"] == ["image/jpeg"]
    assert current["crop_policy"] == "original_crop_only"
    assert current["crop_candidates_supported"] is False
    assert current["upscale_policy_supported"] is True
    assert "natural_enhance" in current["supported_styles"]

    candidates = {candidate["backend_id"]: candidate for candidate in manifest["backend_candidates"]}
    assert sorted(candidates) == ["core_image", "imagemagick", "libvips", "opencv", "pillow"]
    assert candidates["pillow"]["status"] == "current_supported"
    assert candidates["pillow"]["enabled_for_phone_api"] is False
    for backend_id in ("core_image", "imagemagick", "opencv", "libvips"):
        assert candidates[backend_id]["status"] == "future_gate_required"
        assert candidates[backend_id]["dependency_added_by_p3_27"] is False
        assert candidates[backend_id]["enabled_for_phone_api"] is False
        assert candidates[backend_id]["gate_ids"]
        assert candidates[backend_id]["risk_notes"]

    gate_ids = {gate["id"] for gate in manifest["gate_definitions"]}
    assert {
        "dependency_packaging",
        "sandboxed_execution",
        "deterministic_recipe_contract",
        "fixture_render_probe",
        "security_review",
        "phone_capability_truth",
    }.issubset(gate_ids)

    assert manifest["readiness_contract"]["command"] == "local-renderer-backend-readiness"
    assert manifest["phone_api"]["base_path"] == "/mobile/v1"
    assert manifest["phone_api"]["phone_api_unchanged"] is True
    assert manifest["phone_api"]["mobile_bridge_endpoint_added"] is False
    assert manifest["phone_api"]["capabilities_changed"] is False
    assert manifest["safety"]["manifest_only"] is True
    assert manifest["safety"]["does_not_import_future_backends"] is True
    assert manifest["safety"]["does_not_execute_future_backends"] is True
    assert "source_image_base64" not in rendered
    assert "openai_api_key" not in rendered
    assert "api_key" not in rendered
    assert "token" not in rendered
    assert "cv2" not in rendered
    assert "pyvips" not in rendered
    assert "wand" not in rendered
    assert "subprocess" not in rendered


def test_local_renderer_backend_capability_manifest_validates_against_schema() -> None:
    validator = _schema_validator()

    validator.validate(build_local_renderer_backend_capability_manifest())


def test_local_renderer_backend_capability_manifest_blocks_missing_adapter_constants(tmp_path) -> None:
    validator = _schema_validator()

    manifest = build_local_renderer_backend_capability_manifest(
        repo_root=tmp_path,
        photo_pack_root="missing-photo-pack",
    )

    assert manifest["status"] == "blocked"
    assert manifest["ready_for_backend_gate_planning"] is False
    assert manifest["source"]["adapter_constants_readable"] is False
    assert manifest["missing_inputs"] == [
        {
            "id": "recipe_local_adapter_constants",
            "label": "recipe_local adapter constants must be readable before backend gate planning.",
        }
    ]
    validator.validate(manifest)


def test_local_renderer_backend_capability_manifest_blocks_non_literal_adapter_constants(tmp_path) -> None:
    validator = _schema_validator()
    photo_pack = tmp_path / "photo-pack"
    adapters = photo_pack / "adapters"
    adapters.mkdir(parents=True)
    (adapters / "recipe_local.py").write_text(
        "\n".join(
            [
                'RENDERER = "local_parametric"',
                'SCHEMA_VERSION = "photo_edit_recipe.v1"',
                'STYLE_SCENES = dict(natural_enhance="natural")',
                'VARIANT_LABELS = {"variant_clean_pro": "Master", "variant_social_pop": "Social"}',
            ]
        )
    )

    manifest = build_local_renderer_backend_capability_manifest(
        repo_root=tmp_path,
        photo_pack_root="photo-pack",
    )

    assert manifest["status"] == "blocked"
    assert manifest["ready_for_backend_gate_planning"] is False
    assert manifest["source"]["adapter_constants_readable"] is False
    validator.validate(manifest)


def test_local_renderer_backend_capability_manifest_reads_adapter_constants_without_execution(tmp_path) -> None:
    photo_pack = tmp_path / "photo-pack"
    adapters = photo_pack / "adapters"
    adapters.mkdir(parents=True)
    (adapters / "recipe_local.py").write_text(
        "\n".join(
            [
                'PROVIDER = "recipe_local"',
                'RENDERER = "local_parametric"',
                'SCHEMA_VERSION = "photo_edit_recipe.v1"',
                'STYLE_SCENES = {"natural_enhance": "natural"}',
                'VARIANT_LABELS = {"variant_clean_pro": "Master", "variant_social_pop": "Social"}',
                'raise RuntimeError("adapter was executed")',
            ]
        )
    )

    manifest = build_local_renderer_backend_capability_manifest(
        repo_root=tmp_path,
        photo_pack_root="photo-pack",
    )

    assert manifest["current_contract"]["supported_styles"] == ["natural_enhance"]
    assert manifest["current_contract"]["supported_variants"] == [
        {
            "id": "variant_clean_pro",
            "label": "Master",
        },
        {
            "id": "variant_social_pop",
            "label": "Social",
        },
    ]


def test_local_renderer_backend_capability_manifest_schema_rejects_unsafe_drift() -> None:
    validator = _schema_validator()
    manifest = json.loads(json.dumps(build_local_renderer_backend_capability_manifest()))

    changed_styles = json.loads(json.dumps(manifest))
    changed_styles["current_contract"]["supported_styles"] = ["natural_enhance", "experimental_style"]
    assert not validator.is_valid(changed_styles)

    changed_variant = json.loads(json.dumps(manifest))
    changed_variant["current_contract"]["supported_variants"][0]["id"] = "variant_experimental"
    assert not validator.is_valid(changed_variant)

    future_claims_ready = json.loads(json.dumps(manifest))
    future_claims_ready["backend_candidates"][1]["status"] = "current_supported"
    assert not validator.is_valid(future_claims_ready)

    missing_gate_definition = json.loads(json.dumps(manifest))
    missing_gate_definition["gate_definitions"] = missing_gate_definition["gate_definitions"][:-1]
    assert not validator.is_valid(missing_gate_definition)

    under_gated_future_backend = json.loads(json.dumps(manifest))
    under_gated_future_backend["backend_candidates"][1]["gate_ids"] = ["security_review"]
    assert not validator.is_valid(under_gated_future_backend)

    dependency_added = json.loads(json.dumps(manifest))
    dependency_added["backend_candidates"][2]["dependency_added_by_p3_27"] = True
    assert not validator.is_valid(dependency_added)

    phone_capability_changed = json.loads(json.dumps(manifest))
    phone_capability_changed["phone_api"]["capabilities_changed"] = True
    assert not validator.is_valid(phone_capability_changed)

    new_endpoint = json.loads(json.dumps(manifest))
    new_endpoint["phone_api"]["mobile_bridge_endpoint_added"] = True
    assert not validator.is_valid(new_endpoint)

    unsafe_command = json.loads(json.dumps(manifest))
    unsafe_command["backend_candidates"][3]["command"] = "magick input.jpg output.jpg"
    assert not validator.is_valid(unsafe_command)

    unsafe_safety = json.loads(json.dumps(manifest))
    unsafe_safety["safety"]["does_not_execute_future_backends"] = False
    assert not validator.is_valid(unsafe_safety)
