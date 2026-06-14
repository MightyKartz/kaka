# Kaka Host Extension External Materials And Install Drill

Updated: 2026-06-11

This document is the next development handoff after P3.6. It turns the current
external waiting state into an actionable materials checklist for Hermes Plugin
or OpenClaw Skill/sidecar owners.

For the broader productization direction and the boundary between ordinary-user
Host Extensions, Runtime Kit generators, and Codex developer automation, see
`docs/kaka-host-extension-plugin-skill-roadmap.md`.

For the immediate implementation order, acceptance gates, and multi-agent split
to use before writing a new install-focused plan, see
`docs/kaka-host-extension-next-implementation.md`.

## Current Readiness Audit

Runtime Kit P3.6 is implemented, but no real host extension package materials
have been supplied yet.

The current no-input audit commands are:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness --runtime openclaw
```

Both commands currently return:

- `status: "blocked"`
- `ready_for_external_install_drill: false`
- the same eight missing input IDs:
  `install_command`, `update_channel`, `adapter_command_location`,
  `host_ui_entrypoint`, `signed_package_ref`, `signature_ref`,
  `conformance_report_ref`, and `evidence_manifest_ref`

This means the next host-extension work is not another in-repository Runtime Kit
wrapper. The next useful work is to collect real host-owned package facts and
run an external install drill.

The ordinary-user installation path has now been improved by the P3.12 Host
Extension Starter Kit plan:
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-host-extension-starter-kit.md`.
That implementation creates a safe Runtime Kit starter package contract/materializer for
Hermes Plugin and OpenClaw Skill/sidecar owners. It is still not a substitute
for real signed packages, conformance reports, or external install-drill
evidence, but it removes the wrong product posture of asking users to hand-write
adapter code.

The latest host-native package handoff slice is P3.13 Host Extension
installable package handoff:
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-host-extension-installable-package-handoff.md`.
P3.13 turns the starter-kit direction into package handoff materials that
look like a Hermes Plugin or OpenClaw Skill/sidecar: host UI contract files,
install-drill runbook, release-gate command files, manifest files, and an
extension-internal adapter command README. It still does not sign, publish,
install, update, run conformance, invoke private host APIs, or make P3.7 ready
without the eight host-owned inputs below.

Later repository-owned support slices are P3.15 Host Plugin/Skill Devkit,
P3.18 Host Codex developer plugin source, P3.19 Host Extension install
experience acceptance, P3.20 Recall export artifact policy, P3.21 Recall
retrieval packaging readiness, P3.22 asset retention timestamped purge, P3.24
SQLite-backed asset storage/retention, P3.25 store-backed task result detail
persistence, P3.26 Recall retrieval material intake/review, and P3.27 local
renderer backend capability manifest, plus P3.35 Host-Native Plugin/Skill
Installation Blueprint.
P3.15 creates template-only host-team developer
materials over the package handoff. P3.18 creates source-only Codex developer
automation for host engineers. P3.19 strengthens the existing install-package
handoff with host UI acceptance metadata, `host-ui/acceptance.json`, ordered
install-drill steps, evidence receipt refs, and TLS/readiness/evidence/Codex
developer source release gates. P3.20 is a non-installation data-boundary slice
for policy-labeled Recall export. P3.21 is a non-installation retrieval
packaging-readiness slice for host-native embeddings, sidecar adapters, or
capability-negotiated hybrids. P3.22 is a non-installation runtime data-safety
slice for explicit timestamp-aware mock bridge asset purge receipts. P3.24 is a
non-installation Runtime Kit persistence slice for store-backed input/output
asset retention. P3.25 keeps completed photo-edit result detail durable without
persisting unsafe fields. P3.26 reviews local Recall retrieval materials
manifests without fetching refs or invoking providers. P3.27 records current
local renderer truth and future backend gates without adding dependencies or
changing the phone API. P3.35 adds a machine-readable installation blueprint to
`host-extension-install-package` without adding a command or side effects. None
of these slices is the ordinary-user installer, and none replaces the
host-native Hermes Plugin / OpenClaw Skill install drill.

Product decision for follow-up development: keep this as a plugin/skill
installation path. A normal user should install one host extension, open one
host UI panel, enable Pocket Agent Mobile Bridge, then pair the iPhone by QR or Bonjour.
Manual adapter command authoring, environment variables, and Runtime Kit command
chains are development or external-pilot tools only. If a future slice improves
installation, it should improve the Hermes Plugin / OpenClaw Skill package,
host UI, drill receipts, or acceptance gates rather than exposing
`hermes-kaka-host-api`, `openclaw-kaka-host-api`, or private host APIs to Kaka
iPhone.

P3.35 is the latest repository-owned install slice while those real host-owned
materials remain unavailable. It is a host-native Plugin/Skill installation
blueprint, not a public Codex plugin or Codex skill. That blueprint makes the
future package easier for Hermes/OpenClaw teams to build by specifying:

- package manifest fields and disabled-by-default install policy;
- host UI entry point and ordinary-user copy for enabling Pocket Agent Mobile Bridge;
- explicit bridge start/stop, QR, Bonjour, local TLS, health, revoke/re-pair,
  update, logs, repair, and uninstall controls;
- extension-internal private adapter command location requirements;
- P3.2 conformance, P3.4 evidence, P3.6 readiness, P3.28 material-intake, and
  P3.7 install-drill receipt refs;
- a receipt or static test proving that any Codex plugin/skill material is
  host-team automation only.

It must stay read-only/generative: no package install, no signing/publishing,
no bridge startup, no LAN bind, no Bonjour advertisement, no token minting, no
private adapter invocation, no user-home Codex plugin/skill writes, and no phone
API change.

The P3.35 blueprint plan is implemented from
`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
It enriches `host-extension-install-package` with a machine-readable
`installation_blueprint` and
`host-ui/installation-blueprint.json` artifact that host engineers can consume
while preparing the real Hermes Plugin or OpenClaw Skill/sidecar.

## Plugin/Skill Productization Boundary

Future implementation should keep three artifacts separate:

- Ordinary-user Host Extension:
  Hermes Plugin or OpenClaw Skill/sidecar. This is the package users install.
  It owns the native install channel, update channel, host UI entry point,
  extension-internal private adapter command, signed package ref, and
  user-facing health/update/uninstall controls.
- Runtime Kit material generator:
  `host-extension-starter-kit`, `host-extension-install-package`,
  `host-plugin-skill-devkit`, readiness commands, conformance commands, and
  pilot evidence commands. These produce contracts and handoff materials for
  host teams, but they are not public installers.
- Optional Codex developer plugin or skill:
  host-team automation that can scaffold, validate, or review the same
  materials using Codex. It may be useful for Hermes/OpenClaw engineers, but it
  must not replace the host-native Plugin/Skill package that ordinary users
  install.

The next plan that touches installation must state which artifact it is
building. Mixing these surfaces is a release risk: it turns a clean user flow
back into a developer setup exercise.

## Host Package Candidate Bundle

When the user experience question is "should this be a plugin or skill?", the
next development answer is to collect a real host-native package candidate from
Hermes/OpenClaw. Do not ask ordinary users to write adapter code or install a
Codex plugin. The host owner should provide a local, sanitized bundle that can
be reviewed by Runtime Kit before any external P3.7 install drill.

Recommended bundle shape:

```text
host-package-candidate/
  materials.json
  package/
    package-ref.txt
    manifest-ref.txt
    signature-ref.txt
  host-ui/
    entrypoint.txt
    enable-flow.md
    screenshots-ref.txt
  drill-receipts/
    install.json
    enable.json
    pairing.json
    health.json
    revoke-repair.json
    update.json
    failure-recovery.json
    uninstall.json
  evidence/
    p3.2-conformance-ref.txt
    p3.4-evidence-manifest-ref.txt
    release-notes-ref.txt
```

`materials.json` must use `kaka.host_extension_materials.v1` and point to the
same non-secret refs. It should be reviewed first with:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-material-intake \
  --manifest host-package-candidate/materials.json
```

Proceed to P3.7 only when the report returns
`accepted_for_external_install_drill_review` and `host-extension-readiness`
returns `ready_for_external_install_drill`. The bundle must not include private
keys, provider keys, bearer tokens, mobile tokens, raw logs, raw embeddings,
SQLite paths, or proprietary host API source.

## Codex Developer Automation Boundary

The answer to "should this be a plugin or skill?" is yes for the ordinary-user
host integration, but not as a Codex install flow. The ordinary user should
install a host-native Hermes Plugin or OpenClaw Skill/sidecar. A Codex plugin or
Codex skill is useful only as host-team developer automation.

P3.18 now generates Codex developer plugin source for Hermes/OpenClaw
engineers, not install it. The generated tree helps a host engineer ask Codex
to scaffold the Host Extension package, run Runtime Kit readiness commands,
review release gates, and check that `/mobile/v1` remains the only phone
boundary. It is written only under an explicit output directory and uses
runtime-specific roots such as `kaka-host-extension-developer-hermes` and
`kaka-host-extension-developer-openclaw`.

P3.18 must not:

- create or update `~/.agents/plugins/marketplace.json`;
- write into `~/plugins`, `~/.codex/skills`, or `~/.agents/plugins`;
- install or enable a Codex plugin for ordinary users;
- install, sign, publish, update, or uninstall Hermes/OpenClaw packages;
- start Pocket Agent Mobile Bridge, bind LAN, advertise Bonjour, mint tokens, invoke
  private adapter commands, or run conformance;
- expose Hermes/OpenClaw private host APIs to Pocket Agent iPhone.

After P3.19/P3.20/P3.21/P3.22/P3.24/P3.25/P3.26/P3.27/P3.28, the next
installation-focused work should be P3.7 with real host-owned package facts.
Use `host-extension-material-intake --manifest /path/to/materials.json` to
review those facts first. P3.28 stays read-only and does not install, sign,
fetch, start the bridge, invoke private adapters, or create an ordinary-user
Codex installer.

## Required Host-Owned Materials

Pick the first pilot runtime: Hermes or OpenClaw. Then provide these values for
that runtime.

| Readiness input | Owner | Required meaning |
| --- | --- | --- |
| `install_command` | Hermes/OpenClaw host team | The host-owned install action or native channel action that installs the Plugin/Skill package; CLI text is only a runtime-specific ref, not a Kaka user setup requirement. |
| `update_channel` | Hermes/OpenClaw host team | The host-owned update channel name, such as development, beta, or stable. |
| `adapter_command_location` | Hermes/OpenClaw host team | The extension-internal location of `hermes-kaka-host-api` or `openclaw-kaka-host-api`. This is not a normal user setup step. |
| `host_ui_entrypoint` | Hermes/OpenClaw host team | The UI path where users enable Pocket Agent Mobile Bridge, show QR, run health, revoke iPhone, update, uninstall, and open logs. |
| `signed_package_ref` | Hermes/OpenClaw host team | A signed Plugin/Skill package reference or native distribution pointer. |
| `signature_ref` | Hermes/OpenClaw host team | Signature, notarization, or equivalent host trust evidence. |
| `conformance_report_ref` | Kaka + host team | A P3.2 `host-private-adapter-conformance` report for the real host-owned command. |
| `evidence_manifest_ref` | Kaka + host team | A P3.4 `host-shell-pilot-evidence-manifest` for the real pilot artifact set. |

Do not put secrets, raw logs, private keys, provider keys, bearer tokens, mobile
tokens, or credentials in any ref value.

Preferred material format:

- A checked-in or archived signed package ref for the Hermes Plugin or OpenClaw
  Skill/sidecar.
- A short host UI path that a normal user can follow, such as
  `Settings > Plugins > Pocket Agent Mobile Bridge`.
- JSON artifacts produced by Runtime Kit commands for readiness, P3.2
  conformance, P3.4 pilot handoff, artifact review, and evidence manifest.
- Receipt refs for install, update, failure recovery, revoke/re-pair, logs, and
  uninstall drills.
- Release notes that state the phone remains on `/mobile/v1` and that private
  adapter code stays host-owned.

## P3.28 Material Intake Manifest Shape

Host teams should provide the same material as a local manifest that Runtime Kit
can review without fetching refs or mutating host state:

```json
{
  "schema_version": "kaka.host_extension_materials.v1",
  "runtime": "hermes",
  "package_facts": {
    "install_command": "hermes plugins install example/kaka-mobile --no-enable",
    "update_channel": "Hermes stable plugin channel ref 2026-06-11",
    "adapter_command_location": "extension-internal:kaka-mobile-bridge/hermes-kaka-host-api",
    "host_ui_entrypoint": "Settings > Plugins > Pocket Agent Mobile Bridge",
    "signed_package_ref": "artifact://hermes/kaka-mobile-bridge/1.0.0/package",
    "signature_ref": "artifact://hermes/kaka-mobile-bridge/1.0.0/signature",
    "conformance_report_ref": "artifact://hermes/kaka/p3.2/conformance.json",
    "evidence_manifest_ref": "artifact://hermes/kaka/p3.4/evidence-manifest.json"
  },
  "install_drill_refs": {
    "install_receipt_ref": "artifact://hermes/kaka/p3.7/install.json",
    "enable_receipt_ref": "artifact://hermes/kaka/p3.7/enable.json",
    "pairing_receipt_ref": "artifact://hermes/kaka/p3.7/pairing.json",
    "health_receipt_ref": "artifact://hermes/kaka/p3.7/health.json",
    "revoke_repair_receipt_ref": "artifact://hermes/kaka/p3.7/revoke-repair.json",
    "update_receipt_ref": "artifact://hermes/kaka/p3.7/update.json",
    "failure_recovery_receipt_ref": "artifact://hermes/kaka/p3.7/failure-recovery.json",
    "uninstall_receipt_ref": "artifact://hermes/kaka/p3.7/uninstall.json"
  }
}
```

The P3.28 intake command embeds `host-extension-readiness`, rejects missing or
secret-like values, and outputs a review receipt. It does not install the
package, validate signatures, fetch refs, run drills, start Pocket Agent Mobile Bridge,
invoke the private adapter, or change `/mobile/v1`.

## Readiness Command With Materials

After the host team supplies real values, run the readiness contract for the
chosen runtime.

Hermes example:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness \
  --runtime hermes \
  --install-command "hermes plugin install kaka-mobile-bridge" \
  --update-channel beta \
  --adapter-command-location '$EXTENSION_ROOT/bin/hermes-kaka-host-api' \
  --host-ui-entrypoint "Settings > Plugins > Pocket Agent Mobile Bridge" \
  --signed-package-ref "hermes-plugin://kaka-mobile-bridge/1.0.0" \
  --signature-ref "notarization-team:HERMES-KAKA" \
  --conformance-report-ref "artifacts/hermes/conformance.json" \
  --evidence-manifest-ref "artifacts/hermes/evidence-manifest.json"
```

OpenClaw example:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness \
  --runtime openclaw \
  --install-command "openclaw skill install kaka-mobile-bridge" \
  --update-channel beta \
  --adapter-command-location '$EXTENSION_ROOT/bin/openclaw-kaka-host-api' \
  --host-ui-entrypoint "Settings > Skills > Pocket Agent Mobile Bridge" \
  --signed-package-ref "openclaw-skill://kaka-mobile-bridge/1.0.0" \
  --signature-ref "signature-subject:OpenClaw Pocket Agent Mobile Bridge" \
  --conformance-report-ref "artifacts/openclaw/conformance.json" \
  --evidence-manifest-ref "artifacts/openclaw/evidence-manifest.json"
```

Expected ready state:

- `status: "ready_for_external_install_drill"`
- `ready_for_external_install_drill: true`
- `missing_inputs: []`
- `phone_api.base_path: "/mobile/v1"`
- `phone_api.private_host_api_exposed: false`
- `gates.can_mark_p3_4_complete: false`

The last field is intentional. P3.6 proves install-drill readiness; final P3.4
completion still belongs to the external host release review.

## External Install Drill Sequence

Run this only after readiness is `ready_for_external_install_drill`.

1. Install the Plugin/Skill through the host-owned ordinary-user channel.
2. Confirm install does not auto-start the bridge, bind LAN, advertise Bonjour,
   mint credentials, or create login items.
3. Open the declared host UI entry point.
4. Enable **Pocket Agent Mobile Bridge** explicitly.
5. Show a short-lived QR code or opt into Bonjour on a trusted LAN.
6. Pair Pocket Agent iPhone through Mobile Bridge `/mobile/v1`.
7. Run host UI health check and confirm the private adapter command remains
   extension-internal.
8. Revoke the iPhone token, confirm the old token fails, and pair again with a
   new QR.
9. Run update and failure-recovery drills from the host UI.
10. Open logs from the host UI and confirm logs are redacted.
11. Run uninstall and confirm the bridge stops cleanly without leaving a mobile
    token or login item behind.
12. Archive the readiness JSON, P3.2 conformance report, P3.4 evidence
    manifest, install/update/failure drill receipts, release notes ref, and any
    host release review notes.

## In-Repository Starter Kit Sequence

Run this while external package facts are still blocked and the immediate goal
is to hand host teams concrete Plugin/Skill starter artifacts:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-starter-kit \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-starter-kit \
  --runtime openclaw \
  --output-dir artifacts/starter-kits \
  --write
```

The command emits `kaka.host_extension_starter_kit.v1`. With `--write`, it
materializes a safe starter tree containing README, manifest,
extension-internal adapter command README, runtime command JSON files, and
release-gate metadata. Hermes/OpenClaw static manifests declare the starter-kit
entrypoint. `host-extension-readiness` must remain blocked until real host-owned
facts are supplied; the starter kit must never fake install command, signature,
conformance, or evidence-manifest refs. Hand the starter output to the
Hermes/OpenClaw host team as packaging input, not as a final signed public
package.

## Installable Package Handoff Sequence

Use this when the immediate goal is to hand host teams a package-shaped Hermes
Plugin / OpenClaw Skill directory rather than only a starter scaffold:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-install-package \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-install-package \
  --runtime openclaw \
  --output-dir artifacts/install-packages \
  --write
```

Expected P3.13 output:

- schema `kaka.host_extension_install_package.v1`
- host-owned Plugin/Skill manifest files
- host UI contract for the Pocket Agent Mobile Bridge panel
- install-drill runbook for install, explicit enable, QR/Bonjour, health,
  revoke/re-pair, update, failure recovery, logs, and uninstall
- release-gate commands for readiness and conformance
- extension-internal `hermes-kaka-host-api` or `openclaw-kaka-host-api` README
- P3.35 `installation_blueprint` and `host-ui/installation-blueprint.json`
  naming package manifest expectations, host UI states/controls, lifecycle
  receipts, evidence gates, Codex automation boundary, and no-side-effect flags

P3.13 output is still host-team packaging input. P3.7 remains blocked until a
real install command, update channel, adapter command location, host UI
entrypoint, signed package ref, signature ref, conformance report ref, and
evidence manifest ref are supplied.

P3.35 is the latest repository-owned refinement on this same install-package
output. Do not add a second installer command.

## What Not To Build Next

Do not ask ordinary users to write adapter code, export
`HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, or paste Runtime Kit command
chains.

Do not add phone-side private host APIs. The iPhone continues to connect only to
Pocket Agent Mobile Bridge `/mobile/v1`.

Do not add another repository-only pilot wrapper unless it consumes real
host-owned package materials. Runtime Kit already has request, preflight,
runbook, conformance, receipt, handoff, artifact review, evidence manifest, host
extension preview, host extension readiness, and P3.12 starter-kit surfaces.

If external host materials are not available, future in-repository development
should shift to independent product slices. P3.9 retention controls, P3.10a
local HTTPS serving, P3.10b iOS trust/pinning, P3.11 native connection/recovery
UI polish, P3.12 Host Extension Starter Kit, P3.13 Host Extension installable
package handoff, P3.14 runtime retention purge receipts, and P3.15 Host
Plugin/Skill Devkit are now implemented. P3.15 packages and validates
host-team artifacts through template-only devkit output while preserving the
ordinary-user path as a host-native Hermes Plugin or OpenClaw Skill install.
P3.16 local renderer backend readiness, P3.17 photo-edit variant truth,
P3.17b photo-edit MIME truth, P3.20 Recall export artifact policy, P3.21
Recall retrieval packaging readiness, and P3.22 asset retention timestamped
purge are also implemented as repo-owned slices while external materials remain
blocked. P3.24 SQLite-backed asset storage/retention is implemented as the
store-backed continuation of that asset safety boundary.
If the next blocked-period slice is installation-focused, choose an actual
host-native Hermes/OpenClaw package drill with real host inputs. P3.19 has
already strengthened the repository-owned package acceptance artifacts; another
repo-only install wrapper would not prove user installation.
If the next blocked-period slice is retrieval-focused, start from
`recall-retrieval-readiness` and keep provider package, endpoint, keys,
embeddings, and fallback drill evidence host/runtime-owned rather than moving
them into Pocket Agent iPhone.
Codex developer automation must remain source-only, explicit-output-dir-only,
and schema-checked. It may help host engineers create or review Host Extension
materials, but the release proof remains the host-native Hermes Plugin /
OpenClaw Skill install drill.
Do not use future slices to add phone-side runtime settings writes,
phone-triggered purge endpoints, automatic deletion without receipts,
background cleanup jobs, or another host-extension readiness wrapper.
