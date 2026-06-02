# Hermes Plugin Adapter Scaffold

This folder documents the intended Hermes packaging target for Kaka Mobile Bridge.

## Recommended Hermes UX

Hermes should expose a visible **Kaka Mobile Bridge** control in its plugin or settings UI:

- `Enable` installs or activates the plugin.
- `Start Bridge` starts the local bridge for the current user session.
- `Start with Hermes` is opt-in and default off.
- `Show QR` displays `/mobile/v1/pairing/dev.html` or a production short-lived pairing QR.
- `Stop` shuts down the listener and Bonjour advertisement.

Installing the plugin should not silently bind a port or advertise on the LAN.

## Distribution

A public install can be distributed from a Git repository or Hermes plugin registry. A dedicated server is not required just to satisfy:

```bash
hermes plugins install <owner-or-repo>/kaka-mobile --no-enable
hermes plugins enable kaka-mobile
```

For local development, Hermes can install from a local checkout or Git URL if its plugin loader supports that source.

## Bridge Command

The plugin should eventually call the runtime-kit launcher directly instead of asking users to type this command:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile <profile>
```

The command is included for development transparency only. It is not the desired consumer onboarding UX.

## Safety Checklist

- No auto-start during install.
- No provider API keys copied into Kaka iPhone.
- Local-only default; LAN/Bonjour require explicit enable.
- Pairing code is short-lived in production.
- Bridge token can be revoked from Hermes.
- Photo assets remain under the user's local runtime retention policy.
