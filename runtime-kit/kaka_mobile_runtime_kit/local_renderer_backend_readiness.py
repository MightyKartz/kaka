from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


SCHEMA_VERSION = "kaka.local_renderer_backend_readiness.v1"
SURFACE = "hermes_openclaw_local_renderer_backend_readiness"
LOCAL_RENDERER_PROVIDER = "recipe_local"


def build_local_renderer_backend_readiness(
    *,
    repo_root: Path | str = ".",
    photo_pack_root: Path | str = "photo-pack",
    provider: str = LOCAL_RENDERER_PROVIDER,
) -> Mapping[str, object]:
    root = Path(repo_root).resolve()
    photo_pack_path = _resolve_photo_pack_root(root, photo_pack_root)
    adapter_path = photo_pack_path / "adapters" / "recipe_local.py"
    safety = _safety_contract()
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "status": "blocked",
        "ready_for_local_recipe_flow": False,
        "provider": provider,
        "backend": {
            "provider": provider,
            "renderer": "",
            "photo_pack_root": str(photo_pack_path),
            "adapter": {
                "path": str(adapter_path),
                "exists": adapter_path.exists(),
                "loadable": False,
            },
            "pillow": _pillow_report(),
        },
        "recipe_contract": {
            "schema_version": "",
            "supported_styles": [],
            "supported_variants": [],
            "max_return_variants": 0,
            "output_mime_types": ["image/jpeg"],
        },
        "checks": [],
        "missing_inputs": [],
        "probe": {
            "mode": "synthetic_fixture_render",
            "style": "natural_enhance",
        },
        "known_limits": [
            "Current local renderer backend is Pillow/PIL only.",
            "The readiness probe proves JPEG fixture rendering, not HEIC input support.",
            "Safety flags are recipe-contract constraints, not computer-vision identity, text, or logo verification.",
            "Future ImageMagick, OpenCV, or libvips backends should plug in behind this runtime-side readiness boundary.",
        ],
        "phone_api": {
            "base_path": "/mobile/v1",
            "phone_api_unchanged": True,
            "mobile_bridge_endpoint_added": False,
            "capabilities_changed": False,
            "private_host_api_exposed": False,
        },
        "gates": {
            "can_start_bridge": False,
            "can_bind_lan": False,
            "can_advertise_bonjour": False,
            "can_mint_mobile_token": False,
            "can_call_cloud_provider": False,
        },
        "safety": safety,
    }

    if provider != LOCAL_RENDERER_PROVIDER:
        base["checks"] = [
            _check(
                "local_renderer_provider",
                False,
                "Only recipe_local is checked by this local renderer readiness report.",
            ),
        ]
        base["missing_inputs"] = [
            {
                "id": "photo_provider",
                "label": "Use recipe_local for local parameterized renderer readiness.",
            }
        ]
        return base

    adapter_module = _load_recipe_adapter(adapter_path)
    adapter_loadable = adapter_module is not None
    base["backend"]["adapter"]["loadable"] = adapter_loadable
    base["backend"]["renderer"] = str(getattr(adapter_module, "RENDERER", "")) if adapter_module else ""
    base["recipe_contract"] = _recipe_contract(adapter_module)

    probe_report = _run_renderer_probe(root, photo_pack_path, provider)
    probe_ready = bool(probe_report.get("ok"))
    pillow_ready = bool(base["backend"]["pillow"]["available"])
    checks = [
        _check("photo_pack_directory", photo_pack_path.exists(), "Photo Pack directory exists."),
        _check("recipe_local_adapter", adapter_path.exists(), "recipe_local adapter file exists."),
        _check("recipe_local_adapter_loadable", adapter_loadable, "recipe_local adapter can be loaded."),
        _check("pillow_available", pillow_ready, "Pillow is importable for local rendering."),
        _check("synthetic_render_probe", probe_ready, "Synthetic local fixture render produced variants."),
    ]
    ready = all(bool(check["ok"]) for check in checks)
    missing_inputs = [
        {"id": str(check["id"]), "label": str(check["detail"])}
        for check in checks
        if not bool(check["ok"])
    ]

    base.update({
        "status": "ready_for_local_recipe_flow" if ready else "blocked",
        "ready_for_local_recipe_flow": ready,
        "checks": checks,
        "missing_inputs": missing_inputs,
        "probe": probe_report.get("probe", base["probe"]),
    })
    return base


def _resolve_photo_pack_root(repo_root: Path, photo_pack_root: Path | str) -> Path:
    path = Path(photo_pack_root)
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def _run_renderer_probe(
    repo_root: Path,
    photo_pack_path: Path,
    provider: str,
) -> Mapping[str, object]:
    mock_bridge_path = str((repo_root / "mock_bridge").resolve())
    inserted_path = False
    if mock_bridge_path not in sys.path:
        sys.path.insert(0, mock_bridge_path)
        inserted_path = True
    try:
        from agent_pocket_mock_bridge.photo_providers import build_renderer_readiness_report
    except Exception as error:
        return {
            "ok": False,
            "missing": [f"mock_bridge import failed: {type(error).__name__}"],
            "probe": {
                "mode": "synthetic_fixture_render",
                "style": "natural_enhance",
            },
        }
    try:
        return build_renderer_readiness_report(provider, photo_pack_root=photo_pack_path)
    finally:
        if inserted_path:
            try:
                sys.path.remove(mock_bridge_path)
            except ValueError:
                pass


def _pillow_report() -> Mapping[str, object]:
    try:
        from PIL import __version__ as pillow_version

        return {
            "available": True,
            "version": str(pillow_version),
            "required": True,
        }
    except Exception:
        return {
            "available": False,
            "version": "",
            "required": True,
        }


def _load_recipe_adapter(adapter_path: Path) -> ModuleType | None:
    if not adapter_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("kaka_recipe_local_contract", adapter_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def _recipe_contract(adapter_module: ModuleType | None) -> Mapping[str, object]:
    if adapter_module is None:
        return {
            "schema_version": "",
            "supported_styles": [],
            "supported_variants": [],
            "max_return_variants": 0,
            "output_mime_types": ["image/jpeg"],
        }
    variant_labels = getattr(adapter_module, "VARIANT_LABELS", {})
    return {
        "schema_version": str(getattr(adapter_module, "SCHEMA_VERSION", "")),
        "supported_styles": sorted(getattr(adapter_module, "STYLE_SCENES", {}).keys()),
        "supported_variants": [
            {
                "id": str(variant_id),
                "label": str(label),
            }
            for variant_id, label in variant_labels.items()
        ],
        "max_return_variants": len(variant_labels),
        "output_mime_types": ["image/jpeg"],
    }


def _check(check_id: str, ok: bool, detail: str) -> Mapping[str, object]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "detail": detail,
    }


def _safety_contract() -> Mapping[str, object]:
    return {
        "runtime_side_only": True,
        "does_not_start_bridge": True,
        "does_not_bind_lan": True,
        "does_not_advertise_bonjour": True,
        "does_not_mint_credentials": True,
        "does_not_call_cloud_provider": True,
        "does_not_inspect_provider_keys": True,
        "does_not_persist_probe_assets": True,
        "does_not_change_phone_api": True,
        "no_generative_pixels": True,
        "no_asset_retention_change": True,
        "probe_payloads_omitted": True,
    }
