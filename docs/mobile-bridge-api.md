# Agent Pocket Mobile Bridge API

## Overview

The Mobile Bridge is the stable HTTPS boundary between Agent Pocket and a user-owned compatible agent runtime, such as Hermes, OpenClaw, or a sidecar that exposes the same contract. The iPhone app is a thin client: it pairs with a runtime, uploads photos, starts Master Shot tasks, watches progress, downloads results, and hands the edited image to the iOS share sheet. The runtime owns model credentials, workflow selection, vision analysis, crop planning, local image rendering, memory, approvals, and tool execution.

Base path: `/mobile/v1`

Clients must tolerate unknown response fields. Servers must preserve backward compatibility for `/mobile/v1` during Phase 1.

## Authentication

Authenticated requests use:

```http
Authorization: Bearer <mobile_token>
```

Rules:

- `/health` may be public but must not expose secrets.
- `/pairing/exchange` accepts a short-lived one-time pairing code instead of a bearer token.
- All asset, task, event, and download endpoints require a bearer token.
- Non-local remote endpoints must use HTTPS.
- Local developer HTTP is allowed only for `localhost`, `127.0.0.1`, `::1`, `.local`, private LAN, Tailscale CGNAT, or explicit LAN developer mode.

## Error Shape

All non-2xx JSON errors use this shape:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "The mobile token is missing or invalid.",
    "recoverable": true
  }
}
```

Common codes:

- `unauthorized`
- `forbidden`
- `not_found`
- `pairing_expired`
- `pairing_already_used`
- `photo_edit_unavailable`
- `unsupported_media_type`
- `upload_too_large`
- `task_failed`
- `runtime_unavailable`

## Health

`GET /mobile/v1/health`

Response:

```json
{
  "ok": true,
  "runtime": "hermes",
  "runtime_version": "2026.5.16",
  "bridge_version": "0.1.0"
}
```

## Local Discovery

Compatible runtimes can advertise local availability with Bonjour service type `_agent-pocket._tcp`.

Recommended TXT keys:

- `display_name`: human-readable runtime name.
- `runtime`: runtime identifier such as `hermes`, `openclaw`, or another compatible value.
- `scheme`: `http` for local development, `https` for trusted local TLS.
- `endpoint`: optional full endpoint URL; if omitted, clients compose `scheme://host:port`.
- `pairing_payload`: optional full QR pairing JSON.
- `pairing_code` and `expires_at`: optional fields clients can use to build a pairing payload when `pairing_payload` is omitted.

Discovery must not mint long-lived credentials by itself. Clients should show discovered runtimes as confirmation cards and exchange a one-time pairing code through `/pairing/exchange` only after the user chooses a runtime.

Development and mock runtimes may also expose `GET /mobile/v1/pairing/dev` without bearer auth. It returns the current local pairing payload so a client can recover when Bonjour TXT records contain a one-time development code that has already been exchanged. Production deployments should prefer short-lived QR or trusted local TLS pairing flows.

Runtime plugins and skills must treat bridge startup as an explicit user action. Installing a Hermes/OpenClaw skill or plugin must not silently bind a LAN port, advertise Bonjour, or create a login item. A runtime may offer **Start with Hermes/OpenClaw** later, but it must be opt-in and reversible.

Recommended runtime-side controls:

- **Start Kaka Mobile Bridge**: starts the local listener for the current session.
- **Show QR**: shows a short-lived pairing QR.
- **Advertise on Local Network**: enables Bonjour only after user approval.
- **Stop Bridge**: shuts down the listener and advertisement.
- **Revoke iPhone**: revokes the mobile token for a paired device.

## Capabilities

`GET /mobile/v1/capabilities`

Response:

```json
{
  "profiles": [
    {
      "id": "photo-agent",
      "display_name": "Photo Agent",
      "capabilities": ["photo_edit"]
    }
  ],
  "tasks": {
    "photo_edit": {
      "max_upload_mb": 30,
      "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
      "styles": ["natural_enhance", "portrait_polish", "product_shot", "social_cover"],
      "provider": "recipe_local",
      "renderer": "local_parametric",
      "variant_labels": ["Master", "Social"],
      "variant_ids": ["variant_clean_pro", "variant_social_pop"],
      "crop_aspects": ["original", "4:5", "1:1"],
      "supports_crop_candidates": true,
      "supports_upscale_policy": true,
      "supports_sse": true,
      "return_variants_max": 3
    }
  },
  "retention": {
    "input_assets_days": 7,
    "output_assets_days": 30,
    "task_history_days": 30
  }
}
```

## Pairing QR Payload

The QR code encodes JSON:

```json
{
  "version": 1,
  "endpoint": "https://macbook-pro.local:8765",
  "runtime": "hermes",
  "display_name": "Kartz MacBook Runtime",
  "pairing_code": "pair_01JPHOTO",
  "expires_at": "2026-05-30T16:30:00Z"
}
```

The app must reject expired payloads and remote non-HTTPS endpoints before exchanging the code.

## Pairing Exchange

`POST /mobile/v1/pairing/exchange`

Request:

```json
{
  "pairing_code": "pair_01JPHOTO",
  "device_name": "Kartz iPhone",
  "device_public_id": "device_01JPOCKET"
}
```

Response:

```json
{
  "endpoint_id": "endpoint_01JHERMES",
  "display_name": "Kartz MacBook Runtime",
  "runtime": "hermes",
  "runtime_version": "2026.5.16",
  "mobile_token": "mobile_secret_value",
  "token_expires_at": null
}
```

Server requirements:

- Pairing codes expire in 60-300 seconds.
- Pairing codes are single-use.
- The returned token is scoped to mobile bridge access.
- The runtime can revoke tokens.

## Asset Upload

`POST /mobile/v1/assets`

Request:

- `multipart/form-data`
- Field `file`: JPEG, HEIC, or PNG image.
- Field `metadata`: JSON string with width, height, local creation time, and EXIF-safe metadata.

Response:

```json
{
  "asset_id": "asset_01JPHOTO9N0QWQNS9YW4Y3",
  "mime_type": "image/jpeg",
  "size_bytes": 4812291,
  "sha256": "f5b8d8c8bfb5a0c92d9f6b7e7a94f80b6f0f3b0d5a9d0f2af81b9b3f4e2c1d0a"
}
```

## Photo Edit Task

`POST /mobile/v1/tasks/photo-edit`

Request:

```json
{
  "profile_id": "photo-agent",
  "asset_id": "asset_01JPHOTO9N0QWQNS9YW4Y3",
  "style": "natural_enhance",
  "instruction": "Keep it realistic. Do not over-smooth skin or change identity.",
  "return_variants": 2,
  "output_intent": "master_shot",
  "crop_aspects": ["original", "4:5", "1:1"],
  "share_targets": ["wechat", "wechat_moments", "xiaohongshu", "x"]
}
```

Response:

```json
{
  "task_id": "task_01JPHOTOA1YJ7TE4KZ5S4",
  "status": "queued",
  "events_url": "/mobile/v1/tasks/task_01JPHOTOA1YJ7TE4KZ5S4/events"
}
```

## Task Status

`GET /mobile/v1/tasks/{task_id}`

Running response:

```json
{
  "task_id": "task_01JPHOTOA1YJ7TE4KZ5S4",
  "status": "running",
  "progress": 0.45,
  "message": "Analyzing lighting and building a local edit recipe."
}
```

Completed response:

```json
{
  "task_id": "task_01JPHOTOA1YJ7TE4KZ5S4",
  "status": "completed",
  "progress": 1.0,
  "message": "Completed.",
  "variants": [
    {
      "id": "variant_clean_pro",
      "label": "Master",
      "asset_id": "asset_01JPHOTORESULT1",
      "download_url": "/mobile/v1/assets/asset_01JPHOTORESULT1/download",
      "recipe_id": "recipe_01JPHOTO",
      "recommended_for": "save"
    },
    {
      "id": "variant_social_pop",
      "label": "Social",
      "asset_id": "asset_01JPHOTORESULT2",
      "download_url": "/mobile/v1/assets/asset_01JPHOTORESULT2/download",
      "recipe_id": "recipe_01JPHOTO_SOCIAL",
      "recommended_for": "share"
    }
  ],
  "explanation": "Reframed the subject, balanced exposure, reduced color cast, protected important details, and generated local recipe variants without changing identity or adding objects.",
  "renderer": "local_parametric",
  "composition": {
    "selected_aspect_ratio": "4:5",
    "crop": {
      "x": 0.08,
      "y": 0.04,
      "width": 0.84,
      "height": 0.92
    }
  },
  "qa": {
    "master_difference_score": 0.18,
    "social_difference_score": 0.31
  },
  "recipe_summary": "Balanced exposure and reframed to 4:5 without changing identity.",
  "share_caption": "用本机智能体做了一版大师感成片。",
  "provider": {
    "name": "recipe_local",
    "model": "runtime_configured_multimodal",
    "renderer": "local_parametric"
  }
}
```

## Local Recipe Schema

Phase 1 uses model-assisted parameter editing instead of generated image editing. The runtime may expose a recipe summary for debugging, but the iPhone should treat the rendered image asset as the source of truth.

The runtime must validate and clamp recipe values before rendering. The model may suggest parameters, but it must not write executable code or arbitrary filter graphs.

Compatible runtimes should expose the local recipe path through `GET /mobile/v1/capabilities`, not through client-side provider configuration. In Phase 1, the iPhone treats `provider`, `renderer`, `variant_labels`, `variant_ids`, `crop_aspects`, `supports_crop_candidates`, and `supports_upscale_policy` as runtime capabilities. The mock bridge advertises these fields for `recipe_local`; Hermes, OpenClaw, or another sidecar should serve the same shape when they implement the contract.

Inside the runtime, `recipe_local` can run in `fixture` mode for deterministic QA or `runtime_vision` mode for model-assisted recipes. In `runtime_vision` mode the adapter posts the source image as base64 plus style, scene, variant, instruction, supported crop aspects, Kaka `scene_profile` defaults, and safety requirements to a local runtime recipe endpoint. That endpoint may call whichever multimodal model the runtime is configured to use, then must return strict `PhotoEditRecipe` JSON. The adapter validates the JSON before rendering. This endpoint is runtime-side only; it is not called by the iPhone and it must not require provider keys from the iPhone client.

Example:

```json
{
  "schema_version": 1,
  "style": "product_shot",
  "variant": "master",
  "scene": {
    "category": "object",
    "lighting": "dim indoor",
    "main_subject": "product on desk"
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
      {
        "aspect_ratio": "original",
        "x": 0.0,
        "y": 0.0,
        "width": 1.0,
        "height": 1.0,
        "score": 0.72
      },
      {
        "aspect_ratio": "4:5",
        "x": 0.08,
        "y": 0.04,
        "width": 0.84,
        "height": 0.92,
        "score": 0.88
      }
    ],
    "title_safe": true
  },
  "upscale": {
    "policy": "only_if_crop_below_target",
    "target_long_edge": 2048,
    "max_scale": 2.0
  },
  "edits": {
    "exposure": 0.28,
    "contrast": 0.18,
    "highlights": -0.12,
    "shadows": 0.16,
    "temperature": -280,
    "tint": 3,
    "vibrance": 0.2,
    "saturation": 0.04,
    "sharpen": 0.22,
    "denoise": 0.08,
    "vignette": 0.14,
    "subject_boost": 0.16,
    "background_falloff": 0.10
  },
  "safety": {
    "preserve_identity": true,
    "preserve_text": true,
    "preserve_logo": true,
    "preserve_product_color": true,
    "preserve_object_count": true,
    "do_not_add_objects": true,
    "do_not_change_text": true
  },
  "aesthetic": {
    "score": 0.84,
    "reason": "The 4:5 crop strengthens the product subject while keeping label text readable."
  }
}
```

Recommended clamp ranges:

- `exposure`: `-0.7...0.7`
- `contrast`: `-0.35...0.45`
- `highlights`: `-0.5...0.2`
- `shadows`: `-0.2...0.6`
- `temperature`: `-1200...1200`
- `tint`: `-20...20`
- `vibrance`: `-0.2...0.45`
- `saturation`: `-0.25...0.35`
- `sharpen`: `0...0.45`
- `denoise`: `0...0.35`
- `vignette`: `0...0.28`
- `subject_boost`: `0...0.35`
- `background_falloff`: `0...0.30`
- crop coordinates: normalized `0...1`, must remain inside the source image
- `max_scale`: `1...2` for Phase 1 local upscale

Renderer output must preserve the original subject, text, identity, and object count. If the task requires adding/removing objects, replacing backgrounds, or reconstructing missing regions, the runtime should return `photo_edit_unavailable` for Phase 1 or route to a later generative adapter only when explicitly enabled.

## Share Metadata

The bridge can return optional captions and platform hints, but the iPhone owns the actual sharing UI. Phase 1 uses a task-level `share_caption` as the default caption for the selected variant; later bridge versions may also expose variant-specific captions.

Phase 1 sharing path:

1. iPhone downloads the selected variant.
2. App opens the system share sheet with the image and generated caption.
3. User chooses WeChat, WeChat Moments, Xiaohongshu, X, Save Image, AirDrop, or any installed activity.

The bridge should not claim that content was posted to a platform unless a later platform-specific SDK/API integration confirms it. Phase 1 only proves handoff to iOS sharing.

Failed response:

```json
{
  "task_id": "task_01JPHOTOA1YJ7TE4KZ5S4",
  "status": "failed",
  "progress": 1.0,
  "message": "The runtime could not produce a safe local edit recipe for this image.",
  "failure_code": "recipe_rejected_image"
}
```

## Task Events

`GET /mobile/v1/tasks/{task_id}/events`

Server-sent events:

```text
event: task.progress
data: {"progress":0.25,"message":"Analyzing scene."}

event: task.progress
data: {"progress":0.60,"message":"Rendering local variants."}

event: task.completed
data: {"variant_count":2}
```

Clients must fall back to polling when SSE is unavailable or disconnected.

## Asset Download

`GET /mobile/v1/assets/{asset_id}/download`

Response:

- `200 OK`
- `Content-Type: image/jpeg`, `image/png`, or `image/heic`
- Binary image body

Authorization must confirm the caller can access the task or uploaded asset that produced the asset.
