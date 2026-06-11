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
- Require explicit user approval before any mutating host adapter action.
- Do not start the bridge or create a login item during install.
- Do not ask ordinary users to write adapter code, export
  `HERMES_KAKA_HOST_API`, or paste Runtime Kit command chains. Those are
  developer/pilot fallback paths only.
- Treat the P3.12 Host Extension Starter Kit as host-team packaging input only:
  it may generate README/manifest/runtime-command scaffolding, but it must not
  install the plugin, start the bridge, bind LAN, advertise Bonjour, create
  login items, mint mobile tokens, invoke private Hermes commands, or expose
  private host APIs to Kaka iPhone.
- Treat P3.13 Host Extension installable package handoff as host-team packaging
  input too: it may generate package-shaped handoff materials, but
  signing, update channels, proprietary Hermes implementation, conformance
  evidence, and public distribution remain Hermes-owned.
- Treat P3.15 Host Plugin/Skill Devkit and any future Codex developer plugin as
  host-team automation only. They may scaffold and validate Hermes Plugin
  artifacts, but they must not become the ordinary-user install surface.

## Ordinary-User Pairing Flow

1. Run a local preflight equivalent to `kaka-mobile-runtime-kit doctor`.
2. Load `runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json` and render `settings_preview.runtime_side_ui.consumer_ui` plus `settings_preview.runtime_side_ui.process_ownership` from `kaka_mobile_runtime_kit package-preview --runtime hermes`; use `runtime_side_ui.controls` only as the backing control dictionary. Render `kaka_mobile_runtime_kit host-extension-preview --runtime hermes` as the ordinary-user Host Extension install/pairing contract. For packaging handoff, render `kaka_mobile_runtime_kit host-package-preview --runtime hermes`, including `host-package-preview.private_adapter_package`. These Runtime Kit command names are host-shell/agent instructions, not ordinary-user UI copy.
3. Let the user choose loopback/LAN, Bonjour, local Recall/task store path, Recall retrieval provider, and the opt-in Start with Hermes setting on the Hermes side.
4. If the user approves, start the Mobile Bridge for this Hermes profile.
5. Show the pairing QR URL or QR image; use the production QR when `pairing_mode=production`.
6. Tell the user to open Kaka on iPhone and tap Connect or scan the QR.
7. Stop the bridge when the user asks, offer Revoke iPhone through runtime-side action metadata, and keep Install/Update/Uninstall/Open Logs/Health Check/Repair Port Conflict on the Hermes runtime side.
8. Execute approved host actions through `kaka_mobile_runtime_kit host-adapter-run --runtime hermes`; use `--adapter mock` for conformance/local QA, and use `--adapter private` only when the installed Hermes Plugin provides an extension-internal host-private command behind the Runtime Kit contract.

## Host-Team Release/Pilot Workflow Only

These steps are not part of an ordinary "connect Kaka" user flow.

1. Resolve the host-owned command through the Hermes Plugin first. Explicit `--private-adapter-command` / Hermes `private_adapter_command` config, `HERMES_KAKA_HOST_API`, `host_private_adapter.command` in the manifest, or `~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api` remain developer/pilot fallback discovery sources; require a signed or explicitly host-approved command binary before stable distribution.
2. First generate `kaka_mobile_runtime_kit host-shell-pilot-request --runtime hermes --request-id P3.4-hermes --pilot-owner "Hermes host team" --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" --artifact-root artifacts/hermes` and send it to the Hermes host team as the read-only materials request.
3. Before conformance/report/handoff, run `kaka_mobile_runtime_kit host-shell-pilot-preflight --runtime hermes --private-adapter-command "/path/to/hermes-kaka-host-api"` to show missing local host inputs without invoking the private command.
4. Generate `kaka_mobile_runtime_kit host-shell-pilot-runbook --runtime hermes --private-adapter-command "/path/to/hermes-kaka-host-api"` so the host operator has ordered steps, command artifacts, evidence requirements, and acceptance gates before running conformance.
5. When Hermes provides that host-owned command, run `kaka_mobile_runtime_kit host-private-adapter-conformance --runtime hermes --private-adapter-command "/path/to/hermes-kaka-host-api"` from the runtime side before exposing install/update as ready.
6. For P3.4e release review, print `kaka_mobile_runtime_kit host-shell-pilot-handoff --runtime hermes` after the P3.4d audit refs are present; treat `ready_to_submit` as a handoff state only, not final P3.4 completion.
7. After request, preflight, conformance, pilot receipt, and handoff JSON artifacts exist, run `kaka_mobile_runtime_kit host-shell-pilot-artifact-review --runtime hermes` before external review; treat `ready_for_external_review` as review readiness only, not P3.4 completion.
8. After artifact review is ready, run `kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest --runtime hermes --artifact-root artifacts/hermes` to hash local JSON artifacts for external host-owned archival; treat `ready_for_archive` as archive readiness only, not archive creation or P3.4 completion.
9. For the implemented P3.6 readiness contract, provide the real Hermes Plugin install command, update channel, extension-internal adapter command location, host UI entry point, signed package ref, signature/notarization ref, P3.2 conformance report ref, and P3.4 evidence manifest ref. `host-extension-readiness` reports whether the package is ready for an external install drill; it must not install the package or mark P3.4 complete.

## Runtime Contract

The bridge must implement `/mobile/v1` from `docs/mobile-bridge-api.md` and
advertise `recipe_local` with local rendering for Phase 1. For the current
local renderer contract, advertise `photo_edit.return_variants_max: 2` for the
**Master** and **Social** outputs, and advertise
`photo_edit.accepted_mime_types: ["image/jpeg"]`; do not claim a third default
variant or direct HEIC/PNG photo-edit renderer support unless a new renderer
contract and readiness proof lands first.

For image-conversation vision skills, prefer a runtime-owned `runtime_http` vision endpoint over `fixture_vision`. `scan`, `identify`, `translate`, and `food` are bottom-layer skill mappings, not pre-capture modes. `fixture_vision` only proves the Kaka UI flow and must not be presented as real OCR, identification, translation, or food understanding.

Persistence and Recall retrieval settings are runtime-side controls. Hermes may show the local SQLite path and local Recall provider endpoint in its own UI, but `/mobile/v1/runtime/settings` must remain phone-safe and expose only non-secret status such as store availability and retrieval mode.

The package manifest, package preview, and P2.8 `host-package-preview` handoff are disabled by default, do not autostart on install, and classify local paths, provider endpoints, env files, credentials, TLS private key paths, and mobile tokens as runtime-side values. `consumer_ui` is the renderer contract for Hermes, `process_ownership` is the runtime-side lifecycle contract for install/start-at-login/update/uninstall/logs/health/port-conflict repair, and `host-package-preview` is the host packaging handoff contract. They must stay derived from Runtime Kit settings and must not copy runtime-only values into Kaka iPhone settings or `phone_safe_summary`.

P2.9 adds `host-adapter-run` as a Mac/runtime-side action execution surface. It is not a phone API and must not move host action results into Kaka iPhone settings. The iPhone still talks to Hermes only through Kaka Mobile Bridge `/mobile/v1`. `mock` adapter mode is for conformance/local QA. P3.1 `private` adapter mode is a host-private command bridge contract: Runtime Kit invokes the configured command with `shell=False`, sends a sanitized JSON request on stdin, expects JSON on stdout, and returns structured safe failures for missing, failed, invalid, or timed-out commands. Runtime Kit does not include the proprietary Hermes private API implementation; Hermes supplies that behind the command.

P3.2 `host-private-adapter-conformance` is also Mac/runtime-side only. It validates
the configured Hermes-owned command through the P3.1 private adapter behavior
across install, login-item, update, uninstall, logs, health, port repair, and
supervision. Passing conformance does not make Kaka or Runtime Kit the owner or
distributor of Hermes proprietary binaries; distribution remains a Hermes host
manifest/package responsibility.

P3.3 adds `host-package-preview.private_adapter_package` with schema version
`kaka.host_private_adapter_package.v1` for the Hermes-owned command package.
Hermes must keep command paths, logs, process IDs, update feeds, signatures,
tokens, provider settings, and runtime store paths runtime-side only. The
package metadata records host-owned discovery, explicit-user-approved updates,
host-required signatures, and the required
`kaka.host_private_adapter_conformance.v1` report; it does not add a phone API
or bundle the proprietary Hermes private API implementation.

P3.4b `host-shell-pilot-report` may use the same discovery order for pilot
receipts: explicit command, `HERMES_KAKA_HOST_API`, manifest entrypoint, then
the well-known path. If no real external host-owned command is found, the pilot
receipt remains `not_ready`; local fake fixtures are still `synthetic_only` and
cannot mark P3.4 complete.

P3.5 adds the Host Extension productization contract. The stable Hermes path is
an installable plugin that bundles or internally discovers
`hermes-kaka-host-api`, renders Kaka Mobile Bridge pairing/lifecycle UI, and
keeps manual command paths and environment variables out of the ordinary-user
setup flow. Hermes should render `host-extension-preview` alongside the existing
settings, package, host package, and private adapter package contracts.

P3.4i `host-shell-pilot-request` comes before preflight, runbook, conformance,
report, handoff, and artifact review. It emits
`kaka.host_shell_pilot_request.v1` on surface
`hermes_openclaw_host_shell_pilot_request` and is a read-only materials request
bundle for the Hermes host team. It lists the host-owned private adapter command
binary, request/response contract acknowledgement, 9-action matrix, native
distribution channel, signature/notarization, update feed,
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
`hermes_openclaw_host_shell_pilot_preflight` and checks Hermes app/CLI
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
remains Hermes-owned. Runtime Kit must not fetch audit refs, expose phone
`/mobile/v1`, or bundle the proprietary Hermes command.

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
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Example P3.4i pilot request:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime hermes \
  --request-id P3.4-hermes \
  --pilot-owner "Hermes host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --artifact-root artifacts/hermes
```

Example P3.4f pilot preflight:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

Example P3.4g pilot runbook:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

Example private adapter conformance:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

Example P3.4e pilot handoff:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-handoff \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
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
  --native-channel-ref "Hermes stable channel receipt #2026-06-06" \
  --signature-subject "Developer ID Application: Example Hermes Team" \
  --notarization-team-id TEAMID1234 \
  --update-feed-ref "https://updates.example.invalid/hermes/kaka/appcast.xml" \
  --install-receipt-ref "qa://hermes/install/2026-06-06" \
  --update-receipt-ref "qa://hermes/update/2026-06-06" \
  --failure-recovery-receipt-ref "qa://hermes/recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/hermes/kaka/release-notes/1.0.0"
```

Example P3.4h pilot artifact review:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime hermes \
  --preflight-json artifacts/hermes/preflight.json \
  --conformance-json artifacts/hermes/conformance.json \
  --receipt-json artifacts/hermes/pilot-receipt.json \
  --handoff-json artifacts/hermes/handoff.json
```

Example P3.4j pilot evidence manifest:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime hermes \
  --package-id P3.4-hermes \
  --artifact-root artifacts/hermes \
  --request-json artifacts/hermes/request.json \
  --runbook-json artifacts/hermes/runbook.json \
  --archive-filename kaka-p3.4-hermes-pilot-evidence.zip
```
