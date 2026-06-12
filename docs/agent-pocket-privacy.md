# Agent Pocket Privacy

Agent Pocket is a thin client. The phone owns capture, upload, progress, review, save, and share. The user-owned compatible runtime, such as Hermes, OpenClaw, or a Mobile Bridge sidecar, owns model/provider credentials, crop planning, recipe generation, local rendering, optional upscale, workflow execution, memory, retention, and approvals.

The broader Pocket Agents direction keeps the same boundary. The phone can collect share-sheet items, screenshots, explicitly pasted text, voice input, and permissioned context snapshots, but those inputs must remain user-visible and task-scoped unless the user explicitly saves them to Recall.

## Photo Handling

- The app preprocesses uploads with `ImagePreprocessor`, normalizing orientation and re-encoding JPEG without copying source metadata by default.
- Sensitive EXIF and GPS fields should not be sent to the bridge.
- The bridge stores input assets and output assets according to its advertised retention window.
- Task logs should use task IDs, asset IDs, status, recipe IDs, renderer status, and sanitized error codes, not raw images or bearer tokens.
- Phase 1 recipe JSON is edit metadata only. It should not contain raw pixel dumps, hidden source-image data, provider keys, or executable filter code.
- The renderer must preserve faces, products, text, and real-world details unless the user explicitly chooses a later generative adapter.
- P3.27 `local-renderer-backend-capability-manifest` is manifest-only planning.
  It must not import or execute future Core Image/ImageMagick/OpenCV/libvips
  backends, install dependencies, persist assets, include raw image bytes, or
  change phone-facing capabilities.

## Credentials

- Mobile bearer tokens are scoped to Mobile Bridge access and must be revocable.
- Agent Pocket stores saved runtime connection credentials only in iOS Keychain via `StoredConnection`; provider credentials are never stored on the phone.
- If the runtime revokes a mobile token, restore-on-launch clears the saved Keychain entry and requires pairing again.
- Provider API keys remain on the runtime side.
- The iOS app must never contain OpenAI, ComfyUI, cloud, tunnel, or model-provider credentials.
- A runtime-configured multimodal model key can power the Local Recipe path from the Mac side; it does not need to be copied to iPhone.

Production pairing state is runtime-owned. The runtime may keep pairing sessions, device labels, token suffixes, issue times, expiry times, and revocation times so the Mac user can revoke a phone. The phone stores only the selected endpoint and mobile token in Keychain. Runtime settings and `local-tls-readiness` may show TLS trust state, certificate label, non-secret certificate refs, public-key fingerprint, expiry, trust store ref, and renewal procedure ref to the Mac/runtime user, but they must not expose private key paths, raw bearer tokens, auth files, provider credentials, SQLite paths, or task logs to phone-bound endpoints.

P3.10a keeps the same ownership boundary while adding real local HTTPS serving.
The runtime may read host-owned certificate chain and private key files only to
wrap the local Mobile Bridge socket after explicit runtime-side launch
configuration. Kaka must not generate certificates, install trust, modify
Keychain, manage renewal, or copy certificate/private-key paths into phone-bound
responses.

## Runtime-Owned Persistence

The production persistence boundary stays on the Mac/runtime side. The Runtime Kit persistence slice adds a local SQLite store for Recall records, Recall retrieval-index receipts, runtime task records, and task events. The iPhone does not store model-provider keys, production Recall data, production task history, or the runtime SQLite file path.

Production Recall retrieval packaging materials also stay on the Mac/runtime
side. P3.26 `recall-retrieval-material-intake` reviews a local host/runtime
manifest and blocks missing or secret-like refs without echoing their values. It
does not fetch refs, validate signatures, invoke providers, expose provider
endpoints or keys to the iPhone, return raw embeddings/index rows/provider
responses, or add retrieval internals to Recall export.

`--runtime-store-path` is a runtime launcher/server option used by the development bridge. It must not become a Mobile Bridge request field, and it should later be surfaced as a visible Hermes/OpenClaw runtime setting rather than a hidden phone-side choice.

Context Snapshot content remains task-scoped input. It must not be written into the runtime persistence store or Recall export unless the user explicitly chooses a Recall action such as `Remember`.

Export and deletion are explicit user-triggered actions. Export should return only the Recall metadata, summaries, timestamps, and provenance retained by the runtime. Deletion receipts should identify content and retrieval-index records removed by the runtime where the runtime controls those records.

Semantic Recall search is also runtime-owned. Kaka may request `POST /mobile/v1/recall/search` and display ranked Recall items plus a user-safe match reason. Runtime Kit now supports deterministic local scoring, an explicit provider-backed retrieval adapter boundary, and a read-only production retrieval packaging readiness artifact. Raw embeddings, retrieval-index rows, provider endpoints, hidden prompts, provider keys, bearer tokens, SQLite paths, raw provider responses, and unrelated task logs must not be returned to the phone or included in Recall export. Runtime-side provider candidate requests must send only query, limit, sanitized Recall item fields, and allowlisted provenance.

`GET /mobile/v1/runtime/settings` may show whether the local Recall/task store and semantic Recall are enabled, and whether retrieval is `local_deterministic` or `provider_backed`, but it is status/control metadata from the runtime. The iPhone must not become the owner of persistence settings, provider endpoints, provider keys, or the SQLite path.

Runtime Kit `settings-preview` and native Hermes/OpenClaw settings may show local store paths and provider endpoints to the Mac/runtime user because they are runtime-side controls. Those values must not be copied into phone-bound `/mobile/v1/runtime/settings`, Recall export, or search responses.

Hermes/OpenClaw Plugin or Skill installation details are also runtime-side
controls. Package manifests, private adapter command paths, install/update
channels, signature refs, conformance reports, raw logs, process IDs, Codex
developer plugin/skill source roots, and user-home Codex install paths must not
be exposed to Kaka iPhone. The phone should only see `/mobile/v1` pairing,
coarse connection status, and user-safe runtime settings summaries.
The phone must not receive, cache, display, or invoke
`hermes-kaka-host-api` / `openclaw-kaka-host-api`; those names, if present, are
host-extension-internal implementation details.
If future work creates Codex plugin/skill automation, that automation remains
host-team developer tooling. Generated source roots, marketplace metadata,
developer install paths, validation receipts, and release-gate evidence stay on
the host/runtime side and must not become phone-visible onboarding, runtime
settings payloads, Recall export data, search responses, or task logs.

## Pocket Agents Inputs

Future Pocket Agents inputs must follow explicit-user-intent rules:

- **Share to Kaka**: content arrives because the user selected Kaka from the system share sheet or action sheet.
- **Paste**: pasteboard content is read only after a visible paste or submit action. Kaka must not poll the general pasteboard in the background. P3.36b Explicit Paste-to-Inbox Courier reads text once from a user-triggered Inbox Paste control, creates a pending text or http/https link item, and still requires visible `Send`; it does not auto-submit, auto-Recall, fetch URLs, import binary/file pasteboard payloads, or add a new Mobile Bridge endpoint.
- **Voice**: B.1 uses real push-to-talk with on-device transcription. Kaka records only while the user explicitly presses the visible control, transcribes with iOS Speech, lets the user edit the transcript, and sends text through Mobile Bridge. A returned summary may be read aloud by the phone. P3.30 Voice-to-Inbox Draft reuses this same boundary: the reviewed transcript becomes a pending text Inbox item, and the user must still tap `Send`. P3.32 Inbox Voice Instruction also reuses it: the reviewed transcript is saved into an existing `KakaInboxItem.note` and is submitted only after visible Inbox `Send` as text. P3.33 Inbox Instruction Polish keeps the same boundary while adding local edit, clear, and send-preview UI before `Send`. P3.34 Inbox Instruction Templates adds deterministic local chips that write template text into `KakaInboxItem.note`; chip taps do not submit runtime work. P3.36a Inbox Voice Capture Context Copy clarifies local save copy for drafts and instructions without changing this behavior. Raw microphone audio is not uploaded, and always-on background listening, hidden transcription, automatic runtime submission, and automatic Recall writes are out of scope.
- **Result Review Recall provenance**: P3.37 keeps completed Inbox result provenance phone-safe and visible. The result banner may show source surface and whether Context Snapshot was selected; explicit Recall actions can include the existing runtime task ID and source Inbox item ID. This does not remember anything automatically, expose raw Inbox payloads, add a Recall endpoint, or move Recall storage away from the runtime.
- **Screenshot Q&A**: screenshots are treated as sensitive because they may include private messages, account data, or other apps' content.
- **Files and PDFs**: file contents should be uploaded only after the user sees what is being submitted. P3.38 Explicit Files-to-Inbox Import keeps file access user-selected and one-shot: a visible Files picker can copy one supported PDF or image into the Inbox payload store, but it does not scan folders, upload immediately, submit runtime work, write Recall, or add a Mobile Bridge endpoint before the user taps visible `Send`.
- **Pending Inbox discard**: P3.39 lets the user discard one pending Inbox item before `Send`; P3.40 gates that local action behind a visible confirmation dialog. Confirm removes only Kaka's local Inbox record and any Kaka-copied App Group payload through the existing store removal path. Cancel or dismissal leaves the pending item and payload untouched. This is not Recall deletion, runtime task cancellation, retention purge, source-file deletion from Files/Photos, or a Mobile Bridge request.
- **Inbox action feedback**: P3.41 makes existing local Inbox failure/progress state visible in the main Inbox. It does not retry failed work, cancel runtime tasks, submit automatically, write or delete Recall, add a Mobile Bridge request, or expose provider/runtime secrets.
- **Pending Inbox review details**: P3.42 lets the user expand local read-only details for a pending Inbox item before `Send`. It displays only existing local metadata and bounded text/URL excerpts, such as source, type, file name/type, copied-payload state, saved instruction, route, locale/profile when present, and Context Snapshot inclusion state. It must not display raw `relativeFilePath`, read payload bytes, inspect source files, fetch URLs, parse PDFs/OCR, summarize content, submit runtime work, write Recall, expose raw payload dumps, scan folders, delete source files, or add Mobile Bridge requests.

Shared or pasted content should default to task-scoped processing. It should not become long-term memory unless the user chooses `Remember`.

## Context Snapshot

A Context Snapshot is a user-approved packet of situational information sent with one task. It helps the runtime make better decisions, such as shortening replies while the user is moving, delaying long work on low battery, or labeling a receipt with the time and rough place where it was captured.

Allowed fields for an MVP:

- timestamp, locale, and timezone
- source surface, such as camera, share sheet, paste, or voice
- coarse location label when permission is granted
- location precision status, such as coarse, precise, none, or unknown
- one-shot current motion state, such as stationary, walking, running, driving, or unknown
- network and battery state
- optional next-30-minute calendar availability, not full calendar contents by default
- current Kaka conversation context

Rules:

- Context Snapshot defaults to task-scoped use.
- The app should show a compact preview of what will be sent.
- The preview should use readable labels for denied, not-requested, unavailable,
  and coarse optional fields while keeping the underlying Mobile Bridge payload
  values stable for compatibility.
- A snapshot preview should be refreshed per task; a previously previewed snapshot must not be reused for a later task.
- If the user enables Context Snapshot and collection is still preparing, the
  UI should not silently submit without that task's preview.
- Precise location, calendar details, contacts, and health data require separate explicit decisions.
- A snapshot must not be written to Recall unless the user explicitly chooses to remember it.
- Denied permissions must not block core camera or share intake.
- Network context is a one-shot coarse path status such as wifi, cellular, offline, constrained, unknown, or unavailable. It must not include SSID, BSSID, carrier, IP address, hostnames, interface names, or continuous monitoring.
- Motion context is a one-shot current label. It must not request permission implicitly, run in the background, or send motion history, accelerometer samples, routes, speed, confidence, or continuous tracking data.
- Calendar context must stay availability-only for the next 30 minutes. It must not request access implicitly or send event titles, attendees, notes, event locations, calendar identifiers, descriptions, or event bodies.
- Runtime/mock bridge handling should allowlist Context Snapshot fields so unknown keys, nested containers, coordinates, network identifiers, and calendar details are not stored or echoed.

## Voice

Voice interaction should be visible and controllable:

- The UI should show when Kaka is listening, transcribing, sending, or speaking.
- The transcript should remain visible before high-impact actions.
- Voice-to-Inbox should create only a pending Inbox item from the reviewed transcript; creating the draft must not submit to runtime or save to Recall.
- Inbox Voice Instruction should update only the selected existing Inbox item's
  note from the reviewed transcript; saving the note must not submit to runtime,
  save to Recall, record in the background, or upload microphone audio.
- Inbox Instruction Polish may label, edit, clear, and preview a saved note
- Inbox Instruction Templates may write deterministic local template text into a
  saved note
  before `Send`; those controls must remain local UI/store updates and must not
  trigger runtime work.
- Short spoken replies are acceptable for convenience, but durable results should also be shown as text or cards.
- Ambiguous speech must not trigger destructive, paid, public, or persistent actions without confirmation.

## System Surfaces

App Intents, Shortcuts, Siri, Spotlight, widgets, Action Button flows, and Live Activity must stay thinner than the app. They can help the user get back to visible Kaka surfaces, but they must not become hidden task controllers.

The E.1 App Intents surface is allowlisted to opening Inbox, showing Tasks, reviewing an Inbox item, or reviewing a runtime task. These intents write a small app handoff and open Kaka. They do not submit content, approve tasks, cancel tasks, remember Recall items, collect Context Snapshot data, read pasteboard content, start microphone/camera capture, configure providers, or change runtime settings in the background.

Action Button support reuses Kaka's foreground App Intent handoff and only opens visible Inbox or Tasks review surfaces. It does not submit inbox items, approve or cancel runtime tasks, remember Recall items, collect Context Snapshot data, start microphone or camera capture, configure providers, or change runtime settings in the background.

Inbox pending discard remains a visible, confirmed in-app row action only. App Intents, Shortcuts, widgets, Action Button, and Live Activity must not discard Inbox items in the background.

Live Activity payloads are also allowlisted. They may contain only task ID, a client-generated generic title, phase, and whether approval is needed. They must not copy runtime-controlled task titles and must not contain bearer tokens, endpoint URLs, provider keys, hidden prompts, task logs, approval notes, asset bytes, transcripts, Context Snapshot fields, Recall content, embeddings, retrieval-index rows, provider responses, or runtime store paths.

The WidgetKit Live Activity presentation consumes only that phone-safe projection for Lock Screen and Dynamic Island UI. It does not expand the Mobile Bridge API, does not show runtime task messages or progress, and does not approve or cancel tasks outside the visible Kaka app.

## Recall

Recall is long-term memory and must be treated differently from normal task processing.

Required controls:

- `Remember`: save an item and its derived summary/index to the runtime-side memory store.
- `Use Once`: process the item for the current task without long-term storage.
- `Forget`: delete the original artifact, extracted text, summary, and retrieval index entries where the runtime controls them.

Current Recall exposes `POST /mobile/v1/recall/actions`, queryable `GET /mobile/v1/recall/items`, semantic `POST /mobile/v1/recall/search`, `GET /mobile/v1/recall/export`, and `DELETE /mobile/v1/recall/items/{item_id}` with deletion receipts for runtime-owned retrieval indexes. P3.20 labels Recall export as `kaka.recall_export.v1` and attaches an artifact policy proving it is JSON-first, user-readable, and not a database dump. `remember` and `forget` require visible confirmation in the phone UI before submission; `use_once` succeeds without creating a persisted item.

Recall records should keep provenance so the user can understand why an item exists, where it came from, and which task created it. The iPhone offers browsing, search, delete, and export entry points, while the runtime owns storage and index deletion. Searching Recall is user-initiated from Kaka and should not trigger background profiling; export must be explicit, visible, and limited to user-owned Recall item IDs, summaries, created timestamps, and provenance. Export must not include embeddings, retrieval-index rows, provider endpoints or keys, bearer/mobile tokens, SQLite paths, hidden prompts, raw provider responses, unrelated task logs, raw asset bytes, or unconfirmed Context Snapshot content. Production persistence remains the Runtime Kit/Hermes/OpenClaw side of the boundary, not an iPhone database.

P3.9 retention policy controls keep that same ownership model. The runtime host
may show and configure input asset, output asset, and task-history retention
windows in the Hermes/OpenClaw settings shell, and the phone may read those
windows as runtime status. The phone must not write retention policy, and P3.9
does not imply automatic cleanup or SQLite migrations. P3.14 adds explicit
runtime-side `retention-purge` receipts for dry-run/apply cleanup of old
terminal task history. P3.22 extends that explicit receipt to timestamped mock
bridge in-memory input/output assets; untimestamped assets stay preserved as
untracked. P3.24 adds Runtime Kit SQLite-backed input/output asset storage when
a runtime store is configured, and those persisted assets can be deleted only by
explicit runtime-side purge apply. The phone cannot trigger the purge, retention
receipts must not expose store paths, tokens, private key paths, provider
endpoints, raw logs, embeddings, SQLite rows, task result variants, or raw asset
bytes, and Recall remains controlled only by explicit `Remember`, `Forget`,
export, or delete actions.

P3.25 persists completed photo-edit result detail in runtime task metadata so
store-backed task detail remains useful after a bridge restart. That metadata is
a phone-safe manifest only: variant ID, label, asset ID, explanation, and
allowlisted structured recipe/status fields. Raw input/output bytes remain in
`runtime_assets`; `download_url` is rebuilt from `asset_id` when returning task
detail and is not stored as durable state. Task lists stay summary-only, and
completed task events expose only `variant_count`. They must not leak asset IDs,
download URLs, SQLite paths, provider endpoints, tokens, hidden prompts, raw
provider responses, private host data, or raw bytes.

## Network Rules

- Remote endpoints require HTTPS.
- Local `http://127.0.0.1`, `http://localhost`, `.local`, private LAN, and Tailscale CGNAT HTTP endpoints are development-only exceptions.
- Tailscale or another private HTTPS-capable path is preferred for personal remote use.

## User Controls

- Pairing codes are one-time and short-lived in production.
- The connected workspace exposes a change-runtime control so users can clear the saved Keychain connection before pairing another runtime.
- Photo library permission is requested only when saving a result.
- Denied Photos permission must show a recovery path instead of blocking review or share.
- Sharing uses the iOS system share sheet in Phase 1. Direct platform posting to WeChat, WeChat Moments, Xiaohongshu, X, or other networks requires a later explicit SDK/API integration and must not be implied by the bridge.
