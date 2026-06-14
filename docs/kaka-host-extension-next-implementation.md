# Kaka Host Extension Next Implementation Plan

Updated: 2026-06-11

This document is the implementation handoff for the Hermes/OpenClaw connection
experience after the plugin/skill product decision. It exists to keep future
work focused on an installable host-native experience instead of asking ordinary
users to write adapter code, export environment variables, or paste Runtime Kit
command chains.

## Product Decision

The normal user path is:

1. Install a host-native Hermes Plugin or OpenClaw Skill/sidecar.
2. Open the host runtime's **Pocket Agent Mobile Bridge** panel.
3. Explicitly enable or start the bridge.
4. Show a short-lived QR code or opt into Bonjour discovery.
5. Pair Pocket Agent iPhone and keep all phone traffic on `/mobile/v1`.

That means Pocket Agent should not ship a phone-side Hermes/OpenClaw private API client.
It also means a public Codex plugin or public Codex skill is not the ordinary
user installer. Codex automation can help Hermes/OpenClaw engineers scaffold,
validate, and review package materials, but the install surface users see must
belong to Hermes/OpenClaw.

## Three Surfaces

Every future task in this area must name the surface it changes.

| Surface | Owner | Intended user | Allowed work |
| --- | --- | --- | --- |
| Host-native extension | Hermes/OpenClaw host team | Ordinary users | Plugin/Skill package, host UI, bridge enable/start, QR/Bonjour, health, logs, revoke, update, uninstall |
| Runtime Kit generators | Pocket Agent repository | Host engineers and release engineers | Read-only contracts, starter packages, handoff artifacts, readiness/intake/conformance reports |
| Codex developer automation | Host engineers using Codex | Host engineers only | Source-only scaffolding, validation, release-gate review, packaging checklists |

Do not mix these surfaces. If a task installs a Codex skill for an ordinary user,
asks the user to configure `--private-adapter-command`, or makes the iPhone call
private host APIs, it is going in the wrong direction.

## Plugin/Skill Development Gate

When future work says "make this a plugin or skill", translate that request
before implementation:

- For ordinary users, "plugin/skill" means a host-native Hermes Plugin or
  OpenClaw Skill/sidecar that is installed through the host runtime's normal
  package channel.
- For Hermes/OpenClaw engineers, "plugin/skill" may also mean optional Codex
  developer automation that scaffolds, validates, or reviews the host-native
  package.
- For Pocket Agent iPhone, "plugin/skill" must not mean a new phone API, a private host
  API client, a hidden adapter setup flow, or user-visible Codex installation.

A future Codex plugin or Codex skill is acceptable only as source-only
host-team tooling. The plan must prove that it writes only to an explicit
output directory, does not update `~/plugins`, `~/.codex/skills`, or
`~/.agents/plugins`, does not install a marketplace entry, does not start the
bridge, does not invoke private adapters, and does not replace the host-native
package. Use `plugin-creator` and `skill-creator` structure rules only for that
developer-automation surface.

## Immediate Implementation Order

Use this order before writing the next install-focused plan.

1. **Check whether real host package facts exist.**
   Ask the Hermes/OpenClaw owner for a sanitized host package candidate bundle
   with package refs, host UI refs, disabled-by-default evidence,
   extension-internal adapter command location, install/update/uninstall drill
   receipts, P3.2 conformance ref, P3.4 evidence manifest ref, and release
   notes.

2. **Review the bundle locally.**
   Run P3.28 material intake:

   ```bash
   PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit host-extension-material-intake \
     --manifest host-package-candidate/materials.json
   ```

   The accepted report must be `kaka.host_extension_material_intake.v1` and must
   not include secrets, raw logs, provider keys, bearer tokens, mobile tokens,
   SQLite paths, private key paths, embeddings, or proprietary host API source.

3. **Rerun readiness.**
   Run P3.6 `host-extension-readiness` for the chosen runtime and require
   `ready_for_external_install_drill`.

4. **Only then write P3.7.**
   Use `superpowers:writing-plans` to create the P3.7 external install drill
   plan. Execute it with `superpowers:subagent-driven-development` or
   `superpowers:executing-plans`. The drill should prove install, explicit
   enable, QR/Bonjour pairing, health, revoke/re-pair, update, logs, repair,
   uninstall, evidence archive readiness, and unchanged `/mobile/v1` traffic.

5. **If facts are still missing, stop installation work.**
   P3.12/P3.13/P3.15/P3.18/P3.19/P3.28/P3.31/P3.35 already cover starter
   materials, package handoff, devkit, Codex developer source, acceptance
   artifacts, material intake, quickstart, and installation blueprint. Do not
   add another repository-only installer wrapper or public Codex plugin/skill.

6. **Pick an independent product slice while blocked.**
   Good blocked-period work improves phone-visible product value without
   touching Host Extension installation, private APIs, or `/mobile/v1`
   compatibility. Recent completed examples are Voice-to-Inbox Draft, Inbox
   Instruction Templates, Paste-to-Inbox, Inbox Result Review Provenance, and
   P3.38 Explicit Files-to-Inbox Import.

## Host Package Candidate Bundle

Ask the host owner for a local sanitized bundle shaped like this:

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

`materials.json` must use `kaka.host_extension_materials.v1`. All refs should
be non-secret pointers or sanitized receipt IDs, not credentials or raw logs.

## Acceptance Gates

An install-focused plan is acceptable only when it proves these gates:

- ordinary users install the Hermes Plugin or OpenClaw Skill/sidecar, not a
  Codex plugin, Codex skill, or Runtime Kit command chain;
- install is disabled-by-default and does not auto-start a LAN listener;
- LAN binding, Bonjour, QR generation, login items, token minting, update,
  repair, and uninstall are explicit host-owned actions;
- the private adapter command is extension-internal and host-owned;
- Pocket Agent iPhone communicates only through `/mobile/v1`;
- phone-bound responses do not include private adapter command paths, provider
  endpoints or keys, bearer/mobile tokens, SQLite paths, private key paths, raw
  logs, embeddings, or proprietary host API details;
- Codex automation, if present, is source-only host-team tooling with an
  artifact or test proving it is not the public installer.

## Recommended Multi-Agent Split

When the P3.7 materials finally arrive, split execution this way:

- **Host materials agent:** verifies package refs, host UI entry point,
  disabled-by-default evidence, and release notes.
- **Runtime Kit agent:** runs `host-extension-material-intake`,
  `host-extension-readiness`, and schema/static drift checks.
- **iPhone boundary agent:** checks that pairing and user-facing docs still show
  `/mobile/v1` only, with no private host API or provider credential exposure.
- **Drill reviewer:** reviews install/update/revoke/uninstall receipts and
  confirms side effects happened only in the host-owned runtime environment.

## Out Of Scope

Do not implement the following as a workaround for missing host-owned package
facts:

- phone-side Hermes/OpenClaw private API clients;
- public Codex plugin/skill installation for ordinary users;
- user-home writes to `~/plugins`, `~/.codex/skills`, or `~/.agents/plugins`;
- mandatory `HERMES_KAKA_HOST_API` or `OPENCLAW_KAKA_HOST_API` setup for users;
- pasted Runtime Kit command chains as the default onboarding flow;
- automatic bridge start, LAN bind, Bonjour advertisement, token minting, or
  login item creation during install.

## Related Documents

- `docs/kaka-host-extension-plugin-skill-roadmap.md`
- `docs/kaka-host-extension-install-experience-spec.md`
- `docs/kaka-host-extension-external-materials.md`
- `docs/mobile-bridge-api.md`
- `docs/agent-pocket-privacy.md`
- `docs/kaka-pocket-agents-next-development-plan.md`
