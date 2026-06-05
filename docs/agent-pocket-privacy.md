# Agent Pocket Privacy

Agent Pocket is a thin client. The phone owns capture, upload, progress, review, save, and share. The user-owned compatible runtime, such as Hermes, OpenClaw, or a Mobile Bridge sidecar, owns model/provider credentials, crop planning, recipe generation, local rendering, optional upscale, workflow execution, memory, retention, and approvals.

The broader Pocket Agents direction keeps the same boundary. The phone may later collect share-sheet items, screenshots, pasted text, voice input, and permissioned context snapshots, but those inputs must remain user-visible and task-scoped unless the user explicitly saves them to Recall.

## Photo Handling

- The app preprocesses uploads with `ImagePreprocessor`, normalizing orientation and re-encoding JPEG without copying source metadata by default.
- Sensitive EXIF and GPS fields should not be sent to the bridge.
- The bridge stores input assets and output assets according to its advertised retention window.
- Task logs should use task IDs, asset IDs, status, recipe IDs, renderer status, and sanitized error codes, not raw images or bearer tokens.
- Phase 1 recipe JSON is edit metadata only. It should not contain raw pixel dumps, hidden source-image data, provider keys, or executable filter code.
- The renderer must preserve faces, products, text, and real-world details unless the user explicitly chooses a later generative adapter.

## Credentials

- Mobile bearer tokens are scoped to Mobile Bridge access and must be revocable.
- Agent Pocket stores saved runtime connection credentials only in iOS Keychain via `StoredConnection`; provider credentials are never stored on the phone.
- If the runtime revokes a mobile token, restore-on-launch clears the saved Keychain entry and requires pairing again.
- Provider API keys remain on the runtime side.
- The iOS app must never contain OpenAI, ComfyUI, cloud, tunnel, or model-provider credentials.
- A runtime-configured multimodal model key can power the Local Recipe path from the Mac side; it does not need to be copied to iPhone.

## Pocket Agents Inputs

Future Pocket Agents inputs must follow explicit-user-intent rules:

- **Share to Kaka**: content arrives because the user selected Kaka from the system share sheet or action sheet.
- **Paste**: pasteboard content is read only after a visible paste or submit action. Kaka must not poll the general pasteboard in the background.
- **Voice**: push-to-talk or visible recording controls are allowed. Always-on background listening is out of scope.
- **Screenshot Q&A**: screenshots are treated as sensitive because they may include private messages, account data, or other apps' content.
- **Files and PDFs**: file contents should be uploaded only after the user sees what is being submitted.

Shared or pasted content should default to task-scoped processing. It should not become long-term memory unless the user chooses `Remember`.

## Context Snapshot

A Context Snapshot is a user-approved packet of situational information sent with one task. It helps the runtime make better decisions, such as shortening replies while the user is moving, delaying long work on low battery, or labeling a receipt with the time and rough place where it was captured.

Allowed fields for an MVP:

- timestamp, locale, and timezone
- source surface, such as camera, share sheet, paste, or voice
- coarse location label when permission is granted
- motion state, such as stationary, walking, driving, or unknown
- network and battery state
- optional calendar availability, not full calendar contents by default
- current Kaka conversation context

Rules:

- Context Snapshot defaults to task-scoped use.
- The app should show a compact preview of what will be sent.
- Precise location, calendar details, contacts, and health data require separate explicit decisions.
- A snapshot must not be written to Recall unless the user explicitly chooses to remember it.
- Denied permissions must not block core camera or share intake.

## Voice

Voice interaction should be visible and controllable:

- The UI should show when Kaka is listening, transcribing, sending, or speaking.
- The transcript should remain visible before high-impact actions.
- Short spoken replies are acceptable for convenience, but durable results should also be shown as text or cards.
- Ambiguous speech must not trigger destructive, paid, public, or persistent actions without confirmation.

## Recall

Recall is long-term memory and must be treated differently from normal task processing.

Required controls:

- `Remember`: save an item and its derived summary/index to the runtime-side memory store.
- `Use Once`: process the item for the current task without long-term storage.
- `Forget`: delete the original artifact, extracted text, summary, and retrieval index entries where the runtime controls them.

Current Recall D.0 exposes `POST /mobile/v1/recall/actions`, `GET /mobile/v1/recall/items`, and `DELETE /mobile/v1/recall/items/{item_id}`. `remember` and `forget` require visible confirmation in the phone UI before submission; `use_once` succeeds without creating a persisted item. Search/retrieval, export, and retrieval-index deletion remain future Recall work.

Recall records should keep provenance so the user can understand why an item exists, where it came from, and which task created it. The iPhone should offer browsing, search, delete, and export entry points, while the runtime owns storage and index deletion.

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
