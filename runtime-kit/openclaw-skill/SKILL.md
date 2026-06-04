---
name: kaka-mobile-bridge
description: Connect Kaka iPhone to this OpenClaw runtime through a local Mobile Bridge or sidecar after explicit user approval.
---

# Kaka Mobile Bridge Skill For OpenClaw

Use this skill when the user asks OpenClaw to connect Kaka, show a pairing QR, or start a compatible Kaka Mobile Bridge sidecar.

## Safety Rules

- Do not start a listener during skill installation.
- Require explicit approval for LAN bind and Bonjour advertisement.
- Keep model/provider credentials inside OpenClaw or its sidecar.
- Do not print API keys, bearer tokens, or private auth files.
- Pairing should use a short-lived code and revocable mobile token.

## Expected Actions

1. Check that a compatible Mobile Bridge sidecar or native OpenClaw bridge is available.
2. Start the bridge only after the user asks.
3. Show the pairing QR URL or QR image.
4. Confirm Kaka iPhone pairing and then keep the bridge running only for the approved session or opt-in autostart setting.

## Runtime Contract

The bridge must implement `/mobile/v1` from `docs/mobile-bridge-api.md`. For Phase 1, the photo task should return `Master` and `Social` variants produced by a strict local edit recipe, not by client-side provider calls.

For image-conversation vision skills, OpenClaw or its sidecar should provide a runtime-owned vision endpoint and start the bridge with `--vision-provider runtime_http --vision-endpoint <local-url>`. `scan`, `identify`, `translate`, and `food` are bottom-layer mappings used after Kaka suggests a skill or routes typed text; the default `fixture_vision` provider is only for UI/protocol tests and does not inspect real images.
