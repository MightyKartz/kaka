# Agent Pocket Mobile Bridge API

## Overview

The Mobile Bridge is the stable HTTPS boundary between Agent Pocket and a user-owned compatible agent runtime, such as Hermes, OpenClaw, or a sidecar that exposes the same contract. The iPhone app is a thin visual client: it pairs with a runtime, uploads photos and visible shared PDF payloads, starts `image_intake`, shows suggested skills in an image conversation, accepts visible Share Extension inbox items, starts universal `intake` tasks for text, links, and PDFs, starts photo-edit or vision tasks for the user's instruction, watches progress, and downloads edited images when needed. The runtime owns model credentials, workflow selection, vision analysis, crop planning, local image rendering, memory, approvals, and tool execution.

The broader Pocket Agents direction keeps the same boundary for future input types: share-sheet items, screenshots, pasted text, links, visible voice-transcribed notes, and permissioned context snapshots flow through Mobile Bridge as explicit user-initiated intake tasks. Phase A implements the additive `/mobile/v1/tasks/intake` contract beside the existing `image_intake`, `vision`, and `photo_edit` paths. Existing image clients should continue using `image_intake`.

Base path: `/mobile/v1`

Clients must tolerate unknown response fields. Servers must preserve backward compatibility for `/mobile/v1` during Phase 1.

## Ordinary User Boundary

Ordinary users should install Kaka through a host-native Hermes Plugin or
OpenClaw Skill/sidecar. The phone pairs with the runtime-hosted **Kaka Mobile
Bridge** endpoint and then uses only `/mobile/v1`.

Hermes/OpenClaw private APIs, private adapter commands, provider configuration,
raw logs, package paths, update channels, Codex developer plugin/skill source,
and host install roots stay on the Mac/runtime side. They are not Mobile Bridge
request fields, response fields, pairing prerequisites, or iPhone UI settings.

Codex plugin/skill automation may help host engineers scaffold and validate
the host-native package, but it must not become the public user install path.

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
- `vision_unavailable`
- `intake_unavailable`
- `invalid_intake_payload`
- `invalid_recall_action`
- `invalid_recall_payload`
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
- `pairing_page`: optional runtime-side QR page URL, such as `/mobile/v1/pairing/qr.html`.
- `pairing_payload`: optional full QR pairing JSON.
- `pairing_code` and `expires_at`: optional fields clients can use to build a pairing payload when `pairing_payload` is omitted.
- `trusted_local_tls_required`: optional boolean-like value (`true` or `1`) for HTTPS runtimes that require trusted local TLS.
- `tls_public_key_sha256`: optional non-secret 64-hex SHA-256 fingerprint for the host-owned TLS public key.
- `tls_certificate_label`: optional non-secret certificate label shown to users.

Discovery must not mint long-lived credentials by itself. Clients should show discovered runtimes as confirmation cards and exchange a one-time pairing code through `/pairing/exchange` only after the user chooses a runtime.

Production runtimes may expose `GET /mobile/v1/pairing/qr` and `GET /mobile/v1/pairing/qr.html` as explicit runtime-side QR actions. Those routes issue short-lived single-use pairing payloads with 60-300 second expiry. Development and mock runtimes may also expose `GET /mobile/v1/pairing/dev` without bearer auth so a client can recover when Bonjour TXT records contain a one-time development code that has already been exchanged.

Runtime plugins and skills must treat bridge startup as an explicit user action. Installing a Hermes/OpenClaw skill or plugin must not silently bind a LAN port, advertise Bonjour, or create a login item. A runtime may offer **Start with Hermes/OpenClaw** later, but it must be opt-in and reversible.

The P3.12 Host Extension Starter Kit is a host-side packaging scaffold for that
plugin/skill user path. It helps Hermes/OpenClaw host teams ship an installable
extension, but it does not add phone-side private host APIs or require ordinary
users to write adapter code, export `HERMES_KAKA_HOST_API` /
`OPENCLAW_KAKA_HOST_API`, or paste Runtime Kit command chains.

Follow-up installation work should keep the same split. The public user package
is a host-native Hermes Plugin or OpenClaw Skill/sidecar. Codex plugin/skill
automation, if generated, is host-team developer tooling only and must not
become a Mobile Bridge pairing prerequisite. The phone protocol remains
`/mobile/v1`: it does not install host extensions, call private Hermes/OpenClaw
APIs, receive private adapter command paths, or manage Codex plugin/skill roots.

Recommended runtime-side controls:

- **Start Kaka Mobile Bridge**: starts the local listener for the current session.
- **Show QR**: shows a short-lived pairing QR.
- **Advertise on Local Network**: enables Bonjour only after user approval.
- **Stop Bridge**: shuts down the listener and advertisement.
- **Revoke iPhone**: revokes the mobile token for a paired device.

## Runtime-Owned Persistence

Runtime persistence is a runtime launcher/server concern, not a mobile API field. The runtime-persistence execution slice adds a development option named `--runtime-store-path` for `kaka_mobile_runtime_kit start` and the bridge server. The iPhone must not send, choose, or display the SQLite path in Mobile Bridge requests.

A runtime launched with `--runtime-store-path` keeps Recall records, Recall retrieval-index receipts, runtime task records, and task events in a local SQLite database on the Mac/runtime side. Without that option, development and mock bridges may continue to use deterministic in-memory stores for tests.

The Mobile Bridge contract stays the same in both modes. The phone asks for Recall list/search/export/delete, runtime settings/status, and task list/approval/cancel/events; the runtime owns storage, retention, search implementation, deletion, and restart durability.

`GET /mobile/v1/runtime/settings`

This endpoint lets the phone display runtime-owned persistence and retrieval status without owning those settings. It must not expose provider keys, provider endpoints, hidden prompts, bearer tokens, raw embeddings, SQLite paths, or unrelated task logs.

Response:

```json
{
  "recall_store": {
    "enabled": true,
    "owner": "runtime",
    "label": "Local Kaka Recall and task store",
    "phone_can_change": false
  },
  "semantic_recall": {
    "available": true,
    "owner": "runtime",
    "mode": "provider_backed",
    "provider_label": "Runtime provider"
  },
  "retention": {
    "input_assets_days": 7,
    "output_assets_days": 30,
    "task_history_days": 30
  },
  "connection_security": {
    "pairing_code_ttl_seconds": 120,
    "mobile_token_ttl_seconds": null,
    "mobile_token_revocation_supported": true,
    "trusted_local_tls_required": true,
    "tls_trust_state": "configured",
    "tls_certificate_label": "Kaka Local Runtime",
    "tls_public_key_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
}
```

`semantic_recall.mode` is `local_deterministic` for the built-in fallback and `provider_backed` when the runtime has explicitly configured a runtime-owned Recall search provider. `connection_security` is phone-safe status only: it may include QR TTL, token TTL, revocation support, TLS trust state, certificate label, and the non-secret TLS public-key SHA-256 fingerprint, but not raw bearer tokens, raw certificates, certificate chain paths, or TLS private key paths. The mobile settings response intentionally does not include the SQLite file path or provider endpoint. Runtime Kit CLI dry-run, `settings-preview`, `local-tls-readiness`, or a native Hermes/OpenClaw runtime-side UI may show those runtime-side settings and non-secret certificate refs to the Mac/runtime user, but the phone only sees store status, retrieval mode, connection security status, and non-secret labels.

P3.10a is a runtime-side transport serving change only. When the runtime owner
starts the bridge with host-owned certificate files, Runtime Kit can serve Mobile
Bridge over local HTTPS, but it does not add a new Mobile Bridge endpoint and
must not expose certificate chain paths, private key paths, trust-store
internals, or raw certificate material through phone-facing responses.

P3.10b carries that non-secret public-key fingerprint into pairing payloads and
the iOS saved connection. The iOS client uses system trust by default; when an
HTTPS pairing payload includes a valid `tls_public_key_sha256`, it creates a
pinned `URLSession` trust policy for pairing, health checks, restore, and later
bridge requests. Required local TLS payloads without a valid pin are treated as
certificate failures. Local HTTP development endpoints remain allowed only for
local/private hosts.

P3.9 makes the existing `retention.input_assets_days`,
`retention.output_assets_days`, and `retention.task_history_days` values
runtime-configurable from the Hermes/OpenClaw host shell. The phone still treats
this object as read-only status. There is no `POST` or
`PUT /mobile/v1/runtime/settings`, and do not treat P3.9 as automatic deletion
or cleanup enforcement; asset/task purge behavior and deletion receipts are
separate runtime-owned slices.

P3.14 adds that runtime-owned cleanup slice as `retention-purge`, a Runtime Kit
CLI/action that emits `kaka.runtime_retention_purge_receipt.v1` receipts with
dry-run/apply semantics. It is not a Mobile Bridge endpoint: there is still no
`/mobile/v1/runtime/purge`, no phone-side settings write, and no automatic
cleanup on server start or install. The current implementation deletes only old
terminal task history from `SQLiteRuntimeStore`, preserves active tasks and
Recall. P3.22 adds timestamp-aware mock bridge in-memory input/output asset
purge receipts: uploaded input assets and photo-edit output assets carry
runtime-side `role` and `created_at` metadata, appear in `eligible` during
dry-run, and are removed only on explicit runtime-side apply. Untimestamped
assets remain preserved as `untracked_asset_ids`. P3.24 adds the same explicit
retention boundary for SQLite-backed input/output assets when Runtime Kit is
configured with a runtime store. `/mobile/v1/assets` upload/download response
shape stays unchanged, `/mobile/v1/runtime/purge` still does not exist, and
purge receipts contain IDs only rather than raw bytes, SQLite paths, provider
details, tokens, or task result variants.

P3.25 adds store-backed task-detail persistence without adding endpoints or
changing `/mobile/v1/assets`. `GET /mobile/v1/tasks/{id}` rehydrates phone-safe
completed photo-edit result detail after a bridge restart. Persisted task
metadata may store variant IDs, labels, asset IDs, explanation, and allowlisted
structured recipe/status fields. `download_url` is rebuilt from `asset_id` for
the task-detail response, not stored. Task lists remain summary-only, and
store-backed completed task events expose only `variant_count`.

## Capabilities

`GET /mobile/v1/capabilities`

Response:

```json
{
  "profiles": [
    {
      "id": "photo-agent",
      "display_name": "Photo Agent",
      "capabilities": ["photo_edit", "vision", "image_intake", "intake"]
    }
  ],
  "tasks": {
    "photo_edit": {
      "max_upload_mb": 30,
      "accepted_mime_types": ["image/jpeg"],
      "styles": ["natural_enhance", "portrait_polish", "product_shot", "social_cover"],
      "provider": "recipe_local",
      "renderer": "local_parametric",
      "variant_labels": ["Master", "Social"],
      "variant_ids": ["variant_clean_pro", "variant_social_pop"],
      "crop_aspects": ["original"],
      "supports_crop_candidates": false,
      "supports_upscale_policy": true,
      "supports_sse": true,
      "return_variants_max": 2
    },
    "vision": {
      "max_upload_mb": 30,
      "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
      "modes": ["scan", "identify", "translate", "food"],
      "provider": "runtime_configured_multimodal",
      "supports_sse": true
    },
    "image_intake": {
      "max_upload_mb": 30,
      "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
      "provider": "heuristic_image_intake",
      "supports_sse": true
    },
    "intake": {
      "accepted_types": ["text", "url", "image", "pdf", "video"],
      "provider": "heuristic_universal_intake",
      "supports_context_snapshot": true,
      "supports_voice_followup": true,
      "supports_recall_actions": true,
      "supports_sse": false
    }
  },
  "retention": {
    "input_assets_days": 7,
    "output_assets_days": 30,
    "task_history_days": 30
  }
}
```

For the default `recipe_local` renderer, `photo_edit.return_variants_max` is
currently `2`, matching `variant_clean_pro` and `variant_social_pop`, and
`photo_edit.accepted_mime_types` is JPEG-only because the normal iOS photo-edit
path JPEG-normalizes camera/library inputs before upload. Generic asset upload,
`vision`, `image_intake`, and universal intake remain separate broader
boundaries. P3.27 `local-renderer-backend-capability-manifest` is a Runtime Kit
planning artifact for future local renderer backends; it does not change this
Mobile Bridge capability shape, add endpoints, enable Core Image/ImageMagick/
OpenCV/libvips, or change `/mobile/v1`.

## Universal Intake Task

`POST /mobile/v1/tasks/intake`

This additive endpoint handles visible user-shared non-camera items. The iOS Phase A app stores Share Extension payloads in an App Group inbox first; it does not silently upload shared content from the extension. The main app submits visible text and URL inbox items to this endpoint after the user is connected to a runtime.

P3.36b Explicit Paste-to-Inbox Courier uses the same boundary: the phone reads clipboard text only after the user taps the visible Inbox Paste button, creates a pending `.text` or http/https `.url` item with `source.surface = "paste"`, and still waits for visible Inbox `Send` before this endpoint is called.

B.1 voice follow-up, P3.30 Voice-to-Inbox Draft, and P3.32 Inbox Voice Instruction use the same text boundary: Kaka records only while the user explicitly presses the push-to-talk control, transcribes on device with iOS Speech, shows an editable transcript, and sends the reviewed transcript as text. P3.32 saves the reviewed transcript into the selected `KakaInboxItem.note`; P3.33 adds local edit, clear, and send-preview UI for that note; P3.34 adds deterministic local template chips that write selected template text into the same note; the existing submitter sends the note as `note` and `user_instruction` only after the user taps visible Inbox `Send`. For `pdf` and first-release short `video`, the main app uploads the shared/copied file payload from the visible Inbox action, then starts `/mobile/v1/tasks/intake` with the returned `asset_id`. Shared image payloads, including screenshots represented as images, keep routing through `image_intake` so the existing image conversation stays intact.

M1 Local Agent Lens adds phone-native source surfaces while keeping the same visible-review boundary: `agent_scanner`, `document_scanner`, `video_capture`, `action_button`, and `shortcut`. Scanner results are never opened or submitted automatically; Kaka first shows explicit actions such as ask local agent, open URL, copy, save, or connect local runtime. Document scan and video capture/create only local Inbox drafts until the user reviews and taps visible Inbox `Send`. Action Button and Shortcuts only foreground Kaka to the relevant Lens surface.

`supports_voice_followup: true` means the runtime can accept text follow-up submitted from the visible voice UI and may return a short `summary` that the phone can read aloud. It does not mean B.1, P3.30, or P3.32 uploads raw microphone audio. Raw audio stays local and temporary; always-on listening, hidden background transcription, automatic Inbox submission, and automatic Recall writes are out of scope.

Request for text:

```json
{
  "kind": "text",
  "text": "Buy milk and send launch review notes",
  "note": "Extract tasks",
  "locale": "en-US",
  "preferred_profile_id": "photo-agent",
  "source_app": "Notes",
  "received_at": "2026-06-05T07:30:00+08:00",
  "source": {
    "surface": "share_extension",
    "host_app": "Notes"
  },
  "user_instruction": "Extract tasks"
}
```

Request for URL:

```json
{
  "kind": "url",
  "url": "https://example.com/article",
  "source": {
    "surface": "share_extension",
    "host_app": "Safari"
  }
}
```

Request for pasted text after visible Inbox Send:

```json
{
  "kind": "text",
  "text": "Rewrite this message in a calmer tone.",
  "source_app": "Clipboard",
  "source": {
    "surface": "paste",
    "host_app": "Clipboard"
  }
}
```

Request for pasted URL after visible Inbox Send:

```json
{
  "kind": "url",
  "url": "https://example.com/article",
  "source_app": "Clipboard",
  "source": {
    "surface": "paste",
    "host_app": "Clipboard"
  }
}
```

Request for URL with Inbox Voice Instruction:

```json
{
  "kind": "url",
  "url": "https://example.com/article",
  "note": "Summarize first and extract next actions.",
  "source": {
    "surface": "share_extension",
    "host_app": "Safari"
  },
  "user_instruction": "Summarize first and extract next actions."
}
```

Request for Voice-to-Inbox text:

```json
{
  "kind": "text",
  "text": "Summarize this receipt before I send it.",
  "locale": "en-US",
  "source_app": "Kaka Voice",
  "source": {
    "surface": "voice",
    "host_app": "Kaka Voice"
  }
}
```

Request for image, PDF, or video-capable runtimes:

```json
{
  "kind": "video",
  "asset_id": "asset_video_123",
  "source": {
    "surface": "video_capture",
    "host_app": "Kaka"
  }
}
```

The mock bridge also accepts legacy-compatible `"type"` in place of `"kind"`. For `image`, `pdf`, and `video`, the runtime expects an existing `asset_id`. The iOS app obtains PDF/video `asset_id` values only from a visible main-app Inbox submission; the Share Extension, scanner, Action Button, and Shortcuts still never upload directly.

Create response:

```json
{
  "task_id": "task_intake_01",
  "status": "queued",
  "status_url": "/mobile/v1/tasks/task_intake_01",
  "events_url": "/mobile/v1/tasks/task_intake_01/events"
}
```

Completed status:

```json
{
  "task_id": "task_intake_01",
  "status": "completed",
  "progress": 1.0,
  "message": "Completed.",
  "result_type": "intake",
  "intake": {
    "kind": "url",
    "type": "url",
    "title": "Shared link ready",
    "summary": "Kaka received a link from Safari: https://example.com/article",
    "metadata": {
      "source_app": "Safari",
      "url": "https://example.com/article"
    },
    "suggestions": [
      {
        "id": "summarize",
        "label": "Summarize",
        "requires_confirmation": false,
        "is_available": true
      },
      {
        "id": "remember",
        "label": "Remember",
        "requires_confirmation": true,
        "is_available": true
      }
    ]
  }
}
```

The earlier image-only implementation specializes intake around images:

- upload asset
- start `POST /mobile/v1/tasks/image-intake`
- receive summary plus suggested image skills
- route the user's next action to photo-edit or vision tasks

Pocket Agents should continue generalizing this intake family without breaking Phase 1 clients.

Forward-compatible capability shape:

```json
{
  "tasks": {
    "intake": {
      "accepted_types": ["image", "screenshot", "text", "url", "pdf", "video"],
      "supports_context_snapshot": true,
      "supports_voice_followup": true,
      "supports_recall_actions": true,
      "supports_sse": true
    }
  }
}
```

Forward-compatible request shape:

```json
{
  "kind": "url",
  "asset_id": "asset_optional",
  "text": "optional user-visible text",
  "url": "https://example.com/article",
  "source": {
    "surface": "share_extension",
    "host_app": "Safari"
  },
  "context_snapshot": {
    "timestamp": "2026-06-04T11:00:00Z",
    "timezone": "Asia/Shanghai",
    "motion": "walking",
    "network": "wifi",
    "battery": "normal",
    "location_label": "not_requested",
    "location_precision": "none",
    "calendar_availability": "busy_soon"
  },
  "user_instruction": "Summarize this and remember it if useful."
}
```

Current Context Snapshot contract:

- The client omits `context_snapshot` unless the user opts in for that task.
- The client also omits `context_snapshot` unless `GET /mobile/v1/capabilities` includes `"supports_context_snapshot": true` for `tasks.intake`.
- Snapshot fields use snake_case and omit unavailable values, or include stable
  payload sentinel values such as `permission_denied`, `not_requested`, or
  `unavailable`. P3.23 keeps those payload values stable while the iPhone preview
  maps them to readable labels for the user; P3.29 adds motion/calendar values
  inside the same fields.
- The current iOS collector is task-scoped and permission-aware. It may include a one-shot coarse `network` path status, conservative `battery`, one-shot current `motion`, `location_label`, `location_precision`, and one-shot 30-minute `calendar_availability` after visible preview.
- Runtime/mock bridge handling must treat `context_snapshot` as an allowlisted
  payload. Unknown keys, nested containers, coordinates, network identifiers,
  and calendar event details must not be stored or echoed.
- A snapshot is task-scoped input. It is not written to Recall unless the user separately confirms a Recall action.

| Field | Owner | Allowed shape | Must not include |
| --- | --- | --- | --- |
| `network` | iPhone | Coarse state such as `wifi`, `cellular`, `offline`, `constrained`, `unknown`, or `unavailable`. | SSID, BSSID, carrier, IP address, hostnames. |
| `battery` | iPhone | Coarse state such as `normal`, `low`, `critical`, `full`, `charging`, `charging_80_percent`, or `unavailable`. | Battery health history, serial/device identifiers, fine-grained telemetry. |
| `motion` | iPhone | One-shot current labels such as `stationary`, `walking`, `running`, `driving`, `unknown`, `permission_denied`, `not_requested`, or `unavailable`. | Background motion history, accelerometer samples, routes, confidence, or continuous tracking. |
| `location_label` | iPhone | Authorization/status sentinel today, such as `available`, `permission_denied`, `not_requested`, or `unavailable`. Future user-visible coarse labels may include `near_home` or `near_office`. | Coordinates, address book details, precise places by default. |
| `location_precision` | iPhone | `coarse`, `precise`, `none`, or `unknown`. | Latitude/longitude or raw location accuracy values. |
| `calendar_availability` | iPhone | One-shot next-30-minute labels such as `free`, `busy`, `busy_soon`, `write_only`, `permission_denied`, `not_requested`, or `unavailable`. | Event titles, attendees, notes, locations, descriptions, calendar identifiers, or calendar bodies. |

```json
{
  "context_snapshot": {
    "timestamp": "2026-06-05T09:30:00Z",
    "timezone": "Asia/Shanghai",
    "locale": "zh-Hans",
    "source_surface": "share_extension",
    "network": "wifi",
    "battery": "normal",
    "motion": "walking",
    "location_label": "not_requested",
    "location_precision": "none",
    "calendar_availability": "busy_soon"
  }
}
```

Forward-compatible result shape:

```json
{
  "task_id": "task_intake_01",
  "status": "completed",
  "result_type": "intake",
  "intake": {
    "kind": "url",
    "title": "Article summary",
    "summary": "A concise runtime-generated summary.",
    "suggestions": [
      {
        "id": "summarize",
        "label": "Summarize",
        "is_available": true
      },
      {
        "id": "remember",
        "label": "Remember",
        "requires_confirmation": true,
        "is_available": true
      },
      {
        "id": "forget",
        "label": "Forget",
        "requires_confirmation": true,
        "is_available": true
      }
    ]
  }
}
```

Design rules for this API:

- `image_intake` remains valid for existing clients.
- Universal intake must be user-initiated from camera, share sheet, paste, file picker, or visible voice UI.
- P3.36b Explicit Paste-to-Inbox Courier uses this same universal intake boundary after creating a pending Inbox item from a visible Paste action. It adds no paste-specific `/mobile/v1` endpoint, background pasteboard reader, URL fetcher, automatic submission path, or automatic Recall write.
- B.1 voice input is on-device transcription into editable text; raw microphone audio is not uploaded through Mobile Bridge.
- P3.32 Inbox Voice Instruction is a client-side note update before visible
  `Send`; runtimes should treat the submitted value as ordinary
  `note`/`user_instruction` text, not as an audio capability or a separate task
  trigger.
- P3.33 Inbox Instruction Polish is also client-side: edit, clear, and
  send-preview controls do not change request fields or trigger runtime work.
- P3.34 Inbox Instruction Templates is also client-side: template chips write
  deterministic text into `KakaInboxItem.note` and do not add request fields or
  trigger runtime work.
- P3.37 Inbox Result Review Provenance is also client-side: after a visible
  Inbox `Send` completes, Kaka may show source/context review copy and pass the
  existing `source_task_id` plus `source_inbox_item_id` to explicit Recall
  actions. It adds no result-review endpoint, automatic Recall write, runtime
  schema change, Files picker, provider call, or host package behavior.
- P3.38 Explicit Files-to-Inbox Import also stays client-side: the visible file
  picker creates a pending Inbox item from one user-selected PDF or image, and
  runtime upload still waits for visible Inbox `Send`. It does not add a file
  import endpoint, background file access, automatic submission, automatic
  Recall, or Host Extension behavior.
- P3.39 Inbox Pending Item Discard is client-side/local store behavior only: a
  visible Inbox row action removes one pending item before `Send` through the
  existing Inbox store. P3.40 Inbox Discard Confirmation is also client-side:
  the row action opens a visible confirmation dialog, and only the destructive
  confirm action calls the existing local discard path. Cancel or dismissal
  leaves the pending item untouched. These slices do not add a discard endpoint,
  runtime task cancel, asset upload, Recall action/delete, App Intent, or Host
  Extension behavior.
- P3.41 Inbox Action Feedback Banner is client-side presentation only: Inbox
  renders existing local `state`/`progressText` feedback for failures and
  in-flight submission progress. It does not add retry, runtime task cancel,
  automatic submission, Recall action/write/delete, endpoint/schema changes, App
  Intent behavior, or Host Extension behavior.
- P3.42 Inbox Pending Item Review Details is client-side presentation only:
  pending Inbox rows may expand a local read-only details section from existing
  `KakaInboxItem` metadata before visible `Send`. It does not add endpoints,
  request fields, response fields, runtime capabilities, automatic submission,
  Recall behavior, URL fetch, file reads, PDF/OCR parsing, App Intent behavior,
  or Host Extension behavior.
- Host-native Hermes Plugin / OpenClaw Skill packaging and optional Codex
  developer plugin/skill automation are host-team/runtime-side concerns. They
  must not add Mobile Bridge endpoints, request fields, response fields,
  private host API fields, adapter command paths, marketplace metadata, or
  user-home Codex paths to `/mobile/v1`; Kaka iPhone still pairs and talks only
  through the Mobile Bridge contract.
- Context snapshots are optional and task-scoped unless the user chooses a Recall action.
- Recall actions must be explicit and reversible where the runtime controls storage.
- Clients must tolerate unknown `kind`, `suggestions`, and context fields.

## Recall Actions

Recall is explicit-action only. The client must not automatically remember intake results, image conversations, or Context Snapshot payloads. `remember` and `forget` actions should be shown to the user and confirmed before submission; `use_once` may be submitted directly for current-task use and must not create a persisted Recall item. D.1 adds browse/search/export foundations and deletion receipts for runtime-owned retrieval indexes. Storage remains runtime-owned: the iPhone can request Recall operations, but it does not own the database, retention policy, or retrieval index.

`POST /mobile/v1/recall/actions`

Request:

```json
{
  "action": "remember",
  "source_task_id": "task_intake_01",
  "source_inbox_item_id": "12345678-1234-1234-1234-1234567890AB",
  "user_visible_summary": "Remember that launch summaries should be in Chinese."
}
```

`action` is one of `remember`, `use_once`, or `forget`. `source_task_id` and `source_inbox_item_id` are optional provenance fields, but clients should include at least one when available. `user_visible_summary` is the exact summary shown to the user for the action.

Remember response:

```json
{
  "action": "remember",
  "status": "remembered",
  "item": {
    "item_id": "recall_0001",
    "summary": "Remember that launch summaries should be in Chinese.",
    "created_at": "2026-06-05T00:00:00Z",
    "provenance": {
      "source_task_id": "task_intake_01",
      "source_inbox_item_id": "12345678-1234-1234-1234-1234567890AB"
    }
  },
  "deleted_item_ids": []
}
```

Use-once response:

```json
{
  "action": "use_once",
  "status": "used_once",
  "item": null,
  "deleted_item_ids": []
}
```

Forget by source response:

```json
{
  "action": "forget",
  "status": "forgotten",
  "item": null,
  "deleted_item_ids": ["recall_0001"]
}
```

When both `source_task_id` and `source_inbox_item_id` are present on a `forget` request, runtimes should delete only items whose provenance matches all provided fields. Repeated forget calls should be deterministic and return an empty `deleted_item_ids` array once there is no matching item.

`GET /mobile/v1/recall/items`

Optional query parameters:

- `query`: user-entered search text. The runtime may match summary, extracted text, and provenance labels.
- `limit`: positive integer result limit. Clients should default to 25 when showing a browse surface.

Response:

```json
{
  "items": [
    {
      "item_id": "recall_0001",
      "summary": "Remember that launch summaries should be in Chinese.",
      "created_at": "2026-06-05T00:00:00Z",
      "provenance": {
        "source_task_id": "task_intake_01"
      }
    }
  ]
}
```

`POST /mobile/v1/recall/search`

Semantic Recall search is additive to the D.1 browse endpoint. Clients should use it for non-empty user search queries and fall back to `GET /mobile/v1/recall/items?query=...&limit=...` if the runtime does not support semantic search. Runtime Kit provides deterministic local scoring by default and can route ranking through an explicitly configured runtime-owned provider such as `runtime_http`; provider errors fall back to deterministic local scoring when safe. P3.21 adds a read-only `recall-retrieval-readiness` Runtime Kit artifact for production packaging materials, and P3.26 adds `recall-retrieval-material-intake` for reviewing a local host/runtime-supplied materials manifest. Neither artifact changes this Mobile Bridge request or response shape, invokes providers, fetches refs, exposes provider endpoints/keys to iPhone, or includes retrieval internals in Recall export.

Request:

```json
{
  "query": "launch summary language",
  "limit": 5,
  "context": {
    "source_surface": "voice",
    "source_task_id": "task_123"
  }
}
```

Response:

```json
{
  "query": "launch summary language",
  "mode": "semantic",
  "retrieval_mode": "provider_backed",
  "items": [
    {
      "item": {
        "item_id": "recall_0001",
        "summary": "Answer launch summaries in Chinese.",
        "created_at": "2026-06-05T09:30:00Z",
        "provenance": {
          "source_task_id": "task_123"
        }
      },
      "score": 0.91,
      "match_reason": "Matched Recall terms: launch, summary."
    }
  ]
}
```

`mode` remains `semantic` for Swift/client compatibility. `retrieval_mode` is additive and may be `local_deterministic` or `provider_backed`. `score` is a runtime-owned ranking signal for ordering and diagnostics. Clients may show `match_reason`, but should not show raw score unless product design explicitly calls for it. Search responses are allowlisted to `item`, `score`, and `match_reason`; they must not include raw embeddings, retrieval-index rows, provider endpoints, provider keys, hidden prompts, SQLite paths, raw provider responses, or unrelated task logs. Runtime-side provider requests are likewise limited to the query, limit, and sanitized Recall candidates; outbound provenance is allowlisted to `source_task_id`, `source_inbox_item_id`, and `source_surface`.

`GET /mobile/v1/recall/export`

Exports a JSON package of the user-visible Recall metadata, summaries, timestamps, and provenance currently retained by the runtime. The export is a Recall API response, not a database dump. P3.20 adds additive `schema_version` and `artifact_policy` fields so host/runtime tests can verify the export boundary while older Swift clients can continue decoding `format`, `generated_at`, and `items`. Provider keys, provider endpoints, hidden model prompts, bearer/mobile tokens, SQLite paths, raw embeddings, retrieval-index rows, raw provider responses, and unrelated task logs must never be exported through this endpoint.

Response:

```json
{
  "schema_version": "kaka.recall_export.v1",
  "format": "json",
  "generated_at": "2026-06-05T10:00:00Z",
  "artifact_policy": {
    "classification": "user_recall_export",
    "artifact_kind": "recall_export_json",
    "runtime_owned_source": true,
    "database_dump": false,
    "phone_safe": true,
    "item_fields": ["item_id", "summary", "created_at", "provenance"],
    "provenance_fields": ["source_task_id", "source_inbox_item_id", "source_surface"],
    "forbidden_fields": [
      "raw_embeddings",
      "retrieval_index_rows",
      "provider_keys",
      "bearer_tokens",
      "runtime_store_path",
      "hidden_prompts",
      "raw_provider_responses"
    ]
  },
  "items": [
    {
      "item_id": "recall_0001",
      "summary": "Remember that launch summaries should be in Chinese.",
      "created_at": "2026-06-05T00:00:00Z",
      "provenance": {
        "source_task_id": "task_intake_01"
      }
    }
  ]
}
```

`DELETE /mobile/v1/recall/items/{item_id}`

Response:

```json
{
  "status": "forgotten",
  "deleted_item_ids": ["recall_0001"],
  "deleted_index_ids": ["embedding_recall_0001"]
}
```

Repeated delete calls should be deterministic and return empty `deleted_item_ids` and `deleted_index_ids` arrays once there is no matching item. `deleted_index_ids` is a deletion receipt: it means the runtime removed retrieval-index records associated with the deleted Recall item. It is not a command for the iPhone to delete local index data.

## Runtime Task Inbox

Task Inbox E.0 makes runtime work visible and controllable inside Kaka before App Intents or Live Activity are enabled.

Task records and task events are also runtime-owned. After the Runtime Kit SQLite store is connected, task status, approvals, cancellation, completion state, and event history should survive bridge/server recreation when the bridge is launched with `--runtime-store-path`. The iPhone displays and acts on the Mobile Bridge responses; it does not become the production task-state store.

P3.25 extends that runtime-owned task durability to safe result detail for
completed photo-edit tasks. The detail endpoint may include rehydrated
`variants`, `explanation`, and allowlisted recipe/status fields, but task list
responses should continue to omit result detail. Store-backed event streams
expose only `variant_count` for completed photo-edit tasks, not asset IDs,
download URLs, runtime paths, provider endpoints, tokens, raw bytes, or private
host data.

`GET /mobile/v1/tasks`

Response:

```json
{
  "tasks": [
    {
      "id": "task_waiting",
      "title": "Approve Recall write",
      "status": "waiting_for_approval",
      "progress": 0.4,
      "message": "Review memory write",
      "updated_at": "2026-06-05T09:31:00Z"
    }
  ]
}
```

`status` is one of `queued`, `running`, `waiting_for_approval`, `completed`, `failed`, or `cancelled`. Clients should show `waiting_for_approval` first, then active or recent tasks.

`POST /mobile/v1/tasks/{task_id}/cancel`

Response:

```json
{
  "status": "cancelled",
  "task": {
    "id": "task_running",
    "title": "Summarize PDF",
    "status": "cancelled",
    "progress": 1.0,
    "message": "Cancelled.",
    "updated_at": "2026-06-05T09:35:00Z"
  }
}
```

`POST /mobile/v1/tasks/{task_id}/approval`

Request:

```json
{
  "action": "approve",
  "note": "Looks safe."
}
```

Response:

```json
{
  "status": "approved",
  "task": {
    "id": "task_waiting",
    "title": "Approve Recall write",
    "status": "running",
    "progress": 0.5,
    "message": "Approved.",
    "updated_at": "2026-06-05T09:35:00Z"
  }
}
```

Task Inbox E.1 adds iOS system surfaces without changing the Mobile Bridge task API. App Intents open Kaka to visible Inbox, Tasks, or Local Agent Lens surfaces through an app handoff; they do not submit inbox items, approve tasks, cancel tasks, collect Context Snapshot data, or change runtime/provider settings in the background. Approval and cancellation still go through the existing Mobile Bridge endpoints after the app shows the current task state.

Action Button support reuses the same foreground App Intent handoff and may open visible Inbox, Tasks, Scanner, Document Scan, Video Intake, or Voice surfaces. It does not add Mobile Bridge fields, endpoints, or hidden task actions.

Live Activity state is a phone-safe projection of runtime task state. The `title` value is generated by the iPhone from task phase and must not copy the runtime-controlled task title. The allowed system-surface fields are:

- `task_id`
- `title`
- `phase`
- `approval_needed`
- `progress`
- `message`

`progress` is clamped to `0...1`. `message` is the same short, phone-visible task message Kaka can already show in Task Inbox; it must be sanitized by the runtime and is trimmed by the phone projection. The projection must not include `updated_at`, bearer tokens, provider endpoints or keys, hidden prompts, task logs, asset bytes, Context Snapshot fields, Recall content, embeddings, retrieval-index rows, or runtime SQLite paths.

The WidgetKit Live Activity extension renders only this projection on the Lock Screen and Dynamic Island. It does not add task approval or cancellation endpoints; those actions still require opening Kaka and using the visible Task Inbox state.

## Pairing QR Payload

`GET /mobile/v1/pairing/qr` returns the current production QR JSON payload. `GET /mobile/v1/pairing/qr.html` renders a scannable QR page for the runtime-side UI. The QR code encodes JSON:

```json
{
  "version": 1,
  "endpoint": "https://macbook-pro.local:8765",
  "runtime": "hermes",
  "display_name": "Kartz MacBook Runtime",
  "pairing_code": "pair_01JPHOTO",
  "expires_at": "2026-05-30T16:30:00Z",
  "trusted_local_tls_required": true,
  "tls_public_key_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "tls_certificate_label": "Kaka Local Runtime"
}
```

The app must reject expired payloads and remote non-HTTPS endpoints before exchanging the code.
When `trusted_local_tls_required` is true, the payload must use an HTTPS endpoint
and include a valid `tls_public_key_sha256`; otherwise the app treats the pairing
attempt as a certificate failure instead of silently falling back to default
trust.

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

## Pairing Revocation

`POST /mobile/v1/pairing/revoke`

The request requires the current bearer token. The runtime revokes that mobile token and returns:

```json
{
  "status": "revoked"
}
```

After revocation, every bearer-protected endpoint must return `401 unauthorized` for that token. Runtime-side Hermes/OpenClaw UI may expose a **Revoke iPhone** control backed by this lifecycle, but raw mobile tokens must not appear in phone-safe settings or logs.

## Asset Upload

`POST /mobile/v1/assets`

Request:

- `multipart/form-data`
- Field `file`: JPEG, HEIC, PNG image, or a visible shared PDF payload for universal intake.
- Field `metadata`: JSON string. Image uploads include width, height, local creation time, and EXIF-safe metadata. PDF uploads include source, original filename, and sensitive-metadata stripping intent.

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
  "output_intent": "master_shot"
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

## Image Intake Task

`POST /mobile/v1/tasks/image-intake`

This is the first task Kaka starts after capture or gallery selection. It classifies the uploaded image enough to open an image conversation and suggest useful skills. It must not fabricate final OCR, object, nutrition, or edit results; it only recommends what Kaka can do next.

Request:

```json
{
  "profile_id": "photo-agent",
  "asset_id": "asset_123",
  "locale": "zh-Hans"
}
```

Response:

```json
{
  "task_id": "task_intake_1",
  "status": "queued",
  "events_url": "/mobile/v1/tasks/task_intake_1/events"
}
```

Completed status:

```json
{
  "task_id": "task_intake_1",
  "status": "completed",
  "progress": 1.0,
  "result_type": "image_intake",
  "image_intake": {
    "image_type": "text",
    "title": "检测到文字",
    "summary": "我看到这张图片里有多行可读文字。",
    "confidence": 0.82,
    "suggestions": [
      {
        "skill": "ocr",
        "title": "提取文字",
        "reason": "画面中有多行可读文字。",
        "confidence": 0.84,
        "is_available": true
      }
    ]
  }
}
```

Known `skill` values are `photo_enhance`, `ocr`, `translate_text`, `identify_subject`, and `nutrition_estimate`. Servers should include unavailable but relevant skills with `"is_available": false` so the client can explain missing runtime capabilities instead of hiding the possibility.

## Vision Task

`POST /mobile/v1/tasks/vision`

This endpoint is the bottom-layer execution path for image-conversation skills that return information rather than edited image variants: `scan`, `identify`, `translate`, and `food`. The iPhone still uploads the image asset first. The runtime may call whichever multimodal model the user's agent is configured to use; provider keys and model routing stay runtime-side.

Request:

```json
{
  "profile_id": "photo-agent",
  "asset_id": "asset_01JPHOTO9N0QWQNS9YW4Y3",
  "mode": "identify",
  "instruction": "Identify the main visible objects, plants, animals, products, or landmarks.",
  "locale": "zh-Hans"
}
```

Allowed `mode` values:

- `scan`: extract visible text, codes, and document details.
- `identify`: identify visible objects, plants, animals, products, or landmarks.
- `translate`: read visible text and translate into the user's current locale.
- `food`: identify visible food and estimate a calorie range with uncertainty.

Response:

```json
{
  "task_id": "task_01JVISIONA1YJ7TE4KZ5S4",
  "status": "queued",
  "events_url": "/mobile/v1/tasks/task_01JVISIONA1YJ7TE4KZ5S4/events"
}
```

Servers should return `vision_unavailable` when a requested mode is not advertised in `GET /mobile/v1/capabilities`.

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
  "explanation": "Balanced exposure, reduced color cast, protected important details, and generated local recipe variants without changing identity, adding objects, or changing the original frame.",
  "renderer": "local_parametric",
  "composition": {
    "selected_aspect_ratio": "original",
    "crop": {
      "x": 0.0,
      "y": 0.0,
      "width": 1.0,
      "height": 1.0
    }
  },
  "qa": {
    "master_difference_score": 0.18,
    "social_difference_score": 0.31
  },
  "recipe_summary": "Balanced exposure while preserving the original frame.",
  "share_caption": "用本机智能体做了一版大师感成片。",
  "provider": {
    "name": "recipe_local",
    "model": "runtime_configured_multimodal",
    "renderer": "local_parametric"
  }
}
```

Completed vision response:

```json
{
  "task_id": "task_01JVISIONA1YJ7TE4KZ5S4",
  "status": "completed",
  "progress": 1.0,
  "message": "Completed.",
  "result_type": "vision",
  "vision": {
    "mode": "food",
    "title": "食物估算",
    "summary": "画面中像是一份轻食，热量约 320-460 千卡。",
    "text": "可见食材：鸡蛋、蔬菜、面包。实际热量会受分量和调味影响。",
    "language": "zh-Hans",
    "confidence": 0.72,
    "sections": [
      {
        "title": "热量和营养",
        "kind": "nutrition",
        "items": [
          {
            "title": "热量范围",
            "value": "320-460 kcal",
            "subtitle": "基于可见分量估算",
            "confidence": 0.62
          },
          {
            "title": "蛋白质",
            "value": "18-25 g",
            "subtitle": "基于可见鸡蛋和肉类估算",
            "confidence": 0.58
          }
        ]
      },
      {
        "title": "估算依据",
        "kind": "assumptions",
        "items": [
          {
            "title": "不确定性",
            "value": "实际热量受分量、油脂和酱料影响",
            "confidence": 0.75
          }
        ]
      }
    ],
    "items": [
      {
        "title": "热量范围",
        "value": "320-460 kcal",
        "subtitle": "基于可见分量估算",
        "confidence": 0.62
      }
    ]
  },
  "provider": {
    "name": "runtime_configured_multimodal"
  }
}
```

`vision.sections` is optional and recommended for mode-specific result screens. If omitted, clients should fall back to the top-level `vision.items` array. Recommended section `kind` values:

- `ocr`: visible text or translated text blocks for scan/translate.
- `codes`: QR codes, barcodes, or document metadata.
- `candidates`: object, product, plant, animal, or landmark candidates for identify.
- `nutrition`: calories, protein, carbs, fat, and portion estimates for food.
- `assumptions`: uncertainty, capture quality, or visible evidence used by the runtime.

For development, `fixture_vision` returns deterministic structured placeholders only. It does not read the real image. A production-quality Hermes/OpenClaw bridge should use a runtime-owned provider such as `runtime_http`, where the bridge posts image bytes and mode context to a local agent endpoint and receives the same `vision` object shape. Provider keys and model routing remain inside the runtime process.

## Local Recipe Schema

Phase 1 uses model-assisted parameter editing instead of generated image editing. The runtime may expose a recipe summary for debugging, but the iPhone should treat the rendered image asset as the source of truth and should not show recipe controls or recipe chips to users.

The runtime must validate and clamp recipe values before rendering. The model may suggest parameters, but it must not write executable code or arbitrary filter graphs.

Compatible runtimes should expose the local recipe path through `GET /mobile/v1/capabilities`, not through client-side provider configuration. In Phase 1, the iPhone treats `provider`, `renderer`, `variant_labels`, `variant_ids`, `crop_aspects`, `supports_crop_candidates`, and `supports_upscale_policy` as runtime capabilities. The mock bridge advertises these fields for `recipe_local`; Hermes, OpenClaw, or another sidecar should serve the same shape when they implement the contract.

Inside the runtime, `recipe_local` can run in `fixture` mode for deterministic QA or `runtime_vision` mode for model-assisted recipes. In `runtime_vision` mode the adapter posts the source image as base64 plus style, scene, variant, instruction, supported crop aspects, Kaka `scene_profile` defaults, and safety requirements to a local runtime recipe endpoint. Phase 1 advertises only the `original` aspect so the rendered result keeps the source dimensions and framing by default. That endpoint may call whichever multimodal model the runtime is configured to use, then must return strict `PhotoEditRecipe` JSON. The adapter validates the JSON before rendering. This endpoint is runtime-side only; it is not called by the iPhone and it must not require provider keys from the iPhone client.

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
    "selected_aspect_ratio": "original",
    "crop": {
      "x": 0.0,
      "y": 0.0,
      "width": 1.0,
      "height": 1.0
    },
    "crop_candidates": [
      {
        "aspect_ratio": "original",
        "x": 0.0,
        "y": 0.0,
        "width": 1.0,
        "height": 1.0,
        "score": 0.72
      }
    ],
    "title_safe": false
  },
  "upscale": {
    "policy": "none",
    "target_long_edge": 2048,
    "max_scale": 1.0
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
    "reason": "The edit strengthens product contrast and subject separation while preserving the original frame."
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

For vision tasks, the completion event may omit `variant_count` and use `result_type` instead:

```text
event: task.completed
data: {"result_type":"vision"}
```

Clients must fall back to polling when SSE is unavailable or disconnected.

## Asset Download

`GET /mobile/v1/assets/{asset_id}/download`

Response:

- `200 OK`
- `Content-Type: image/jpeg`, `image/png`, or `image/heic`
- Binary image body

Authorization must confirm the caller can access the task or uploaded asset that produced the asset.
