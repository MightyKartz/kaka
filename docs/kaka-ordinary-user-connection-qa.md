# Kaka Ordinary-User Connection QA

Status: P3.0 ordinary-user connection QA and host adapter readiness checklist.

This document is for validating the first-run connection journey before or
alongside wiring host-private adapter commands. It keeps the product boundary
narrow: the iPhone connects only to Kaka Mobile Bridge `/mobile/v1` with an
endpoint and paired mobile token. Host setup, package previews, adapter actions,
health checks, logs, port repair, and QA reports all belong on the Mac/runtime
side.

## Host Prerequisites

- Kaka Runtime Kit scaffold is available from this checkout or from the
  Hermes/OpenClaw plugin or skill being tested.
- A Hermes/OpenClaw host shell, sidecar, or local development checkout can render
  Runtime Kit JSON contracts such as `settings-preview`, `package-preview`,
  `host-package-preview`, `host-adapter-run`, and `connection-qa-preview`.
- For P3.1 private-mode QA, a Hermes/OpenClaw host-private command can be
  supplied to Runtime Kit with `--private-adapter-command`. This command is
  host-owned; it is not a private API bundled in this repository.
- The test network is trusted: local loopback for Simulator, trusted LAN for a
  physical iPhone, or a controlled Tailscale/development path.
- Production pairing mode is enabled for ordinary-user QA. Saved-token reconnect
  and token revocation drills should use a runtime store configured on the
  Mac/runtime side.
- The iPhone has visible permission prompts available for Local Network/Bonjour
  discovery, or the tester is ready to use QR/manual endpoint fallback.

## Non-Mutating Preview

Use the P3.0 preview command to generate a deterministic readiness report before
touching live bridge state:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit connection-qa-preview \
  --runtime hermes \
  --bridge-enabled \
  --lan \
  --bonjour \
  --bonjour-host 192.168.1.10 \
  --pairing-mode production \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --recall-search-provider fixture
```

`connection-qa-preview` is a Mac/runtime-side report. It must not start the
bridge, bind a port, advertise Bonjour, create login items, install packages,
mint credentials, mutate the host OS, call `subprocess.call`, or call
Hermes/OpenClaw proprietary private APIs. Its readiness output should record
`private_api_called: false` and list the host-private capabilities that a P3.1
command implementation must provide.

The report is allowed to reference runtime-side preview commands and mock
adapter results. Any phone-safe summary must stay allowlisted and must not
include runtime SQLite paths, provider endpoints, auth/env files, raw mobile
bearer tokens, TLS private key paths, hidden prompts, raw embeddings, index
rows, task logs, process IDs, or host log paths.

## First-Run Checklist

Target product flow for QA: the tester should behave like an ordinary user who
has installed a Hermes Plugin or OpenClaw Skill/sidecar. The tester should not
write adapter code, set `HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, paste
Runtime Kit command chains into onboarding, or install a Codex plugin/skill as
the public package. Those paths are allowed only for host-team development and
external pilot fallback.

| Step | Owner | Expected pass signal |
| --- | --- | --- |
| Install or enable the Kaka Runtime Kit scaffold in the Hermes/OpenClaw shell. | Host runtime | The package or skill is present, disabled by default, and did not auto-start a bridge listener. |
| Enable Kaka Mobile Bridge in the host shell. | Host runtime | The runtime UI shows the bridge as enabled and still requires an explicit start action. |
| Explicitly start the bridge from the host shell or local Runtime Kit command. | Host runtime | The bridge binds only to the selected loopback/LAN address and uses the selected Bonjour setting. |
| Show a production pairing QR code. | Host runtime | The QR is short-lived, single-use, and represents a Mobile Bridge pairing exchange, not a private host API call. |
| Pair the iPhone by scanning the QR code or using trusted LAN/Bonjour discovery. | Phone + host runtime | Kaka stores only the endpoint and mobile token, then communicates through `/mobile/v1`. |
| Run a health check from the runtime shell. | Host runtime | Health status is visible in the host shell and any phone-visible status is coarse and non-secret. |
| Verify saved-token reconnect. | Phone | Relaunching Kaka or reconnecting to the bridge uses the saved endpoint/token without exposing token material. |
| Revoke the iPhone token from the host shell. | Host runtime | Existing requests with the old mobile token fail as unauthorized. |
| Generate a new production QR and reconnect. | Phone + host runtime | Kaka reconnects with a new token, while the revoked token remains unusable. |

## Failure Drills

| Drill | Trigger | Expected user recovery |
| --- | --- | --- |
| Expired QR | Wait until the production QR expires before scanning or exchange. | The phone asks the user to refresh or scan a new QR; the host shell generates a new short-lived QR. |
| Revoked token | Revoke the saved iPhone token and then reconnect or call a protected endpoint. | Kaka treats the session as unauthorized and asks for a new mobile pairing code, not a phone-side token editor. |
| Bridge unavailable | Stop the bridge or point the phone to an unavailable endpoint. | Kaka shows an offline/bridge unavailable state; the host shell action is to start Kaka Mobile Bridge. |
| Missing Bonjour or Local Network permission | Disable Bonjour, use a missing Bonjour host, or deny iOS Local Network permission. | Kaka falls back to QR/manual endpoint recovery; the host shell explains Bonjour/LAN requirements. |
| Port conflict | Bind the expected bridge port with another process or use a conflicting host setting. | The host shell offers port check/repair guidance; the phone does not own port settings. |
| Disabled host action | Try an install/update/repair/log action when the runtime state does not permit it. | The runtime shell explains why the action is disabled and what state must change first. |
| Missing runtime store path | Run production revocation or saved-token persistence drills without a configured runtime store. | The host shell explains that durable token state is runtime-owned and requires an explicit store path. |
| Private adapter command missing | Run private adapter readiness without `--private-adapter-command`. | The report marks private host adapter unavailable and directs testers to mock/manual QA or to configure the host-owned command for P3.1. |

## Privacy Boundary

The phone may display or store only:

- Mobile Bridge endpoint.
- Paired mobile token in Keychain.
- Coarse connection, pairing, runtime settings, Recall availability, and health
  status returned through `/mobile/v1`.
- User-visible Inbox, Recall, task, and connection UI state.

The Mac/runtime owns:

- Provider keys and model routing.
- Tool execution and task state.
- Runtime Recall store, retrieval index, deletion receipts, and export contents.
- Logs, process state, port repair, install/update/uninstall state, login item
  state, and supervision.
- Any Hermes/OpenClaw private host API calls made behind the host-owned command bridge.

The iPhone must not call `host-adapter-run`, `connection-qa-preview`, package
preview commands, private adapter APIs, installer APIs, log APIs, port repair
APIs, or runtime store configuration APIs. Those surfaces remain Runtime Kit or
host-shell surfaces on the Mac/runtime side.

## P3.1 Host-Private Command Bridge

P3.0 proves readiness with deterministic previews, mock adapter behavior, manual
host QA, and user-facing recovery copy. P3.1's repository boundary is a
host-private command bridge contract, not a bundled Hermes/OpenClaw proprietary
implementation.

For follow-up development, keep this command bridge behind the host-native
Plugin/Skill. A future P3.35 installation blueprint may define the host UI,
manifest, and receipt expectations around it, but ordinary-user QA should still
start from "install the plugin or skill, enable Kaka Mobile Bridge, scan QR" and
never from "write a command wrapper."

Example private adapter health check:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Runtime Kit invokes the configured command with `shell=False`, sends a
sanitized JSON request on stdin, expects a JSON response on stdout, and converts
missing, failed, invalid, or timed-out command results into structured safe
adapter failures. Mutating private actions still require `--approved` and must
not run unless the current host package state enables the action. The iPhone
never calls this command and must not receive private adapter internals.

The host-owned command should provide these capabilities behind the contract:

- Distribution/package lookup and verification.
- Install and enablement.
- Start with runtime or login item registration.
- Update.
- Uninstall.
- Logs.
- Health checks.
- Port conflict detection and repair.
- Process supervision and restart policy.

Those APIs should be wired behind the existing Mac/runtime-side private adapter
surface only after the first-run journey and readiness report are confirmed.
