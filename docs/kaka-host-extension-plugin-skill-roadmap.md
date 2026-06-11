# Kaka Host Extension Plugin/Skill Roadmap

Updated: 2026-06-11

This document is the development-facing decision record for turning the
Hermes/OpenClaw connection experience into something users can install, rather
than a setup that asks them to write adapter code or paste Runtime Kit command
chains.

## Product Decision

The ordinary-user path should be host-native:

1. Install **Kaka Mobile Bridge** as a Hermes Plugin or OpenClaw Skill/sidecar.
2. Open the host runtime UI entry point for Kaka Mobile Bridge.
3. Enable the bridge explicitly.
4. Pair Kaka iPhone with a short-lived QR code or visible Bonjour discovery.
5. Keep all phone traffic on `/mobile/v1`.

Runtime Kit can generate contracts, starter materials, handoff packages,
readiness receipts, conformance receipts, install-drill runbooks, and developer
automation source for host teams. It should not become the public user
installer.

Codex plugin/skill automation is useful only for Hermes/OpenClaw engineers who
are packaging and validating the host extension. It must not be the ordinary
user onboarding surface.

## Future Development Recommendation

The product answer to "this should be a plugin or skill" is yes, but only in
the host-native sense for ordinary users. Future development should make the
manual adapter work disappear behind the Hermes Plugin or OpenClaw
Skill/sidecar package, not move that work into a public Codex marketplace
install or a user-home skill folder.

Use this gate before writing new implementation plans:

1. If a real host package candidate exists, review its local materials manifest
   with P3.28, rerun P3.6 readiness, and then write P3.7.
2. If host package facts are missing, do not build another installer wrapper.
   Improve existing read-only acceptance artifacts only when they directly
   reduce P3.7 evidence risk.
3. If Codex automation is requested, keep it host-team-only: generate or update
   source under an explicit output directory, follow `plugin-creator` or
   `skill-creator` structure guidance, and include tests/receipts proving no
   marketplace update, no user-home writes, no bridge start, no private adapter
   invocation, and no ordinary-user install surface.
4. If the next work is product-facing rather than installation-facing, choose a
   separately permissioned Kaka feature and leave Host Extension packaging
   untouched.

## 2026-06-11 Follow-Up Decision

The user's concern is correct: asking people to hand-write adapter code or
paste Runtime Kit command chains would make Kaka feel like a developer
exercise. The product should therefore continue as a host-native Plugin/Skill
installation experience.

The next installation-focused implementation should not create a public Codex
plugin or Codex skill for ordinary users. If Codex automation is useful, build
it only as host-team developer source that can scaffold, validate, and review
the Hermes Plugin or OpenClaw Skill package.

Recommended next install-focused slice, if real P3.7 materials are still
missing:

- **P3.35 Host-Native Plugin/Skill Installation Blueprint**: turn the current
  handoff contracts into an acceptance-ready host package blueprint. This slice
  should define package manifest expectations, host UI entry points, disabled
  defaults, explicit enable/start behavior, QR/Bonjour controls, local TLS
  readiness display, revoke/re-pair, logs/health/update/uninstall receipts, and
  the evidence refs needed for P3.7.
- It may extend Runtime Kit generators or static acceptance artifacts only when
  that directly improves host-team packaging.
- It must not install packages, sign or publish artifacts, start the bridge,
  bind LAN, advertise Bonjour, mint tokens, invoke private adapters, write
  Codex user-home plugin/skill roots, or change the iPhone `/mobile/v1`
  contract.

If a Hermes/OpenClaw owner supplies real install package facts first, skip the
blueprint slice and proceed directly to P3.7 external install drill using
`docs/kaka-host-extension-external-materials.md`.

P3.35 is now implemented from:
`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
The existing `host-extension-install-package` payload now includes
`installation_blueprint`, writes `host-ui/installation-blueprint.json`, includes
the blueprint in generated Hermes/OpenClaw host manifests, and validates the
shape in schema/static drift tests. It does not add a new public Runtime Kit
command or turn Codex plugin/skill automation into the user install path.

## Post-P3.35 Development Posture

Do not add another repository-only installer wrapper while real Hermes/OpenClaw
package facts are missing. P3.12/P3.13/P3.15/P3.18/P3.19/P3.31/P3.35 now cover
starter materials, install-package handoff, host-team devkit, Codex developer
source, host UI acceptance, user quickstart, and the host-native installation
blueprint. More local wrapper layers would make the user experience look
developer-owned again without proving that Hermes or OpenClaw can ship the real
package.

The next installation-focused step is therefore one of two things:

1. **P3.7 external install drill** after a host runtime supplies all eight real
   P3.6 material inputs and P3.28 accepts the local materials manifest.
2. **Read-only acceptance hardening** only when it directly improves P3.7
   evidence review. This must extend existing intake/readiness/blueprint
   contracts, not introduce a new public installer, public Codex skill, public
   Codex plugin, user-home install write, bridge autostart, private adapter
   invocation, or `/mobile/v1` change.

If neither condition is true, move to a non-installation product slice. P3.36a
Inbox Voice Capture Context Copy and P3.36b Explicit Paste-to-Inbox Courier are
now complete; choose the next separately permissioned product slice instead of
another installation wrapper.

The implementation handoff for this decision is
`docs/kaka-host-extension-next-implementation.md`. Use it before writing any
new install-focused plan. P3.38 Explicit Files-to-Inbox Import is now complete
as a non-installation blocked-period product slice: a visible main-app Files
button copies one supported PDF or image into the existing Inbox payload store
with `sourceSurface = "file_picker"` and still requires visible Inbox `Send`.

## Next Install-Focused Development Handoff

The product answer to the installation concern is now settled: yes, the user
experience should be a Plugin/Skill installation, but that means a
host-native Hermes Plugin or OpenClaw Skill/sidecar, not a public Codex plugin
or Codex skill. The next install-focused development step must therefore be a
host package candidate handoff, not another Runtime Kit wrapper.

Ask the Hermes/OpenClaw owner for one sanitized host package candidate bundle:

- a real Plugin/Skill package or native-channel package ref;
- the declared host UI path for **Kaka Mobile Bridge**;
- evidence that install is disabled-by-default and does not auto-start the
  bridge;
- the extension-internal `hermes-kaka-host-api` or
  `openclaw-kaka-host-api` command location;
- local TLS, QR, Bonjour, revoke/re-pair, health, update, logs, repair, and
  uninstall drill receipt refs;
- P3.2 conformance report and P3.4 evidence manifest refs;
- release notes stating that Kaka iPhone talks only to `/mobile/v1`;
- a `kaka.host_extension_materials.v1` manifest reviewed by
  `host-extension-material-intake`.

Only after that bundle passes P3.28 material intake should the team write and
execute the external P3.7 install drill. If the bundle is unavailable, keep
installation work paused and select a non-installation product slice. Do not
fill the gap with manual adapter setup, a public Codex marketplace entry, a
user-home skill install, or another repository-only command chain.

## Three Separate Surfaces

Every future installation task must name which surface it is changing.

| Surface | Owner | User |
| --- | --- | --- |
| Host-native extension | Hermes/OpenClaw host team | Ordinary users |
| Runtime Kit generators | Kaka repository | Host engineers and release engineers |
| Codex developer automation | Host engineers using Codex | Host engineers only |

### Host-Native Extension

This is the real product package:

- Hermes Plugin or OpenClaw Skill/sidecar package.
- Host-owned install and update channel.
- Host UI panel for Kaka Mobile Bridge.
- Extension-internal `hermes-kaka-host-api` or `openclaw-kaka-host-api`.
- Health, logs, revoke, re-pair, update, repair, and uninstall controls.
- Signed package and signature/notarization evidence.

Ordinary users should only see this layer.

### Runtime Kit Generators

These are repository-owned tools that help host teams build and verify the real
extension:

- `host-extension-preview`
- `host-extension-readiness`
- `host-extension-starter-kit`
- `host-extension-install-package`
- `host-plugin-skill-devkit`
- `host-codex-developer-plugin-source`
- `host-private-adapter-conformance`
- `host-shell-pilot-*`

These commands may write materialized output only to explicit output
directories. They do not install the host extension, start the bridge, bind LAN,
advertise Bonjour, mint credentials, run private adapters, sign packages, or
update user-home Codex plugin/skill roots.

### Codex Developer Automation

This is optional source for host engineers:

- A Codex developer plugin can scaffold and review host extension materials.
- A Codex skill can encode the host team's packaging and release workflow.
- Both should follow `plugin-creator` and `skill-creator` structure guidance
  when implemented.
- Both remain source-only until a host engineer intentionally installs them in a
  developer environment.

Do not make Codex marketplace installation, `~/plugins`, `~/.codex/skills`, or
`~/.agents/plugins` part of normal Kaka onboarding.

## Current Repository Truth

The repository already has the contracts needed to support the product shape:

- P3.5 defines the installable Host Extension contract.
- P3.6 defines `host-extension-readiness` and the eight required host-owned
  distribution facts.
- P3.12 generates starter-kit materials for Hermes Plugin and OpenClaw
  Skill/sidecar owners.
- P3.13 generates package-shaped handoff materials.
- P3.15 generates a template-only Host Plugin/Skill devkit.
- P3.18 generates source-only Codex developer plugin materials for host
  engineers.
- P3.19 strengthens host UI acceptance, ordered install drill steps, evidence
  refs, and release gates.
- P3.26 adds non-installation Recall retrieval material intake/review while
  external Host Extension package facts remain blocked.
- P3.27 adds non-installation local renderer backend capability planning while
  external Host Extension package facts remain blocked.
- P3.28 adds read-only Host Extension material intake/review for local
  host-owned package facts and install-drill refs while external P3.7 execution
  remains blocked.
- P3.31 is now implemented as the latest install-experience refinement:
  `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-extension-user-quickstart.md`.
  It extends the existing `host-extension-install-package` output with
  ordinary-user quickstart copy and a user-journey acceptance artifact. It is
  not a new installer, not a Codex public install flow, and not a replacement
  for the host-native Hermes Plugin / OpenClaw Skill package.

Current installation-focused review command:

`host-extension-material-intake --manifest /path/to/materials.json`

The command emits `kaka.host_extension_material_intake.v1`, embeds P3.6
readiness, rejects missing or secret-like refs, and is not a package installer,
not a signing/publishing tool, and not a Codex ordinary-user installer.

External P3.7 remains blocked until at least one host runtime supplies real
values for:

- `install_command`
- `update_channel`
- `adapter_command_location`
- `host_ui_entrypoint`
- `signed_package_ref`
- `signature_ref`
- `conformance_report_ref`
- `evidence_manifest_ref`

Use `docs/kaka-host-extension-external-materials.md` as the external handoff for
those values.

## Recommended Next Implementation Order

1. **Do not add another repository-only installer wrapper.**
   P3.12/P3.13/P3.15/P3.18/P3.19 already cover the repository-owned scaffold,
   handoff, developer automation source, and acceptance-gate layers.

2. **If a real host package candidate bundle arrives, review it and then run P3.7.**
   Review the bundle with P3.28 `host-extension-material-intake`, fill the
   eight P3.6 readiness inputs, rerun `host-extension-readiness`, then write
   and execute the external install drill against the chosen host runtime.

3. **If facts are still blocked but installation work must continue, use P3.28
   material intake.**
   Ask the host team for a local `kaka.host_extension_materials.v1` manifest and
   review it with `host-extension-material-intake`. Keep the next step read-only
   until the report is accepted; no install, sign, fetch, bridge start, LAN
   bind, Bonjour, token minting, private adapter invocation, phone API change,
   or user-home Codex install.

4. **If facts are still blocked and the next work is not installation-focused,
   improve non-installation product slices.**
   P3.24 Runtime Kit SQLite-backed asset storage/retention, P3.25
   store-backed task result detail/variant persistence, and P3.26 Recall
   retrieval material intake/review are now implemented, and P3.27 local
   renderer backend capability manifest is now implemented. Further
   blocked-period work should choose another independent product slice. P3.29
   has already completed the separately permissioned Context Snapshot
   motion/calendar slice.

5. **If installation work must continue while facts are blocked, tighten
   acceptance artifacts only.**
   Acceptable repository work is limited to clearer host UI acceptance checks,
   release-gate validation, install-drill receipt shape, or static drift tests
   that directly help the future P3.7 proof. Do not duplicate P3.28 material
   intake; extend it only if new host-owned evidence refs are required, and keep
   any extension read-only. P3.31 Host Extension User Quickstart is now the
   latest completed example of this pattern: ordinary-user quickstart copy and a
   user-journey acceptance artifact on the existing install-package handoff.
   P3.35 Host-Native Plugin/Skill Installation Blueprint is now the completed
   example of this pattern after P3.31: it adds a generated blueprint artifact
   to the same install-package handoff and keeps Codex automation out of the
   ordinary-user installer.

6. **If building Codex automation, keep it host-team-only.**
   The implementation should be source generation or validation for host
   engineers. It should not install a Codex plugin/skill for normal users or
   replace the host-native extension.

## Next Developer Handoff

Use this decision tree before starting the next implementation:

1. If a Hermes/OpenClaw owner provides a host package candidate bundle with all
   eight P3.6 material inputs and install-drill receipt refs, review it through
   P3.28 `host-extension-material-intake`, then write and execute the P3.7
   external install drill.
2. If those inputs are still missing, do not build another installer wrapper.
   P3.24, P3.25, and P3.26 have already improved durable runtime storage,
   store-backed result browsing, and Recall retrieval material review inside
   existing repo-owned boundaries; P3.27 has already added local renderer
   backend capability planning.
3. If the next work is still installation-focused, collect a real
   `kaka.host_extension_materials.v1` manifest and host package candidate
   artifacts; review them with P3.28 `host-extension-material-intake`.
4. If the next work is product-focused rather than installation-focused, choose
   the next independent permissioned product slice; P3.29 has already completed
   Context Snapshot motion/calendar.
5. If installation work continues after P3.28, keep it as host-team tooling and
   acceptance receipts only; do not turn Runtime Kit or Codex automation into
   the ordinary-user installer.
6. If the immediate need is still installation-focused without real host package
   facts, build only on the completed P3.35 blueprint boundary or wait for P3.7
   materials. Do not add a second installer.
7. If the immediate work is product-focused while host package facts are still
   blocked, choose another independent permissioned Inbox/Recall slice that
   does not touch Host Extension packaging; P3.38 Explicit Files-to-Inbox Import
   is already complete.

## Acceptance Criteria For Future Plans

Any future plan that touches Hermes/OpenClaw installation should pass these
checks before implementation:

- It states which of the three surfaces it changes.
- It keeps ordinary-user onboarding host-native.
- It keeps iPhone communication on `/mobile/v1`.
- It does not expose private host APIs, provider keys, runtime store paths,
  private key paths, bearer tokens, mobile tokens, embeddings, raw logs, or raw
  asset bytes to the phone.
- It keeps install disabled-by-default until the user explicitly enables Kaka
  Mobile Bridge.
- It treats LAN binding, Bonjour, token minting, login items, and private
  adapter invocation as explicit user or host-owned actions.
- It has a concrete test or receipt proving that Codex developer automation is
  not the ordinary-user installer.

## Anti-Patterns

Do not implement future onboarding as:

- user-written adapter code;
- a required `--private-adapter-command` setup step;
- required `HERMES_KAKA_HOST_API` or `OPENCLAW_KAKA_HOST_API` environment
  variables;
- pasted Runtime Kit command chains as the default flow;
- a Codex plugin marketplace install for ordinary users;
- a Codex skill in `~/.codex/skills` as the public package;
- a phone-side private Hermes/OpenClaw API client.

The crisp user story remains: install the host-native plugin or skill, enable
Kaka Mobile Bridge in the host UI, scan the QR or choose Bonjour, then use Kaka
iPhone through `/mobile/v1`.
