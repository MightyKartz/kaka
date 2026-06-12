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
- Require explicit user approval before any mutating host adapter action.
- Do not start the bridge or create a login item during install.
- Do not ask ordinary users to write adapter code, export
  `OPENCLAW_KAKA_HOST_API`, or paste Runtime Kit command chains. Those are
  developer/pilot fallback paths only.
- Treat the P3.12 Host Extension Starter Kit as host-team packaging input only:
  it may generate README/manifest/runtime-command scaffolding, but it must not
  install the Skill/sidecar, start the bridge, bind LAN, advertise Bonjour,
  create login items, mint mobile tokens, invoke private OpenClaw commands, or
  expose private host APIs to Kaka iPhone.
- Treat P3.13 Host Extension installable package handoff as host-team packaging
  input too: it may generate package-shaped handoff materials, but
  signing, update channels, proprietary OpenClaw implementation, conformance
  evidence, and public distribution remain OpenClaw-owned.
- Treat P3.15 Host Plugin/Skill Devkit and any future Codex developer plugin as
  host-team automation only. They may scaffold and validate OpenClaw Skill or
  sidecar artifacts, but they must not become the ordinary-user install surface.
- P3.35 now adds the Host-Native Plugin/Skill Installation Blueprint while
  external P3.7 package facts remain blocked:
  `../../docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
  It clarifies the OpenClaw Skill/sidecar
  manifest, host UI entry point, disabled defaults, explicit Enable/Start,
  QR/Bonjour, local TLS, Revoke iPhone, health, logs, update, repair,
  uninstall, and evidence refs. It must remain read-only or generative until
  OpenClaw supplies real package materials; it must not install a public Codex
  skill, start the bridge, invoke private adapters, or write user-home Codex
  plugin/skill roots.

## Ordinary-User Pairing Flow

1. Check that a compatible Mobile Bridge sidecar or native OpenClaw bridge is available.
2. Load `runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json` and render `settings_preview.runtime_side_ui.consumer_ui` plus `settings_preview.runtime_side_ui.process_ownership` from `kaka_mobile_runtime_kit package-preview --runtime openclaw`; use `runtime_side_ui.controls` only as the backing control dictionary. Render `kaka_mobile_runtime_kit host-extension-preview --runtime openclaw` as the ordinary-user Host Extension install/pairing contract. For packaging handoff, render `kaka_mobile_runtime_kit host-package-preview --runtime openclaw`, including `host-package-preview.private_adapter_package`. These Runtime Kit command names are host-shell/agent instructions, not ordinary-user UI copy.
3. Let the user choose loopback/LAN, Bonjour, local Recall/task store path, Recall retrieval provider, and the opt-in Start with OpenClaw setting on the OpenClaw side.
4. Start the bridge only after the user asks.
5. Show the pairing QR URL or QR image; use the production QR when `pairing_mode=production`.
6. Confirm Kaka iPhone pairing and then keep the bridge running only for the approved session or opt-in autostart setting.
7. Offer Revoke iPhone through runtime-side action metadata when production pairing is enabled, and keep Install/Update/Uninstall/Open Logs/Health Check/Repair Port Conflict on the OpenClaw runtime side.
8. Execute approved host actions through `kaka_mobile_runtime_kit host-adapter-run --runtime openclaw`; use `--adapter mock` for conformance/local QA, and use `--adapter private` only when the installed OpenClaw Skill or sidecar provides an extension-internal host-private command behind the Runtime Kit contract.

## Host-Team Release/Pilot Workflow Only

These steps are not part of an ordinary "connect Kaka" user flow.

1. Resolve the host-owned command through the OpenClaw Skill or sidecar first. Explicit `--private-adapter-command` / OpenClaw `private_adapter_command` config, `OPENCLAW_KAKA_HOST_API`, `host_private_adapter.command` in the manifest, or `~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api` remain developer/pilot fallback discovery sources; require a signed or explicitly host-approved command binary before stable distribution.
2. First generate `kaka_mobile_runtime_kit host-shell-pilot-request --runtime openclaw --request-id P3.4-openclaw --pilot-owner "OpenClaw host team" --expected-private-adapter-command-path "~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api" --artifact-root artifacts/openclaw` and send it to the OpenClaw host team as the read-only materials request.
3. Before conformance/report/handoff, run `kaka_mobile_runtime_kit host-shell-pilot-preflight --runtime openclaw --private-adapter-command "/path/to/openclaw-kaka-host-api"` to show missing local host inputs without invoking the private command.
4. Generate `kaka_mobile_runtime_kit host-shell-pilot-runbook --runtime openclaw --private-adapter-command "/path/to/openclaw-kaka-host-api"` so the host operator has ordered steps, command artifacts, evidence requirements, and acceptance gates before running conformance.
5. When OpenClaw provides that host-owned command, run `kaka_mobile_runtime_kit host-private-adapter-conformance --runtime openclaw --private-adapter-command "/path/to/openclaw-kaka-host-api"` from the runtime side before exposing install/update as ready.
6. For P3.4e release review, print `kaka_mobile_runtime_kit host-shell-pilot-handoff --runtime openclaw` after the P3.4d audit refs are present; treat `ready_to_submit` as a handoff state only, not final P3.4 completion.
7. After request, preflight, conformance, pilot receipt, and handoff JSON artifacts exist, run `kaka_mobile_runtime_kit host-shell-pilot-artifact-review --runtime openclaw` before external review; treat `ready_for_external_review` as review readiness only, not P3.4 completion.
8. After artifact review is ready, run `kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest --runtime openclaw --artifact-root artifacts/openclaw` to hash local JSON artifacts for external host-owned archival; treat `ready_for_archive` as archive readiness only, not archive creation or P3.4 completion.
9. For the implemented P3.6 readiness contract, provide the real OpenClaw Skill/sidecar install command, update channel, extension-internal adapter command location, host UI entry point, signed package ref, signature/notarization ref, P3.2 conformance report ref, and P3.4 evidence manifest ref. `host-extension-readiness` reports whether the package is ready for an external install drill; it must not install the package or mark P3.4 complete.

## Runtime Contract

The bridge must implement `/mobile/v1` from `docs/mobile-bridge-api.md`. For
Phase 1, the photo task should return `Master` and `Social` variants produced by
a strict local edit recipe, not by client-side provider calls. For the current
local renderer contract, advertise `photo_edit.return_variants_max: 2` and
`photo_edit.accepted_mime_types: ["image/jpeg"]`; do not claim a third default
variant or direct HEIC/PNG photo-edit renderer support unless a new renderer
contract and readiness proof lands first.

For image-conversation vision skills, OpenClaw or its sidecar should provide a runtime-owned vision endpoint and start the bridge with `--vision-provider runtime_http --vision-endpoint <local-url>`. `scan`, `identify`, `translate`, and `food` are bottom-layer mappings used after Kaka suggests a skill or routes typed text; the default `fixture_vision` provider is only for UI/protocol tests and does not inspect real images.

Persistence and Recall retrieval settings are runtime-side controls. OpenClaw may show the local SQLite path and local Recall provider endpoint in its own UI, but `/mobile/v1/runtime/settings` must remain phone-safe and expose only non-secret status such as store availability and retrieval mode.

The sidecar manifest, package preview, and P2.8 `host-package-preview` handoff are disabled by default, do not autostart on install, and classify local paths, provider endpoints, env files, credentials, TLS private key paths, and mobile tokens as runtime-side values. `consumer_ui` is the renderer contract for OpenClaw, `process_ownership` is the runtime-side lifecycle contract for install/start-at-login/update/uninstall/logs/health/port-conflict repair, and `host-package-preview` is the host packaging handoff contract. They must stay derived from Runtime Kit settings and must not copy runtime-only values into Kaka iPhone settings or `phone_safe_summary`.

P2.9 adds `host-adapter-run` as a Mac/runtime-side action execution surface. It is not a phone API and must not move host action results into Kaka iPhone settings. The iPhone still talks to OpenClaw only through Kaka Mobile Bridge `/mobile/v1`. `mock` adapter mode is for conformance/local QA. P3.1 `private` adapter mode is a host-private command bridge contract: Runtime Kit invokes the configured command with `shell=False`, sends a sanitized JSON request on stdin, expects JSON on stdout, and returns structured safe failures for missing, failed, invalid, or timed-out commands. Runtime Kit does not include the proprietary OpenClaw private API implementation; OpenClaw supplies that behind the command.

P3.2 `host-private-adapter-conformance` is also Mac/runtime-side only. It validates
the configured OpenClaw-owned command through the P3.1 private adapter behavior
across install, login-item, update, uninstall, logs, health, port repair, and
supervision. Passing conformance does not make Kaka or Runtime Kit the owner or
distributor of OpenClaw proprietary binaries; distribution remains an OpenClaw
host manifest/package responsibility.

P3.3 adds `host-package-preview.private_adapter_package` with schema version
`kaka.host_private_adapter_package.v1` for the OpenClaw-owned command package.
OpenClaw must keep command paths, logs, process IDs, update feeds, signatures,
tokens, provider settings, and runtime store paths runtime-side only. The
package metadata records host-owned discovery, explicit-user-approved updates,
host-required signatures, and the required
`kaka.host_private_adapter_conformance.v1` report; it does not add a phone API
or bundle the proprietary OpenClaw private API implementation.

P3.4b `host-shell-pilot-report` may use the same discovery order for pilot
receipts: explicit command, `OPENCLAW_KAKA_HOST_API`, manifest entrypoint, then
the well-known path. If no real external host-owned command is found, the pilot
receipt remains `not_ready`; local fake fixtures are still `synthetic_only` and
cannot mark P3.4 complete.

P3.5 adds the Host Extension productization contract. The stable OpenClaw path is
an installable Skill or sidecar that bundles or internally discovers
`openclaw-kaka-host-api`, renders Kaka Mobile Bridge pairing/lifecycle UI, and
keeps manual command paths and environment variables out of the ordinary-user
setup flow. OpenClaw should render `host-extension-preview` alongside the
existing settings, package, host package, and private adapter package contracts.

P3.4i `host-shell-pilot-request` comes before preflight, runbook, conformance,
report, handoff, and artifact review. It emits
`kaka.host_shell_pilot_request.v1` on surface
`hermes_openclaw_host_shell_pilot_request` and is a read-only materials request
bundle for the OpenClaw host team. It lists the host-owned private adapter
command binary, request/response contract acknowledgement, 9-action matrix,
native distribution channel, signature/notarization, update feed,
install/update/failure-recovery drill receipts, release notes, required audit
refs (`native_channel_ref`, `signature_subject`, `notarization_team_id`,
`update_feed_ref`, `install_receipt_ref`, `update_receipt_ref`,
`failure_recovery_receipt_ref`, `release_notes_ref`), and expected Runtime Kit
artifacts: preflight, conformance, pilot receipt, handoff, artifact review, and
evidence manifest JSON. `request_status: "ready_to_send"` and `ok: true` only mean the request
package was generated. It still reports `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`. It does not invoke the private
adapter command, run preflight or conformance, read artifacts, fetch audit refs,
mutate host state, submit handoff, or change the iPhone `/mobile/v1` surface.

P3.4f `host-shell-pilot-preflight` comes before conformance, report, and
handoff. It emits `kaka.host_shell_pilot_preflight.v1` on surface
`hermes_openclaw_host_shell_pilot_preflight` and checks OpenClaw app/CLI
presence, explicit/env/manifest/well-known private command discovery, and PATH
command availability as informational-only. It does not invoke the private
adapter command, run conformance, fetch audit refs, mutate host state, or expose
phone `/mobile/v1`. `ok: true` with `status: "ready_for_conformance"` only means
conformance can run next; it always keeps `p3_4_complete: false`.

P3.4g `host-shell-pilot-runbook` is a read-only host operator runbook generated
before conformance, report, and handoff. It emits
`kaka.host_shell_pilot_runbook.v1` on surface
`hermes_openclaw_host_shell_pilot_runbook` and includes the brief, pilot target,
preflight summary, ordered steps, command artifacts, evidence requirements, and
acceptance gates. It composes P3.4f preflight only: it does not invoke the
private adapter command, run conformance, fetch evidence refs, mutate host
state, or expose phone `/mobile/v1`. `ok: true` with
`runbook_status: "ready_for_conformance"` means conformance can run next, not
that handoff is ready to submit or P3.4 is complete. It always keeps
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

P3.4e `host-shell-pilot-handoff` is the machine-readable external pilot
handoff package. It wraps `host-shell-pilot-report` in schema
`kaka.host_shell_pilot_handoff.v1` on surface
`hermes_openclaw_host_shell_pilot_handoff`, adds deliverables,
`release_handoff`, P3.4d `audit_refs` completeness, and safety flags, and
does not change receipt readiness. It is `ready_to_submit` only when all P3.4d
audit refs are supplied; otherwise it is `incomplete`. It always reports
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell` because final P3.4 completion
remains OpenClaw-owned. Runtime Kit must not fetch audit refs, expose phone
`/mobile/v1`, or bundle the proprietary OpenClaw command.

P3.4h `host-shell-pilot-artifact-review` is a read-only external-review gate
for the four already-generated JSON artifacts: preflight, conformance, pilot
receipt, and handoff. It emits
`kaka.host_shell_pilot_artifact_review.v1` on surface
`hermes_openclaw_host_shell_pilot_artifact_review`, summarizes load/schema
status, and cross-checks runtime, embedded conformance, embedded receipt,
audit refs, and private command consistency. It reports
`review_status: "ready_for_external_review"` only when the artifacts are ready
and consistent. It does not invoke the private adapter command, run
conformance, fetch refs, mutate host state, or expose phone `/mobile/v1`; it
always keeps `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

P3.4j `host-shell-pilot-evidence-manifest` is a read-only evidence index for
local pilot JSON artifacts after artifact review. It emits
`kaka.host_shell_pilot_evidence_manifest.v1` on surface
`hermes_openclaw_host_shell_pilot_evidence_manifest`, records byte sizes and
SHA-256 hashes, and can report `manifest_status: "ready_for_archive"` only when
required artifacts are loaded, schema-aligned, runtime-aligned, and `ok: true`.
It does not invoke the private adapter command, run conformance, fetch refs,
submit handoff, mutate host state, create an archive, or expose phone
`/mobile/v1`; it always keeps `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

Example private adapter health check:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime openclaw \
  --adapter private \
  --private-adapter-command "/path/to/openclaw-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Example P3.4i pilot request:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime openclaw \
  --request-id P3.4-openclaw \
  --pilot-owner "OpenClaw host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api" \
  --artifact-root artifacts/openclaw
```

Example P3.4f pilot preflight:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api"
```

Example P3.4g pilot runbook:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api"
```

Example private adapter conformance:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api"
```

Example P3.4e pilot handoff:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-handoff \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api" \
  --distribution-source signed_download \
  --distribution-channel stable \
  --package-version 1.0.0 \
  --host-api-level v1 \
  --native-channel-verified \
  --signature-verified \
  --update-feed-verified \
  --install-verified \
  --update-verified \
  --failure-recovery-verified \
  --release-notes-verified \
  --native-channel-ref "OpenClaw stable channel receipt #2026-06-06" \
  --signature-subject "Developer ID Application: Example OpenClaw Team" \
  --notarization-team-id TEAMID1234 \
  --update-feed-ref "https://updates.example.invalid/openclaw/kaka/appcast.xml" \
  --install-receipt-ref "qa://openclaw/install/2026-06-06" \
  --update-receipt-ref "qa://openclaw/update/2026-06-06" \
  --failure-recovery-receipt-ref "qa://openclaw/recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/openclaw/kaka/release-notes/1.0.0"
```

Example P3.4h pilot artifact review:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime openclaw \
  --preflight-json artifacts/openclaw/preflight.json \
  --conformance-json artifacts/openclaw/conformance.json \
  --receipt-json artifacts/openclaw/pilot-receipt.json \
  --handoff-json artifacts/openclaw/handoff.json
```

Example P3.4j pilot evidence manifest:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime openclaw \
  --package-id P3.4-openclaw \
  --artifact-root artifacts/openclaw \
  --request-json artifacts/openclaw/request.json \
  --runbook-json artifacts/openclaw/runbook.json \
  --archive-filename kaka-p3.4-openclaw-pilot-evidence.zip
```

## P3.4a Pilot Receipt Checklist

Before Kaka can mark P3.4 complete, the OpenClaw host shell must provide:

- host-owned private adapter command outside the Kaka repository
- native distribution channel evidence
- signature or notarization evidence
- update-feed evidence
- passing `host-private-adapter-conformance`
- install drill receipt
- update drill receipt
- expected-failure recovery receipt
- user-facing release notes

Runtime Kit verifies and records those facts with `host-shell-pilot-report`; it
does not own, build, sign, distribute, install, update, or bundle the
proprietary OpenClaw private adapter binary. Local fake fixtures and local
conformance are `synthetic_only` and cannot mark P3.4 complete. P3.4 requires a
real host-owned `openclaw-kaka-host-api` binary outside this repository.
