# Kaka Mobile Runtime Kit

Kaka Mobile Runtime Kit is the local bridge scaffold for connecting the iPhone app to a user-owned runtime such as Hermes, OpenClaw, or a compatible sidecar.

The important product decision is safety first: installing a skill or plugin must not silently start a LAN listener. The bridge starts only after an explicit user action, and LAN plus Bonjour exposure are opt-in.

## Current Status

This directory is a development scaffold, not the final public installer.
The follow-up plugin/skill productization roadmap lives in
`../docs/kaka-host-extension-plugin-skill-roadmap.md`.

- It wraps the existing `mock_bridge/agent_pocket_mock_bridge.server` entrypoint.
- It defaults to `recipe_local`, the Phase 1 local recipe renderer path.
- It can print an exact dry-run command for Hermes/OpenClaw plugin authors.
- It can print a runtime-side settings preview JSON contract that a Hermes/OpenClaw plugin shell can render, including derived `consumer_ui` and `process_ownership` models.
- It can print a native runtime package preview derived from the same settings contract, consumer UI model, and process ownership contract.
- It can print a P2.8 `host-package-preview` handoff contract for Hermes/OpenClaw host-native packaging adapters.
- It can run a P2.9 `host-adapter-run` action result through a Runtime Kit host adapter binding surface.
- It can describe the P3.1 host-private command bridge contract for `host-adapter-run --adapter private`; proprietary Hermes/OpenClaw implementations are supplied by the host command, not bundled in this repository.
- It can run a P3.2 `host-private-adapter-conformance` report against a host-owned private adapter command without changing the phone API or bundling proprietary Hermes/OpenClaw binaries.
- It can embed P3.3 `private_adapter_package` metadata in `host-package-preview` so host shells can discover, distribute, sign, update, and release-gate their own private adapter command binaries.
- P3.4a adds `host-shell-pilot-report`, a Runtime Kit receipt for the first external Hermes/OpenClaw host-shell pilot. P3.4b lets that report discover the host-owned command in order from an explicit CLI argument, runtime env var, manifest entrypoint, then well-known path. It can validate local synthetic readiness, but missing discovery still reports `not_ready`, and P3.4 release completion still requires a real host-owned `hermes-kaka-host-api` or `openclaw-kaka-host-api` binary outside this repository.
- P3.4c adds `packaging/HOST_PRIVATE_ADAPTER_IMPLEMENTATION.md` and schema-checked `packaging/examples/` JSON so external host teams can implement the real private adapter command without copying proprietary APIs into Kaka.
- P3.4d keeps the `host-shell-pilot-report` verified boolean gate unchanged while allowing optional host-supplied evidence refs for distribution and drill artifacts.
- P3.4e adds `host-shell-pilot-handoff`, a machine-readable external pilot handoff package that wraps the `host-shell-pilot-report` receipt with release handoff metadata, deliverables, audit-ref completeness, and safety flags. It can report `handoff_status: "ready_to_submit"` only when all P3.4d audit refs are present, but it always keeps `p3_4_complete: false` because final P3.4 completion remains owned by the external host shell.
- P3.4f adds `host-shell-pilot-preflight`, a read-only local-input check that tells the host shell what is missing before conformance, pilot report, or handoff. It emits `kaka.host_shell_pilot_preflight.v1` on `hermes_openclaw_host_shell_pilot_preflight`, does not invoke the private adapter command, and always keeps `p3_4_complete: false`.
- P3.4g adds `host-shell-pilot-runbook`, a read-only operator artifact for the external host team. It emits `kaka.host_shell_pilot_runbook.v1` with a brief, pilot target, preflight summary, ordered steps, command artifacts, evidence requirements, and acceptance gates before conformance/report/handoff, and always keeps `p3_4_complete: false`.
- P3.4h adds `host-shell-pilot-artifact-review`, a read-only post-run review of the preflight, conformance, pilot receipt, and handoff JSON artifacts. It checks load/schema status, runtime consistency, embedded conformance/receipt consistency, audit-ref completeness, and private command consistency without running host commands or fetching refs.
- P3.4i adds `host-shell-pilot-request`, a read-only materials request bundle for Hermes/OpenClaw host teams. It lists the host-owned command binary, request/response contract, action matrix, distribution/signature/update/drill/release-note evidence, audit refs, and expected Runtime Kit JSON artifacts without invoking commands or marking P3.4 complete.
- P3.4j adds `host-shell-pilot-evidence-manifest`, a read-only evidence index for local pilot JSON artifacts. It hashes preflight, conformance, pilot receipt, handoff, and artifact-review files, can include request/runbook JSON, blocks missing/bad artifacts, and does not create the external archive or mark P3.4 complete.
- P3.5 adds `host-extension-preview`, the installable Host Extension productization contract. Ordinary users should install a Hermes Plugin or OpenClaw Skill/sidecar that bundles or internally discovers the host-private adapter command; explicit command paths and `HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API` remain developer and external-pilot fallback mechanisms only.
- P3.6 adds a read-only `host-extension-readiness` contract for real Plugin/Skill distribution facts: install command, update channel, extension-internal adapter command location, host UI entry point, signed package ref, signature/notarization ref, P3.2 conformance report ref, and P3.4 evidence manifest ref. It also hardens P3.5 schema/manifest drift checks without installing packages or invoking private commands.
- The 2026-06-07 no-input readiness audit reports both Hermes and OpenClaw as `blocked` on the same eight host-owned inputs. Use `../docs/kaka-host-extension-external-materials.md` to collect a host package candidate bundle, review it with P3.28 `host-extension-material-intake`, and rerun P3.6 readiness before writing a P3.7 external install drill plan.
- P3.8 adds `local-tls-readiness`, a read-only local TLS certificate readiness contract for production pairing metadata. It records certificate label/ref, public-key fingerprint, expiry, trust store ref, and renewal procedure ref without generating certificates, modifying Keychain, reading private keys, starting the bridge, binding LAN, advertising Bonjour, or minting mobile tokens.
- P3.9 adds Runtime Kit retention policy controls for input assets, output assets, and task history. `settings-preview`, `package-preview`, `start --dry-run`, generated server commands, mock bridge capabilities, and read-only runtime settings now preserve configured retention values without adding automatic cleanup, SQLite migrations, phone-side settings writes, or Swift UI changes.
- P3.10a adds real local HTTPS serving for the Mobile Bridge using host-owned certificate-chain and private-key files, while keeping certificate provisioning, trust installation, and renewal outside this slice.
- P3.10b carries the non-secret TLS public-key SHA-256 fingerprint into pairing payloads and iOS saved connections, using a pinned `URLSession` policy for HTTPS payloads with a valid pin while preserving default system trust and local HTTP development behavior.
- P3.12 adds `host-extension-starter-kit`, a safe starter package contract/materializer so Hermes/OpenClaw host teams can ship an installable Plugin/Skill experience instead of asking ordinary users to write adapter code, export `HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, or paste Runtime Kit command chains.
- P3.13 adds `host-extension-install-package`, a package-shaped handoff contract/materializer for Hermes Plugin / OpenClaw Skill owners. It generates host UI, install-drill, release-gate, manifest, and extension-internal adapter README materials while leaving signing, update channels, proprietary private adapter implementation, conformance evidence, and final distribution host-owned.
- P3.14 adds explicit runtime-side `retention-purge` receipts with dry-run/apply
  semantics. It emits `kaka.runtime_retention_purge_receipt.v1`, deletes only
  old terminal task history from `SQLiteRuntimeStore`, preserves active tasks
  and Recall, and does not add automatic cleanup, background jobs, phone-side
  settings writes, Mobile Bridge purge endpoints, or Recall deletion outside
  explicit user `Forget`/delete actions. P3.22 extends this explicit receipt to
  timestamped mock bridge in-memory input/output assets while preserving
  untimestamped assets as untracked. P3.24 adds store-backed input/output asset
  persistence in `SQLiteRuntimeStore` when a runtime store is configured, and
  includes those persisted assets in explicit runtime-side purge receipts.
- P3.25 adds store-backed task result detail persistence for completed
  photo-edit tasks. It persists only phone-safe result manifests in
  `RuntimeTaskRecord.metadata`, keeps raw bytes in `runtime_assets`, rebuilds
  variant `download_url` values from `asset_id`, keeps task lists summary-only,
  and exposes only `variant_count` in store-backed completed task events. Plan:
  `../docs/superpowers/plans/2026-06-11-kaka-pocket-agents-store-backed-task-result-detail.md`.
- P3.26 adds `recall-retrieval-material-intake`, a read-only materials manifest
  review contract for production Recall retrieval packaging. It ingests a local
  host/runtime-owned manifest, blocks missing or secret-like materials, embeds
  the P3.21 readiness report, and does not fetch refs, validate signatures,
  invoke providers, expose provider endpoints/keys to iPhone, include retrieval
  internals in Recall export, or change `/mobile/v1/recall/search`.
- P3.15 adds `host-plugin-skill-devkit`, a host-team development materials
  index for Hermes/OpenClaw Plugin/Skill owners. It composes P3.12/P3.13
  contracts into contract indexes, command files, acceptance gates,
  ordinary-user boundary files, adapter templates, and optional Codex automation
  templates without creating a third install package, real Codex plugin,
  marketplace entry, or ordinary-user install surface.
- Future Codex developer plugins or Codex skills should stay in that same
  host-team automation lane: scaffold, validate, and review Plugin/Skill
  materials. They must not replace the host-native Hermes Plugin or OpenClaw
  Skill/sidecar that ordinary users install.
- P3.18 `host-codex-developer-plugin-source` materializes that automation as
  source only: a runtime-specific Codex developer plugin tree
  written under an explicit output directory for host engineers. It must not
  install the Codex plugin, update marketplaces, write user-home install roots,
  install Hermes/OpenClaw packages, start listeners, invoke private adapters,
  run conformance, or change `/mobile/v1`.
- P3.19 strengthens `host-extension-install-package` with host UI acceptance
  metadata, generated `host-ui/acceptance.json`, ordered install-drill steps,
  evidence receipt refs, TLS/readiness/evidence/Codex developer source release
  gates, and static manifest/schema drift protection. It does not add a new
  CLI, install packages, sign/publish, start listeners, invoke private adapters,
  or turn Codex automation into ordinary-user onboarding.
- P3.35 implements the host-native installation blueprint while real P3.7
  package facts remain unavailable:
  `../docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
  It extends the existing `host-extension-install-package` handoff with a
  declarative `installation_blueprint`, writes
  `host-ui/installation-blueprint.json`, includes the blueprint in generated
  host manifests, and does not add a new command or public Codex install path.
  After P3.35, Runtime Kit should not add another repository-only installer
  wrapper; installation progress now requires real host-owned P3.7 materials or
  a read-only extension to an existing readiness/intake/blueprint artifact.
- P3.28 adds `host-extension-material-intake`, a read-only local manifest review
  for host-owned Plugin/Skill package facts and install-drill refs. It emits
  `kaka.host_extension_material_intake.v1`, embeds P3.6 readiness, rejects
  missing or secret-like refs, and is not an installer, signer, publisher,
  bridge starter, private adapter runner, or Codex ordinary-user install path.
- P3.16 adds `local-renderer-backend-readiness`, a runtime-side synthetic
  `recipe_local` probe and closed schema proving the existing local parametric
  renderer can produce the expected two JPEG variants without adding a phone
  API, cloud provider, bridge startup behavior, or new renderer dependency.
- P3.27 adds `local-renderer-backend-capability-manifest`, a read-only local
  renderer backend capability planning manifest. It records the current
  Pillow/`recipe_local` contract and future Core Image/ImageMagick/OpenCV/libvips
  gates without installing dependencies, importing or executing future
  backends, changing capabilities, or changing `/mobile/v1`.
- P3.17 aligns default photo-edit variant truth with that probe:
  `photo_edit.return_variants_max` is `2` for `recipe_local`, matching
  `variant_clean_pro` and `variant_social_pop`.
- P3.17b narrows default photo-edit MIME truth for `recipe_local`:
  `photo_edit.accepted_mime_types` is `["image/jpeg"]`. Generic asset upload,
  vision, image intake, and universal intake stay broad.
- It can print a P3.0 `connection-qa-preview` readiness report for the ordinary-user first-run connection checklist.
- It includes static Hermes/OpenClaw shell manifests plus JSON schemas under `runtime-kit/packaging/`.
- It does not install launch agents, background login items, or provider credentials.
- Runtime-owned SQLite persistence for Recall and task state is available through the explicit `--runtime-store-path` development opt-in.
- Runtime-owned semantic Recall search is available through `POST /mobile/v1/recall/search` with deterministic local scoring and optional provider-backed retrieval adapters for development bridges.
- `GET /mobile/v1/runtime/settings` reports local store and semantic Recall status without exposing provider keys or phone-owned persistence controls.

## Developer Commands

Run a local doctor check:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
```

Print the bridge command without starting it:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start --dry-run
```

Print the runtime-side settings/plugin shell contract without starting the bridge:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit settings-preview \
  --bridge-enabled \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --recall-search-provider fixture \
  --input-assets-days 7 \
  --output-assets-days 30 \
  --task-history-days 30
```

`settings-preview` is for Hermes/OpenClaw plugin authors and runtime-side UI shells. It now includes both `runtime_side_ui.consumer_ui` and `runtime_side_ui.process_ownership`. `consumer_ui` is the polished renderer contract for ordinary-user bridge settings: Process, Connection, Pairing, Local Memory, and Recall Retrieval sections, status badges, primary actions, warning copy, and a stopped-bridge empty state. `process_ownership` is the runtime-side lifecycle contract for install, start-at-login/start-with-runtime, update, uninstall, logs, health checks, and port-conflict repair. P3.9 also exposes bounded retention day steppers for input assets, output assets, and task history. Runtime shells should render those models first and use `runtime_side_ui.controls` as the underlying control source.

The process ownership contract is declarative. P2.8 adds the host packaging handoff contract, schema, static manifest declaration, and safe command artifacts. P2.9 adds `host-adapter-run`, a Mac/runtime-side execution action surface for host shells. It still does not change the iPhone API, and it still does not create macOS login items or LaunchAgents, auto-start the bridge, install/update/uninstall runtime packages through real host APIs, open private log windows, or supervise processes by itself. The `mock` adapter is for conformance and local QA. P3.1 narrows `private` adapter mode to a host-private command bridge contract: Runtime Kit invokes a configured command, while Hermes/OpenClaw own any proprietary native API implementation behind that command.

The underlying `runtime_side_ui.controls` block may include local paths, provider endpoints, bind mode, Bonjour controls, QR/revocation/TLS controls, and the exact `actions.start_bridge` command because those settings belong to the Mac/runtime side. Its nested `phone_safe_summary` is the only part shaped like phone-visible status, and it intentionally omits runtime store paths, provider endpoints, auth/env file paths, bearer tokens, TLS private key paths, raw embeddings, and index rows.

Dry-run runtime-owned retention cleanup and print a safe receipt:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit retention-purge \
  --runtime hermes \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --input-assets-days 7 \
  --output-assets-days 30 \
  --task-history-days 30
```

Apply cleanup only from the Mac/runtime side with an explicit `--apply`:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit retention-purge \
  --runtime hermes \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --input-assets-days 7 \
  --output-assets-days 30 \
  --task-history-days 30 \
  --apply
```

`retention-purge` emits `kaka.runtime_retention_purge_receipt.v1` on
`hermes_openclaw_runtime_retention_purge`. It deletes only old terminal task
history from the runtime-owned store, preserves active tasks and Recall, and
does not expose runtime store paths, provider endpoints, bearer tokens, TLS
private key paths, raw logs, embeddings, SQLite rows, or raw asset bytes.
Timestamped mock bridge in-memory input/output assets are listed in
`eligible.input_asset_ids` / `eligible.output_asset_ids` and are removed only
when the runtime explicitly applies the purge. Untimestamped assets remain in
`preserved.untracked_asset_ids` with `asset_purge_status` set to
`partial_missing_asset_timestamps` or `skipped_missing_asset_timestamps`. This
command is not a Mobile Bridge endpoint, and the iPhone cannot trigger it.

Print the native runtime package shell contract without starting the bridge:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit package-preview \
  --bridge-enabled \
  --runtime hermes \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3
```

`package-preview` wraps `settings-preview` with install defaults, actions, runtime-only value classification, retention policy controls, consumer UI metadata, process ownership metadata, and security status for Hermes/OpenClaw shells. It is intentionally derived from `settings-preview` so packaging does not grow a second source of truth.

Print the P2.8 host packaging handoff contract without starting the bridge:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-package-preview \
  --runtime hermes \
  --distribution-source local_checkout \
  --distribution-channel development \
  --package-version development
```

`host-package-preview` is for Hermes/OpenClaw host-native adapters. It describes distribution metadata, disabled-by-default install policy, host-owned lifecycle actions, safe preview commands, `consumer_ui`, `process_ownership`, and the P3.3 `private_adapter_package` release-gate metadata in one JSON contract. It is not a private Hermes/OpenClaw installer API call and it does not mutate host system state.

Print the P3.5 Host Extension productization contract without starting the bridge:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-extension-preview \
  --runtime hermes
```

`host-extension-preview` emits `kaka.host_extension_preview.v1` on
`hermes_openclaw_host_extension_preview`. It describes the ordinary-user install
shape for Hermes Plugin or OpenClaw Skill/sidecar, marks the private adapter
command as `extension_internal`, keeps environment variables and explicit command
paths as developer/pilot fallback only, and records pairing UX, phone API, safety,
and release gates. It does not invoke the private adapter command, start the
bridge, bind LAN, advertise Bonjour, mint credentials, create login items, or
mark P3.4 complete.

Print the P3.6 Host Extension distribution readiness contract without installing
or invoking anything:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-extension-readiness \
  --runtime hermes \
  --install-command "hermes plugin install kaka-mobile-bridge" \
  --update-channel stable \
  --adapter-command-location '$EXTENSION_ROOT/bin/hermes-kaka-host-api' \
  --host-ui-entrypoint "Settings > Plugins > Kaka Mobile Bridge" \
  --signed-package-ref "hermes-plugin://kaka-mobile-bridge/1.0.0" \
  --signature-ref "notarization-team:HERMES-KAKA" \
  --conformance-report-ref "artifacts/hermes/conformance.json" \
  --evidence-manifest-ref "artifacts/hermes/evidence-manifest.json"
```

`host-extension-readiness` emits `kaka.host_extension_readiness.v1` on
`hermes_openclaw_host_extension_readiness`. Missing host-owned distribution
facts produce `status: "blocked"` with stable `missing_inputs`; complete
metadata produces `status: "ready_for_external_install_drill"`. It is
read-only: it does not install the plugin/skill, invoke the private adapter
command, fetch refs, start the bridge, bind LAN, advertise Bonjour, mint
credentials, create login items, or mark P3.4 complete.

To reproduce the current blocked audit before external materials arrive:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-readiness --runtime openclaw
```

Both reports should stay blocked until the host team supplies the real install
command, update channel, extension-internal adapter location, host UI entry
point, signed package ref, signature/notarization ref, P3.2 conformance report
ref, and P3.4 evidence manifest ref.

For the next install-focused development pass, ask the Hermes/OpenClaw owner for
a sanitized host package candidate bundle rather than another Runtime Kit
wrapper. That bundle should contain the real Plugin/Skill package ref, host UI
entrypoint, disabled-by-default evidence, extension-internal adapter command
location, install/pairing/update/uninstall drill receipts, P3.2 conformance ref,
P3.4 evidence manifest ref, and release notes confirming that Kaka iPhone stays
on `/mobile/v1`. Review the bundle with `host-extension-material-intake` before
writing or executing P3.7.

Review a host-supplied Host Extension materials manifest without installing or
fetching refs:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-material-intake \
  --manifest artifacts/hermes/host-extension-materials.json
```

The input manifest uses `kaka.host_extension_materials.v1`; the output report
uses `kaka.host_extension_material_intake.v1`. A complete, non-secret manifest
can return `accepted_for_external_install_drill_review`, which means it is ready
for external P3.7 install-drill review. It is not proof that the package was
installed, signed, published, fetched, started, or validated by Runtime Kit.

Generate a Host Extension starter package without installing or invoking
anything:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-starter-kit \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-starter-kit \
  --runtime openclaw \
  --output-dir artifacts/starter-kits \
  --write
```

This P3.12 command emits `kaka.host_extension_starter_kit.v1` and optionally
writes a safe starter tree with README, manifest, extension-internal adapter
command README, runtime contract command files, and release-gate metadata. It
does not install a plugin/skill, start the bridge, bind LAN, advertise Bonjour,
create login items, mint tokens, invoke private adapter commands, or expose
private host APIs to Kaka iPhone.

Generate package-shaped Host Extension handoff materials without installing or
invoking anything:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-install-package \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-install-package \
  --runtime openclaw \
  --output-dir artifacts/install-packages \
  --write
```

This P3.13 command emits `kaka.host_extension_install_package.v1` and optionally
writes a host-team package handoff tree with Plugin/Skill manifest files, host UI
contract, install-drill runbook, release-gate commands, and an
extension-internal adapter command README. It does not sign, publish, install,
start the bridge, bind LAN, advertise Bonjour, create login items, mint tokens,
run conformance, invoke private adapter commands, or expose private host APIs to
Kaka iPhone.

Generate a Host Plugin/Skill devkit without installing or invoking anything:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-plugin-skill-devkit \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-plugin-skill-devkit \
  --runtime openclaw \
  --output-dir artifacts/devkits \
  --write
```

This P3.15 command emits `kaka.host_plugin_skill_devkit.v1` and optionally
writes a host-team devkit tree with contract indexes, command files,
acceptance gates, ordinary-user boundary metadata, adapter templates, and
template-only Codex automation. It does not write a real `.codex-plugin`
manifest, a real Codex `SKILL.md`, host Plugin/Skill install manifests, or
`bin` adapter stubs. It does not sign, publish, install, start the bridge, bind
LAN, advertise Bonjour, create login items, mint tokens, run conformance,
invoke private adapter commands, update Codex marketplaces, or expose private
host APIs to Kaka iPhone.

P3.18 turns the template-only Codex automation into a real Codex developer
plugin source tree for host engineers:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-codex-developer-plugin-source \
  --runtime hermes
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-codex-developer-plugin-source \
  --runtime openclaw \
  --output-dir artifacts/codex-developer-plugins \
  --write
```

The write form requires `--output-dir` and creates only a runtime-specific
source root such as
`artifacts/codex-developer-plugins/kaka-host-extension-developer-openclaw/`.
It contains source files such as `.codex-plugin/plugin.json`,
`skills/kaka-host-extension-developer/SKILL.md`, references, and `source.json`;
it must not create `~/.agents/plugins/marketplace.json`, write `~/plugins`,
write `~/.codex/skills`, or install anything for ordinary users. The public
user install path remains Hermes Plugin / OpenClaw Skill in the host UI.

Print the P3.8 local TLS certificate readiness contract without reading private
keys or modifying the host trust store:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit local-tls-readiness \
  --runtime hermes \
  --tls-trust-state configured \
  --tls-certificate-label "Kaka Local Runtime" \
  --tls-certificate-ref "keychain://login/kaka-local-runtime" \
  --tls-public-key-sha256 "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" \
  --tls-expires-at "2036-12-31T23:59:59Z" \
  --trust-store-ref "macos-keychain://login" \
  --renewal-procedure-ref "docs/kaka-local-tls-renewal.md"
```

`local-tls-readiness` emits `kaka.local_tls_readiness.v1` on
`hermes_openclaw_local_tls_readiness`. Missing TLS metadata returns
`status: "blocked"`; complete metadata returns
`status: "ready_for_production_pairing"`. This is still a readiness report only:
it does not create certificates, install trust, read private key paths, start
the bridge, bind LAN, advertise Bonjour, mint
credentials, or change the phone API.

Start the bridge with host-owned local TLS files:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host 192.168.1.10 \
  --pairing-mode production \
  --trusted-local-tls \
  --tls-trust-state configured \
  --tls-certificate-label "Kaka Local Runtime" \
  --tls-public-key-sha256 "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" \
  --tls-certificate-chain-path /path/to/kaka-local-runtime.crt \
  --tls-private-key-path /path/to/kaka-local-runtime.key
```

Runtime Kit reads those files only to wrap the local bridge socket. It does not
generate certificates, install trust, modify Keychain, or expose certificate
paths or private key paths to iPhone `/mobile/v1` responses. Pairing QR payloads
and Bonjour TXT may include `tls_public_key_sha256`, which is non-secret and is
used by iOS for HTTPS public-key pinning.

The top-level `private_adapter_package` object has schema version
`kaka.host_private_adapter_package.v1` and surface
`hermes_openclaw_host_private_adapter_package`. It states that the command
binary is owned by `host_shell`, its repository owner is `hermes_or_openclaw`,
and the private API implementation is `not_bundled_in_kaka`. Default command
names are `hermes-kaka-host-api` and `openclaw-kaka-host-api`. Discovery belongs
to the host shell. Runtime Kit resolves host-owned commands in this order:
explicit `--private-adapter-command` / `private_adapter_command` config,
`HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, manifest entrypoint
`host_private_adapter.command`, then well-known paths under
`~/Library/Application Support/<Runtime>/Kaka/`. Distribution metadata records
host-owned `source`, `channel`, and `version`, with
`update_policy: explicit_user_approved`, `download_owner: host_shell`, and
`signature_policy: host_shell_required`. Stable install/update UI should require
`requires_conformance_passed: true` with report schema
`kaka.host_private_adapter_conformance.v1`. The phone API remains `/mobile/v1`
with `phone_api_unchanged: true`.

Run a P2.9 host adapter action result for conformance/local QA:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Mutating host actions require explicit approval:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter mock \
  --action-id install_runtime_package \
  --approved
```

Host-team/development/pilot only: run the P3.1 private host command bridge
contract from the Mac/runtime side:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

`host-adapter-run` is a Runtime Kit host action binding for Mac/runtime-side shell execution. It is not a Mobile Bridge endpoint and it is not a phone-owned settings API. The `mock` adapter simulates state transitions for conformance and local QA without mutating the actual host OS. In `private` mode, Runtime Kit parses the configured `--private-adapter-command`, invokes it with `shell=False`, sends a sanitized JSON request on stdin, validates the JSON response on stdout, and maps the result back into the structured host adapter action result. Missing command configuration returns `private_host_adapter_unavailable`; non-zero, invalid, or timed-out command results stay structured and safe with no claimed host mutation. Mutating host actions still require `--approved`.

Host-team/development/pilot only: before conformance, generate the P3.4i
host-shell pilot request for the external host team:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime hermes \
  --request-id P3.4-hermes \
  --pilot-owner "Hermes host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --artifact-root artifacts/hermes
```

`host-shell-pilot-request` emits
`kaka.host_shell_pilot_request.v1` and lists the host-owned materials needed for
the external pilot: private adapter command binary, request/response contract,
9-action lifecycle matrix, native distribution/signature/update evidence,
install/update/failure-recovery drill receipts, release notes, audit refs, and
the expected Runtime Kit JSON artifacts. `ok: true` means the request package
was generated; it does not mean the host has provided anything. It does not
invoke the private adapter command, run preflight or conformance, fetch audit
refs, mutate host state, submit handoff, expose phone `/mobile/v1` fields, or
mark P3.4 complete.

Then run the P3.4f host-shell pilot preflight to check local host inputs without
mutating state:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

`host-shell-pilot-preflight` checks host shell app/CLI presence, private adapter
command discovery sources, and PATH command availability as informational-only
diagnostics. Discovery can use an explicit argument, runtime env var, manifest
entrypoint, or well-known path; PATH does not make the command ready by itself.
The preflight does not invoke the private adapter command, run conformance,
fetch audit refs, mutate host state, or expose phone `/mobile/v1` fields.
`ok: true` with `status: "ready_for_conformance"` means the host can run
conformance next; it is not P3.4 completion and still reports
`p3_4_complete: false`.

Then print the P3.4g host-shell pilot runbook for the external host operator:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

`host-shell-pilot-runbook` composes the read-only preflight summary with ordered
operator steps, command artifacts for preflight/conformance/report/handoff, the
eight required P3.4d evidence refs, and acceptance gates. It does not invoke the
private adapter command, run conformance, fetch audit refs, mutate host state,
or expose phone `/mobile/v1` fields. `ok: true` with
`runbook_status: "ready_for_conformance"` means the host can run conformance
next; it is not handoff submission and it is not P3.4 completion.

Run the P3.2 host-private adapter conformance report from the Mac/runtime side:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

`host-private-adapter-conformance` is runtime-side only. It accepts a host-owned
private adapter command, exercises it through the same P3.1
`host-adapter-run --adapter private` behavior, and validates the required
install, login-item, update, uninstall, logs, health, port repair, and
supervision lifecycle matrix. The report is evidence for the configured host
command; distribution, command discovery, and package ownership remain the
Hermes/OpenClaw host shell's responsibility. Passing conformance does not mean
Kaka owns, ships, or bundles proprietary Hermes/OpenClaw binaries.
External host teams should use
`runtime-kit/packaging/HOST_PRIVATE_ADAPTER_IMPLEMENTATION.md` and the
schema-checked JSON examples under `runtime-kit/packaging/examples/` as the
authoring contract for real `hermes-kaka-host-api` or
`openclaw-kaka-host-api` binaries.

Record the P3.4a external host-shell pilot receipt:

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

`host-shell-pilot-report` verifies and records host-supplied readiness evidence;
Runtime Kit does not own, build, sign, distribute, install, update, or bundle
the proprietary Hermes/OpenClaw private adapter binary. When
`--private-adapter-command` is omitted, P3.4b discovery checks the runtime env
var, manifest entrypoint, and well-known path in that order; if no external
host-owned command is found, the receipt remains `not_ready`. Local fake fixtures
and local conformance can only produce `synthetic_only` readiness for Runtime Kit
regression checks, and `synthetic_only` cannot mark P3.4 complete. P3.4 remains
incomplete until a real host-owned `hermes-kaka-host-api` or
`openclaw-kaka-host-api` binary outside this repository produces a ready
receipt.

P3.4d adds optional evidence reference fields without changing the readiness
gate. Distribution evidence may include
`distribution.evidence.native_channel_ref`,
`distribution.evidence.signature_subject`,
`distribution.evidence.notarization_team_id`, and
`distribution.evidence.update_feed_ref`. Drill evidence may include
`drills.evidence.install_receipt_ref`,
`drills.evidence.update_receipt_ref`,
`drills.evidence.failure_recovery_receipt_ref`, and
`drills.evidence.release_notes_ref`. These refs are identifiers or pointers
supplied by the host shell for human audit trails only: they do not
automatically set any `*_verified` boolean, and Runtime Kit does not download,
read, or validate the external material they name. They are runtime-side pilot
receipt metadata only, are not exposed through the phone `/mobile/v1` API, and
must not contain secrets, raw logs, private keys, provider keys, bearer tokens,
mobile tokens, or other credentials.

Print the P3.4e external pilot handoff bundle:

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
  --notarization-team-id "TEAMID1234" \
  --update-feed-ref "https://example.invalid/hermes/kaka/update-feed.json" \
  --install-receipt-ref "host-pilot://hermes/install/2026-06-06" \
  --update-receipt-ref "host-pilot://hermes/update/2026-06-06" \
  --failure-recovery-receipt-ref "host-pilot://hermes/failure-recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/hermes/kaka/release-notes/1.0.0"
```

`host-shell-pilot-handoff` wraps the receipt in schema
`kaka.host_shell_pilot_handoff.v1` on surface
`hermes_openclaw_host_shell_pilot_handoff`. It does not change receipt
readiness, fetch audit refs, expose phone `/mobile/v1` fields, or bundle the
proprietary binary. `handoff_status` is `ready_to_submit` only when the embedded
pilot receipt is ready and all P3.4d audit refs are complete; otherwise it is
`incomplete`. Even when ready to submit, the bundle reports
`p3_4_complete: false` and `p3_4_completion_owner: external_host_shell`.

After the host team has generated preflight, conformance, receipt, and handoff
JSON artifacts, review them without rerunning host commands:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime hermes \
  --preflight-json /path/to/preflight.json \
  --conformance-json /path/to/conformance.json \
  --receipt-json /path/to/receipt.json \
  --handoff-json /path/to/handoff.json
```

`host-shell-pilot-artifact-review` emits
`kaka.host_shell_pilot_artifact_review.v1` and reports
`ready_for_external_review` only when all four artifacts are loaded, have the
expected schema identity, match the requested runtime, embed the same
conformance/receipt data, include complete audit refs, and the handoff is
`ready_to_submit`. It still reports `p3_4_complete: false`.

After artifact review, print the P3.4j evidence manifest for host-side archival:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime hermes \
  --package-id P3.4-hermes \
  --artifact-root artifacts/hermes \
  --request-json artifacts/hermes/request.json \
  --runbook-json artifacts/hermes/runbook.json \
  --archive-filename kaka-p3.4-hermes-pilot-evidence.zip
```

`host-shell-pilot-evidence-manifest` emits
`kaka.host_shell_pilot_evidence_manifest.v1` and hashes local JSON artifact
files only. With `--artifact-root`, it reads `preflight.json`,
`conformance.json`, `pilot-receipt.json`, `handoff.json`, and
`artifact-review.json` by default. It can report `ready_for_archive` only when
required artifacts are loaded, match schema/surface/runtime identity, and each
artifact is `ok: true`; artifact review must also be ready for external review.
It does not invoke the private adapter command, rerun conformance, fetch audit
refs, submit handoff, mutate host state, create the zip file, expose phone
`/mobile/v1` fields, or mark P3.4 complete.

Print the P3.0 ordinary-user connection QA report without starting the bridge:

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

`connection-qa-preview` is a deterministic QA/readiness report for the first-run checklist in `docs/kaka-ordinary-user-connection-qa.md`. It composes Runtime Kit preview contracts and mock adapter readiness into first-run steps, failure fixtures, safety notes, and the remaining P3.1 host-private command capability list. It is non-mutating: it must not start a bridge process, bind ports, advertise Bonjour, create login items, install packages, mint credentials, repair ports, or call host-private adapter commands. It does not change the iPhone API; the phone still connects only through Mobile Bridge `/mobile/v1`.

Keep the three API surfaces separate:

- Phone-to-agent connection: Kaka iPhone uses the local Mobile Bridge `/mobile/v1` API.
- Host shell rendering and flow setup: Hermes/OpenClaw shells use Runtime Kit preview JSON and CLI contracts such as `settings-preview`, `package-preview`, and `host-package-preview`.
- Host-side action execution: Hermes/OpenClaw shells call P2.9 `host-adapter-run` from the Mac/runtime side.
- Host-private adapter conformance: Runtime Kit `host-private-adapter-conformance` runs on the Mac/runtime side against a host-owned command and produces report evidence only.
- Host-private adapter package metadata: Runtime Kit `host-package-preview.private_adapter_package` describes host-owned command discovery, distribution, signatures, and conformance gates without downloading or executing the command.
- Host Extension productization: Runtime Kit `host-extension-preview` describes the ordinary-user Hermes Plugin / OpenClaw Skill install shape while keeping adapter commands extension-internal and manual command/env discovery fallback-only.
- Host Extension distribution readiness: Runtime Kit `host-extension-readiness` records real Plugin/Skill package facts and returns `blocked` or `ready_for_external_install_drill` without installing packages, invoking private commands, fetching refs, starting the bridge, or marking P3.4 complete.
- Host Plugin/Skill devkit: Runtime Kit `host-plugin-skill-devkit` is the P3.15
  host-team development materials index. It points at existing starter,
  package, readiness, conformance, and evidence contracts, and writes only
  templates plus acceptance gates; it is not the ordinary-user install surface.
- Host Codex developer plugin source: P3.18 generates optional Codex developer
  plugin source for host engineers only. It is source output, not installation,
  marketplace publication, user onboarding, or a replacement for
  Hermes/OpenClaw host-native packages.
- Host Extension install experience acceptance: P3.19 strengthens
  `host-extension-install-package` handoff output with host UI acceptance,
  ordered install drill, evidence receipts, and release gates. It is not a new
  phone API, new CLI, package installer, or ordinary-user Codex install path.
- Host Extension installation blueprint: P3.35 is implemented as one more
  declarative artifact inside `host-extension-install-package`. The output is
  `installation_blueprint` plus `host-ui/installation-blueprint.json` for
  Hermes/OpenClaw host engineers; Runtime Kit still avoids installing, signing,
  publishing, starting the bridge, invoking private adapters, writing Codex
  user-home roots, or changing `/mobile/v1`.
- Retention purge receipts: P3.14 is an explicit runtime-side `retention-purge`
  action that emits safe receipts and keeps retention settings phone-read-only.
  P3.22 adds timestamp-aware mock bridge input/output asset receipts for
  in-memory assets. P3.24 adds SQLite-backed input/output asset persistence and
  store-backed purge integration when `--runtime-store-path` is configured. It
  does not run automatically on server start, add a mobile purge endpoint, or
  expose runtime store paths, provider details, tokens, private key paths, logs,
  embeddings, SQLite rows, task result variants, or raw asset bytes.
- External host-shell pilot request: Runtime Kit `host-shell-pilot-request` is a P3.4i read-only materials request for the Hermes/OpenClaw host team. It enumerates required host-owned deliverables, audit refs, and expected Runtime Kit artifacts; it does not probe, execute, fetch, mutate, submit, or mark P3.4 complete.
- External host-shell pilot preflight: Runtime Kit `host-shell-pilot-preflight` is a P3.4f read-only local-input diagnostic that runs before conformance, report, and handoff. It reports missing host shell app/CLI and private adapter discovery inputs, treats PATH command discovery as informational only, does not invoke the private adapter command, and keeps `p3_4_complete: false`.
- External host-shell pilot runbook: Runtime Kit `host-shell-pilot-runbook` is a P3.4g read-only operator artifact that sequences preflight, conformance, host evidence, pilot receipt, and handoff commands. It reports evidence requirements and acceptance gates, but does not run the private command, fetch refs, mutate host state, submit handoff, or mark P3.4 complete.
- External host-shell pilot artifact review: Runtime Kit `host-shell-pilot-artifact-review` is a P3.4h read-only post-run checker for generated JSON artifacts. It reviews preflight, conformance, receipt, and handoff files for load/schema/readiness/consistency only; it does not rerun conformance, fetch refs, mutate host state, submit handoff, or mark P3.4 complete.
- External host-shell pilot evidence manifest: Runtime Kit `host-shell-pilot-evidence-manifest` is a P3.4j read-only archive index for local JSON artifacts. It calculates byte sizes and SHA-256 hashes only; it does not create the archive, run commands, fetch refs, submit handoff, or mark P3.4 complete.
- External host-shell pilot receipt: Runtime Kit `host-shell-pilot-report` verifies and records P3.4a evidence only; optional P3.4d evidence refs are audit pointers that do not flip verified booleans, are not fetched or validated by Runtime Kit, and are not phone API fields. Runtime Kit does not own, build, sign, distribute, install, update, or bundle the proprietary command binary.
- External host-shell pilot handoff: Runtime Kit `host-shell-pilot-handoff` wraps that receipt into the P3.4e machine-readable release handoff package, requires complete P3.4d audit refs for `ready_to_submit`, and still reports `p3_4_complete: false` because final completion remains external-host-owned.
- Ordinary-user connection QA: Runtime Kit `connection-qa-preview` runs on the Mac/runtime side and produces checklist/failure-fixture evidence only.
- Native install, login item, update, uninstall, logs, health, repair, and supervision: `mock` is conformance/local QA; `private` calls a configured host-private adapter command when supplied, or returns structured unavailable when no command is configured. This repository does not include proprietary Hermes/OpenClaw private API implementations.

Start for Simulator-only loopback QA:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start
```

Opt into a local SQLite store during development:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --repo-root . \
  --runtime sidecar \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3
```

`--runtime-store-path` is a Runtime Kit launcher/server option, not a Mobile Bridge field. The path belongs to the Mac/runtime side and holds runtime-owned Recall records, retrieval-index deletion receipts, runtime task records, and task events. The iPhone continues to call the same `/mobile/v1` endpoints and does not learn the SQLite path.

For now this flag is an opt-in development setting. Runtime Kit's `consumer_ui` model exposes it as a visible runtime-side setting such as "Use local Kaka Recall and task store", not a hidden phone-side behavior. The bridge also exposes `/mobile/v1/runtime/settings` so Kaka can display whether the runtime-owned store and semantic Recall search are available, while leaving the actual setting on the Mac/runtime side.

Semantic Recall search starts with deterministic local token-overlap scoring so contract tests are stable. Runtime Kit also supports an explicit provider-backed development boundary:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --repo-root . \
  --runtime hermes \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3 \
  --recall-search-provider runtime_http \
  --recall-search-endpoint http://127.0.0.1:8788/kaka/recall/search \
  --dry-run
```

The `runtime_http` adapter posts only the query, limit, and sanitized Recall candidates to a runtime-owned local endpoint. Provider errors fall back to deterministic local scoring when safe. Raw embeddings, index rows, provider keys, provider endpoints, SQLite paths, hidden prompts, and raw provider responses are not returned to the phone or included in Recall export.

Recall export is now labeled as `kaka.recall_export.v1`. Runtime Kit builds the export through a shared artifact-policy helper and validates it with `runtime-kit/packaging/recall-export.schema.json`; the artifact remains JSON-first user Recall metadata rather than a database dump. Export items are limited to `item_id`, `summary`, `created_at`, and `provenance`, and the schema keeps embeddings, retrieval-index rows, provider endpoints/keys, bearer/mobile tokens, SQLite paths, hidden prompts, raw provider responses, unrelated task logs, and unconfirmed Context Snapshot data out of exported item data.

`--recall-search-endpoint` must point to localhost, Tailscale CGNAT, `.local`, or a private LAN endpoint. Runtime Kit rejects public HTTP(S) endpoints for `runtime_http` Recall search by default because Recall candidates belong inside the user-owned local runtime boundary.

Production retrieval packaging can be checked without invoking a provider:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit recall-retrieval-readiness \
  --runtime hermes \
  --strategy sidecar_adapter \
  --adapter-package-ref host://retrieval/adapter \
  --runtime-settings-ui-ref host-ui://settings/recall \
  --signature-ref sig://retrieval \
  --conformance-report-ref conformance://retrieval \
  --privacy-review-ref privacy://retrieval \
  --fallback-drill-ref drill://retrieval-fallback \
  --release-notes-ref notes://retrieval
```

`recall-retrieval-readiness` emits `kaka.recall_retrieval_readiness.v1`. It is a read-only readiness artifact for host-native embeddings, sidecar adapter, or capability-negotiated hybrid packaging strategies. It does not choose a provider, run embeddings, invoke endpoints, fetch refs, expose provider endpoints or keys to iPhone, return raw embeddings/index rows/provider responses, include retrieval internals in Recall export, or change `/mobile/v1/recall/search`.

Review a host/runtime-supplied retrieval materials manifest without fetching its
refs:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit recall-retrieval-material-intake \
  --runtime hermes \
  --materials-json artifacts/hermes/recall-retrieval-materials.json
```

The input manifest uses `kaka.recall_retrieval_materials.v1`; the output report
uses `kaka.recall_retrieval_material_intake.v1`. A complete, non-secret
manifest can return `accepted_for_external_retrieval_packaging_review`, which
means it is ready for external host/runtime review. It is not proof that
production retrieval is implemented, signed, privacy-reviewed, or deployed.

Review local renderer backend planning gates without installing or running
future backends:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit local-renderer-backend-capability-manifest
```

The output uses `kaka.local_renderer_backend_capability_manifest.v1`. It keeps
Pillow/`recipe_local` as the only current supported local backend, marks Core
Image, ImageMagick, OpenCV, and libvips as `future_gate_required`, and leaves the
phone-facing `photo_edit` capability and `/mobile/v1` API unchanged.

Start for a physical iPhone on the same trusted LAN:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead
```

Start with image-conversation vision skills routed to the local runtime:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime hermes \
  --hermes-profile dev-lead \
  --vision-provider runtime_http \
  --vision-endpoint http://127.0.0.1:<agent-port>/kaka/vision
```

For development, this repository also includes a lightweight local `/kaka/vision` endpoint so the `runtime_http` path can be tested before Hermes/OpenClaw owns the full model call. On macOS it uses Apple Vision for local OCR-backed skills (`ocr` -> `scan`, `translate_text` -> `translate`) and local image classification/text clues for conservative `identify_subject` and `nutrition_estimate` results. When it cannot find reliable local clues, it returns low-confidence model-not-configured guidance instead of fabricated objects or calorie estimates.

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit.vision_server \
  --host 127.0.0.1 \
  --port 8787
```

Then start the bridge with `--vision-endpoint http://127.0.0.1:8787/kaka/vision`. In this configuration, Kaka's image conversation can execute OCR from a suggestion or typed request and show extracted text from the uploaded photo rather than placeholder endpoint status.

The default `fixture_vision` provider is intentionally limited: it proves UI flow and response shape, but it does not read the uploaded image. A production Hermes/OpenClaw integration should expose a local endpoint that accepts:

- `task`: `vision`
- `mode`: `scan`, `identify`, `translate`, or `food`
- `instruction`
- `locale`
- `image_base64`

and returns either a root `vision` object or `{ "vision": { ... } }` using the schema in `docs/mobile-bridge-api.md`.

The iPhone no longer asks the user to choose scan/identify/translate/food before shooting. The bridge first returns an `image_intake` task result with suggested skills, then Kaka routes suggestion taps or typed requests to these bottom-layer vision modes.

For OpenClaw, the same bridge contract should use `--runtime openclaw` and an OpenClaw-owned recipe endpoint or sidecar configuration once that adapter exists.

## Security Contract

- Install does not auto-start the bridge.
- Default bind host is `127.0.0.1`.
- Physical iPhone discovery requires explicit `--lan` and `--bonjour`.
- Runtime-side settings preview may show local paths, provider endpoints, QR controls, revocation controls, and TLS trust metadata, but `/mobile/v1/runtime/settings` and `phone_safe_summary` must not expose runtime-only secrets. `phone_safe_summary` is allowlisted to coarse store and semantic Recall status only.
- Production mode uses `/mobile/v1/pairing/qr` for short-lived single-use QR payloads, persists revocation when `--runtime-store-path` is configured, exposes runtime-side revoke metadata, and reports trusted local TLS metadata plus optional public-key pinning metadata without exposing private key paths.
- Development mode may keep `pair_dev`; discovery alone does not mint credentials.
- Provider/model keys stay inside the Mac runtime process.
- Logs and doctor output must not print API keys or bearer tokens.
- Runtime-side `process_ownership`, P2.8 `host-package-preview`, and P2.9/P3.1 `host-adapter-run` cover install, start-at-login/start-with-runtime, update, uninstall, logs, health checks, port-conflict repair, and supervision as runtime-side contracts. Mutating `host-adapter-run` actions require explicit approval. Install does not auto-start the bridge and does not create a login item. The `mock` adapter must not mutate the actual host OS, and the `private` adapter may call only the configured host command, using stdin/stdout JSON and structured safe failure handling.
- P3.2 `host-private-adapter-conformance` is a runtime-side validation report for a host-owned command. It validates the lifecycle matrix through the P3.1 private adapter bridge, keeps distribution host-owned, and does not imply Runtime Kit bundles Hermes/OpenClaw proprietary binaries.
- P3.3 `private_adapter_package` is a runtime-side package contract for host-owned command binaries. It records explicit-user-approved updates, host-owned downloads/signatures, and required conformance evidence; it does not bundle Hermes/OpenClaw private APIs or change Mobile Bridge `/mobile/v1`.
- P3.4j `host-shell-pilot-evidence-manifest` is a runtime-side archival index for local pilot JSON only. It does not create archives, run conformance, invoke the private adapter, fetch audit refs, submit handoff, or complete P3.4.
- P3.0 `connection-qa-preview` and the ordinary-user checklist are QA/readiness surfaces only. They report first-run steps, recovery fixtures, and P3.1 host-private command gaps without changing Mobile Bridge `/mobile/v1`, host adapter state, launch items, credentials, ports, or provider configuration.

## Product Path

The target first-run UX is:

1. User installs the Hermes Plugin or OpenClaw Skill/sidecar for Kaka Mobile
   Bridge.
2. User opens the runtime UI and enables **Kaka Mobile Bridge**.
3. The runtime shows a QR code and optionally advertises Bonjour.
4. Kaka iPhone app discovers or scans the bridge.
5. iPhone stores only the endpoint and mobile token in Keychain.

The user should not write adapter code, export an environment variable, or paste
Runtime Kit command chains. The host extension owns adapter discovery and
lifecycle wiring internally. Codex developer plugin or skill automation is for
host engineers only, not ordinary-user installation. Runtime Kit CLI commands
remain the development, conformance, and release-evidence surface for host
teams.

This is the practical version of an AirPods-like setup for a local agent runtime: one explicit enable action, then the phone does the rest.

Use `docs/kaka-ordinary-user-connection-qa.md` as the P3.0 first-run checklist:
install the host-native Plugin/Skill, or for development QA only enable the
scaffold, explicitly start the bridge, show a production QR, pair iPhone, run
health checks, verify saved-token reconnect, revoke the token, and reconnect
with a new QR.
