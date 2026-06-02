---
name: kaka-mobile-bridge
description: Connect Kaka iPhone to this Hermes runtime through the local Mobile Bridge after explicit user approval.
---

# Kaka Mobile Bridge Skill

Use this skill when the user asks Hermes to connect Kaka, show a Kaka pairing QR, or start the local Kaka Mobile Bridge.

## Safety Rules

- Do not start the bridge during skill installation.
- Ask for explicit confirmation before exposing the bridge on LAN or advertising Bonjour.
- Keep provider/model credentials in Hermes. Never send them to the iPhone.
- Do not print API keys, bearer tokens, or full auth files.
- Prefer a short-lived pairing code. Revoke old mobile tokens when requested.

## Expected Actions

1. Run a local preflight equivalent to `kaka-mobile-runtime-kit doctor`.
2. If the user approves, start the Mobile Bridge for this Hermes profile.
3. Show the pairing QR URL or QR image.
4. Tell the user to open Kaka on iPhone and tap Connect or scan the QR.
5. Stop the bridge when the user asks, and offer revocation for mobile tokens.

## Runtime Contract

The bridge must implement `/mobile/v1` from `docs/mobile-bridge-api.md` and advertise `recipe_local` with local rendering for Phase 1.
