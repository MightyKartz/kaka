#!/usr/bin/env python3
"""Local recipe renderer for Agent Pocket Master Shot Phase 1."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat


PROVIDER = "recipe_local"
RENDERER = "local_parametric"
SCHEMA_VERSION = "photo_edit_recipe.v1"

STYLE_SCENES = {
    "natural_enhance": "natural",
    "portrait_polish": "portrait",
    "product_shot": "product",
    "social_cover": "social_cover",
}

VARIANT_LABELS = {
    "variant_clean_pro": "Master",
    "variant_social_pop": "Social",
}

GLOBAL_RANGES = {
    "exposure": (-1.0, 1.0),
    "contrast": (-1.0, 1.0),
    "highlights": (-1.0, 1.0),
    "shadows": (-1.0, 1.0),
    "temperature": (-1500.0, 1500.0),
    "tint": (-1.0, 1.0),
    "vibrance": (-1.0, 1.0),
    "saturation": (-1.0, 1.0),
    "clarity": (0.0, 1.0),
}

LOCAL_RANGES = {
    "subject_boost": (0.0, 1.0),
    "skin_smoothing": (0.0, 1.0),
    "background_falloff": (0.0, 1.0),
    "background_soften": (0.0, 1.0),
    "sharpen": (0.0, 1.0),
    "denoise": (0.0, 1.0),
    "vignette": (0.0, 1.0),
}

REQUIRED_SAFETY_FLAGS = [
    "preserve_identity",
    "preserve_text",
    "preserve_logo",
    "preserve_product_color",
    "no_generative_pixels",
]

ALLOWED_TOP_LEVEL_KEYS = {
    "schema_version",
    "style",
    "variant",
    "scene",
    "global",
    "local",
    "composition",
    "upscale",
    "safety",
}

STYLE_DEFAULTS: dict[str, dict[str, dict[str, float]]] = {
    "natural_enhance": {
        "global": {
            "exposure": 0.14,
            "contrast": 0.16,
            "highlights": -0.10,
            "shadows": 0.16,
            "temperature": 180.0,
            "tint": 0.0,
            "vibrance": 0.18,
            "saturation": 0.08,
            "clarity": 0.12,
        },
        "local": {
            "subject_boost": 0.16,
            "skin_smoothing": 0.03,
            "background_falloff": 0.08,
            "background_soften": 0.02,
            "sharpen": 0.16,
            "denoise": 0.05,
            "vignette": 0.05,
        },
    },
    "portrait_polish": {
        "global": {
            "exposure": 0.12,
            "contrast": 0.10,
            "highlights": -0.12,
            "shadows": 0.20,
            "temperature": 120.0,
            "tint": 0.03,
            "vibrance": 0.10,
            "saturation": 0.04,
            "clarity": 0.08,
        },
        "local": {
            "subject_boost": 0.20,
            "skin_smoothing": 0.10,
            "background_falloff": 0.12,
            "background_soften": 0.06,
            "sharpen": 0.10,
            "denoise": 0.08,
            "vignette": 0.06,
        },
    },
    "product_shot": {
        "global": {
            "exposure": 0.18,
            "contrast": 0.18,
            "highlights": -0.04,
            "shadows": 0.10,
            "temperature": 60.0,
            "tint": 0.0,
            "vibrance": 0.08,
            "saturation": 0.04,
            "clarity": 0.18,
        },
        "local": {
            "subject_boost": 0.18,
            "skin_smoothing": 0.0,
            "background_falloff": 0.08,
            "background_soften": 0.02,
            "sharpen": 0.24,
            "denoise": 0.04,
            "vignette": 0.04,
        },
    },
    "social_cover": {
        "global": {
            "exposure": 0.16,
            "contrast": 0.24,
            "highlights": -0.08,
            "shadows": 0.18,
            "temperature": 220.0,
            "tint": 0.02,
            "vibrance": 0.28,
            "saturation": 0.12,
            "clarity": 0.16,
        },
        "local": {
            "subject_boost": 0.24,
            "skin_smoothing": 0.04,
            "background_falloff": 0.14,
            "background_soften": 0.04,
            "sharpen": 0.20,
            "denoise": 0.04,
            "vignette": 0.08,
        },
    },
}

STYLE_GOALS = {
    "natural_enhance": "realistic exposure, white balance, shadow/highlight recovery, mild clarity",
    "portrait_polish": "face-safe brightness, skin tone protection, subtle background falloff, no identity changes",
    "product_shot": "brighter subject, sharper edges, cleaner color, restrained vignette",
    "social_cover": "stronger crop, contrast, color, and subject separation while preserving original content",
}


class RecipeValidationError(ValueError):
    """Raised when a recipe is unsafe or not renderable."""


def build_fixture_recipe(style: str, variant_id: str = "variant_clean_pro") -> dict[str, Any]:
    if style not in STYLE_SCENES:
        raise ValueError(f"Unsupported style: {style}")
    if variant_id not in VARIANT_LABELS:
        raise ValueError(f"Unsupported variant: {variant_id}")

    base = deepcopy(STYLE_DEFAULTS[style])
    if variant_id == "variant_social_pop":
        _boost_for_social(base["global"], base["local"])

    return {
        "schema_version": SCHEMA_VERSION,
        "style": style,
        "variant": variant_id,
        "scene": STYLE_SCENES[style],
        "global": base["global"],
        "local": base["local"],
        "composition": {
            "selected_aspect_ratio": "4:5",
            "crop": {"x": 0.20, "y": 0.0, "width": 0.60, "height": 1.0},
            "crop_candidates": [
                {"aspect_ratio": "original", "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "score": 0.72},
                {"aspect_ratio": "4:5", "x": 0.20, "y": 0.0, "width": 0.60, "height": 1.0, "score": 0.88},
                {"aspect_ratio": "1:1", "x": 0.125, "y": 0.0, "width": 0.75, "height": 1.0, "score": 0.76},
            ],
            "title_safe_area": {"x": 0.08, "y": 0.08, "width": 0.84, "height": 0.84},
        },
        "upscale": {
            "policy": "only_if_crop_below_target",
            "target_long_edge": 2048,
            "max_scale": 2.0,
        },
        "safety": {
            "preserve_identity": True,
            "preserve_text": True,
            "preserve_logo": True,
            "preserve_product_color": True,
            "no_generative_pixels": True,
        },
    }


def validate_recipe(recipe: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(recipe, Mapping):
        raise RecipeValidationError("Recipe must be a JSON object.")

    unknown_keys = sorted(set(recipe.keys()) - ALLOWED_TOP_LEVEL_KEYS)
    if unknown_keys:
        raise RecipeValidationError(f"Unsupported recipe fields: {', '.join(unknown_keys)}")

    validated = deepcopy(dict(recipe))
    if validated.get("schema_version") != SCHEMA_VERSION:
        raise RecipeValidationError(f"Unsupported schema_version: {validated.get('schema_version')}")

    style = str(validated.get("style", ""))
    if style not in STYLE_SCENES:
        raise RecipeValidationError(f"Unsupported style: {style}")
    variant = str(validated.get("variant", ""))
    if variant not in VARIANT_LABELS:
        raise RecipeValidationError(f"Unsupported variant: {variant}")

    validated["global"] = _validate_numeric_section("global", validated.get("global"), GLOBAL_RANGES)
    validated["local"] = _validate_numeric_section("local", validated.get("local"), LOCAL_RANGES)
    validated["composition"] = _validate_composition(validated.get("composition"))
    validated["upscale"] = _validate_upscale(validated.get("upscale"))
    validated["safety"] = _validate_safety(validated.get("safety"))
    return validated


def run_edit(
    input_path: Path,
    output_dir: Path,
    style: str,
    instruction: str,
    return_variants: int = 2,
    recipe_mode: str = "fixture",
    runtime_recipe_endpoint: str | None = None,
    runtime_timeout: float = 10.0,
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if style not in STYLE_SCENES:
        raise ValueError(f"Unsupported style: {style}")
    if recipe_mode not in {"fixture", "runtime_vision"}:
        raise ValueError(f"Unsupported recipe_mode: {recipe_mode}")
    if recipe_mode == "runtime_vision" and not runtime_recipe_endpoint:
        raise RecipeValidationError("runtime_recipe_endpoint is required for runtime_vision mode.")
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(input_path).convert("RGB")
    source_bytes = input_path.read_bytes()

    variant_ids = ["variant_clean_pro", "variant_social_pop"][: max(1, min(int(return_variants), 2))]
    rendered_variants: list[dict[str, Any]] = []
    difference_scores: dict[str, float] = {}
    selected_recipe: dict[str, Any] | None = None
    selected_recipe_model = "fixture"
    selected_upscale: dict[str, Any] | None = None

    for variant_id in variant_ids:
        if recipe_mode == "runtime_vision":
            runtime_recipe = build_runtime_vision_recipe(
                input_path=input_path,
                source_bytes=source_bytes,
                style=style,
                instruction=instruction,
                variant_id=variant_id,
                endpoint=str(runtime_recipe_endpoint),
                timeout=runtime_timeout,
            )
            recipe = validate_recipe(runtime_recipe["recipe"])
            recipe_model = str(runtime_recipe.get("model") or "runtime_configured_multimodal")
        else:
            recipe = validate_recipe(build_fixture_recipe(style, variant_id=variant_id))
            recipe_model = "fixture"
        selected_recipe = recipe if selected_recipe is None else selected_recipe
        selected_recipe_model = recipe_model if selected_recipe is recipe else selected_recipe_model
        rendered = render_image(source, recipe)
        rendered, upscale_metadata = apply_upscale_policy(rendered, recipe["upscale"])
        selected_upscale = upscale_metadata if selected_upscale is None else selected_upscale
        filename = "master.jpg" if variant_id == "variant_clean_pro" else "social.jpg"
        output_path = output_dir / filename
        rendered.save(output_path, format="JPEG", quality=92, optimize=True, subsampling=0)
        score_key = "master_difference_score" if variant_id == "variant_clean_pro" else "social_difference_score"
        difference_scores[score_key] = difference_score(source, rendered)
        rendered_variants.append(
            {
                "id": variant_id,
                "label": VARIANT_LABELS[variant_id],
                "path": str(output_path),
                "mime_type": "image/jpeg",
                "recommended_for": "save" if variant_id == "variant_clean_pro" else "share",
                "explanation": recipe_summary(style, variant_id),
            }
        )

    selected_recipe = selected_recipe or validate_recipe(build_fixture_recipe(style, "variant_clean_pro"))
    selected_upscale = selected_upscale or build_upscale_metadata(selected_recipe["upscale"], (0, 0), (0, 0), 1.0, False)
    if "social_difference_score" not in difference_scores:
        difference_scores["social_difference_score"] = difference_scores["master_difference_score"]

    result = {
        "status": "completed",
        "provider": PROVIDER,
        "renderer": RENDERER,
        "recipe_mode": recipe_mode,
        "recipe_model": selected_recipe_model,
        "schema_version": SCHEMA_VERSION,
        "style": style,
        "instruction": instruction,
        "variants": rendered_variants,
        "composition": selected_recipe["composition"],
        "upscale": selected_upscale,
        "qa": {
            **difference_scores,
            "source_size_bytes": len(source_bytes),
            "variant_count": len(rendered_variants),
        },
        "safety": selected_recipe["safety"],
        "recipe_summary": recipe_summary(style, "variant_clean_pro"),
        "share_caption": share_caption(style),
        "explanation": recipe_summary(style, "variant_clean_pro"),
    }

    (output_dir / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def build_runtime_vision_recipe(
    input_path: Path,
    source_bytes: bytes,
    style: str,
    instruction: str,
    variant_id: str,
    endpoint: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    payload = {
        "schema_version": "photo_edit_recipe_request.v1",
        "provider": PROVIDER,
        "renderer": RENDERER,
        "style": style,
        "scene": STYLE_SCENES[style],
        "variant_id": variant_id,
        "variant_label": VARIANT_LABELS[variant_id],
        "instruction": instruction,
        "source_mime_type": _guess_mime_type(input_path),
        "source_size_bytes": len(source_bytes),
        "source_image_base64": base64.b64encode(source_bytes).decode("ascii"),
        "supported_crop_aspects": ["original", "4:5", "1:1", "16:9"],
        "return_recipe_schema": SCHEMA_VERSION,
        "scene_profile": build_scene_profile(style),
        "safety_contract": {key: True for key in REQUIRED_SAFETY_FLAGS},
    }
    response = _post_json(endpoint, payload, timeout=timeout)
    if "recipe" in response:
        recipe = response["recipe"]
    else:
        recipe = response
    if not isinstance(recipe, Mapping):
        raise RecipeValidationError("runtime_vision response must contain a recipe object.")
    model = response.get("model", "runtime_configured_multimodal") if isinstance(response, Mapping) else "runtime_configured_multimodal"
    return {"recipe": recipe, "model": model}


def build_scene_profile(style: str) -> dict[str, Any]:
    if style not in STYLE_SCENES:
        raise ValueError(f"Unsupported style: {style}")
    return {
        "style": style,
        "scene": STYLE_SCENES[style],
        "goal": STYLE_GOALS[style],
        "default_recipe": deepcopy(STYLE_DEFAULTS[style]),
        "supported_variants": [
            {"id": variant_id, "label": label}
            for variant_id, label in VARIANT_LABELS.items()
        ],
        "safety_flags": {key: True for key in REQUIRED_SAFETY_FLAGS},
    }


def _post_json(endpoint: str, payload: Mapping[str, Any], timeout: float) -> Mapping[str, Any]:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise RecipeValidationError(f"runtime_vision endpoint returned HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise RecipeValidationError(f"runtime_vision endpoint is unavailable: {error.reason}") from error
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecipeValidationError("runtime_vision endpoint returned invalid JSON.") from error
    if not isinstance(decoded, Mapping):
        raise RecipeValidationError("runtime_vision endpoint must return a JSON object.")
    return decoded


def _guess_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "image/jpeg"


def render_image(source: Image.Image, recipe: Mapping[str, Any]) -> Image.Image:
    image = _crop_image(source, recipe["composition"]["crop"])
    global_edits = recipe["global"]
    local_edits = recipe["local"]

    image = _apply_temperature_and_tint(image, global_edits["temperature"], global_edits["tint"])
    image = ImageEnhance.Brightness(image).enhance(1.0 + global_edits["exposure"] * 0.55)
    image = ImageEnhance.Contrast(image).enhance(1.0 + global_edits["contrast"] * 0.85)
    image = ImageEnhance.Color(image).enhance(
        max(0.05, 1.0 + global_edits["saturation"] + global_edits["vibrance"] * 0.55)
    )
    image = _apply_shadow_lift(image, global_edits["shadows"])
    image = _apply_highlight_recovery(image, global_edits["highlights"])
    image = _apply_local_polish(image, local_edits)
    image = ImageEnhance.Sharpness(image).enhance(1.0 + local_edits["sharpen"] * 2.0 + global_edits["clarity"])
    return ImageOps.autocontrast(image, cutoff=0.5)


def apply_upscale_policy(image: Image.Image, upscale: Mapping[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    input_size = image.size
    policy = str(upscale.get("policy", "none"))
    target_long_edge = int(upscale.get("target_long_edge", max(input_size) if input_size else 0))
    max_scale = float(upscale.get("max_scale", 1.0))
    scale = 1.0
    upscaled = False

    if policy == "only_if_crop_below_target" and input_size and max(input_size) < target_long_edge:
        scale = min(max_scale, target_long_edge / max(input_size))
        if scale > 1.0:
            output_size = (
                max(1, int(round(input_size[0] * scale))),
                max(1, int(round(input_size[1] * scale))),
            )
            image = image.resize(output_size, Image.Resampling.LANCZOS)
            upscaled = output_size != input_size

    metadata = build_upscale_metadata(upscale, input_size, image.size, scale if upscaled else 1.0, upscaled)
    return image, metadata


def build_upscale_metadata(
    upscale: Mapping[str, Any],
    input_size: tuple[int, int],
    output_size: tuple[int, int],
    scale: float,
    upscaled: bool,
) -> dict[str, Any]:
    return {
        **dict(upscale),
        "upscaled": upscaled,
        "scale": round(scale, 4),
        "input_size": [int(input_size[0]), int(input_size[1])],
        "output_size": [int(output_size[0]), int(output_size[1])],
    }


def difference_score(source: Image.Image, rendered: Image.Image) -> float:
    comparable_source = source.convert("RGB").resize(rendered.size, Image.Resampling.BICUBIC)
    diff = ImageChops.difference(comparable_source, rendered.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return round(sum(stat.mean) / (255.0 * 3.0), 4)


def recipe_summary(style: str, variant_id: str) -> str:
    if variant_id == "variant_social_pop":
        return "Stronger crop, color, contrast, and subject separation for sharing."
    summaries = {
        "natural_enhance": "Balanced exposure, warmer color, cleaner contrast, and subtle subject separation.",
        "portrait_polish": "Face-safe lighting, warmer skin tone, restrained smoothing, and identity preservation.",
        "product_shot": "Cleaner whites, sharper edges, and restrained commercial lighting.",
        "social_cover": "Platform-ready crop with stronger color and subject separation.",
    }
    return summaries.get(style, "Local recipe rendered a professional photo variant.")


def share_caption(style: str) -> str:
    captions = {
        "natural_enhance": "Made into a Master Shot by my local photo agent.",
        "portrait_polish": "Polished locally with identity-safe edits.",
        "product_shot": "Clean product shot, rendered by my local agent.",
        "social_cover": "Share-ready crop and color, rendered locally.",
    }
    return captions.get(style, "Polished by my local photo agent.")


def _boost_for_social(global_edits: dict[str, float], local_edits: dict[str, float]) -> None:
    global_edits["exposure"] += 0.04
    global_edits["contrast"] += 0.16
    global_edits["vibrance"] += 0.14
    global_edits["saturation"] += 0.08
    global_edits["clarity"] += 0.08
    local_edits["subject_boost"] += 0.12
    local_edits["background_falloff"] += 0.08
    local_edits["sharpen"] += 0.08
    local_edits["vignette"] += 0.08


def _validate_numeric_section(
    name: str,
    value: Any,
    ranges: Mapping[str, tuple[float, float]],
) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise RecipeValidationError(f"{name} must be an object.")
    result: dict[str, float] = {}
    for key, value_range in ranges.items():
        if key not in value:
            raise RecipeValidationError(f"{name}.{key} is required.")
        result[key] = _clamp_number(value[key], value_range[0], value_range[1], f"{name}.{key}")
    unsupported = sorted(set(value.keys()) - set(ranges.keys()))
    if unsupported:
        raise RecipeValidationError(f"Unsupported {name} fields: {', '.join(unsupported)}")
    return result


def _validate_composition(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RecipeValidationError("composition must be an object.")
    selected = str(value.get("selected_aspect_ratio", ""))
    if selected not in {"original", "4:5", "1:1", "16:9"}:
        raise RecipeValidationError(f"Unsupported selected_aspect_ratio: {selected}")
    crop = _validate_crop(value.get("crop"), "composition.crop")
    candidates = value.get("crop_candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise RecipeValidationError("composition.crop_candidates must be a non-empty list.")
    validated_candidates = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            raise RecipeValidationError(f"composition.crop_candidates[{index}] must be an object.")
        aspect = str(candidate.get("aspect_ratio", ""))
        validated_candidate = {
            "aspect_ratio": aspect,
            **_validate_crop(candidate, f"composition.crop_candidates[{index}]"),
            "score": _clamp_number(candidate.get("score", 0.0), 0.0, 1.0, f"composition.crop_candidates[{index}].score"),
        }
        if aspect not in {"original", "4:5", "1:1", "16:9"}:
            raise RecipeValidationError(f"Unsupported crop candidate aspect_ratio: {aspect}")
        validated_candidates.append(validated_candidate)

    title_safe_area = value.get("title_safe_area", {"x": 0.08, "y": 0.08, "width": 0.84, "height": 0.84})
    return {
        "selected_aspect_ratio": selected,
        "crop": crop,
        "crop_candidates": validated_candidates,
        "title_safe_area": _validate_crop(title_safe_area, "composition.title_safe_area"),
    }


def _validate_crop(value: Any, name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise RecipeValidationError(f"{name} must be an object.")
    width = _clamp_number(value.get("width"), 0.05, 1.0, f"{name}.width")
    height = _clamp_number(value.get("height"), 0.05, 1.0, f"{name}.height")
    x = _clamp_number(value.get("x"), 0.0, 1.0 - width, f"{name}.x")
    y = _clamp_number(value.get("y"), 0.0, 1.0 - height, f"{name}.y")
    return {
        "x": round(x, 4),
        "y": round(y, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def _validate_upscale(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RecipeValidationError("upscale must be an object.")
    policy = str(value.get("policy", ""))
    if policy not in {"none", "only_if_crop_below_target"}:
        raise RecipeValidationError(f"Unsupported upscale policy: {policy}")
    return {
        "policy": policy,
        "target_long_edge": int(_clamp_number(value.get("target_long_edge"), 512, 4096, "upscale.target_long_edge")),
        "max_scale": _clamp_number(value.get("max_scale"), 1.0, 3.0, "upscale.max_scale"),
    }


def _validate_safety(value: Any) -> dict[str, bool]:
    if not isinstance(value, Mapping):
        raise RecipeValidationError("safety must be an object.")
    result: dict[str, bool] = {}
    for key in REQUIRED_SAFETY_FLAGS:
        if key not in value:
            raise RecipeValidationError(f"safety.{key} is required.")
        if value[key] is not True:
            raise RecipeValidationError(f"safety.{key} must be true.")
        result[key] = True
    unsupported = sorted(set(value.keys()) - set(REQUIRED_SAFETY_FLAGS))
    if unsupported:
        raise RecipeValidationError(f"Unsupported safety fields: {', '.join(unsupported)}")
    return result


def _clamp_number(value: Any, minimum: float, maximum: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RecipeValidationError(f"{name} must be numeric.")
    return max(minimum, min(maximum, float(value)))


def _crop_image(image: Image.Image, crop: Mapping[str, float]) -> Image.Image:
    width, height = image.size
    left = int(round(crop["x"] * width))
    top = int(round(crop["y"] * height))
    right = int(round((crop["x"] + crop["width"]) * width))
    bottom = int(round((crop["y"] + crop["height"]) * height))
    right = max(left + 1, min(width, right))
    bottom = max(top + 1, min(height, bottom))
    return image.crop((left, top, right, bottom))


def _apply_temperature_and_tint(image: Image.Image, temperature: float, tint: float) -> Image.Image:
    red, green, blue = image.split()
    temp_scale = temperature / 1500.0
    tint_scale = tint
    red = red.point(lambda pixel: _byte(pixel * (1.0 + max(0.0, temp_scale) * 0.16)))
    blue = blue.point(lambda pixel: _byte(pixel * (1.0 + min(0.0, temp_scale) * -0.16)))
    if temp_scale > 0:
        blue = blue.point(lambda pixel: _byte(pixel * (1.0 - temp_scale * 0.10)))
    elif temp_scale < 0:
        red = red.point(lambda pixel: _byte(pixel * (1.0 + temp_scale * 0.10)))
    green = green.point(lambda pixel: _byte(pixel * (1.0 + tint_scale * 0.05)))
    return Image.merge("RGB", (red, green, blue))


def _apply_shadow_lift(image: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return image
    lifted = ImageEnhance.Brightness(image).enhance(1.0 + amount * 0.22)
    grayscale = ImageOps.grayscale(image)
    mask = ImageOps.invert(grayscale).point(lambda pixel: _byte(pixel * amount))
    return Image.composite(lifted, image, mask)


def _apply_highlight_recovery(image: Image.Image, amount: float) -> Image.Image:
    if amount >= 0:
        return image
    recovered = ImageEnhance.Brightness(image).enhance(1.0 + amount * 0.18)
    grayscale = ImageOps.grayscale(image)
    mask = grayscale.point(lambda pixel: _byte(pixel * abs(amount)))
    return Image.composite(recovered, image, mask)


def _apply_local_polish(image: Image.Image, local_edits: Mapping[str, float]) -> Image.Image:
    denoise = local_edits["denoise"]
    if denoise > 0:
        image = Image.blend(image, image.filter(ImageFilter.MedianFilter(size=3)), min(0.45, denoise))

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    width, height = image.size
    inset_x = int(width * 0.18)
    inset_y = int(height * 0.14)
    draw.ellipse((inset_x, inset_y, width - inset_x, height - inset_y), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(width, height) * 0.08))

    boost = local_edits["subject_boost"]
    if boost > 0:
        boosted = ImageEnhance.Brightness(image).enhance(1.0 + boost * 0.22)
        boosted = ImageEnhance.Contrast(boosted).enhance(1.0 + boost * 0.14)
        image = Image.composite(boosted, image, mask)

    falloff = local_edits["background_falloff"]
    if falloff > 0:
        darker = ImageEnhance.Brightness(image).enhance(1.0 - falloff * 0.18)
        image = Image.composite(image, darker, mask)

    soften = local_edits["background_soften"] + local_edits["skin_smoothing"] * 0.4
    if soften > 0:
        blurred = image.filter(ImageFilter.GaussianBlur(radius=soften * 1.8))
        image = Image.composite(image, blurred, mask)

    vignette = local_edits["vignette"]
    if vignette > 0:
        image = _apply_vignette(image, vignette)
    return image


def _apply_vignette(image: Image.Image, amount: float) -> Image.Image:
    width, height = image.size
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        (
            -int(width * 0.18),
            -int(height * 0.10),
            int(width * 1.18),
            int(height * 1.10),
        ),
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(width, height) * 0.18))
    darker = ImageEnhance.Brightness(image).enhance(1.0 - amount * 0.28)
    return Image.composite(image, darker, mask)


def _byte(value: float) -> int:
    return int(max(0, min(255, round(value))))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Agent Pocket local recipe renderer.")
    parser.add_argument("--input", required=True, type=Path, help="Input image path.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for edited variants.")
    parser.add_argument("--style", required=True, choices=sorted(STYLE_SCENES), help="Kaka scene pack.")
    parser.add_argument("--instruction", required=True, help="User or default edit instruction.")
    parser.add_argument("--return-variants", type=int, default=2, help="Number of variants to return, max 2.")
    parser.add_argument(
        "--recipe-mode",
        default="fixture",
        choices=["fixture", "runtime_vision"],
        help="Recipe source: deterministic fixture or compatible local runtime vision endpoint.",
    )
    parser.add_argument(
        "--runtime-recipe-endpoint",
        default=None,
        help="Local runtime endpoint that returns strict PhotoEditRecipe JSON for runtime_vision mode.",
    )
    parser.add_argument("--runtime-timeout", type=float, default=10.0, help="Runtime recipe request timeout in seconds.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_edit(
        input_path=args.input,
        output_dir=args.output_dir,
        style=args.style,
        instruction=args.instruction,
        return_variants=args.return_variants,
        recipe_mode=args.recipe_mode,
        runtime_recipe_endpoint=args.runtime_recipe_endpoint,
        runtime_timeout=args.runtime_timeout,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
