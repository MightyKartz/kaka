# Kaka Runtime Packaging Contract

This directory defines the runtime-side packaging shell for Kaka Mobile Bridge.
It is a machine-readable scaffold for Hermes/OpenClaw adapters, not a production
installer.

P3.1's private-adapter boundary is a host-private command bridge contract. This
repository defines the request/response shape and the `host-adapter-run`
invocation surface; it does not bundle proprietary Hermes/OpenClaw private API
implementations. Hermes or OpenClaw should expose those native distribution,
install, login item, update, uninstall, log, health, port-repair, and supervision
capabilities behind a host command supplied with `--private-adapter-command`.

P3.2 adds a conformance report for that boundary. The
`host-private-adapter-conformance` CLI is still Mac/runtime-side only: it takes
a host-owned command, validates the P3.1 private adapter behavior, and leaves
distribution, command discovery, and proprietary Hermes/OpenClaw binaries owned
by the host shell.

P3.3 adds package-contract metadata for that host-owned command. Runtime Kit now
embeds a top-level `private_adapter_package` object in `host-package-preview`;
the preview remains non-mutating and does not execute, download, install, or
validate the private command by itself.

P3.4i adds a host-shell pilot materials request before preflight/conformance.
`host-shell-pilot-request` is read-only: it lists what the Hermes/OpenClaw host
team must provide, including the host-owned private adapter command binary,
request/response contract, action matrix, distribution/signature/update/drill
evidence, release notes, audit refs, and expected Runtime Kit JSON artifacts. It
does not invoke the private adapter command, run preflight or conformance, fetch
audit refs, mutate host state, submit handoff, expose phone `/mobile/v1`, or
mark P3.4 complete.

P3.4f adds a host-shell pilot preflight before conformance, pilot report, and
handoff. `host-shell-pilot-preflight` is read-only: it checks local host shell
app/CLI presence, private adapter command discovery inputs, and PATH command
availability as informational-only diagnostics. It emits
`kaka.host_shell_pilot_preflight.v1` on
`hermes_openclaw_host_shell_pilot_preflight`, does not invoke the private
adapter command, does not fetch audit refs, does not mutate host state, does not
expose phone `/mobile/v1`, and keeps `p3_4_complete: false`.

P3.4g adds a host-shell pilot runbook before conformance, pilot report, and
handoff. `host-shell-pilot-runbook` is read-only: it generates a brief, pilot
target, preflight summary, ordered operator steps, command artifacts, evidence
requirements, and acceptance gates for the external host team. It does not
invoke the private adapter command, run conformance, fetch audit refs, mutate
host state, expose phone `/mobile/v1`, or mark P3.4 complete.

P3.4h adds a host-shell pilot artifact review after the host operator has run
the sequence. `host-shell-pilot-artifact-review` is read-only: it loads
preflight, conformance, pilot receipt, and handoff JSON artifacts, checks their
schema identity, runtime alignment, embedded conformance/receipt consistency,
audit-ref completeness, and private command consistency. It does not invoke the
private adapter command, rerun conformance, fetch audit refs, mutate host state,
submit handoff, expose phone `/mobile/v1`, or mark P3.4 complete.

P3.4j adds a host-shell pilot evidence manifest after artifact review.
`host-shell-pilot-evidence-manifest` is read-only: it hashes local preflight,
conformance, pilot receipt, handoff, and artifact-review JSON artifacts, can
include request/runbook JSON, and reports whether the package is ready for an
external host-owned archive. It does not invoke the private adapter command,
rerun conformance, fetch audit refs, submit handoff, create the archive, expose
phone `/mobile/v1`, or mark P3.4 complete.

P3.5 adds the installable Host Extension layer. Runtime Kit exposes a
`host-extension-preview` contract for Hermes Plugin and OpenClaw Skill/sidecar
packaging so ordinary users install one host extension, enable Kaka Mobile
Bridge, and pair by QR or Bonjour. The private adapter command remains
host-owned but becomes extension-internal; explicit command paths and
`HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API` are developer or pilot fallback
inputs, not ordinary-user setup requirements.

P3.6 adds a read-only `host-extension-readiness` contract. It collects the real
Plugin/Skill install command, update channel,
extension-internal adapter command location, host UI entry point, signed package
ref, signature/notarization ref, P3.2 conformance report ref, and P3.4 evidence
manifest ref, then reports `blocked` or `ready_for_external_install_drill`.
It must not install packages, invoke private commands, fetch audit refs, start
the bridge, bind LAN, advertise Bonjour, mint credentials, create login items,
or mark P3.4 complete. P3.6 also hardens the P3.5 schemas so `runtime` is
bound to install shape, command names, env vars, well-known paths, and
manifest entrypoints; keep ordinary-user sources separate from developer/pilot
fallback sources.

The 2026-06-07 no-input P3.6 audit leaves both Hermes and OpenClaw blocked on
all eight host-owned inputs. The packaging next step is external material
collection, not another repository-only wrapper. Use
`../../docs/kaka-host-extension-external-materials.md` to collect the first
real Plugin/Skill install command, update channel, extension-internal adapter
location, host UI entry point, signed package ref, signature/notarization ref,
P3.2 conformance report ref, and P3.4 evidence manifest ref before running an
external install drill.

P3.28 adds read-only Host Extension material intake for that external waiting
state. `host-extension-material-intake` reviews a local
`kaka.host_extension_materials.v1` manifest containing host-owned Plugin/Skill
package facts and install-drill refs, embeds the existing P3.6 readiness result,
and emits `kaka.host_extension_material_intake.v1`. It does not install, sign,
publish, fetch refs, start the bridge, bind LAN, advertise Bonjour, mint mobile
tokens, invoke private adapters, write Codex user-home roots, or change
`/mobile/v1`.

P3.8 adds a read-only local TLS readiness contract. `local-tls-readiness`
collects certificate label/ref, public-key SHA-256 fingerprint, expiry, trust
store ref, and renewal procedure ref so Hermes/OpenClaw shells can gate
production QR/LAN pairing on non-secret TLS metadata. It does not generate
certificates, install trust, modify Keychain, read private keys, start the
bridge, bind LAN, advertise Bonjour, mint mobile tokens, fetch refs, or expose
private host APIs to iPhone.

P3.15 adds the Host Plugin/Skill Devkit layer. `host-plugin-skill-devkit` is a
template-only host-team materials index over the existing starter-kit,
install-package, readiness, conformance, and evidence contracts. It may write a
developer bundle with contract indexes, command files, acceptance gates,
ordinary-user boundary metadata, adapter templates, and Codex automation
templates. It must not create a third install package, real Codex plugin, real
host `SKILL.md`, marketplace entry, bin adapter stub, package-manager call,
signed package, bridge process, private adapter invocation, conformance run, or
phone-side private host API.

P3.18 adds the Host Codex developer plugin source layer. It is the first slice
allowed to generate real Codex plugin source files, but only for host engineers
and only under an explicit output directory. Its schema and manifests prove
`ordinary_user_install: false`, `installs_codex_plugin: false`,
`updates_marketplace: false`, `writes_user_home: false`, and no phone API
change. The writer rejects user-home install roots such as `~/plugins`,
`~/.codex/skills`, and `~/.agents/plugins`, and uses runtime-specific source
roots to avoid Hermes/OpenClaw output collisions.
This layer does not change the packaging lifecycle: release proof still comes
from the host-native Hermes Plugin / OpenClaw Skill install drill.

P3.19 strengthens the Host Extension install experience without changing the
packaging lifecycle. `host-extension-install-package` now emits acceptance-grade
host UI metadata, a generated `host-ui/acceptance.json`, ordered install-drill
steps, evidence receipt refs, TLS/readiness/evidence/Codex developer source
release gates, and static manifest/schema drift protection. It does not add a
new packaging command, install/sign/publish packages, start the bridge, invoke
private adapters, or present Codex developer automation as the ordinary-user
installer.

P3.35 is implemented as the install-focused refinement while real P3.7
materials are still blocked:
`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
The existing `host-extension-install-package` schema and materialized output now
include `installation_blueprint` and `host-ui/installation-blueprint.json`. It
stays declarative: no new command, no package install/sign/publish, no bridge
startup, no private adapter invocation, no Codex user-home writes, and no
`/mobile/v1` change.

## Contract Files

- `settings-preview.schema.json` freezes the JSON produced by
  `python3 -m kaka_mobile_runtime_kit settings-preview`.
- `runtime-shell-manifest.schema.json` freezes the static Hermes/OpenClaw shell
  manifest shape.
- `host-package.schema.json` freezes the JSON produced by
  `python3 -m kaka_mobile_runtime_kit host-package-preview`.
- `host-adapter-action-result.schema.json` freezes the JSON produced by
  `python3 -m kaka_mobile_runtime_kit host-adapter-run`.
- `host-private-adapter-request.schema.json` freezes the sanitized JSON request
  Runtime Kit sends to a configured host-private adapter command on stdin.
- `host-private-adapter-response.schema.json` freezes the JSON response the host
  command returns to Runtime Kit on stdout.
- `host-private-adapter-conformance.schema.json` freezes the runtime-side report
  produced by `python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance`.
- `host-private-adapter-package.schema.json` freezes the P3.3
  `private_adapter_package` object embedded in `host-package-preview`.
- `host-extension-preview.schema.json` freezes the P3.5
  `kaka.host_extension_preview.v1` Host Extension productization contract emitted
  by `python3 -m kaka_mobile_runtime_kit host-extension-preview`.
- `host-extension-readiness.schema.json` freezes the P3.6
  `kaka.host_extension_readiness.v1` distribution readiness contract emitted by
  `python3 -m kaka_mobile_runtime_kit host-extension-readiness`.
- `host-extension-materials.schema.json` freezes the P3.28 local
  `kaka.host_extension_materials.v1` manifest supplied by Hermes/OpenClaw host
  teams for package-fact and install-drill ref review.
- `host-extension-material-intake.schema.json` freezes the P3.28
  `kaka.host_extension_material_intake.v1` read-only review report emitted by
  `python3 -m kaka_mobile_runtime_kit host-extension-material-intake`.
- `local-tls-readiness.schema.json` freezes the P3.8
  `kaka.local_tls_readiness.v1` local TLS certificate readiness contract emitted
  by `python3 -m kaka_mobile_runtime_kit local-tls-readiness`.
- `host-plugin-skill-devkit.schema.json` freezes the P3.15
  `kaka.host_plugin_skill_devkit.v1` Host Plugin/Skill developer materials
  contract emitted by
  `python3 -m kaka_mobile_runtime_kit host-plugin-skill-devkit`.
- `host-codex-developer-plugin-source.schema.json` freezes the P3.18
  `kaka.host_codex_developer_plugin_source.v1` host-team Codex developer plugin
  source contract emitted by
  `python3 -m kaka_mobile_runtime_kit host-codex-developer-plugin-source`.
- `host-shell-pilot-request.schema.json` freezes the P3.4i
  `kaka.host_shell_pilot_request.v1` materials request emitted by
  `python3 -m kaka_mobile_runtime_kit host-shell-pilot-request`.
- `host-shell-pilot-preflight` emits the P3.4f
  `kaka.host_shell_pilot_preflight.v1` local-input diagnostic before
  conformance, pilot report, or handoff.
- `host-shell-pilot-runbook.schema.json` freezes the P3.4g
  `kaka.host_shell_pilot_runbook.v1` operator runbook emitted by
  `python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook`.
- `host-shell-pilot-artifact-review.schema.json` freezes the P3.4h
  `kaka.host_shell_pilot_artifact_review.v1` post-run artifact review emitted
  by `python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review`.
- `host-shell-pilot-evidence-manifest.schema.json` freezes the P3.4j
  `kaka.host_shell_pilot_evidence_manifest.v1` local evidence index emitted by
  `python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest`.
- `HOST_PRIVATE_ADAPTER_IMPLEMENTATION.md` is the host-team author guide for
  implementing a real external `hermes-kaka-host-api` or
  `openclaw-kaka-host-api` command without moving proprietary APIs into Kaka.
- `examples/` contains schema-checked golden request, response, invalid
  response, and pilot receipt JSON for external adapter authors.
- `../hermes-plugin/kaka-mobile-bridge.package.json` is the Hermes shell
  manifest.
- `../openclaw-skill/kaka-mobile-bridge.sidecar.json` is the OpenClaw sidecar
  manifest.

## Lifecycle

The runtime package lifecycle is intentionally conservative:

1. `installed_disabled`
2. `enabled_by_user`
3. `running_after_explicit_start`
4. `stopped_by_user`

Installing a package must not start a listener, bind a port, advertise Bonjour,
or mint mobile credentials. Start with runtime/login is an opt-in setting,
default false, and must be changed only by explicit user approval.
Installing a Hermes Plugin or OpenClaw Skill may stage the host-owned private
adapter command inside the extension package, but it must not execute the
command, start the bridge, bind LAN, advertise Bonjour, mint credentials, or
create a login item during install.

## Runtime-Side Controls

Hermes/OpenClaw shells should render `settings-preview.runtime_side_ui.consumer_ui`
as the primary settings UI model and
`settings-preview.runtime_side_ui.process_ownership` as the process lifecycle
model. `consumer_ui` contains status badges, primary actions, warnings, empty
state, and five sections: Process, Connection, Pairing, Local Memory, and Recall
Retrieval. `process_ownership` covers install, start-at-login/start-with-runtime,
update, uninstall, open logs, run health check, and repair port conflict actions.
`runtime_side_ui.controls` remains the low-level control dictionary that backs
those sections.

The low-level controls include:

- `bridge_enabled`
- `start_with_runtime`
- `bind_mode`
- `bonjour_enabled`
- `pairing_mode`
- `qr_ttl_seconds`
- `trusted_local_tls`
- `revoke_mobile_tokens`
- `local_store_enabled`
- `runtime_store_path`
- `recall_search_provider`
- `recall_search_endpoint`
- `install_runtime_package`
- `update_runtime_package`
- `uninstall_runtime_package`
- `open_runtime_logs`
- `run_health_check`
- `repair_port_conflict`

`actions.start_bridge` is a spawnable argument list. Shells should launch it
after explicit approval instead of asking users to copy a command. `actions.stop_bridge`
is scoped to the process that the shell started.

The process ownership actions remain runtime-side. P2.8 adds the
`host-package-preview` JSON handoff contract, schema, static manifest declaration,
and safe command artifacts so host shells can wire packaging flows consistently:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-package-preview \
  --runtime hermes \
  --distribution-source local_checkout \
  --distribution-channel development \
  --package-version development
```

This handoff contract is not a private Hermes/OpenClaw host API. Runtime Kit
does not create login items or LaunchAgents, auto-start the bridge, install or
delete apps, run updaters, open native log windows, or supervise processes.
P2.9 adds `host-adapter-run` as the Mac/runtime-side action execution surface
for those declared actions:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id install_runtime_package \
  --approved
```

The phone still connects only through Kaka Mobile Bridge `/mobile/v1`; host
adapter result JSON is runtime-side only and must not become phone settings. The
`mock` adapter is for conformance and local QA and must not mutate the actual
host OS.

Host-team/development/pilot only: P3.1 `private` mode is configured by the host
shell with a command bridge:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Runtime Kit invokes that command with `shell=False`, sends a sanitized
`kaka.host_private_adapter_request.v1` JSON request on stdin, and expects a
`kaka.host_private_adapter_response.v1` JSON response on stdout. Missing command
configuration returns `private_host_adapter_unavailable`; non-zero, invalid JSON,
invalid schema, or timeout cases return structured safe failures with
`mutated_host_state: false`. Mutating actions still require explicit user
approval through `--approved`, and install must not start the bridge, bind a
port, advertise Bonjour, mint credentials, or create a login item. The iPhone
never calls the private command and must not see private adapter details.

P3.2 conformance validates a host-owned private adapter command across the
runtime lifecycle matrix.

Generate the P3.4i request first so the host team has a machine-readable list of
materials to provide:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime hermes \
  --request-id P3.4-hermes \
  --pilot-owner "Hermes host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --artifact-root artifacts/hermes
```

The request can be generated even before the command exists. `ok: true` means
the request bundle is ready to send; it does not mean the host has provided the
command or evidence, and it never marks P3.4 complete.

Then run P3.4f preflight to see which local host inputs are missing:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The preflight checks explicit `--private-adapter-command`, the runtime env var,
manifest `host_private_adapter.command`, and the well-known path before
reporting `status: "ready_for_conformance"`. PATH command discovery is included
only as host-facing information. `ok: true` means ready to run conformance next,
not ready to mark P3.4 complete.

Then print the P3.4g runbook to show the host-owned execution sequence and
evidence requirements:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The runbook includes command artifacts for `host-shell-pilot-preflight`,
`host-private-adapter-conformance`, `host-shell-pilot-report`, and
`host-shell-pilot-handoff`, plus the eight P3.4d evidence refs and acceptance
gates. `ok: true` means `ready_for_conformance`; it does not mean the handoff is
ready to submit or that P3.4 is complete.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The conformance runner invokes the configured command only through the P3.1
`host-adapter-run --adapter private` behavior and reports on install,
login-item, update, uninstall, logs, health, port repair, and supervision cases.
It is not a phone settings API, not a distribution channel, and not proof that
Kaka owns or distributes Hermes/OpenClaw proprietary binaries. Real package
distribution and command binary ownership stay in the Hermes/OpenClaw host
manifest and installer flow.

After generating the four run artifacts, review them without rerunning host
commands:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime hermes \
  --preflight-json /path/to/preflight.json \
  --conformance-json /path/to/conformance.json \
  --receipt-json /path/to/receipt.json \
  --handoff-json /path/to/handoff.json
```

The artifact review can report `ready_for_external_review`, but it still keeps
`p3_4_complete: false`; final pilot completion remains external-host-owned.

After artifact review is ready, generate the evidence manifest without creating
the external archive:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime hermes \
  --package-id P3.4-hermes \
  --artifact-root artifacts/hermes \
  --request-json artifacts/hermes/request.json \
  --runbook-json artifacts/hermes/runbook.json \
  --archive-filename kaka-p3.4-hermes-pilot-evidence.zip
```

With `--artifact-root`, Runtime Kit looks for `preflight.json`,
`conformance.json`, `pilot-receipt.json`, `handoff.json`, and
`artifact-review.json`. The manifest records byte sizes and SHA-256 hashes only.
`ready_for_archive` means the local JSON set can be archived by the external host
shell; Runtime Kit still does not create the archive or mark P3.4 complete.

P3.3 host package previews include the release gate and discovery metadata that
the host shell must satisfy before stable distribution:

- `schema_version`: `kaka.host_private_adapter_package.v1`
- `surface`: `hermes_openclaw_host_private_adapter_package`
- binary owner: `host_shell`, `repository_owner: hermes_or_openclaw`, and
  `private_api_implementation: not_bundled_in_kaka`
- default command names: `hermes-kaka-host-api` and `openclaw-kaka-host-api`
- discovery sources, in resolution order: explicit
  `--private-adapter-command` / host config key `private_adapter_command`, env
  vars `HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, manifest entrypoint
  `host_private_adapter.command`, and well-known paths under
  `~/Library/Application Support/<Runtime>/Kaka/`
- distribution policy: host-owned `source`, `channel`, and `version`,
  `update_policy: explicit_user_approved`, `download_owner: host_shell`, and
  `signature_policy: host_shell_required`
- validation gate: `requires_conformance_passed: true`,
  `report_schema: kaka.host_private_adapter_conformance.v1`, and the
  `host-private-adapter-conformance` command artifact
- mobile boundary: `phone_api_path: /mobile/v1` and `phone_api_unchanged: true`

This is metadata for Hermes/OpenClaw release flows, not a bundled private API
implementation. Kaka does not own, distribute, or bundle proprietary
Hermes/OpenClaw private API binaries.

## P3.4a External Host Shell Pilot Receipt

`host-shell-pilot-report` records whether a Hermes/OpenClaw host-owned private
adapter binary is ready for the first external dogfood pilot. Runtime Kit
verifies and records readiness evidence only; it does not own, build, sign,
distribute, install, update, or bundle the proprietary host binary.

The command can run in three states:

- `not_ready`: no real external command or missing host distribution/drill evidence.
- `synthetic_only`: local fake fixture conformance passed, useful for Runtime Kit
  regression checks only. `synthetic_only` cannot mark P3.4 complete.
- `ready`: real external command outside this repository passed conformance and
  the host supplied native distribution, signature, update, install/update/failure
  drill, and release-note evidence.

P3.4b command discovery is still host-owned. If
`--private-adapter-command` is omitted, `host-shell-pilot-report` resolves the
runtime env var, manifest entrypoint, then well-known path; if no real external
command is found, the receipt remains `not_ready`.

P3.4d keeps the verified boolean gate unchanged and adds optional host-supplied
evidence refs for audit trails. Distribution refs are
`distribution.evidence.native_channel_ref`,
`distribution.evidence.signature_subject`,
`distribution.evidence.notarization_team_id`, and
`distribution.evidence.update_feed_ref`. Drill refs are
`drills.evidence.install_receipt_ref`,
`drills.evidence.update_receipt_ref`,
`drills.evidence.failure_recovery_receipt_ref`, and
`drills.evidence.release_notes_ref`.

These refs do not automatically set `native_channel_verified`,
`signature_verified`, `update_feed_verified`, `install_verified`,
`update_verified`, `failure_recovery_verified`, or `release_notes_verified`.
Runtime Kit records the supplied strings only; it does not download, read, or
validate external artifacts behind the refs. They are not exposed through the
phone `/mobile/v1` API and must not contain secrets, raw logs, private keys,
provider keys, bearer tokens, mobile tokens, or other credentials.

Example:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-report \
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
  --notarization-team-id "TEAMID1234" \
  --update-feed-ref "https://example.invalid/hermes/kaka/update-feed.json" \
  --install-receipt-ref "host-pilot://hermes/install/2026-06-06" \
  --update-receipt-ref "host-pilot://hermes/update/2026-06-06" \
  --failure-recovery-receipt-ref "host-pilot://hermes/failure-recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/hermes/kaka/release-notes/1.0.0"
```

P3.4 remains incomplete until Hermes/OpenClaw supplies a real host-owned
`hermes-kaka-host-api` or `openclaw-kaka-host-api` binary outside this
repository and the receipt reports `status: "ready"`.

## P3.4e External Pilot Handoff

`host-shell-pilot-handoff` prints the machine-readable external pilot handoff
package for host release review. It wraps the existing `host-shell-pilot-report`
receipt in schema `kaka.host_shell_pilot_handoff.v1` on surface
`hermes_openclaw_host_shell_pilot_handoff`, adds `deliverables`,
`release_handoff`, P3.4d `audit_refs` completeness, and safety flags, and keeps
the proprietary host binary outside this repository.

`handoff_status` is `ready_to_submit` only when the embedded pilot receipt is
ready and every P3.4d audit ref is supplied; otherwise it is `incomplete`.
This handoff does not change receipt readiness and does not fetch, open, or
validate audit refs. It is not a phone `/mobile/v1` API surface and it does not
bundle proprietary Hermes/OpenClaw binaries.

Even a `ready_to_submit` handoff reports `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`. Final P3.4 completion remains
external-host-owned after host release review.

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

## Network Consent

Default bind mode is loopback. LAN exposure and Bonjour advertisement require
explicit user approval. Bonjour also requires either LAN mode or a concrete
Bonjour host so the iPhone receives a reachable endpoint.

## Pairing And Revocation

Production pairing and token revocation are now represented in the runtime UI
contract. Production mode uses short-lived single-use QR payloads, exposes a
Revoke iPhone action, and can report trusted local TLS state. Process-owner UX
is represented by `runtime_side_ui.process_ownership`, and P2.8/P3.3 host
packaging handoff is represented by `host-package-preview`; P2.9 `host-adapter-run`
provides the testable runtime-side adapter action result surface. Concrete
host-native login item, update, uninstall, and supervision behavior is supplied
by the configured Hermes/OpenClaw host command, not by Runtime Kit itself. P3.2
conformance can validate that configured command, but it does not transfer
distribution or binary ownership into this repository. P3.3 adds
`private_adapter_package` metadata for host-owned command discovery,
distribution, signature policy, and release gating without changing the phone
API.

## Recall Retrieval Materials

Production Recall retrieval remains host/runtime-owned. P3.21
`recall-retrieval-readiness` records the seven non-secret refs required for
adapter package, runtime settings UI, signature, conformance, privacy review,
fallback drill, and release notes. P3.26 adds a separate local materials intake
step for host/runtime teams:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit recall-retrieval-material-intake \
  --runtime hermes \
  --materials-json artifacts/hermes/recall-retrieval-materials.json
```

The input manifest uses `kaka.recall_retrieval_materials.v1`; the output report
uses `kaka.recall_retrieval_material_intake.v1`. This command reviews local
opaque refs and embeds the P3.21 readiness snapshot. It does not fetch refs,
validate signatures, invoke providers, generate embeddings, inspect provider
keys, expose provider internals to iPhone, add retrieval internals to Recall
export, or change `/mobile/v1/recall/search`.

## Local Renderer Backend Capability Manifest

P3.27 adds a read-only local renderer backend capability planning manifest:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit local-renderer-backend-capability-manifest
```

The output uses `kaka.local_renderer_backend_capability_manifest.v1`. It records
the current Pillow/`recipe_local` local renderer contract and lists future Core
Image, ImageMagick, OpenCV, and libvips backend gates. It does not install
dependencies, import or execute future backends, run shell commands, persist
assets, call cloud providers, change the phone-facing `photo_edit` capability,
add Mobile Bridge endpoints, or change `/mobile/v1`.

## Phone-Safe Boundary

Runtime-side UI may show local paths and provider endpoints. The iPhone-facing
summary must stay allowlisted and must not include:

- SQLite/runtime store paths
- provider endpoints
- auth or env file paths
- provider credentials
- bearer or mobile tokens
- raw embeddings
- retrieval index rows
- hidden prompts
- raw provider responses
