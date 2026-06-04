# Kaka Mobile Runtime Kit

Kaka Mobile Runtime Kit is the local bridge scaffold for connecting the iPhone app to a user-owned runtime such as Hermes, OpenClaw, or a compatible sidecar.

The important product decision is safety first: installing a skill or plugin must not silently start a LAN listener. The bridge starts only after an explicit user action, and LAN plus Bonjour exposure are opt-in.

## Current Status

This directory is a development scaffold, not the final public installer.

- It wraps the existing `mock_bridge/agent_pocket_mock_bridge.server` entrypoint.
- It defaults to `recipe_local`, the Phase 1 local recipe renderer path.
- It can print an exact dry-run command for Hermes/OpenClaw plugin authors.
- It does not install launch agents, background login items, or provider credentials.

## Developer Commands

Run a local doctor check:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
```

Print the bridge command without starting it:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start --dry-run
```

Start for Simulator-only loopback QA:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start
```

Start for a physical iPhone on the same trusted LAN:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead
```

Start with image-conversation vision skills routed to the local runtime:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead \
  --vision-provider runtime_http \
  --vision-endpoint http://127.0.0.1:<agent-port>/kaka/vision
```

For development, this repository also includes a lightweight local `/kaka/vision` endpoint so the `runtime_http` path can be tested before Hermes/OpenClaw owns the full model call. On macOS it uses Apple Vision for local OCR-backed skills (`ocr` -> `scan`, `translate_text` -> `translate`) and local image classification/text clues for conservative `identify_subject` and `nutrition_estimate` results. When it cannot find reliable local clues, it returns low-confidence model-not-configured guidance instead of fabricated objects or calorie estimates.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit.vision_server \
  --host 127.0.0.1 \
  --port 8787
```

Then start the bridge with `--vision-endpoint http://127.0.0.1:8787/kaka/vision`. In this configuration, Kaka's image conversation can execute OCR from a suggestion or typed request and show extracted text from the uploaded photo rather than placeholder endpoint status.

The default `fixture_vision` provider is intentionally limited: it proves UI flow and response shape, but it does not read the uploaded image. A production Hermes/OpenClaw integration should expose a local endpoint that accepts:

- `task`: `vision`
- `mode`: `scan`, `identify`, `translate`, or `food`
- `instruction`
- `locale`
- `image_base64`

and returns either a root `vision` object or `{ "vision": { ... } }` using the schema in `docs/mobile-bridge-api.md`.

The iPhone no longer asks the user to choose scan/identify/translate/food before shooting. The bridge first returns an `image_intake` task result with suggested skills, then Kaka routes suggestion taps or typed requests to these bottom-layer vision modes.

For OpenClaw, the same bridge contract should use `--runtime openclaw` and an OpenClaw-owned recipe endpoint or sidecar configuration once that adapter exists.

## Security Contract

- Install does not auto-start the bridge.
- Default bind host is `127.0.0.1`.
- Physical iPhone discovery requires explicit `--lan` and `--bonjour`.
- Pairing uses a short-lived or development pairing code; discovery alone does not mint credentials.
- Provider/model keys stay inside the Mac runtime process.
- Logs and doctor output must not print API keys or bearer tokens.
- Start-at-login is a later opt-in UI toggle, not a default install behavior.

## Product Path

The target first-run UX is:

1. User installs the Kaka runtime plugin/skill in Hermes or OpenClaw.
2. User opens the runtime UI and enables **Kaka Mobile Bridge**.
3. The runtime shows a QR code and optionally advertises Bonjour.
4. Kaka iPhone app discovers or scans the bridge.
5. iPhone stores only the endpoint and mobile token in Keychain.

This is the practical version of an AirPods-like setup for a local agent runtime: one explicit enable action, then the phone does the rest.
