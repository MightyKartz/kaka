# Agent Pocket Troubleshooting

## Cannot Connect To Runtime

Check the bridge health endpoint:

```bash
curl http://127.0.0.1:8765/mobile/v1/health
```

If testing from a physical iPhone, bind the mock bridge to `0.0.0.0`, use the Mac LAN IP, and confirm the phone and Mac are on the same network:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server \
  --host 0.0.0.0 \
  --port 8765 \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)"
```

If Agent Pocket shows **Certificate Problem**, the endpoint is reachable but iOS rejected the TLS setup. Use a trusted HTTPS certificate, Tailscale HTTPS/MagicDNS, or a local-development HTTP URL that the app explicitly allows.

If **Discover Local Runtime** asks for Local Network access, tap **Open Settings** in Agent Pocket, enable **Local Network**, return to the app, then try discovery again.

If **Discover Local Runtime** finds nothing, confirm macOS allows incoming local network traffic for Python, the iPhone is on the same Wi-Fi/VPN segment, and the printed Bonjour endpoint uses the Mac LAN IP rather than `127.0.0.1`.

## Unauthorized

Use the development token for mock bridge requests:

```text
Authorization: Bearer dev-mobile-token
```

For a real compatible runtime such as Hermes or OpenClaw, revoke and regenerate the mobile token if the phone was re-paired or the token store was reset.

## Pairing Code Fails

- `pairing_expired`: generate a fresh QR payload.
- `pairing_already_used`: generate a new code; codes are single-use.
- `remoteEndpointRequiresHTTPS`: use HTTPS for remote endpoints, or a local development URL only while testing.

## Photo Selection Returns To Main Screen

This usually means the app selected and prepared the asset but the connected capture screen did not enter the ready/send state.

Check locally with the Simulator ready-state smoke:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-capture-ready.png \
  --receipt-file docs/qa-receipts/simulator-capture-ready-latest.json
```

Expected receipt fields:

- `state: ready`
- `has_prepared_upload: true`
- `send_to_runtime_enabled: true` or the current app's equivalent send-action flag

If this passes in Simulator but fails on a physical iPhone, inspect Photos permission, HEIC/JPEG preprocessing, and the connected capture view state transition after the Photos picker returns.

## Upload Fails

- `unsupported_media_type`: verify the app sends `image/jpeg`, `image/png`, or `image/heic`.
- `upload_too_large`: reduce image size or check the bridge `max_upload_mb` capability.
- `invalid image`: confirm preprocessing can decode the selected asset.
- Runtime token was rejected: use the change-runtime flow and pair again.
- `Photo Pack missing`: install or enable the Photo Pack in the selected runtime, then reconnect.

## Local Recipe Task Never Completes

Use polling as the fallback if SSE fails:

```bash
curl -H "Authorization: Bearer dev-mobile-token" http://127.0.0.1:8765/mobile/v1/tasks/<task_id>
```

For the current Phase 1 path, a stuck task is usually one of these:

- `recipe_local` adapter is not installed or not selected.
- The runtime cannot call its configured multimodal vision model.
- The model returned JSON that fails the strict `PhotoEditRecipe` schema.
- The renderer failed to decode the source or write the output variants.

The phone should show sanitized recovery text only. Model/provider credentials, raw prompts, and local file paths should stay in runtime/Mac logs.

## Result Looks Too Similar

Phase 1 should be realistic, but the edit must be obvious at a glance. If before/after looks identical:

- Increase bounded defaults for each style before model-specific tuning.
- Always return two variants: `Master` and `Social`.
- Make `Master` visibly more professional through crop/reframe, exposure, white balance, local clarity, subject separation, and conservative sharpen/denoise.
- Make `Social` more visibly different through 4:5 or 1:1 crop, contrast, vibrance, local clarity, and subject/background separation.
- Use optional upscale only when the selected crop would make the output too small.
- Add renderer QA that measures basic image difference so a no-op output cannot pass.

Do not solve this by switching to generative image replacement first. The product direction is parameterized local polish, preserving faces, products, text, and real details.

## Save Fails On iPhone

If Photos permission is denied, tap **Open Settings** from the result screen and allow Photos access for Agent Pocket. The app should still allow reviewing and sharing the downloaded result.

## Share Is Disabled

Download the selected variant first. Save and Share stay disabled until Agent Pocket has the edited bytes locally.

Phase 1 sharing should use the iOS system share sheet with the selected image and generated caption. Direct WeChat, WeChat Moments, Xiaohongshu, and X SDK/API posting is a later enhancement.

## Runtime Has An API Key, But Photos Still Do Not Run

That key must be visible to the Mac-side runtime path that produces `PhotoEditRecipe`. The iPhone does not need the key and should not store it.

For the Local Recipe path, the selected runtime must be able to call whatever multimodal vision model the user's agent is configured to use. It does not need to be an OpenAI Images API key, because Phase 1 does not call an image generation/editing endpoint.

Expected current proof for the fixture/local renderer path:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight \
  --photo-provider recipe_local \
  --photo-pack-root photo-pack \
  --hermes-profile dev-lead \
  --receipt-file docs/qa-receipts/recipe-provider-preflight-latest.json
```

## Legacy OpenAI Images Key Missing

If an old receipt says `OPENAI_API_KEY` is missing, treat it as legacy OpenAI Images adapter evidence. It does not block the current Local Recipe Phase 1 unless the optional generative adapter is explicitly re-enabled.
