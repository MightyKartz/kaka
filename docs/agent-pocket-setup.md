# Agent Pocket Setup

This guide is for Phase 1 development and QA. Ordinary users should not run
`runtime-kit`, `mock_bridge`, `photo-pack/adapters`, `curl`, or manual LAN
endpoint commands as their normal setup path.

The intended ordinary-user flow is: install the host-native Hermes Plugin or
OpenClaw Skill/sidecar, open the host **Kaka Mobile Bridge** panel, explicitly
enable the bridge, pair by QR or Bonjour, and use Kaka iPhone through
`/mobile/v1`. Manual endpoints, LAN IPs, Runtime Kit commands, and shell
diagnostics below are developer, host-engineer, or external-pilot
troubleshooting paths only.

## Current Phase 1 Direction

Phase 1 uses **Master Shot Agent + Local Recipe Photo Flow**:

1. iPhone connects to a user-owned local agent runtime/Mobile Bridge endpoint.
2. iPhone uploads the original photo, selected scene pack, and optional instruction only.
3. The runtime uses its configured multimodal vision model to produce a strict `PhotoEditRecipe` JSON object with crop, edit, optional upscale, and preservation rules.
4. The Mac-side runtime validates/clamps the recipe and renders `Master` plus `Social` locally.
5. iPhone downloads the variants, compares Original / Master / Social, saves, or opens the iOS system share sheet with image plus caption.

The old OpenAI Images adapter is a legacy optional path. It is not required for the first shippable Kaka/Agent Pocket build, and missing `OPENAI_API_KEY` no longer blocks the Local Recipe milestone.

## Local Mock Bridge

Run the mock Mobile Bridge:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server --host 127.0.0.1 --port 8765
```

Verify from the Mac:

```bash
curl http://127.0.0.1:8765/mobile/v1/health
curl http://127.0.0.1:8765/mobile/v1/pairing/dev
open http://127.0.0.1:8765/mobile/v1/pairing/dev.html
curl -H "Authorization: Bearer dev-mobile-token" http://127.0.0.1:8765/mobile/v1/capabilities
curl -H "Authorization: Bearer dev-mobile-token" http://127.0.0.1:8765/mobile/v1/qa/status
```

For iPhone or another device on the same LAN, bind to all interfaces:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server --host 0.0.0.0 --port 8765
ipconfig getifaddr en0
```

Use `http://<mac-lan-ip>:8765` only for local development. Remote endpoints must use HTTPS.

To make **Discover Local Runtime** work during LAN QA, advertise with Bonjour:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server \
  --host 0.0.0.0 \
  --port 8765 \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)"
```

The mock bridge publishes `_agent-pocket._tcp` with a runtime identifier such as `hermes` or `openclaw` and the development `pair_dev` pairing code. If the advertised code was already used, Agent Pocket refreshes `/mobile/v1/pairing/dev` and retries with the current local QA code.

## 使用真实 Claude API 运行

The mock bridge can be started as a minimal real runtime for vision and intake by explicitly opting in to the Anthropic provider. The default remains deterministic fake behavior for CI and local tests.

Install the official SDK in the runtime Python environment:

```bash
python3 -m pip install anthropic
```

Set the API key only in the runtime process environment:

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
export KAKA_MODEL=claude-opus-4-8
```

`KAKA_MODEL` is optional and defaults to `claude-opus-4-8`; the provider uses `max_tokens=16000` by default.

Start the bridge with the explicit provider flag:

```bash
PYTHONPATH=mock_bridge:runtime-kit python3 -m agent_pocket_mock_bridge.server \
  --host 127.0.0.1 \
  --port 8765 \
  --provider anthropic
```

For LAN testing, use the same `--provider anthropic` flag with the existing `--host 0.0.0.0`, `--bonjour`, and `--bonjour-host` options. If `ANTHROPIC_API_KEY` is missing, startup fails with a configuration error instead of falling back to fake responses.

The key stays on the Mac/runtime side. The iPhone continues to call only `/mobile/v1`, and Mobile Bridge requests, responses, pairing payloads, QA status, and task results must never contain `ANTHROPIC_API_KEY` or raw provider responses.

## 使用本机 Hermes 运行

The mock bridge can also use a local Hermes API server as a minimal real runtime for image intake, vision skills, and universal intake. This is explicit opt-in only; the default provider remains deterministic fake behavior.

Enable the Hermes API server yourself before starting Kaka. See [Hermes Local Integration Notes](hermes-local-integration-notes.md) for the read-only survey and the Hermes-side settings. Kaka does not modify Hermes config or start/restart Hermes for you.

Set only runtime-side environment variables:

```bash
export KAKA_HERMES_BASE_URL=http://127.0.0.1:8642/v1
export KAKA_HERMES_API_KEY=<redacted>
export KAKA_HERMES_MODEL=jiqimao
export KAKA_HERMES_TIMEOUT_SECONDS=60
```

`KAKA_HERMES_BASE_URL` defaults to `http://127.0.0.1:8642/v1`. `KAKA_HERMES_MODEL` is optional; if unset, startup probes `GET /v1/models` and uses the returned model id. `KAKA_HERMES_TIMEOUT_SECONDS` is optional.

Start the bridge with the explicit provider flag:

```bash
PYTHONPATH=mock_bridge:runtime-kit python3 -m agent_pocket_mock_bridge.server \
  --host 127.0.0.1 \
  --port 8765 \
  --provider hermes
```

For LAN testing, combine `--provider hermes` with the same `--host 0.0.0.0`, `--bonjour`, and `--bonjour-host` options used by the local mock bridge. If `KAKA_HERMES_API_KEY` is missing, or if the Hermes `/health` or `/v1/models` startup probes fail, startup fails instead of falling back to fake responses.

The key stays on the Mac/runtime side. The iPhone continues to call only `/mobile/v1`; pairing payloads, capabilities, task results, QA status, logs, and Recall data must never include `KAKA_HERMES_API_KEY`.

Do not point Kaka at the Hermes dashboard or raw proxy. `127.0.0.1:9120` is the web dashboard, not the agent API. `127.0.0.1:8645` is the `hermes proxy` raw upstream proxy, not the Kaka provider target.

## First iPhone Connection

The first-run connection flow is user-initiated:

1. Start Hermes, OpenClaw, or the compatible Mobile Bridge on the Mac. For normal users this should be a visible **Kaka Mobile Bridge** enable/start control inside the runtime, not a pasted terminal command.
2. Open Kaka on iPhone.
3. Tap **Connect** to begin Bonjour discovery. This is when iOS may ask for Local Network permission.
4. If Kaka finds one or more local runtimes, confirm the displayed Mac card to exchange the one-time pairing code for a mobile token.
5. If discovery finds nothing, scan the pairing QR shown by the Mac bridge.
6. Use manual endpoint entry only as a troubleshooting fallback.

The app no longer starts Bonjour discovery automatically on first launch. On launch it only tries to restore a previously saved Keychain connection, then waits for the user to start discovery or scan a QR code.

## Runtime Kit Development Path

The repository now includes a `runtime-kit/` scaffold for the intended Hermes/OpenClaw install path. It wraps the current mock bridge with an explicit-start launcher and defaults to the `recipe_local` Phase 1 provider.

Run local checks:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start --dry-run
```

Simulator-only loopback start:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start
```

Physical iPhone LAN start for development:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead
```

### 真机 + 真实模型

For daily iPhone testing against a real Claude-backed runtime, keep
`ANTHROPIC_API_KEY` exported only in the Mac/runtime environment, then start
through Runtime Kit so the same LAN pairing and SQLite persistence path is used:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime-store-path "$HOME/.kaka/kaka-runtime.sqlite3" \
  --provider anthropic \
  --runtime hermes
```

This command never passes the key as an argument. Runtime Kit only reports the
environment variable name and whether it is set; the key value stays outside
preview JSON, logs, pairing payloads, `/mobile/v1` responses, and SQLite.

These commands are developer diagnostics. The product goal is to hide them behind a Hermes/OpenClaw **Kaka Mobile Bridge** toggle with **Show QR**, **Stop**, and token revocation controls. Install must not auto-start a bridge; LAN and Bonjour exposure must be explicit.

## Development Pairing Payload

The mock bridge serves the current development payload from:

```bash
curl http://<mac-lan-ip>:8765/mobile/v1/pairing/dev
open http://<mac-lan-ip>:8765/mobile/v1/pairing/dev.html
```

Use the LAN IP instead of `127.0.0.1` when testing from a physical phone. The iOS target allows private LAN and Tailscale CGNAT HTTP only for development pairing and mock-bridge QA; production or public endpoints must use HTTPS.

During physical iPhone QA, use the local-only status endpoint to prove which bridge actions happened:

```bash
curl -H "Authorization: Bearer dev-mobile-token" \
  http://<mac-lan-ip>:8765/mobile/v1/qa/status
```

## Local Recipe QA

The current Phase 1 provider is `recipe_local`. In fixture/local renderer mode it accepts the original photo, scene pack, instruction, target crop aspects, and `return_variants`, then:

1. build a deterministic fixture recipe for tests, or call a compatible local `runtime_vision` recipe endpoint that owns the runtime-configured multimodal model and credentials;
2. validate and clamp the recipe;
3. render `Master` and `Social` locally with visible crop/tone/local-polish differences;
4. apply optional upscale only when the selected crop is below the target output size;
5. write a manifest with variant paths, crop metadata, recipe summary, renderer metadata, QA difference metrics, and share captions.

Current local recipe adapter command:

```bash
python3 photo-pack/adapters/recipe_local.py \
  --input /path/to/photo.jpg \
  --output-dir /tmp/agent-pocket-recipe \
  --style natural_enhance \
  --instruction "Keep it realistic but make the professional edit obvious." \
  --return-variants 2
```

Runtime-vision recipe mode, for Hermes/OpenClaw/a sidecar endpoint that returns strict `PhotoEditRecipe` JSON:

```bash
python3 photo-pack/adapters/recipe_local.py \
  --input /path/to/photo.jpg \
  --output-dir /tmp/agent-pocket-recipe \
  --style natural_enhance \
  --instruction "Keep it realistic but make the professional edit obvious." \
  --return-variants 2 \
  --recipe-mode runtime_vision \
  --runtime-recipe-endpoint http://127.0.0.1:8791/mobile/v1/recipes/photo-edit
```

This runtime-vision endpoint is Mac/runtime-side only. It can use the user's configured model and API key, but the iPhone still sends only photo/task data to the Mobile Bridge.

Current provider preflight:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight \
  --photo-provider recipe_local \
  --photo-pack-root photo-pack \
  --hermes-profile dev-lead \
  --receipt-file docs/qa-receipts/recipe-provider-preflight-latest.json
```

`--hermes-profile` is the current mock/Hermes helper flag. OpenClaw or another compatible runtime should expose the same Mobile Bridge behavior through its own profile/runtime selector or sidecar configuration.

Real iPhone local-recipe run once the simulator smoke is proven:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan \
  --host <mac-lan-ip> \
  --device-id <coredevice-id> \
  --photo-provider recipe_local \
  --hermes-profile dev-lead \
  --receipt-file docs/qa-receipts/local-recipe-photo-flow.json
```

Verify the saved receipt:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt \
  --file docs/qa-receipts/local-recipe-photo-flow.json \
  --phase photo-flow \
  --photo-provider recipe_local
```

Use `--photo-provider script` only for legacy bridge plumbing and UI state checks. It cannot prove the Master Shot product promise because it does not crop, enhance, rank, or upscale.

## Simulator QA

Use these checks when the physical iPhone is unavailable:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight \
  --receipt-file docs/qa-receipts/simulator-ui-test-preflight-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-suite \
  --suite-receipt-file docs/qa-receipts/simulator-suite-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-connection-smoke \
  --host 127.0.0.1 \
  --port 8766 \
  --receipt-file docs/qa-receipts/simulator-connection-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-discovery-refresh-smoke \
  --bundle-id com.kaka.AgentPocket \
  --receipt-file docs/qa-receipts/simulator-discovery-refresh-latest.json \
  --screenshot-file /tmp/agent-pocket-simulator-discovery-refresh.png

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library \
  --image-file /tmp/agent-pocket-simulator-library-fixture.png

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-picker-ui-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-picker-ui-smoke.png

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-capture-ready.png \
  --receipt-file docs/qa-receipts/simulator-capture-ready-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-capture-completed.png \
  --receipt-file docs/qa-receipts/simulator-capture-completed-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-result-gallery.png \
  --receipt-file docs/qa-receipts/simulator-result-gallery-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-downloaded-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-result-gallery-downloaded.png \
  --receipt-file docs/qa-receipts/simulator-result-gallery-downloaded-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-local-recipe-smoke \
  --host 127.0.0.1 \
  --port 8769 \
  --receipt-file docs/qa-receipts/simulator-local-recipe-photo-flow.json \
  --screenshot-file /tmp/agent-pocket-simulator-local-recipe.png

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-share-sheet-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-share-sheet.png \
  --receipt-file docs/qa-receipts/share-sheet-flow-latest.json
```

The downloaded-state command seeds the selected variant with local result bytes and writes a receipt proving `state: downloaded`, `downloaded_asset_bytes > 0`, `save_enabled: true`, and `share_enabled: true`. The current `simulator-local-recipe-smoke` command should prove `recipe_local`, two rendered variants, crop metadata, renderer metadata, Master/Social image-difference metrics, nonblank result screenshots, and downloaded assets once a Simulator is booted. The `simulator-share-sheet-smoke` command launches the Debug-only share handoff view and should write a receipt proving `UIActivityViewController` was presented with an image file plus generated caption.

To see the current milestone evidence ledger without using the physical iPhone:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa test-receipt \
  --name python \
  --receipt-file docs/qa-receipts/python-tests-latest.json \
  --timeout 600 \
  -- python3 -m pytest mock_bridge/tests photo-pack/tests ios/tests -q

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa test-receipt \
  --name swift \
  --receipt-file docs/qa-receipts/swift-test-latest.json \
  -- swift test

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-audit

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa readiness-report \
  --output-file docs/agent-pocket-readiness.md
```

Expect simulator-backed Gates A, B, C, D, and E to pass when the saved receipts above are present. The Master Shot Local Recipe milestone remains open until the simulator local-recipe smoke, real iPhone local-recipe flow, and share-sheet handoff receipts exist. Current app-side result/share readiness includes recipe summary decoding, nonempty share-caption receipt checks, and a Debug share-sheet smoke path.

## iOS Build Notes

Verify shared implementation with Swift Package Manager:

```bash
swift test
```

Build the installable simulator app:

```bash
xcodebuild \
  -project ios/AgentPocket.xcodeproj \
  -target AgentPocket \
  -configuration Debug \
  -sdk iphonesimulator \
  build
```

Do not add `CODE_SIGNING_ALLOWED=NO` when testing connection restore in Simulator. The app needs the normal simulated entitlements Xcode embeds during a signed local simulator build, otherwise Keychain saves can fail and the UI may show a saved-runtime credential error.

Install and launch on a booted Simulator:

```bash
xcrun simctl bootstatus booted -b
xcrun simctl install booted ios/build/Debug-iphonesimulator/AgentPocket.app
xcrun simctl launch booted com.kaka.AgentPocket
```

Build for a physical iPhone:

```bash
xcodebuild \
  -project ios/AgentPocket.xcodeproj \
  -target AgentPocket \
  -configuration Debug \
  -sdk iphoneos \
  DEVELOPMENT_TEAM=<team-id> \
  -allowProvisioningUpdates \
  -allowProvisioningDeviceRegistration \
  build
```

Install and launch with CoreDevice:

```bash
xcrun devicectl device install app \
  --device <coredevice-id> \
  ios/build/Debug-iphoneos/AgentPocket.app

xcrun devicectl device process launch \
  --device <coredevice-id> \
  com.kaka.AgentPocket
```

If Xcode says a device runtime is not installed while `xcrun devicectl list devices` shows the iPhone as connected or paired, the CLI/CoreDevice path can still reach signing, install, and launch. If signing fails with `No Account for Team` or `No profiles for 'com.kaka.AgentPocket' were found`, accept pending Apple Developer Program agreements, refresh the Apple ID in Xcode > Settings > Apple Accounts, and create the matching development provisioning profile.

## Connection Persistence

After a successful manual connection, QR scan, or Bonjour pairing, Agent Pocket stores the bridge endpoint and mobile bearer token in Keychain. On launch it verifies the saved runtime before showing the capture flow. If there is no saved connection, it does not search the local network until the user taps Connect. If the saved endpoint is offline, the app shows the offline recovery state so the user can retry discovery or scan a fresh QR code.

If the runtime revokes the token, the app clears the saved connection during restore and returns to the connection flow. To pair with a different runtime, use the connected workspace's change-runtime control.

## Connected Photo Flow

After pairing, take a photo on iPhone or choose a library photo, tap **Make Master Shot** or pick one of the four scene packs, and tap the send action. The app preprocesses the image, uploads it through the saved runtime connection, starts a `photo_edit` task, polls until terminal status, and then shows Review Results when variants are returned.

On the results screen, tap Download Selected before saving or sharing. The app downloads the selected variant with the same mobile bridge token, caches the bytes locally for the current session, and enables Save and Share after the download succeeds.

The Phase 1 share action should use the iOS system share sheet with the selected image and generated caption. Direct WeChat, WeChat Moments, Xiaohongshu, and X SDK/API posting is a later enhancement, not a first-version blocker.

Camera capture uses the system iOS camera sheet on devices with a camera. On simulators or Macs without a camera, Agent Pocket shows a recoverable message and keeps the library picker available.

## Legacy Optional OpenAI Images Adapter

`photo-pack/adapters/openai_image.py` remains available for future generative image editing experiments. Use it later for object removal, background replacement, or full image generation only after the Local Recipe flow is proven.

Provider/model API keys stay in the user-owned runtime or bridge host. They must not be added to the iOS app.
