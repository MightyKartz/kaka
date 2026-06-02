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
