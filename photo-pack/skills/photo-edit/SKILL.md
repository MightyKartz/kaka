# Photo Edit Skill

Use this skill when Agent Pocket starts `/mobile/v1/tasks/photo-edit` for the Master Shot flow.

## Inputs

- `profile_id`: expected `photo-agent`.
- `asset_id`: uploaded source asset.
- `style`: one of the Kaka scene packs: `natural_enhance`, `portrait_polish`, `product_shot`, `social_cover`.
- `instruction`: user/default editing instruction.
- `return_variants`: Phase 1 default is `2`.
- `crop_aspects`: optional target aspects such as `original`, `4:5`, and `1:1`.

## Phase 1 Workflow

1. Load the source asset from Mobile Bridge asset storage.
2. Validate style, media type, size, and requested variant count.
3. Ask the runtime-configured multimodal vision model to analyze the photo and return a strict `PhotoEditRecipe` JSON object with composition, edit, optional upscale, and safety sections.
4. Validate and clamp the recipe against the local schema.
5. Generate or validate crop candidates for master-shot composition.
6. Render variants locally with deterministic image-processing operations.
7. Store returned variants as bridge assets.
8. Return task status with variant labels, download URLs, crop metadata, recipe summary, renderer metadata, QA metrics, and a share caption.

The model should choose bounded edit parameters only. It must not request arbitrary code, provider URLs, generative pixels, face replacement, text replacement, product redesign, or background replacement in Phase 1.

## Provider Adapter Contract

Adapters accept:

```json
{
  "input_path": "/runtime/assets/source.jpg",
  "output_dir": "/runtime/tasks/task_123",
  "style": "natural_enhance",
  "instruction": "Keep it realistic but make the professional edit obvious.",
  "return_variants": 2,
  "crop_aspects": ["original", "4:5", "1:1"],
  "recipe_mode": "fixture | runtime_vision",
  "runtime_recipe_endpoint": "http://127.0.0.1:8791/mobile/v1/recipes/photo-edit"
}
```

Use `fixture` for deterministic QA. Use `runtime_vision` only inside a compatible local runtime or sidecar that owns model credentials. The adapter sends photo context, Kaka `scene_profile` defaults, and safety requirements to the local endpoint, receives strict `PhotoEditRecipe` JSON, validates/clamps it, and then renders locally. Do not pass model-provider keys, provider URLs, or cloud image-edit requests through the iPhone client.

The runtime-vision request includes `scene_profile`:

```json
{
  "style": "natural_enhance",
  "scene": "natural",
  "goal": "realistic exposure, white balance, shadow/highlight recovery, mild clarity",
  "default_recipe": {
    "global": {"exposure": 0.14, "contrast": 0.16},
    "local": {"subject_boost": 0.16, "sharpen": 0.16}
  },
  "supported_variants": [
    {"id": "variant_clean_pro", "label": "Master"},
    {"id": "variant_social_pop", "label": "Social"}
  ],
  "safety_flags": {
    "preserve_identity": true,
    "preserve_text": true,
    "preserve_logo": true,
    "preserve_product_color": true,
    "no_generative_pixels": true
  }
}
```

Adapters return:

```json
{
  "status": "completed",
  "provider": "recipe_local",
  "renderer": "local_parametric",
  "variants": [
    {
      "id": "variant_clean_pro",
      "label": "Master",
      "path": "/runtime/tasks/task_123/clean_pro.jpg",
      "recommended_for": "save"
    },
    {
      "id": "variant_social_pop",
      "label": "Social",
      "path": "/runtime/tasks/task_123/social_pop.jpg",
      "recommended_for": "share"
    }
  ],
  "composition": {
    "selected_aspect_ratio": "4:5",
    "crop": {"x": 0.08, "y": 0.04, "width": 0.84, "height": 0.92}
  },
  "qa": {
    "master_difference_score": 0.18,
    "social_difference_score": 0.26
  },
  "upscale": {
    "policy": "only_if_crop_below_target",
    "target_long_edge": 2048,
    "max_scale": 2.0,
    "upscaled": true,
    "scale": 2.0,
    "input_size": [960, 1200],
    "output_size": [1920, 2400]
  },
  "recipe_summary": "Balanced exposure, warmer skin tone, added subject separation, protected identity.",
  "share_caption": "Polished with my local photo agent."
}
```

## Recipe Contract

Minimum recipe shape:

```json
{
  "schema_version": "photo_edit_recipe.v1",
  "style": "natural_enhance",
  "scene": "portrait",
  "global": {
    "exposure": 0.18,
    "contrast": 0.16,
    "highlights": -0.12,
    "shadows": 0.18,
    "temperature": 250,
    "vibrance": 0.18,
    "clarity": 0.12
  },
  "local": {
    "subject_boost": 0.18,
    "skin_smoothing": 0.08,
    "background_soften": 0.10,
    "sharpen": 0.14,
    "denoise": 0.08
  },
  "composition": {
    "selected_aspect_ratio": "4:5",
    "crop": {
      "x": 0.08,
      "y": 0.04,
      "width": 0.84,
      "height": 0.92
    },
    "crop_candidates": [
      {"aspect_ratio": "original", "x": 0, "y": 0, "width": 1, "height": 1, "score": 0.72},
      {"aspect_ratio": "4:5", "x": 0.08, "y": 0.04, "width": 0.84, "height": 0.92, "score": 0.88}
    ]
  },
  "upscale": {
    "policy": "only_if_crop_below_target",
    "target_long_edge": 2048,
    "max_scale": 2.0
  },
  "safety": {
    "preserve_identity": true,
    "preserve_text": true,
    "preserve_logo": true,
    "preserve_product_color": true,
    "no_generative_pixels": true
  }
}
```

## Style Targets

- `natural_enhance`: realistic exposure, color, clarity, and subtle composition improvement.
- `portrait_polish`: skin-safe retouching, face-aware lighting, identity preservation, and background separation.
- `product_shot`: cleaner whites, sharper subject, product detail preservation, and commercial lighting.
- `social_cover`: stronger crop, color pop, contrast, subject separation, and platform-ready look.

Always return `Master` and `Social` display labels. Internal IDs may stay `variant_clean_pro` and `variant_social_pop` so older clients can remain compatible.

## Failure Handling

- Missing asset: return `not_found`.
- Unsupported style: return `photo_edit_unavailable` or `unsupported_style`.
- Invalid recipe: return `task_failed` with recoverable text and log schema details on the runtime side only.
- Invalid crop or unsafe upscale request: return `task_failed` before rendering.
- Renderer failure: return `task_failed` with recoverable text and keep source asset unchanged.
- Oversized image: return `upload_too_large` before provider execution.
