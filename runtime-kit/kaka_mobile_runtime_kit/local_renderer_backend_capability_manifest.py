from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "kaka.local_renderer_backend_capability_manifest.v1"
SURFACE = "hermes_openclaw_local_renderer_backend_capability_manifest"
STATUS = "ready_for_backend_gate_planning"
LOCAL_RENDERER_PROVIDER = "recipe_local"


def build_local_renderer_backend_capability_manifest(
    *,
    repo_root: Path | str = ".",
    photo_pack_root: Path | str = "photo-pack",
) -> Mapping[str, object]:
    root = Path(repo_root).resolve()
    photo_pack_path = _resolve_photo_pack_root(root, photo_pack_root)
    adapter_path = photo_pack_path / "adapters" / "recipe_local.py"
    adapter_contract, adapter_constants_readable = _read_recipe_adapter_constants(adapter_path)
    missing_inputs = []
    if not adapter_constants_readable:
        missing_inputs.append({
            "id": "recipe_local_adapter_constants",
            "label": "recipe_local adapter constants must be readable before backend gate planning.",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "status": STATUS if adapter_constants_readable else "blocked",
        "ready_for_backend_gate_planning": bool(adapter_constants_readable),
        "provider": LOCAL_RENDERER_PROVIDER,
        "source": {
            "photo_pack_root": str(photo_pack_path),
            "adapter_path": str(adapter_path),
            "adapter_constants_readable": bool(adapter_constants_readable),
        },
        "current_contract": _current_contract(adapter_contract),
        "backend_candidates": _backend_candidates(),
        "gate_definitions": _gate_definitions(),
        "missing_inputs": missing_inputs,
        "readiness_contract": {
            "command": "local-renderer-backend-readiness",
            "schema_version": "kaka.local_renderer_backend_readiness.v1",
            "required_before_phone_capability_change": True,
        },
        "phone_api": {
            "base_path": "/mobile/v1",
            "phone_api_unchanged": True,
            "mobile_bridge_endpoint_added": False,
            "capabilities_changed": False,
            "private_host_api_exposed": False,
        },
        "safety": _safety_contract(),
        "notes": [
            "P3.27 is a capability planning manifest, not a renderer backend implementation.",
            "Future backends require separate packaging, sandboxing, security review, and readiness proof before enablement.",
            "The current phone-facing photo_edit capability remains recipe_local with two JPEG variants.",
        ],
    }


def _resolve_photo_pack_root(repo_root: Path, photo_pack_root: Path | str) -> Path:
    path = Path(photo_pack_root)
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def _read_recipe_adapter_constants(adapter_path: Path) -> tuple[Mapping[str, object], bool]:
    if not adapter_path.exists():
        return {}, False
    try:
        tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
    except Exception:
        return {}, False

    values: dict[str, object] = {}
    wanted_names = {"RENDERER", "SCHEMA_VERSION", "STYLE_SCENES", "VARIANT_LABELS"}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted_names:
                try:
                    values[target.id] = ast.literal_eval(node.value)
                except Exception:
                    continue
    readable = (
        isinstance(values.get("RENDERER"), str)
        and isinstance(values.get("SCHEMA_VERSION"), str)
        and isinstance(values.get("STYLE_SCENES"), Mapping)
        and isinstance(values.get("VARIANT_LABELS"), Mapping)
    )
    return values, readable


def _current_contract(adapter_contract: Mapping[str, object]) -> Mapping[str, object]:
    variant_labels = adapter_contract.get("VARIANT_LABELS")
    if not isinstance(variant_labels, Mapping):
        variant_labels = {
            "variant_clean_pro": "Master",
            "variant_social_pop": "Social",
        }
    style_scenes = adapter_contract.get("STYLE_SCENES")
    if not isinstance(style_scenes, Mapping):
        style_scenes = {
            "natural_enhance": "natural",
            "portrait_polish": "portrait",
            "product_shot": "product",
            "social_cover": "social_cover",
        }
    return {
        "provider": LOCAL_RENDERER_PROVIDER,
        "renderer": str(adapter_contract.get("RENDERER") or "local_parametric"),
        "recipe_schema_version": str(adapter_contract.get("SCHEMA_VERSION") or "photo_edit_recipe.v1"),
        "supported_styles": sorted(str(style) for style in style_scenes.keys()),
        "supported_variants": [
            {
                "id": str(variant_id),
                "label": str(label),
            }
            for variant_id, label in variant_labels.items()
        ],
        "return_variants_max": len(variant_labels) if variant_labels else 2,
        "output_mime_types": ["image/jpeg"],
        "crop_policy": "original_crop_only",
        "crop_candidates_supported": False,
        "upscale_policy_supported": True,
    }


def _backend_candidates() -> list[Mapping[str, object]]:
    return [
        {
            "backend_id": "pillow",
            "display_name": "Pillow/PIL",
            "status": "current_supported",
            "dependency_added_by_p3_27": False,
            "enabled_for_phone_api": False,
            "gate_ids": ["fixture_render_probe", "phone_capability_truth"],
            "risk_notes": [
                "Covered by the existing P3.16 local-renderer-backend-readiness probe.",
                "Does not change the phone-facing two-variant recipe_local capability.",
            ],
        },
        {
            "backend_id": "core_image",
            "display_name": "Core Image",
            "status": "future_gate_required",
            "dependency_added_by_p3_27": False,
            "enabled_for_phone_api": False,
            "gate_ids": [
                "dependency_packaging",
                "sandboxed_execution",
                "deterministic_recipe_contract",
                "fixture_render_probe",
                "security_review",
                "phone_capability_truth",
            ],
            "risk_notes": [
                "Requires a separate macOS runtime bridge design and deterministic recipe mapping.",
            ],
        },
        {
            "backend_id": "imagemagick",
            "display_name": "ImageMagick",
            "status": "future_gate_required",
            "dependency_added_by_p3_27": False,
            "enabled_for_phone_api": False,
            "gate_ids": [
                "dependency_packaging",
                "sandboxed_execution",
                "deterministic_recipe_contract",
                "fixture_render_probe",
                "security_review",
                "phone_capability_truth",
            ],
            "risk_notes": [
                "Requires explicit sandbox and input policy review before any external tool execution.",
            ],
        },
        {
            "backend_id": "opencv",
            "display_name": "OpenCV",
            "status": "future_gate_required",
            "dependency_added_by_p3_27": False,
            "enabled_for_phone_api": False,
            "gate_ids": [
                "dependency_packaging",
                "sandboxed_execution",
                "deterministic_recipe_contract",
                "fixture_render_probe",
                "security_review",
                "phone_capability_truth",
            ],
            "risk_notes": [
                "Requires separate binary/package provenance and render parity tests.",
            ],
        },
        {
            "backend_id": "libvips",
            "display_name": "libvips",
            "status": "future_gate_required",
            "dependency_added_by_p3_27": False,
            "enabled_for_phone_api": False,
            "gate_ids": [
                "dependency_packaging",
                "sandboxed_execution",
                "deterministic_recipe_contract",
                "fixture_render_probe",
                "security_review",
                "phone_capability_truth",
            ],
            "risk_notes": [
                "Requires separate packaging, memory-use, and output fidelity validation.",
            ],
        },
    ]


def _gate_definitions() -> list[Mapping[str, object]]:
    return [
        {
            "id": "dependency_packaging",
            "label": "Backend dependency is packaged by the host runtime with provenance.",
            "required_before_enablement": True,
        },
        {
            "id": "sandboxed_execution",
            "label": "Backend execution is constrained to runtime-owned temp/input/output paths.",
            "required_before_enablement": True,
        },
        {
            "id": "deterministic_recipe_contract",
            "label": "Backend consumes the same strict PhotoEditRecipe contract.",
            "required_before_enablement": True,
        },
        {
            "id": "fixture_render_probe",
            "label": "Backend passes a synthetic local render readiness probe.",
            "required_before_enablement": True,
        },
        {
            "id": "security_review",
            "label": "Backend has a local execution and file handling security review.",
            "required_before_enablement": True,
        },
        {
            "id": "phone_capability_truth",
            "label": "Phone-facing capability truth is updated only after runtime readiness is proven.",
            "required_before_enablement": True,
        },
    ]


def _safety_contract() -> Mapping[str, object]:
    return {
        "runtime_side_only": True,
        "manifest_only": True,
        "does_not_install_dependencies": True,
        "does_not_import_future_backends": True,
        "does_not_execute_future_backends": True,
        "does_not_start_bridge": True,
        "does_not_bind_lan": True,
        "does_not_advertise_bonjour": True,
        "does_not_mint_credentials": True,
        "does_not_call_cloud_provider": True,
        "does_not_inspect_provider_keys": True,
        "does_not_persist_assets": True,
        "does_not_include_raw_image_bytes": True,
        "does_not_change_phone_api": True,
        "no_generative_pixels": True,
    }
