# Hermes Plugin Adapter Scaffold

This folder documents the intended Hermes packaging target for Pocket Agent Mobile Bridge.

The static shell manifest lives at `kaka-mobile-bridge.package.json`. It is
machine-readable scaffolding for Hermes packaging, but it does not assume a
private Hermes plugin API and it does not install or start anything by itself.

P3.5 turns this scaffold into the product install shape: ordinary users install
a Hermes Plugin, not adapter source code. The plugin should bundle or internally
discover `hermes-kaka-host-api`, render the Pocket Agent Mobile Bridge setup UI, and keep
explicit command paths, `HERMES_KAKA_HOST_API`, and Runtime Kit command chains as
developer/pilot fallback tools only.

## Recommended Hermes UX

Hermes should render Runtime Kit's `settings_preview.runtime_side_ui.consumer_ui`
as the visible **Pocket Agent Mobile Bridge** settings surface and
`settings_preview.runtime_side_ui.process_ownership` as the lifecycle surface in
its plugin or settings UI. The consumer UI model provides ordinary-user copy,
status badges, warning states, an empty state for a stopped bridge, and five
sections:

- Process: install, start with Hermes, update, uninstall, logs, health check, and port-conflict repair.
- Connection: enable/start/stop, loopback or LAN binding, Bonjour, and trusted local TLS state.
- Pairing: development or production QR, QR TTL, and Revoke iPhone metadata.
- Local Memory: runtime-owned Recall/task SQLite store enablement and path picker.
- Recall Retrieval: local, fixture, or `runtime_http` provider selection with a Hermes-owned local endpoint.

The primary actions come from the model: Start Bridge when stopped, Stop Bridge
and Show QR when running, and Revoke iPhone when production pairing is enabled.
The process ownership model covers Install, Start with Hermes, Update, Uninstall,
Open Logs, Run Health Check, and Repair Port Conflict. Hermes should use
`runtime_side_ui.controls` as the backing dictionary rather than inventing a
second settings source.

Installing the plugin should not silently bind a port, advertise on the LAN,
create a login item, or start the bridge. P2.8 declares the host packaging
handoff contract for Hermes. P2.9 adds `host-adapter-run` as the Mac/runtime-side
action result surface. The `mock` adapter is for conformance and local QA; the
P3.1 `private` adapter is a host-private command bridge contract. Runtime Kit
does not ship a proprietary Hermes implementation; Hermes should provide a
command that calls Hermes-native install, update, uninstall, login item, log,
health, repair, supervision, and distribution APIs behind that contract.
P3.2 conformance validates that host-owned command from the runtime side; it
does not make Runtime Kit the distributor of Hermes binaries.

## Distribution

A public install can be distributed from a Git repository or Hermes plugin registry. A dedicated server is not required just to satisfy:

```bash
hermes plugins install <owner-or-repo>/kaka-mobile --no-enable
hermes plugins enable kaka-mobile
```

For local development, Hermes can install from a local checkout or Git URL if its plugin loader supports that source.

The production distribution target is a Host Extension package with:

- the Hermes plugin manifest
- Runtime Kit launcher integration
- Pocket Agent Mobile Bridge settings and pairing UI
- an extension-internal `hermes-kaka-host-api` command or host-owned discovery
  hook
- P3.2 conformance evidence
- P3.4 pilot handoff, artifact review, and evidence manifest outputs
- P3.6 readiness metadata for install command, update channel, signed package
  ref, signature/notarization ref, extension-internal command location, and host
  UI entry point

Users should see Install, Enable Pocket Agent Mobile Bridge, Show QR, optional Bonjour,
Health Check, Revoke iPhone, Update, Uninstall, and Open Logs. They should not
see instructions to write adapter code or export `HERMES_KAKA_HOST_API`.

P3.12 makes this easier to implement by adding a Runtime Kit
`host-extension-starter-kit` command. The command prints or writes a safe Hermes
starter tree with README, manifest, extension-internal
`hermes-kaka-host-api` README, runtime contract command files, and release-gate
metadata. It is packaging input for the Hermes host team, not a final signed
public package, and it must not install the plugin, start the bridge, bind LAN,
advertise Bonjour, mint tokens, create login items, or invoke private Hermes
commands.

P3.13 turns that starter output into a package-shaped handoff for the Hermes
host team: Hermes Plugin manifest files, Pocket Agent Mobile Bridge host UI contract,
install-drill runbook, release-gate commands, and the extension-internal
`hermes-kaka-host-api` README. It still leaves signing, update channels,
proprietary Hermes implementation, conformance evidence, and public distribution
with Hermes.

P3.15 adds `host-plugin-skill-devkit` as a host-team developer materials index
on top of P3.12/P3.13. It may emit contract indexes, command files, acceptance
gates, adapter templates, and optional Codex automation templates. Treat any
future Codex developer plugin or Codex skill as host-team automation only; the
ordinary-user installer remains this host-native Hermes Plugin.

P3.35 now adds the host-native Plugin/Skill installation blueprint while
external P3.7 package facts remain blocked:
`../../docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
For Hermes, that blueprint clarifies
the plugin manifest, Pocket Agent Mobile Bridge panel entry point, disabled install
defaults, explicit Enable/Start, QR/Bonjour, local TLS status, Revoke iPhone,
health, logs, update, repair, uninstall, and evidence refs. It must stay
read-only or generative until Hermes supplies real package materials; it should
not become a public Codex plugin, run the private adapter, start the bridge, or
write user-home Codex plugin/skill roots.

P3.16/P3.17 clarify the current photo-edit renderer truth for that plugin:
`recipe_local` is the default local renderer, it produces the **Master** and
**Social** JPEG variants, and the bridge should advertise
`photo_edit.return_variants_max: 2` and
`photo_edit.accepted_mime_types: ["image/jpeg"]` for this local contract.

## Bridge Command

The plugin can use Runtime Kit's settings preview as its JSON shell contract:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit settings-preview \
  --bridge-enabled \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile <profile> \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --recall-search-provider fixture
```

The preview includes `runtime_side_ui.consumer_ui` for the visible renderer model,
`runtime_side_ui.process_ownership` for install/start-at-login/update/uninstall
and process repair actions, `runtime_side_ui.controls` for the backing settings,
`actions.start_bridge` for the exact command to launch after explicit approval,
`actions.show_qr` for the pairing page, and a nested `phone_safe_summary` that
excludes paths, endpoints, keys, tokens, TLS private key paths, embeddings, and
index rows.

Hermes shells can also ask Runtime Kit for a packaging wrapper around the same
contract:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit package-preview \
  --runtime hermes \
  --hermes-profile <profile>
```

The package preview adds install defaults, runtime-only field classification,
consumer UI metadata, process ownership metadata, and security status while
continuing to derive bridge actions from `settings-preview`.

Hermes host adapters can request the P2.8 packaging handoff contract directly:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-package-preview \
  --runtime hermes \
  --distribution-source local_checkout \
  --distribution-channel development \
  --package-version development
```

This JSON is the host shell contract for rendering package source, disabled
install defaults, host-owned lifecycle actions, and safe command artifacts. It is
not a call into a private Hermes installer/update/login-item API. P3.3 adds
`host-package-preview.private_adapter_package` to the same non-mutating preview
so Hermes can render host-owned private command discovery, distribution, update,
signature, and conformance-gate metadata without executing the command.

Hermes host shell checklist:

- Treat P3.5 Host Extension packaging as the ordinary-user path. Manual
  `--private-adapter-command` and `HERMES_KAKA_HOST_API` discovery are
  development/pilot fallback paths, not the stable install UX.
- Use the implemented P3.6 `host-extension-readiness` contract as the
  release-readiness check for real Hermes Plugin distribution facts. It is
  read-only and must not install the plugin, invoke `hermes-kaka-host-api`,
  start the bridge, or mark P3.4 complete.
- Render `host-package-preview.private_adapter_package` next to the package and
  lifecycle controls.
- Resolve the host-owned command in order from explicit
  `--private-adapter-command` / Hermes `private_adapter_command` config,
  `HERMES_KAKA_HOST_API`, `host_private_adapter.command` in the manifest, or the
  well-known path
  `~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api`.
- Generate `host-shell-pilot-request` first and send it to the Hermes host team
  so they know which host-owned binary, contract acknowledgement, 9-action
  matrix, distribution/signature/update/drill evidence, release notes, audit
  refs, and Runtime Kit JSON artifacts they must provide.
- Run `host-shell-pilot-preflight` before conformance/report/handoff to show
  missing local host inputs without invoking the private command.
- Generate `host-shell-pilot-runbook` before conformance/report/handoff so the
  operator has the brief, pilot target, preflight summary, ordered steps,
  command artifacts, evidence requirements, and acceptance gates.
- After request, preflight, conformance, pilot receipt, and handoff JSON
  artifacts exist, run `host-shell-pilot-artifact-review` before external
  review.
- After artifact review is ready, run `host-shell-pilot-evidence-manifest` to
  hash the local JSON artifacts for the external host-owned archive; Runtime Kit
  does not create that archive.
- Require a signed or explicitly host-approved `hermes-kaka-host-api` command
  binary before exposing stable install/update distribution as ready.
- Run `host-private-adapter-conformance` and require a passing
  `kaka.host_private_adapter_conformance.v1` report before showing install or
  update as ready.
- Keep command paths, logs, process IDs, update feeds, signatures, tokens,
  provider settings, and runtime store paths on the Hermes runtime side only.

Hermes can execute the P2.9 host adapter binding surface from the runtime side:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Mutating actions require explicit user approval:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id install_runtime_package \
  --approved
```

When Hermes has a host-private API command, pass it explicitly:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Hermes should render `host-package-preview`, then execute host actions through
`host-adapter-run` when the user approves. Host adapter results are runtime-side
only and must not be copied into Pocket Agent iPhone settings. The phone continues to
connect to Hermes only through Pocket Agent Mobile Bridge `/mobile/v1`. Runtime Kit
invokes the private command with `shell=False`, sends JSON on stdin, reads JSON
from stdout, and converts missing, failed, invalid, or timed-out command results
into structured safe adapter failures. Mutating private actions still require
`--approved`; the private command is never a phone-facing API.

Before treating a host-private command as ready for real packaging, Hermes
should generate the P3.4i materials request for the host team, then run the
P3.4f preflight, print the P3.4g host operator runbook, and run the P3.2
runtime-side conformance report:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime hermes \
  --request-id P3.4-hermes \
  --pilot-owner "Hermes host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --artifact-root artifacts/hermes
```

`host-shell-pilot-request` emits schema
`kaka.host_shell_pilot_request.v1` on surface
`hermes_openclaw_host_shell_pilot_request`. It is a read-only request bundle for
the Hermes host team and lists the host-owned private adapter command binary,
request/response contract acknowledgement, 9-action matrix, native distribution
channel, signature/notarization, update feed, install/update/failure-recovery
drill receipts, release notes, required audit refs
(`native_channel_ref`, `signature_subject`, `notarization_team_id`,
`update_feed_ref`, `install_receipt_ref`, `update_receipt_ref`,
`failure_recovery_receipt_ref`, `release_notes_ref`), and expected Runtime Kit
artifacts (`preflight.json`, `conformance.json`, `pilot-receipt.json`,
`handoff.json`, `artifact-review.json`). `request_status: "ready_to_send"` and
`ok: true` only mean the request package was generated; it still reports
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`. It does not invoke the private
adapter command, run preflight or conformance, read artifacts, fetch audit refs,
mutate host state, submit handoff, or change the iPhone `/mobile/v1` surface.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The preflight emits `kaka.host_shell_pilot_preflight.v1` on
`hermes_openclaw_host_shell_pilot_preflight`. It checks Hermes app/CLI presence,
explicit/env/manifest/well-known private command discovery, and PATH command
availability as informational-only. It does not invoke the private adapter
command, run conformance, fetch audit refs, mutate host state, or expose phone
`/mobile/v1`; `ok: true` / `status: "ready_for_conformance"` only means
conformance can run next and still keeps `p3_4_complete: false`.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The runbook emits `kaka.host_shell_pilot_runbook.v1` on
`hermes_openclaw_host_shell_pilot_runbook`. It composes P3.4f preflight only and
adds operator steps, command artifacts, evidence requirements, and acceptance
gates. It does not invoke the private adapter command, run conformance, fetch
evidence refs, mutate host state, or expose phone `/mobile/v1`; `ok: true` /
`runbook_status: "ready_for_conformance"` means ready to run conformance next,
not ready to submit handoff and not P3.4 complete. It always reports
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

P3.4h artifact review waits until the request, preflight, conformance report,
pilot receipt, and handoff JSON artifacts already exist; it is not a
replacement for the request, runbook, or the conformance run.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The report uses the same P3.1 `host-adapter-run --adapter private` behavior and
checks install, login-item, update, uninstall, logs, health, port repair, and
supervision. It is evidence for the configured Hermes-owned command only:
distribution, command discovery, update channels, and proprietary Hermes
binaries remain owned by Hermes, not by Kaka or Runtime Kit.

## P3.4a Pilot Receipt Checklist

Before Pocket Agent can mark P3.4 complete, the Hermes host shell must provide:

- host-owned private adapter command outside the Pocket Agent repository, preferably
  bundled or internally discovered by the Hermes Plugin rather than manually
  configured by the user
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
proprietary Hermes private adapter binary. If Hermes does not pass an explicit
command, the report may discover it from `HERMES_KAKA_HOST_API`, the manifest
entrypoint, then the well-known path; if discovery finds no real external
command, the receipt remains `not_ready`. Local fake fixtures and local
conformance are `synthetic_only` and cannot mark P3.4 complete. P3.4 requires a
real host-owned `hermes-kaka-host-api` binary outside this repository.

For P3.4e release review, Hermes should print the machine-readable external
pilot handoff package with `host-shell-pilot-handoff`. It wraps the same
`host-shell-pilot-report` receipt in schema
`kaka.host_shell_pilot_handoff.v1` on surface
`hermes_openclaw_host_shell_pilot_handoff`, adds deliverables,
`release_handoff`, P3.4d `audit_refs` completeness, and safety flags, and
does not change the receipt readiness result. The handoff is
`ready_to_submit` only when all P3.4d audit refs are present; otherwise it is
`incomplete`. It always reports `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`, because final P3.4 completion
remains Hermes-owned. Runtime Kit does not fetch audit refs, expose phone
`/mobile/v1`, or bundle the proprietary Hermes command.

Example:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-handoff \
  --runtime hermes \
  --private-adapter-command "/Users/kartz/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
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

After handoff, Hermes can summarize the four already-generated artifacts for
external review:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime hermes \
  --preflight-json artifacts/hermes/preflight.json \
  --conformance-json artifacts/hermes/conformance.json \
  --receipt-json artifacts/hermes/pilot-receipt.json \
  --handoff-json artifacts/hermes/handoff.json
```

`host-shell-pilot-artifact-review` emits schema
`kaka.host_shell_pilot_artifact_review.v1` on surface
`hermes_openclaw_host_shell_pilot_artifact_review`. It summarizes load/schema
status and cross-checks runtime, embedded conformance, embedded receipt,
audit refs, and private command consistency. It reports
`review_status: "ready_for_external_review"` only when the artifacts are ready
and consistent. It does not invoke the private adapter command, run
conformance, fetch refs, mutate host state, expose phone `/mobile/v1`, or mark
P3.4 complete; it always keeps `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

After artifact review, Hermes can generate a local evidence manifest for the
external host-owned archive:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime hermes \
  --package-id P3.4-hermes \
  --artifact-root artifacts/hermes \
  --request-json artifacts/hermes/request.json \
  --runbook-json artifacts/hermes/runbook.json \
  --archive-filename kaka-p3.4-hermes-pilot-evidence.zip
```

`host-shell-pilot-evidence-manifest` emits schema
`kaka.host_shell_pilot_evidence_manifest.v1` on surface
`hermes_openclaw_host_shell_pilot_evidence_manifest`. It reads local JSON files,
records byte sizes and SHA-256 hashes, blocks missing or invalid artifacts, and
can report `ready_for_archive`. It does not invoke the private adapter command,
run conformance, fetch refs, submit handoff, mutate host state, create the
archive, expose phone `/mobile/v1`, or mark P3.4 complete.

The plugin should call the runtime-kit launcher directly instead of asking users to type this command:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile <profile>
```

If Hermes exposes a local vision endpoint for Pocket Agent image-conversation vision skills, the plugin should pass it explicitly:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile <profile> \
  --vision-provider runtime_http \
  --vision-endpoint http://127.0.0.1:<hermes-port>/kaka/vision
```

Without `runtime_http`, scan/identify/translate/food use `fixture_vision`, which is only useful for deterministic UI testing and will not identify real camera content.

The command is included for development transparency only. It is not the desired consumer onboarding UX.

## Safety Checklist

- No auto-start during install.
- No provider API keys copied into Pocket Agent iPhone.
- Local-only default; LAN/Bonjour require explicit enable.
- Pairing code is short-lived in production.
- Bridge token can be revoked from Hermes.
- Development pairing may use `/mobile/v1/pairing/dev.html`; production mode uses short-lived single-use QR payloads, runtime-side revocation metadata, and trusted local TLS status.
- `host-package-preview`, `process_ownership`, and `host-adapter-run` actions are runtime-side contracts; Hermes must require explicit approval for mutating actions.
- `mock` adapter results are for conformance/local QA; `private` adapter results come only from the configured Hermes host-private command, or structured unavailable when no command is configured.
- `host-private-adapter-conformance` is runtime-side evidence for a host-owned command and must not be exposed as a Pocket Agent iPhone setting or imply Kaka bundles Hermes proprietary binaries.
- Install must not auto-start the bridge or create a login item.
- Photo assets remain under the user's local runtime retention policy.
- Store paths and Recall provider endpoints stay in the Hermes runtime UI and must not be copied into Pocket Agent iPhone settings.
- Provider API keys, bearer tokens, auth files, hidden prompts, raw embeddings, and raw provider responses must not be printed.
