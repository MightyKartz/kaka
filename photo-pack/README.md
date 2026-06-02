# Agent Pocket Photo Pack

This Photo Pack runs inside a user-owned compatible agent runtime such as Hermes, OpenClaw, or a Mobile Bridge sidecar. Agent Pocket uploads photos through the Mobile Bridge; this pack turns the selected scene pack into local, deterministic Master Shot variants and returns edited assets to the phone.

## Phase 1 Direction

Preferred Phase 1 provider: `recipe_local`.

The iPhone is only a client. It uploads the source photo, scene pack, and instruction to the user's runtime. That runtime uses whichever multimodal vision model the user's agent is configured to call, then produces a strict `PhotoEditRecipe`. The Mac-side renderer then applies bounded local edits through Core Image, Pillow, OpenCV, ImageMagick, libvips, or another deterministic image-processing backend.

The source photo is not converted into a pixel JSON document. JSON is only the edit recipe: exposure, white balance, contrast, highlights, shadows, vibrance, sharpening, denoise, crop/reframe, subject emphasis, optional upscale policy, preservation flags, and safe scene-pack metadata.

## Phase 1 Adapters

- `adapters/recipe_local.py`: implemented preferred local renderer adapter. It supports deterministic `fixture` recipes for tests and `runtime_vision` recipes from a compatible local runtime endpoint, sends Kaka scene-profile defaults, validates/clamps strict `PhotoEditRecipe` JSON, renders `Master` and `Social`, and records `manifest.json`.
- `adapters/script.py`: deterministic local smoke-test adapter. It copies the input image into the output directory and writes `manifest.json`.
- `adapters/openai_image.py`: legacy optional OpenAI Images Edits adapter. Keep it for later generative editing experiments, not as the first shippable path.
- ComfyUI adapter: later local/self-hosted workflow path after `recipe_local` is proven.

## Install In A Compatible Runtime

1. Copy `photo-pack/` into the profiles, packs, plugins, or skills directory used by your runtime.
2. Register `photo-agent/SOUL.md` and `skills/photo-edit/SKILL.md` as the `photo-agent` profile and `photo-edit` skill.
3. Enable the Mobile Bridge endpoints from `docs/mobile-bridge-api.md`.
4. Package startup through a visible runtime control such as **Kaka Mobile Bridge**. A normal user should not need to paste a long bridge command.
5. Use `runtime-kit/` as the current development scaffold for Hermes/OpenClaw packaging. The public plugin/skill should expose **Start**, **Show QR**, **Stop**, optional **Start with runtime**, and mobile-token revocation.

Installing a skill/plugin must not automatically start a bridge or advertise Bonjour. LAN exposure, Bonjour, and login/startup behavior must be explicit opt-ins.

6. Confirm capabilities advertise `recipe_local`, two variants, crop support, and the four Kaka scene packs:

   ```json
   {
     "tasks": {
       "photo_edit": {
         "provider": "recipe_local",
         "renderer": "local_parametric",
         "return_variants": 2,
         "variant_labels": ["Master", "Social"],
         "variant_ids": ["variant_clean_pro", "variant_social_pop"],
         "styles": ["natural_enhance", "portrait_polish", "product_shot", "social_cover"],
         "crop_aspects": ["original", "4:5", "1:1"],
         "supports_upscale_policy": true
       }
     }
   }
   ```

## Local Recipe Adapter

Current fixture/local renderer command:

```bash
python3 photo-pack/adapters/recipe_local.py \
  --input /path/to/input.jpg \
  --output-dir /tmp/agent-pocket-photo-recipe \
  --style natural_enhance \
  --instruction "Keep it realistic but make the professional edit obvious." \
  --return-variants 2
```

Runtime-vision recipe command, for a compatible local runtime or sidecar that already owns model credentials:

```bash
python3 photo-pack/adapters/recipe_local.py \
  --input /path/to/input.jpg \
  --output-dir /tmp/agent-pocket-photo-recipe \
  --style natural_enhance \
  --instruction "Keep it realistic but make the professional edit obvious." \
  --return-variants 2 \
  --recipe-mode runtime_vision \
  --runtime-recipe-endpoint http://127.0.0.1:8791/mobile/v1/recipes/photo-edit
```

The adapter posts source image bytes as base64 plus style, scene, variant, instruction, supported crop aspects, a `scene_profile` object, and safety requirements. `scene_profile` contains the Kaka scene goal, default global/local recipe values, supported variants, and required safety flags. The runtime endpoint must return a strict `PhotoEditRecipe` object or `{ "recipe": { ... }, "model": "<runtime-model-name>" }`. The adapter validates the returned recipe before rendering and never sends provider keys from the iPhone.

Expected manifest shape:

```json
{
  "status": "completed",
  "provider": "recipe_local",
  "renderer": "local_parametric",
  "style": "natural_enhance",
  "recipe_id": "recipe_01JPHOTO...",
  "variants": [
    {
      "id": "variant_clean_pro",
      "label": "Master",
      "path": "/runtime/tasks/task_123/master.jpg",
      "recommended_for": "save"
    },
    {
      "id": "variant_social_pop",
      "label": "Social",
      "path": "/runtime/tasks/task_123/social.jpg",
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
  "recipe_summary": "Balanced exposure, warmer skin tone, added subject separation, protected facial identity.",
  "share_caption": "Polished with my local photo agent."
}
```

Minimum recipe fields:

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

The adapter must reject or clamp out-of-range values, unknown operations, arbitrary code, provider URLs, and any recipe that requests generative edits.

## Style Targets

- `natural_enhance`: balanced exposure, white balance, contrast, shadows, highlights, vibrance, mild clarity, and subtle crop.
- `portrait_polish`: face-safe lighting, low skin smoothing, eye/face clarity, background separation, and identity preservation.
- `product_shot`: cleaner whites, product edge sharpness, controlled shadows, neutral color, and text/logo preservation.
- `social_cover`: stronger crop, color pop, contrast, subject separation, and title-safe composition.

Always return:

- `Master`: realistic professional result for saving.
- `Social`: stronger crop/contrast/color/subject separation for sharing.

The renderer should reject a no-op result. A first QA threshold can be simple: edited output must differ from source bytes, have valid dimensions, include crop metadata, and pass a basic image-difference score while preserving subject/text/identity.

## Script Adapter Smoke Test

```bash
python3 photo-pack/adapters/script.py \
  --input /path/to/input.jpg \
  --output-dir /tmp/agent-pocket-photo \
  --style natural_enhance \
  --instruction "Keep it realistic."
```

The adapter prints JSON to stdout and writes a manifest:

```json
{
  "status": "completed",
  "style": "natural_enhance",
  "variants": [
    {
      "id": "variant_natural_enhance",
      "label": "Natural Enhance",
      "path": "/tmp/agent-pocket-photo/natural_enhance.jpg"
    }
  ]
}
```

## Mock Bridge Provider QA

The local mock Mobile Bridge can route `/mobile/v1/tasks/photo-edit` through `recipe_local`:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight \
  --photo-provider recipe_local \
  --photo-pack-root photo-pack \
  --hermes-profile dev-lead \
  --receipt-file docs/qa-receipts/recipe-provider-preflight-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-local-recipe-smoke \
  --host 127.0.0.1 \
  --port 8769 \
  --receipt-file docs/qa-receipts/simulator-local-recipe-photo-flow.json \
  --screenshot-file /tmp/agent-pocket-simulator-local-recipe.png

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan \
  --host <mac-lan-ip> \
  --device-id <coredevice-id> \
  --photo-provider recipe_local \
  --hermes-profile dev-lead \
  --receipt-file docs/qa-receipts/local-recipe-photo-flow.json
```

`--hermes-profile` is the current Hermes/mock helper flag. OpenClaw or another compatible runtime should provide an equivalent runtime/profile selection path while keeping the Mobile Bridge API stable.

The mock bridge now preserves recipe metadata from `manifest.json` through provider variants, task status, and `/mobile/v1/qa/status`. Local-recipe receipts are expected to prove `provider: recipe_local`, two variants, renderer `local_parametric`, crop metadata, Master/Social difference metrics, downloaded assets, and share-ready summary/caption metadata.

Run `iphone-credential-boundary --receipt-file docs/qa-receipts/iphone-credential-boundary-latest.json` to prove the iPhone client keeps provider/model credentials out of the app. The phone should only receive the runtime endpoint, session token, task state, download URLs, edited image assets, recipe summary, and share caption.

## Legacy Optional OpenAI Images Adapter

Configure the legacy provider key only inside the user-owned runtime or bridge host:

```bash
export OPENAI_API_KEY="<server-side-api-key>"
export OPENAI_IMAGE_MODEL="gpt-image-1.5"
```

Run:

```bash
python3 photo-pack/adapters/openai_image.py \
  --input /path/to/input.jpg \
  --output-dir /tmp/agent-pocket-photo-openai \
  --style portrait_polish \
  --instruction "Keep the person recognizable." \
  --return-variants 2
```

Use this adapter only when intentionally testing a later generative path. Missing `OPENAI_API_KEY` does not block Local Recipe Phase 1.
