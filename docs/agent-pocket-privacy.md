# Agent Pocket Privacy

Agent Pocket is a thin client. The phone owns capture, upload, progress, review, save, and share. The user-owned compatible runtime, such as Hermes, OpenClaw, or a Mobile Bridge sidecar, owns model/provider credentials, crop planning, recipe generation, local rendering, optional upscale, workflow execution, memory, retention, and approvals.

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
