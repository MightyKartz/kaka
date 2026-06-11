# Kaka Pocket Agents Post-E0 Development Plan

Updated: 2026-06-11

This document records the next development direction after the current Pocket Agents foundation work. It is based on code-first analysis of the working tree, not only on earlier roadmap text.

Most recent follow-up plan referenced by this document:

`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-pending-item-review-details.md`

Most recent repo-owned product slice implemented while Host Extension materials
remain blocked:

`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-pending-item-review-details.md`

P3.41 Inbox Action Feedback Banner is now implemented. Inbox shows visible local
feedback for failed Inbox actions and in-flight submission progress using the
existing `InboxViewModel.state` and `progressText`; failures can be dismissed
locally. It adds no retry, runtime task cancel, automatic submission, Recall
action/write/delete, Mobile Bridge endpoint/schema, App Intent, Host Extension
change, source-file deletion, or P3.7 install drill.

P3.42 Inbox Pending Item Review Details is now implemented. Pending Inbox rows
can expand a local Review Details section before visible `Send`; the section is
driven by `InboxPendingItemReviewPresentation` and shows only existing local
item metadata such as source, type, bounded text or URL excerpt, file name, MIME
type, copied-payload state, saved instruction, route, locale/profile when
present, and Context Snapshot inclusion state. It does not compute file size,
read payload bytes, fetch URLs, parse PDFs/OCR, summarize content, submit,
upload, write/delete Recall, add Mobile Bridge endpoint/schema fields, add App
Intent/Shortcut/Widget/Live Activity behavior, change Host Extension packaging,
scan folders, delete source files, or execute P3.7.

Current installation-focused material review command:

`host-extension-material-intake --manifest /path/to/materials.json`

Current installation-experience follow-up spec:

`docs/kaka-host-extension-install-experience-spec.md`

Current plugin/skill productization roadmap:

`docs/kaka-host-extension-plugin-skill-roadmap.md`

Current Host Extension implementation handoff:

`docs/kaka-host-extension-next-implementation.md`

Current install-productization decision:

Ordinary users should install a host-native Hermes Plugin or OpenClaw
Skill/sidecar. Codex plugin/skill automation is allowed only as source-only
host-team developer tooling for scaffolding, validation, and release gates. It
must not become the public install path, write user-home Codex plugin/skill
roots, or replace the host-native package.

Future plugin/skill development gate:

1. Host-native Plugin/Skill work is the ordinary-user product path: Hermes or
   OpenClaw owns package distribution, host UI, explicit bridge enablement,
   QR/Bonjour pairing, lifecycle controls, private adapter discovery, and
   release evidence.
2. Runtime Kit work may generate or validate contracts, starter materials,
   handoff packages, readiness reports, material-intake receipts, and
   install-drill artifacts for host teams.
3. Codex plugin/skill work is allowed only as host-team developer automation.
   It must follow `plugin-creator` / `skill-creator` structure rules, write only
   under an explicit output directory, and prove no marketplace update,
   `~/plugins`, `~/.codex/skills`, `~/.agents/plugins`, bridge start, private
   adapter invocation, or ordinary-user install surface.
4. Kaka iPhone remains unchanged by installation packaging work: no private
   Hermes/OpenClaw API client, no new `/mobile/v1` endpoint, no hidden adapter
   setup UI, and no provider/runtime secrets on the phone.

Next install-focused development handoff: collect a real Hermes/OpenClaw host
package candidate bundle, review its `kaka.host_extension_materials.v1` manifest
with P3.28 `host-extension-material-intake`, rerun P3.6
`host-extension-readiness`, and only then write/execute P3.7. If that bundle is
not available, do not build another installer wrapper or public Codex
plugin/skill; choose a separately permissioned product slice instead.

Latest install-experience refinement:

`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-extension-user-quickstart.md`

Previous repo-owned follow-up implemented while external Host Extension
materials remain blocked:

`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-result-review-provenance.md`

P3.37 Inbox Result Review Provenance is now implemented. It is intentionally
not another installation wrapper and not a new Mobile Bridge API: after a
visible Inbox `Send` completes, the result banner preserves the source Inbox
item ID, source app/surface, item kind, and whether Context Snapshot was
selected. The banner passes both `source_task_id` and `source_inbox_item_id` to
the existing explicit Recall controls. It adds no automatic Recall write, new
endpoint, runtime schema change, provider call, Host Extension packaging change,
or P3.7 install drill; P3.37 itself added no Files picker.

P3.38 Explicit Files-to-Inbox Import is now implemented. It extends the same
explicit-review Inbox path rather than installation: the user taps a visible
Files button in the main app, selects one supported PDF or image, Kaka copies it
into `SharedPayloads`, creates a pending Inbox item, and waits for visible Inbox
`Send`. This keeps Files import separate from Share Extension, Paste, Voice,
Recall, and Host Extension packaging.

P3.39 Inbox Pending Item Discard is now implemented. It completes the same
pre-`Send` Inbox review loop by giving each pending item a visible Discard
control. The action removes only that local Inbox item through
`KakaInboxStoring.remove(id:)`, so any Kaka-copied `SharedPayloads` payload uses
the existing payload cleanup behavior. It does not upload, submit, cancel
runtime work, delete Recall, add an endpoint, add an App Intent, scan folders,
or change Host Extension packaging.

P3.40 Inbox Discard Confirmation is now implemented. It hardens P3.39 without
changing the deletion semantics: the row-level Discard control now opens a
visible confirmation dialog, and only the destructive confirm action calls the
existing local discard path. Cancel or dismissal leaves the pending item and
payload untouched. It adds no runtime upload/task/cancel, Recall action/delete,
Mobile Bridge endpoint, App Intent, Host Extension change, folder scan,
source-file deletion, or P3.7 install drill.

P3.41 Inbox Action Feedback Banner is now implemented. It keeps improving the
same visible review loop by rendering failed Inbox actions and in-flight
submission progress from existing local ViewModel state. The failure banner can
be dismissed locally. It does not add retry, runtime task cancel, automatic
submission, Recall action/write/delete, Mobile Bridge endpoint/schema, App
Intent, Host Extension change, source-file deletion, or P3.7 install drill.

P3.42 Inbox Pending Item Review Details is now implemented. It keeps the same
pre-`Send` review loop local and explicit: a row-level Review Details toggle
expands read-only metadata for the pending item, including source/type, bounded
text or URL excerpt, file name/type, local copied-payload state, saved
instruction, and Context Snapshot inclusion state. It adds no ViewModel submit
state, runtime task, endpoint/schema field, Recall action, App Intent, Host
Extension change, URL fetch, PDF/OCR parsing, file read, folder scan, source
deletion, or P3.7 install drill.

Most recent repo-owned product slice:

`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-pending-item-review-details.md`

P3.30 Voice-to-Inbox Draft is implemented. It reuses the existing B.1 voice
capture and on-device transcription stack, saves the reviewed transcript as a
pending text Inbox item, and leaves the normal visible Inbox `Send` action as
the only runtime submission path. It does not upload raw microphone audio, start
hidden recording, auto-submit to runtime, write Recall automatically, add a new
`/mobile/v1` endpoint, or create another Hermes/OpenClaw installation wrapper.

P3.32 Inbox Voice Instruction is implemented. It reuses the same voice capture
sheet at the existing Inbox row level: a user can add or replace an instruction
on an already captured universal-intake item, Kaka saves the reviewed transcript
into `KakaInboxItem.note`, and the runtime still receives it only through the
normal visible Inbox `Send` path. Universal intake already maps the note to
`note` and `user_instruction`, so P3.32 adds no Mobile Bridge endpoint, raw audio
upload, auto-submit path, automatic Recall write, App Intent recording path, or
Host Extension packaging change.

P3.33 Inbox Instruction Polish is implemented. It adds a focused
`InboxInstructionPresentation`, labels saved instructions, changes the row action
to edit when a note exists, allows clearing `KakaInboxItem.note` before
submission, and shows send-preview copy that the instruction will travel with
the item. The runtime boundary remains the existing universal intake
`note` / `user_instruction` text path; P3.33 adds no Mobile Bridge endpoint, raw
audio upload, automatic submission, automatic Recall write, App Intent recording,
or Host Extension packaging change.

P3.34 Inbox Instruction Templates is implemented. Universal-intake Inbox rows
now expose deterministic local chips for Summarize, Extract Actions, Translate,
and Ask Follow-up. Tapping a chip only writes the selected template text into
`KakaInboxItem.note`; the user still reviews and presses visible `Send` before
the runtime receives existing `note` / `user_instruction` text. P3.34 adds no
endpoint, audio upload, automatic submission, automatic Recall, App Intent
recording, provider call, or Host Extension packaging change.

P3.31 Host Extension User Quickstart is implemented as the latest
install-experience refinement. It extends the existing
`host-extension-install-package`
handoff with ordinary-user quickstart copy and a user-journey acceptance artifact
so host teams can package Kaka as a native Hermes Plugin / OpenClaw Skill without
asking users to write adapter code, paste Runtime Kit commands, install Codex
automation, or touch private host APIs.

P3.35 **Host-Native Plugin/Skill Installation Blueprint** is implemented from
`docs/superpowers/plans/2026-06-11-kaka-pocket-agents-host-native-installation-blueprint.md`.
It makes the desired package shape concrete with manifest expectations, host UI
state/control requirements, lifecycle receipts, evidence gates, Codex automation
boundaries, and no-side-effect flags. The implementation extends
`host-extension-install-package` with `installation_blueprint` and
`host-ui/installation-blueprint.json`; it is not a new command, public Codex
plugin, public Codex skill, or command-wrapper installer.

P3.36a Inbox Voice Capture Context Copy is implemented. `VoiceCaptureView` now
accepts context presentation while preserving the default image-conversation
copy; Inbox draft sheets say "Save Draft", row-level instruction sheets say
"Save Instruction", and localized tests cover both contexts. Behavior remains
unchanged: draft text becomes a pending Inbox item, instruction text becomes
`KakaInboxItem.note`, and runtime submission still requires visible Inbox
`Send`.

P3.36b Explicit Paste-to-Inbox Courier is implemented. Inbox now exposes a
visible Paste button next to Voice Draft. The button reads text from the system
pasteboard once via `ClipboardCourierReading`, trims it, classifies valid
http/https URLs as `.url`, otherwise creates `.text`, writes a pending
universal-intake item with source app `Clipboard` and `sourceSurface = "paste"`,
and never calls the runtime submitter. Runtime submission still waits for
visible Inbox `Send`.

P3.37 Inbox Result Review Provenance is implemented. Successful Inbox
submissions now keep a phone-safe `InboxSubmissionContext` for the result banner:
source Inbox item ID, source app, source surface, item kind, and Context
Snapshot selected state. The result banner shows source/context review copy and
passes the source Inbox item ID into `RecallView`, so explicit Remember/Use
Once/Forget actions can preserve both task and Inbox provenance through the
existing Recall action contract.

Post-P3.37 development decision: if real Hermes/OpenClaw package facts are not
available, stop adding repository-only installation wrappers. The ordinary-user
install answer is now stable enough for this repository: install the
host-native Hermes Plugin or OpenClaw Skill, enable Kaka Mobile Bridge in the
host UI, then pair by QR or Bonjour through `/mobile/v1`. The next in-repo work
should either execute P3.7 with real host-owned materials, or move to another
small product-facing slice that preserves visible review and existing Mobile
Bridge contracts.

The next install-focused trigger is a host package candidate bundle, not a new
repository-owned installer. The bundle should contain the real Plugin/Skill
package ref, host UI entry point, disabled-by-default evidence,
extension-internal adapter command location, install/update/uninstall and pairing drill
receipts, P3.2 conformance ref, P3.4 evidence manifest ref, and release notes
confirming the phone remains on `/mobile/v1`.

Recent product slices:

1. **P3.37 Inbox Result Review Provenance**:
   `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-result-review-provenance.md`.
   Implemented as a result-banner provenance handoff: completed Inbox results
   show source/context review copy and pass both `source_task_id` and
   `source_inbox_item_id` into explicit Recall controls. It does not implement
   automatic Recall, new endpoints, runtime schema changes, Files picker, host
   installation work, or P3.7.
2. **P3.39 Inbox Pending Item Discard**:
   `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-pending-item-discard.md`.
   Implemented as a local pre-`Send` queue cleanup action: a visible row-level
   Discard button removes only the selected pending Inbox item through
   `KakaInboxStoring.remove(id:)` and relies on existing payload cleanup. It does
   not submit, upload, cancel runtime tasks, delete Recall, add endpoints, add
   App Intents, scan folders, or change Host Extension packaging.
3. **P3.40 Inbox Discard Confirmation**:
   `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-discard-confirmation.md`.
   Implemented as a confirmation gate on the P3.39 local discard path: row-level
   Discard opens a visible dialog, destructive confirmation calls the existing
   local discard method, and cancel/dismiss leaves the pending item untouched. It
   does not submit, upload, cancel runtime tasks, delete Recall, add endpoints,
   add App Intents, scan folders, delete source files, or change Host Extension
   packaging.
4. **P3.41 Inbox Action Feedback Banner**:
   `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-action-feedback-banner.md`.
   Implemented as local visible feedback for existing Inbox action state:
   failed actions and in-flight submission progress render in the Inbox, and
   failures can be dismissed locally. It does not retry, auto-submit, cancel
   runtime tasks, write/delete Recall, add endpoints, add App Intents, scan
   folders, delete source files, or change Host Extension packaging.
5. **P3.42 Inbox Pending Item Review Details**:
   `docs/superpowers/plans/2026-06-11-kaka-pocket-agents-inbox-pending-item-review-details.md`.
   Implemented as a local, read-only row-level details expansion for pending
   Inbox metadata before `Send`. It shows existing local source/type, bounded
   text or URL excerpt, file name/type, copied-payload state, saved instruction,
   and Context Snapshot inclusion state without fetching URLs, parsing
   PDFs/OCR, reading payload bytes, submitting, writing Recall, changing
   endpoints, adding App Intents, or touching Host Extension packaging.

Next candidate while Host Extension materials remain blocked:

- Choose another separately permissioned product-facing slice, or run P3.7 only
  after real host-owned Plugin/Skill package facts pass P3.28/P3.6 review. Do
  not add another installation wrapper or repeat P3.42 as a runtime/API feature.

Next development tracks:

1. Repo-owned install UX/productization that just landed:
   P3.15 Host Plugin/Skill Devkit turns the P3.12 starter-kit and P3.13
   install-package handoff into template-only host-team development materials:
   contract index, command files, acceptance gates, ordinary-user boundary,
   adapter templates, and optional Codex automation templates. It does not
   create a third install package, real Codex plugin, marketplace entry, or
   ordinary-user install surface.
2. External Host Extension productization that should remain the user-install
   direction:
   Kaka should be installed into Hermes as a Hermes Plugin and into OpenClaw as
   an OpenClaw Skill or sidecar. The private adapter command is a host-owned
   implementation detail inside that extension, not a normal user setup step.
   External P3.7 cannot proceed until real host-owned
   install/signature/conformance/evidence inputs exist. If those inputs remain
   blocked but installation UX still needs work, build only on the completed
   P3.35 blueprint boundary, not a public Codex plugin/skill and not another
   command-wrapper installer. The concrete next install handoff is a
   host-owned package candidate bundle reviewed by P3.28 material intake before
   P3.7.
3. Repo-owned runtime safety that just landed:
   P3.14 runtime retention enforcement and purge receipts added explicit
   Runtime Kit `retention-purge`, a closed
   `kaka.runtime_retention_purge_receipt.v1` schema, dry-run/apply behavior,
   idempotent terminal-task cleanup, active task preservation, mock asset
   timestamp skip reporting, and tests proving Recall remains explicit and
   phone settings remain read-only. It did not add automatic cleanup,
   background jobs, Swift UI, phone-triggered purge APIs, or SQLite path
   exposure.
4. Repo-owned renderer/capability truth that just landed:
   P3.16 proves the existing `recipe_local` local renderer path with a
   runtime-side readiness probe. P3.17 aligns the default `photo_edit` capability
   with that proof by advertising exactly two variants:
   `variant_clean_pro` and `variant_social_pop`. P3.17b narrows only default
   `photo_edit.accepted_mime_types` to JPEG for that local recipe flow. These
   are capability truth corrections, not a new cloud image provider, phone API,
   persistent asset store, generic upload restriction, or renderer dependency.
5. Repo-owned developer automation that just landed:
   P3.18 materializes the P3.15 Codex automation templates into a real
   Codex developer plugin source tree for Hermes/OpenClaw host engineers. It
   writes only under an explicit output directory, uses runtime-specific
   source roots such as `kaka-host-extension-developer-hermes` and
   `kaka-host-extension-developer-openclaw`, and report
   `ordinary_user_install: false`, `installs_codex_plugin: false`,
   `updates_marketplace: false`, and `writes_user_home: false`. It does not
   install a Codex plugin, update a Codex marketplace, write `~/.codex`,
   `~/.agents`, or `~/plugins`, install Hermes/OpenClaw packages, start the
   bridge, invoke private adapters, run conformance, or change `/mobile/v1`.
6. Repo-owned install experience acceptance that just landed:
   P3.19 strengthens the existing `host-extension-install-package` output with
   host UI acceptance metadata, generated `host-ui/acceptance.json`, ordered
   install-drill steps, evidence receipt refs, TLS/readiness/evidence/Codex
   developer-source release gates, and static manifest/schema drift protection.
   It does not add a new CLI, install packages, sign/publish, start the bridge,
   expose private host APIs, or make Codex automation the ordinary-user
   installer.
7. Repo-owned Recall export safety that just landed:
   P3.20 labels Recall export as `kaka.recall_export.v1` and attaches a closed
   artifact policy so export remains JSON-first user Recall metadata rather than
   a SQLite/database dump. It keeps embeddings, retrieval-index rows, provider
   endpoints/keys, bearer/mobile tokens, SQLite paths, hidden prompts, raw
   provider responses, unrelated task logs, raw asset bytes, and unconfirmed
   Context Snapshot content out of the exported artifact.
8. Repo-owned Recall retrieval packaging readiness that just landed:
   P3.21 adds Runtime Kit `recall-retrieval-readiness` for production retrieval
   packaging refs across host-native embeddings, sidecar adapter, and
   capability-negotiated hybrid strategies. It is read-only, does not choose or
   invoke a provider, does not fetch refs, does not change
   `/mobile/v1/recall/search`, and tightens outbound runtime HTTP candidate
   provenance to a small source-field allowlist.
9. Repo-owned asset retention timestamping that just landed:
   P3.22 extends explicit runtime-side `retention-purge` receipts so timestamped
   mock bridge input/output assets appear in eligible/deleted groups and are
   removed only on runtime-side apply. Upload and photo-edit result assets now
   carry in-memory `role` and `created_at` metadata; untimestamped assets remain
   preserved as untracked. P3.22 itself did not add automatic cleanup, a Mobile
   Bridge purge endpoint, phone-side settings writes, Swift UI, SQLite asset
   storage, Recall purge, or raw asset bytes in receipts.
10. Repo-owned SQLite asset storage/retention that just landed:
    P3.24 adds Runtime Kit `runtime_assets` storage for configured
    `SQLiteRuntimeStore` instances. Mock bridge upload, download, photo-edit,
    vision, image-intake, universal-intake metadata, QA status, and explicit
    retention purge now route through asset helpers that use SQLite when
    available and preserve in-memory behavior otherwise. Store-backed assets
    survive app restart and can be deleted only by explicit runtime-side
    `retention-purge` apply. P3.24 does not add automatic cleanup, a Mobile
    Bridge purge endpoint, phone-side settings writes, Swift UI, Recall purge,
    provider calls, host package changes, raw bytes/path leakage in receipts,
    or task result detail/variant persistence.
11. Repo-owned durable result browsing follow-up that just landed:
    P3.25 makes store-backed `GET /mobile/v1/tasks/{id}` return the same
    phone-safe photo-edit result detail users saw before restart. Persist only
    safe manifest fields in `RuntimeTaskRecord.metadata`: variant ID, label,
    asset ID, explanation, and allowlisted structured recipe/status fields.
    Keep raw bytes in `runtime_assets`, rebuild variant `download_url` from
    `asset_id` at response time, keep task lists summary-only, and expose only
    `variant_count` in store-backed completed task events.
12. Repo-owned Recall retrieval material intake that just landed:
    P3.26 adds `recall-retrieval-material-intake`, a Runtime Kit read-only
    report that ingests a local host/runtime-owned materials manifest, filters
    secret-like fields and values, embeds the P3.21 readiness snapshot, and can
    report `accepted_for_external_retrieval_packaging_review` without calling a
    provider, fetching refs, validating signatures, exposing provider internals,
    changing Recall export, or changing `/mobile/v1/recall/search`.
13. Repo-owned local renderer backend capability manifest that just landed:
    P3.27 adds `local-renderer-backend-capability-manifest`, a Runtime Kit
    read-only planning manifest that records current Pillow/`recipe_local` truth
    and future Core Image/ImageMagick/OpenCV/libvips gates. It does not install
    dependencies, import or execute future backends, add endpoints, change
    phone-facing capabilities, or change `/mobile/v1`.

14. Repo-owned Host Extension material intake that just landed:
    P3.28 adds `host-extension-material-intake`, a Runtime Kit read-only
    manifest review for the eight P3.6 package facts and install-drill refs. It
    embeds existing `host-extension-readiness`, redacts/blocks secret-like
    values before readiness echoes refs, and emits
    `kaka.host_extension_material_intake.v1` for future P3.7 external
    install-drill review. It does not install, sign, publish, fetch refs, start
    the bridge, bind LAN, advertise Bonjour, mint tokens, invoke private
    adapters, write Codex user-home install roots, or change `/mobile/v1`.
15. Repo-owned voice-first product slice that just landed:
    P3.30 adds Voice-to-Inbox Draft. The Inbox gains a visible microphone
    affordance that reuses `VoiceCaptureView`; the reviewed transcript becomes a
    pending `.text` `KakaInboxItem`; source provenance is recorded as voice; and
    the user still reviews and taps Inbox `Send`. This is intentionally not
    Clipboard/Link Courier, not audio upload, not hidden listening, not
    automatic Recall, and not an installation wrapper.
16. Repo-owned install-experience refinement that just landed:
    P3.31 adds ordinary-user quickstart and user-journey acceptance output
    to the existing `host-extension-install-package` handoff. This is a
    packaging UX/acceptance improvement for host teams, not a new installer and
    not a public Codex plugin/skill path.
17. Repo-owned voice-first Inbox refinement that just landed:
    P3.32 adds Inbox Voice Instruction. Existing universal-intake Inbox rows can
    open the same `VoiceCaptureView`, save the reviewed transcript into
    `KakaInboxItem.note`, and then wait for the normal visible Inbox `Send`
    action. The existing submitter sends the note as `note` and
    `user_instruction`; this is not a raw-audio path, hidden listener,
    auto-submit action, Recall write, new bridge endpoint, App Intent recorder,
    or Host Extension packaging change.
18. Repo-owned Inbox instruction polish that just landed:
    P3.33 adds visible edit/clear and submit-preview polish for saved Inbox
    instructions. It introduces a small presentation helper, clears notes through
    `InboxViewModel.clearVoiceInstruction`, and keeps runtime submission on the
    existing `note` / `user_instruction` path after visible `Send`.
19. Repo-owned Inbox instruction templates that just landed:
    P3.34 adds deterministic local chips for Summarize, Extract Actions,
    Translate, and Ask Follow-up on universal-intake Inbox rows. Chip taps call
    `InboxViewModel.applyInstructionTemplate`, which reuses
    `updateVoiceInstruction` to write `KakaInboxItem.note` only; runtime
    submission still waits for visible Inbox `Send`.

Completed P3.12 Host Extension Starter Kit is the product-shape correction for
Hermes/OpenClaw onboarding: ordinary users should install a Hermes Plugin or
OpenClaw Skill/sidecar, open the host Kaka Mobile Bridge panel, explicitly
enable the bridge, show QR or opt into Bonjour, and pair Kaka iPhone through
`/mobile/v1`. They should not write adapter code, export
`HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, or paste Runtime Kit command
chains.

Current product decision for future work: yes, the Hermes/OpenClaw integration
should be packaged as an installable Host Extension. Runtime Kit may generate
starter-kit and install-package handoff artifacts for host teams, but ordinary
users should see a native host install surface and a Kaka Mobile Bridge panel,
not terminal setup. Any future plan that asks users to edit adapter code, expose
private host APIs to the iPhone, or configure `--private-adapter-command` as the
default onboarding path is off direction.

Plugin/skill packaging decision for future work: keep three surfaces separate.
The ordinary-user install surface is the host-native Hermes Plugin or OpenClaw
Skill/sidecar. Runtime Kit is the repo-owned contract and material generator for
host teams. A future Codex developer plugin or Codex skill may automate
scaffolding, validation, and release-gate checks for host engineers, but it must
not become the public user installer or a replacement for the host-native
extension. Use `skill-creator` and `plugin-creator` as design guardrails for
the Codex automation shape, but do not follow their personal-marketplace install
flow for ordinary Kaka users.

Next implementation recommendation: do not add another installation wrapper
while P3.7 remains blocked on external host-owned package facts. If installation
UX remains the priority, build only on the completed P3.35 Host-Native
Plugin/Skill Installation Blueprint boundary. If continuing the voice-first product line after
P3.34, choose a new independently reviewable Inbox polish slice while preserving
visible review, no automatic submission, no automatic Recall, and the existing
universal intake `note` / `user_instruction` path. If installation work becomes
unblocked, switch back to P3.7 with real Hermes/OpenClaw package materials.

Completed P3.19 Host Extension install experience acceptance strengthens the
existing P3.13 package handoff instead of adding another wrapper. Runtime Kit now
generates a stricter host UI acceptance file, a complete ordered install-drill
runbook, evidence receipt refs, and release gates that connect P3.6 readiness,
P3.2 conformance, P3.4 evidence manifest, P3.8/P3.10 TLS readiness, and P3.18
developer automation source.

External P3.7 still cannot start until P3.4/P3.6 host-owned install drill
materials are available. The external development handoff remains
`docs/kaka-host-extension-external-materials.md`, which lists the exact Hermes
Plugin / OpenClaw Skill materials required before writing a P3.7 install-drill
execution plan. While that material collection is blocked, P3.9 retention policy
controls, P3.10a local HTTPS serving, and P3.10b iOS trust/pinning integration
have been completed as in-repository security/platform slices. P3.12 Host
Extension Starter Kit, P3.13 Host Extension installable package handoff, and
P3.15 Host Plugin/Skill Devkit have landed as the current ordinary-user
installation/productization support slices; P3.11 native iOS connection polish
has also landed as the current repo-owned phone-side recovery slice; P3.14
runtime retention purge receipts has now landed as the current repo-owned
Runtime Kit safety slice, and P3.22 has now landed as the timestamp-aware mock
bridge asset purge receipt follow-up. P3.20 Recall export artifact policy and
P3.21 Recall retrieval packaging readiness have now landed as the current
repo-owned Recall data/retrieval boundary slices.

Completed P3.13 Host Extension installable package handoff is the packaging
step after P3.12. Runtime Kit now turns the starter-kit output into a host-team
package handoff with plugin/skill manifest files, host UI contract files,
install-drill runbooks, and release-gate commands. It still leaves signing,
update channels, proprietary private adapter implementation, conformance
evidence, and final distribution with Hermes/OpenClaw host teams.

Completed P3.14 Runtime retention purge receipts is the safety step after P3.9.
Runtime Kit now has explicit `retention-purge` dry-run/apply behavior, closed
receipt schema validation, terminal-task-only store cleanup, active task
preservation, and a runtime-side receipt boundary for assets. P3.22 now adds
timestamp-aware mock bridge input/output asset receipt groups on that boundary.
P3.14 keeps Recall deletion explicit and does not add automatic cleanup,
phone-side purge APIs, phone settings writes, or Swift UI.

Completed P3.15 Host Plugin/Skill Devkit is the installation experience slice
after P3.14. Runtime Kit now exposes `host-plugin-skill-devkit`, which can print
or write a host-team development materials bundle with contract indexes, command
files, acceptance gates, ordinary-user boundary metadata, adapter templates, and
template-only Codex automation. It does not ask ordinary users to write adapter
code, export environment variables, paste Runtime Kit commands, install Codex
automation, or connect the phone to private host APIs.

Completed P3.16 Local renderer backend readiness is the renderer truth slice
after P3.15. Runtime Kit now exposes `local-renderer-backend-readiness`, which
runs a synthetic `recipe_local` probe through the local parametric renderer and
emits `kaka.local_renderer_backend_readiness.v1`. It proves the current local
renderer can produce the expected two JPEG variants without adding a phone API,
cloud image provider path, persistent asset storage, bridge startup behavior,
LAN binding, Bonjour, credentials, or new renderer dependencies.

Completed P3.17 Photo edit capability truth aligns the default local mock bridge
and docs with P3.16: `photo_edit.return_variants_max` is `2` for `recipe_local`,
matching `variant_clean_pro` and `variant_social_pop`. This does not narrow the
generic asset upload surface, vision/image-intake MIME handling, or universal
intake.

Completed P3.17b Photo edit MIME truth narrows only the default
`recipe_local` `photo_edit.accepted_mime_types` to `["image/jpeg"]`, matching
the normal iOS camera/library photo-edit path that JPEG-normalizes before
upload. It keeps `/mobile/v1/assets`, `vision`, `image_intake`, and universal
intake broad and unchanged.

Completed P3.20 Recall export artifact policy makes `GET /mobile/v1/recall/export`
machine-verifiable without changing the existing endpoint. Runtime Kit now uses
a shared export sanitizer and `recall-export.schema.json` so exports contain
only user-readable Recall item ID, summary, created timestamp, and provenance.
It explicitly excludes embeddings, retrieval-index rows, provider endpoints or
keys, bearer/mobile tokens, SQLite paths, hidden prompts, raw provider
responses, unrelated task logs, raw asset bytes, and unconfirmed Context
Snapshot content.

Completed P3.21 Recall retrieval packaging readiness gives host teams a
read-only production packaging proof before choosing a real retrieval provider
implementation. Runtime Kit now exposes `recall-retrieval-readiness` with
`kaka.recall_retrieval_readiness.v1`, strategy enum, required non-secret refs,
safety consts, CLI/schema tests, and outbound runtime HTTP provenance
allowlisting. It keeps provider package, endpoint, keys, embeddings, fallback
drill evidence, and production provider choice host/runtime-owned.

Completed P3.22 Asset retention timestamped purge closes the P3.14 mock-asset
gap for in-memory mock bridge assets. Runtime Kit `retention-purge` now
classifies timestamped input/output assets, reports them in eligible/deleted
receipt groups, and removes them only on explicit runtime-side apply. Mock
bridge uploads and photo-edit outputs carry `role` and `created_at` metadata.
Untimestamped assets remain preserved as untracked; P3.22 itself did not add
automatic cleanup, Mobile Bridge purge endpoint, phone-side settings write,
Swift UI, SQLite asset table, Recall purge, or raw asset bytes in receipts.

Completed P3.24 SQLite asset storage retention is the store-backed continuation
of P3.22. Runtime Kit now stores Mobile Bridge input/output assets in
`SQLiteRuntimeStore` when a runtime store is configured, and `retention-purge`
can include those persisted assets in explicit dry-run/apply receipts. Mock
bridge upload/download/photo-edit/vision/image-intake/universal-intake metadata
and QA paths use a shared helper layer so no-store mode remains in-memory. P3.24
does not add a phone purge endpoint, automatic cleanup, phone-side settings
write, Swift UI, Recall purge, provider calls, host package changes, raw
bytes/path receipt leakage, or task result detail/variant persistence.

Completed P3.23 Context Snapshot permission UX improves the Inbox preview
without changing the Mobile Bridge payload. `ContextSnapshotViewModel` now
exposes readable preview rows for permission-denied, not-requested, unavailable,
coarse precision, network, battery, location, and calendar sentinel values while
keeping raw payload values stable for runtime compatibility. The preview shows a
preparing state, and Inbox Send is disabled only while user-enabled context is
still being collected. P3.23 does not add new permission prompt flows,
background collection, entitlements, Mobile Bridge fields, runtime APIs, Recall
writes, provider calls, or storage changes.

Recommended next implementation order:

1. Recheck external readiness:
   if a real host package candidate bundle is available, choose the first external
   pilot host:
   Hermes first if the local Hermes shell remains available, otherwise OpenClaw.
2. Generate P3.13 install-package handoff artifacts for that runtime and hand
   them to the host owner as packaging input, not as a public signed package.
3. Collect the eight P3.6 readiness inputs from the host owner:
   `install_command`, `update_channel`, `adapter_command_location`,
   `host_ui_entrypoint`, `signed_package_ref`, `signature_ref`,
   `conformance_report_ref`, and `evidence_manifest_ref`.
4. Review the bundle with P3.28 `host-extension-material-intake`, then rerun
   `host-extension-readiness` with real values. Only when both reports accept
   the material and readiness returns
   `ready_for_external_install_drill` should the next agent write and execute
   P3.7 external install drill steps.
5. If external materials remain blocked, do not add another installation wrapper
   after P3.19 unless it consumes real host-owned package facts. P3.31 is the
   allowed exception because it only strengthens the existing
   `host-extension-install-package` quickstart/user-journey acceptance artifacts
   and does not install, sign, publish, invoke private adapters, or create a
   Codex ordinary-user installer.
6. If external materials remain blocked but the next work must stay
   installation-focused, collect a real `kaka.host_extension_materials.v1`
   manifest and review it with P3.28 `host-extension-material-intake`, or build
   on the P3.31 pattern when the gap is ordinary-user quickstart/acceptance
   copy. Do not add another wrapper or Codex ordinary-user installer.
7. If external materials remain blocked and the next work is not about
   installation, choose the next independent repo-owned product slice. C.1b
   network-only, P3.16 local renderer backend readiness, P3.17 variant truth,
   P3.17b MIME truth, P3.18 Host Codex developer plugin source, P3.19 Host
   Extension install experience acceptance, P3.20 Recall export artifact policy,
   P3.21 Recall retrieval packaging readiness, P3.22 asset retention
   timestamped purge, P3.23 Context Snapshot permission UX, P3.24
   SQLite-backed asset storage/retention, and P3.25 store-backed task result
   detail persistence, P3.26 Recall retrieval material intake, and P3.27 local
   renderer backend capability manifest, P3.29 Context Snapshot motion/calendar,
   P3.30 Voice-to-Inbox Draft, P3.36a Inbox Voice Capture Context Copy,
   P3.36b Explicit Paste-to-Inbox Courier, P3.37 Inbox Result Review
   Provenance, P3.38 Explicit Files-to-Inbox Import, P3.39 Inbox Pending
   Item Discard, P3.40 Inbox Discard Confirmation, and P3.41 Inbox Action
   Feedback Banner are now implemented. Use a
   real-material P3.28 review followed by P3.7 only when host-owned package
   facts arrive; otherwise choose the next separately permissioned product slice.
8. For future plugin/skill work, continue using `skill-creator` and
   `plugin-creator` as design guardrails only after deciding the exact target:
   Codex developer automation, Hermes Plugin public package, or OpenClaw
   Skill/sidecar public package. Do not mix those surfaces in one deliverable,
   and do not install Codex automation as ordinary-user onboarding.

Implementation boundary note for the next developer: the current working tree
also contains earlier Swift/iOS, App Intent, WidgetKit, and Runtime Kit SQLite
store changes. Do not treat those files as part of the P3.12 starter-kit file
set, P3.10a local HTTPS serving, or P3.9 retention controls. Any release review,
staging, or follow-up plan should isolate the current slice's file set from
those pre-existing changes, or explicitly promote the older changes into their
own numbered slice before landing them.

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-retention-policy-controls.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-host-extension-packaging-pairing-ux.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-manifest.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-request-bundle.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-artifact-review.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-runbook.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-preflight.md`

Previous agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-handoff-bundle.md`

Earlier agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-refs.md`

Earlier agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-private-adapter-authoring-kit.md`

Earlier agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-command-discovery.md`

Earlier agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-external-host-shell-pilot-readiness.md`

Earlier agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-real-host-packaging-distribution.md`

Completed P3.1 slice: Runtime Kit now defines and executes the host-private
command bridge behind `host-adapter-run --adapter private`. The repository still
does not bundle proprietary Hermes/OpenClaw private API implementations.
Runtime Kit builds a sanitized request, invokes a configured host command with
`shell=False`, sends JSON on stdin, reads JSON on stdout, blocks disabled or
unapproved private actions before calling the command, and maps failures into
structured safe adapter results. The Hermes/OpenClaw host shell supplies the
command that calls its native private APIs.

Completed P3.2 slice: Runtime Kit now exposes a runtime-side
`host-private-adapter-conformance` CLI that accepts a host-owned command and
validates install, login item, update, uninstall, logs, health, port-repair, and
supervision through the P3.1 private adapter behavior. It keeps distribution and
proprietary binaries host-owned, emits a closed conformance report schema, proves
unapproved/disabled action gates do not invoke the private command, and leaves
the iPhone isolated to Mobile Bridge `/mobile/v1`.

Completed P3.3 slice: real host packaging/distribution contract metadata.
Runtime Kit now embeds `host-package-preview.private_adapter_package` with
`kaka.host_private_adapter_package.v1` metadata for host-owned binary naming,
discovery, distribution channels, explicit-user-approved updates, host-owned
downloads/signatures, and the required P3.2 conformance gate. The preview stays
non-mutating, does not execute private commands, and does not move proprietary
Hermes/OpenClaw binaries into Kaka.

Completed P3.4a slice: external host-shell pilot readiness receipt. Runtime Kit
now exposes `host-shell-pilot-report` with a closed
`kaka.host_shell_pilot_receipt.v1` schema, static Hermes/OpenClaw manifest
declarations, and docs for real-vs-synthetic external host-shell pilot evidence.
It returns structured `not_ready` receipts for missing or malformed commands,
reports repository fake fixture conformance as `synthetic_only`, rejects forged
`ready` receipts with missing command evidence, and still refuses to mark P3.4
complete without a real host-owned binary outside this repository.

Completed P3.4b slice: host-shell pilot command discovery. Runtime Kit now lets
`host-shell-pilot-report` resolve a host-owned private adapter command from the
same runtime-side discovery sources declared by P3.3: explicit
`--private-adapter-command`, `HERMES_KAKA_HOST_API` or `OPENCLAW_KAKA_HOST_API`,
manifest `host_private_adapter.command`, and the well-known Application Support
path. Discovery does not search `$PATH`, does not expose private host APIs to
iPhone, and does not complete P3.4; missing discovery remains `not_ready`.

Completed P3.4c slice: host private adapter authoring kit. Runtime Kit now
includes a host-team implementation guide and schema-checked JSON examples for
the private adapter stdin request, stdout response, invalid extra-field response,
and pilot ready receipt. It also hardens direct conformance for executable
command paths that contain spaces, which matters for Application Support
install locations. The guide and examples are public contract artifacts only;
they do not implement or bundle Hermes/OpenClaw proprietary APIs.

Completed P3.4d slice: host-shell pilot evidence refs. Runtime Kit now lets
`host-shell-pilot-report` record optional host-supplied audit refs under
`distribution.evidence` and `drills.evidence` for native channel, signature,
notarization team, update feed, install drill, update drill, failure recovery
drill, and release notes. These refs do not set verified booleans, are not
downloaded/read/validated by Runtime Kit, are not exposed to phone `/mobile/v1`,
and must not contain secrets, raw logs, private keys, provider keys, tokens, or
credentials.

Completed P3.4e slice: host-shell pilot handoff bundle. Runtime Kit now exposes
`host-shell-pilot-handoff`, a machine-readable wrapper around the existing pilot
receipt. It records deliverables, checks whether all P3.4d audit refs are
present, emits `ready_to_submit` only when the embedded receipt is ready and all
refs are present, and still keeps `p3_4_complete: false` because final P3.4
completion belongs to the external host shell.

Completed P3.4f slice: host-shell pilot preflight. Runtime Kit now exposes
`host-shell-pilot-preflight`, a read-only report that checks whether the local
Mac has the Hermes/OpenClaw host shell and a host-owned private adapter command
discoverable by explicit arg, runtime env var, manifest entrypoint, or
well-known path. `$PATH` discovery is informational only. The command never
invokes the private adapter, never runs conformance, never fetches audit refs,
and reports `ready_for_conformance` rather than pilot completion.

Completed P3.4g slice: host-shell pilot runbook. Runtime Kit now exposes
`host-shell-pilot-runbook`, a read-only operator artifact for the external host
team. It composes the P3.4f preflight summary with a brief, pilot target,
ordered steps, command artifacts, evidence requirements, and acceptance gates.
It does not invoke the private adapter, run conformance, fetch audit refs,
mutate host state, submit handoff, or mark P3.4 complete.

Completed P3.4h slice: host-shell pilot artifact review. Runtime Kit now
exposes `host-shell-pilot-artifact-review`, a read-only post-run checker for
preflight, conformance, pilot receipt, and handoff JSON artifacts. It checks
load/schema status, runtime alignment, embedded conformance/receipt consistency,
audit-ref completeness, and private command consistency without invoking host
commands, running conformance, fetching refs, mutating host state, submitting
handoff, or marking P3.4 complete.

Completed P3.4i slice: host-shell pilot request bundle. Runtime Kit now exposes
`host-shell-pilot-request`, a read-only materials request for the external
Hermes/OpenClaw host team. It lists the host-owned private adapter command
binary, request/response contract, 9-action matrix, distribution/signature/update
and drill evidence, release notes, required audit refs, and expected Runtime Kit
JSON artifacts without invoking commands, probing files, fetching refs, mutating
host state, submitting handoff, exposing phone `/mobile/v1`, or marking P3.4
complete.

Completed P3.4j slice: host-shell pilot evidence manifest. Runtime Kit now
exposes `host-shell-pilot-evidence-manifest`, a read-only evidence index for
local P3.4 pilot JSON artifacts. It hashes preflight, conformance, pilot
receipt, handoff, and artifact-review files, optionally includes request and
runbook JSON, emits a closed
`kaka.host_shell_pilot_evidence_manifest.v1` schema, and blocks archive-ready
when required artifacts are missing, oversized, schema-mismatched, or
`ok: false`. It does not invoke the private adapter command, rerun conformance,
fetch audit refs, submit handoff, create the external archive, expose phone
`/mobile/v1`, or mark P3.4 complete.

Planned P3.4 slice after P3.4j: first external host-shell dogfood/release pilot.
P3.4 should run the P3.3 package contract against an actual Hermes or OpenClaw
host-owned command binary outside this repository, pass preflight, collect conformance evidence,
record native distribution/signature/update/drill/release-note evidence refs,
emit a ready `host-shell-pilot-handoff` bundle, and document install/update
failure drills for ordinary users.

Current P3.4 execution state after the 2026-06-06 P3.4j multi-agent review:
Runtime Kit now has the full in-repository pilot support sequence
(`host-shell-pilot-request`, `host-shell-pilot-preflight`,
`host-shell-pilot-runbook`, `host-private-adapter-conformance`,
`host-shell-pilot-report`, `host-shell-pilot-handoff`,
`host-shell-pilot-artifact-review`, and
`host-shell-pilot-evidence-manifest`). The next P3.4 step should not be another
wrapper command such as a dossier or submission checklist, because those would
only restate existing request/runbook/review/evidence-manifest outputs. P3.4 is
now in external host execution state: Hermes/OpenClaw must provide a real
host-owned command binary or discovery source plus native distribution,
signature/update, drill, release-note, conformance, handoff, artifact-review,
and evidence-manifest outputs before Kaka can truthfully advance the release
pilot.

Current P3.4 preflight finding from the 2026-06-06 multi-agent check: this
machine has a real Hermes host shell (`/Applications/Hermes.app`,
`/Applications/Hermes Setup.app`, and `/Users/kartz/.local/bin/hermes`), but it
does not currently expose a Kaka private adapter command. No
`hermes-kaka-host-api` or `openclaw-kaka-host-api` command was found on `PATH`,
no well-known Hermes/OpenClaw Kaka private adapter path was present under
`~/Library/Application Support`, and no `HERMES_KAKA_HOST_API` or
`OPENCLAW_KAKA_HOST_API` environment variable was configured. P3.4a readiness
evidence collection is now implemented in Runtime Kit, while P3.4 completion
still requires a real host-owned binary from Hermes/OpenClaw.

Fresh P3.4 external-waiting audit from the current continuation: Runtime Kit
preflight still reports `kaka.host_shell_pilot_preflight.v1 hermes blocked
False False missing_private_adapter_command` for Hermes and
`kaka.host_shell_pilot_preflight.v1 openclaw blocked False False
missing_host_shell,missing_private_adapter_command` for OpenClaw. No
`artifacts/hermes` or `artifacts/openclaw` pilot JSON set is present, and the
static Hermes/OpenClaw manifests still do not configure
`host_private_adapter.command`. A read-only multi-agent audit also found no
`HERMES_KAKA_HOST_API`, `OPENCLAW_KAKA_HOST_API`, PATH command, or well-known
Application Support command. Therefore the next real P3.4 action remains
external: pick Hermes or OpenClaw as the first pilot host, provide a real
host-owned command binary or discovery source, then run the existing preflight,
conformance, receipt, handoff, artifact-review, and evidence-manifest sequence.

Product-direction correction for the next slice: the ordinary-user path must not
be "write an adapter command, export `HERMES_KAKA_HOST_API`, and paste Runtime
Kit commands." That is acceptable only for development and external pilot
evidence. The product path is an installable Host Extension: Hermes ships a
Hermes Plugin and OpenClaw ships an OpenClaw Skill or sidecar package. That
extension bundles or internally discovers the private adapter command, renders
Runtime Kit's `consumer_ui`, `process_ownership`, `private_adapter_package`, and
pairing contracts, and lets users enable Kaka Mobile Bridge, show QR, optionally
advertise Bonjour, run health checks, revoke iPhone tokens, update, uninstall,
and open logs from the host UI. The command binary remains host-owned, but it
must be an extension-internal implementation detail rather than a manual setup
step for ordinary users.

Completed P3.12 slice: Host Extension Starter Kit. Runtime Kit now exposes
`host-extension-starter-kit` with schema `kaka.host_extension_starter_kit.v1`
and optional safe materialization for a Hermes/OpenClaw starter package tree:
README, manifest, extension-internal adapter command README, runtime contract
command files, and release-gate metadata. The contract derives from the existing
`host-extension-preview`, `host-extension-readiness`, `settings-preview`,
`package-preview`, and `host-package-preview` surfaces. It does not install
packages, start the bridge, bind LAN, advertise Bonjour, create login items,
mint tokens, invoke private adapter commands, expose private host APIs to the
phone, or bundle proprietary Hermes/OpenClaw implementation code. The
agent-executable plan is
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-host-extension-starter-kit.md`.

Completed P3.5 slice: installable Host Extension packaging and pairing UX.
Runtime Kit now exposes `host-extension-preview` with schema
`kaka.host_extension_preview.v1`, static Hermes/OpenClaw manifest declarations,
and tests that distinguish ordinary-user installation from developer/pilot
fallback command discovery. P3.5 does not claim P3.4 release completion; stable
release still requires a real host-owned command binary, P3.2 conformance, P3.4
audit refs, handoff, artifact review, and evidence manifest.

Completed P3.6 slice: Host Extension distribution readiness. Runtime Kit now
exposes `host-extension-readiness` with schema
`kaka.host_extension_readiness.v1`, static Hermes/OpenClaw manifest
declarations, CLI support, tests, and P3.5 schema hardening. The contract
collects the real Hermes Plugin / OpenClaw Skill install command, update
channel, extension-internal adapter command location, host UI entry point,
signed package ref, signature/notarization ref, P3.2 conformance report ref,
and P3.4 evidence manifest ref into a read-only readiness report. It does not
install the package, invoke private commands, fetch evidence refs, start the
bridge, or mark P3.4 complete. The output answers whether the host package is
`blocked` or `ready_for_external_install_drill`, while keeping the ordinary-user
flow as "install the plugin/skill and scan QR."

Fresh P3.6 readiness audit from 2026-06-07: both
`host-extension-readiness --runtime hermes` and
`host-extension-readiness --runtime openclaw` currently return
`status: "blocked"` and `ready_for_external_install_drill: false`. Both reports
are missing the same eight host-owned inputs: `install_command`,
`update_channel`, `adapter_command_location`, `host_ui_entrypoint`,
`signed_package_ref`, `signature_ref`, `conformance_report_ref`, and
`evidence_manifest_ref`. This confirms that the next step is external material
collection and an install drill, not another repository-only Runtime Kit wrapper.

Next P3.7 entry condition: choose Hermes or OpenClaw as the first pilot host,
fill the material checklist in `docs/kaka-host-extension-external-materials.md`,
rerun `host-extension-readiness` with real values, and only then write the
agent-executable P3.7 Host Extension external install drill plan. Until that
happens, ordinary-user docs should continue to say "install the plugin/skill and
scan QR," while developer/pilot command paths remain fallback-only.

Completed P3.8 slice: local TLS certificate readiness. While P3.7 waits on
external host-owned materials, Runtime Kit now exposes `local-tls-readiness`
with schema `kaka.local_tls_readiness.v1`, CLI support, and tests. The contract
collects non-secret local TLS metadata for production pairing: certificate
label, certificate ref, public-key SHA-256 fingerprint, expiry timestamp, trust
store ref, and renewal procedure ref. It returns `blocked` until trust state is
`configured` and all refs are present, and returns
`ready_for_production_pairing` only for complete metadata. It does not generate
certificates, install trust, modify Keychain, read private keys, start the
bridge, bind LAN, advertise Bonjour, mint mobile tokens, fetch refs, or change
the phone `/mobile/v1` API. P3.10a/P3.10b now add real TLS serving and iOS
pinning while keeping certificate creation, trust installation, renewal, and
private key storage host-owned.

Completed P3.9 slice: retention policy controls. Runtime Kit now adds
runtime-side controls for `retention.input_assets_days`,
`retention.output_assets_days`, and `retention.task_history_days`, preserving the
current defaults of `7/30/30`. The configured values flow through
`settings-preview`, `package-preview`, `start --dry-run`, `build_server_command`,
the mock bridge server parser, capabilities, and
`GET /mobile/v1/runtime/settings`. P3.9 does not implement automatic asset/task
cleanup, background purge jobs, SQLite migrations, phone-side settings writes,
Swift UI changes, or any new private host API. The agent-executable plan is
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-retention-policy-controls.md`.
Because the repository currently has older dirty Swift/iOS and
`runtime_store.py` work in progress, reviewers should judge P3.9 against only
the Runtime Kit CLI, mock bridge, tests, and docs touched by the retention
control slice.

Completed P3.10a slice: Runtime Kit local HTTPS serving. The plan is
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-local-https-serving.md`.
Runtime Kit now adds runtime-side certificate-chain and private-key launch
inputs, validates them when `--trusted-local-tls` starts the bridge, wraps the
local Mobile Bridge server socket with `ssl.SSLContext`, and keeps
local-development HTTP unchanged when trusted TLS is absent. P3.10a does not
generate certificates, install trust, modify Keychain, expose private key paths
to iPhone, or touch Swift/iOS files.

Completed P3.10b slice: iOS trust/pinning integration. Runtime Kit and mock
bridge pairing payloads can carry non-secret `tls_public_key_sha256`; Swift
decodes and persists the pin, treats required-TLS payload mistakes as
certificate failures, and uses a pinned `URLSession` trust policy for HTTPS
pairing, restore, and saved-connection bridge clients without weakening the
development HTTP exception.

Completed P3.11 slice: ordinary-user native SwiftUI connection polish. Kaka now
ports the connection QA, pairing, saved-connection recovery, local network,
certificate, and host-owned recovery guidance into native SwiftUI without
turning the phone into a runtime settings owner.

The P3.11 agent plan is recorded at
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-native-connection-recovery-ui.md`.
The implemented boundary is that Kaka iPhone renders phone-safe guidance for
expired QR, already-used QR, revoked saved connections, bridge unavailable,
Bonjour/local network fallback, host-owned port conflict, disabled host action,
host extension unavailable, and TLS/certificate failure; it does not expose
Runtime Kit command chains, host adapter commands, private host APIs, log paths,
provider endpoints, SQLite paths, bearer-token fields, or certificate private-key
paths.

Completed P3.13 slice: Host Extension installable package handoff. Runtime Kit
now extends the P3.12 starter-kit direction into host-team package handoff
materials for Hermes Plugin and OpenClaw Skill/sidecar distribution. The plan is
`docs/superpowers/plans/2026-06-07-kaka-pocket-agents-host-extension-installable-package-handoff.md`.
P3.13 generates package handoff contracts and files for host UI, install-drill,
release-gate, and manifest packaging, but it does not sign,
publish, install, start, bind LAN, advertise Bonjour, mint tokens, implement
proprietary private APIs, or expose private host APIs to the iPhone.

The most recently executed detailed plan follows the `superpowers:writing-plans`
format and records the completed P3.42 Inbox Pending Item Review Details slice.
P3.42 renders existing pending Inbox item metadata as a local row-level details
expansion before visible `Send`; it does not fetch URLs, read payload bytes,
parse PDFs/OCR, submit, call Recall, add endpoints, add App Intents, delete
source files, or change Host Extension packaging.
P3.4j added `host-shell-pilot-evidence-manifest`, a closed evidence manifest
schema, static manifest entrypoints, a blocked manifest example, and tests
proving it hashes local JSON artifacts without invoking the private command,
rerunning conformance, fetching refs, submitting handoff, creating archives, or
marking P3.4 complete. P3.4i added `host-shell-pilot-request`, a closed materials request schema,
static manifest entrypoints, a host request example, and tests proving it
generates the host-team materials checklist without invoking the private
command, running preflight or conformance, reading artifacts, fetching refs,
mutating host state, submitting handoff, or marking P3.4 complete. P3.4h
added `host-shell-pilot-artifact-review`, a closed artifact review schema,
static manifest entrypoints, a blocked artifact review example, and tests
proving it reads generated JSON artifacts without invoking the private command,
rerunning conformance, fetching refs, mutating host state, submitting handoff,
or marking P3.4 complete. P3.4g
added `host-shell-pilot-runbook`, a closed runbook schema, static manifest
entrypoints, a blocked runbook example, and tests proving it generates host
operator steps, command artifacts, evidence requirements, and acceptance gates
without invoking the private command or running conformance. P3.4f
added `host-shell-pilot-preflight`, a closed preflight schema, static manifest
entrypoints, a blocked preflight example, and tests proving it checks local host
inputs without invoking the private command or running conformance. P3.4e added
`host-shell-pilot-handoff`, a closed handoff schema, static manifest entrypoints,
a blocked handoff example, and tests proving it wraps the existing receipt
without changing receipt readiness or marking P3.4 complete.
P3.4d added optional closed evidence-ref objects and CLI flags to
`host-shell-pilot-report`, updated safe examples/docs, and preserved the
unchanged verified boolean gate. P3.4c added the external host-team
implementation guide, schema-checked JSON examples, example validation tests,
and command path-with-spaces hardening for direct conformance. P3.4b aligned
`host-shell-pilot-report` with the P3.3 command discovery contract, tightened
receipt source schema validation, allowed optional manifest
`host_private_adapter.command`, updated docs, and preserved the phone-facing
Mobile Bridge `/mobile/v1` boundary without bundling host-owned Hermes/OpenClaw
private API implementations. P3.4a added `host-shell-pilot-report`, a closed
receipt schema, static manifest declarations, docs, tests, malformed-command
hardening, and final quality review.
Kaka now has foreground App Intents for opening Inbox and Tasks review surfaces,
Action Button-recommended shortcuts that reuse the same foreground handoff, an
App Group handoff into the main app tab router, a phone-safe runtime-task
activity projection with client-generated generic titles, ActivityKit coordinator
hooks from Task Inbox, plist/entitlement guards for Live Activity support without
Siri/APNs entitlement creep, a WidgetKit extension rendering the safe projection
on the Lock Screen and Dynamic Island, production-capable Runtime Kit pairing, a
derived `consumer_ui` renderer contract for ordinary-user Hermes/OpenClaw runtime
controls, a `process_ownership` runtime-side contract for
install/start-at-login/update/uninstall, explicit logs, health checks, and
port-conflict repair, a P2.8 `host-package-preview` JSON handoff contract for
host packaging/distribution adapters, and P2.9 `host-adapter-run` for
Mac/runtime-side host action execution.

P2.9 deliberately keeps the phone connection on Kaka Mobile Bridge `/mobile/v1`
and does not expose private host APIs to iPhone. `host-adapter-run` is a
Mac/runtime-side action result surface. Its `mock` adapter is for conformance and
local QA. P3.1 now narrows `private` mode to a command bridge: without
`--private-adapter-command` it returns structured unavailable, and with a command
it calls the host-owned adapter through stdin/stdout JSON. Mutating actions
require explicit approval, disabled actions do not invoke the private command,
and install does not auto-start the bridge or create a login item. Continuation
hardening tightened the action-result schema with adapter/state enums, bounded
`detail` and `error.message` fields, full forbidden phone-safe field coverage in
shell manifests, and closed host-private request/response schemas. P3.2 now
turns that contract into host-owned conformance evidence; P3.3 now turns
passing conformance into a concrete host-owned packaging/distribution
contract by extending `host-package-preview` rather than adding phone-side
private APIs.

Completed plan history is available for P3.4j host-shell pilot evidence manifest at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-manifest.md`,
P3.4i host-shell pilot request bundle at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-request-bundle.md`,
P3.4h host-shell pilot artifact review at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-artifact-review.md`,
P3.4g host-shell pilot runbook at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-runbook.md`,
P3.4f host-shell pilot preflight at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-preflight.md`,
P3.4e host-shell pilot handoff bundle at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-handoff-bundle.md`,
P3.4d host-shell pilot evidence refs at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-refs.md`,
P3.4c host private adapter authoring kit at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-private-adapter-authoring-kit.md`,
P3.4b host-shell command discovery at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-command-discovery.md`,
P3.4a external host-shell pilot readiness at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-external-host-shell-pilot-readiness.md`,
P3.3 real host packaging/distribution at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-real-host-packaging-distribution.md`,
P3.2 host-private adapter dogfood at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-private-adapter-dogfood.md`,
P3.1 host-private command bridge at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-private-host-adapter-apis.md`,
P3.0 ordinary-user connection QA at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-ordinary-user-connection-qa.md`,
P2.9 host adapter binding at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-adapter-binding.md`,
P2.8 consumer host packaging handoff at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-consumer-host-packaging-distribution.md`,
P2.7 runtime process ownership at
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-runtime-process-ownership.md`,
P2.6 Hermes/OpenClaw consumer runtime UI
at `docs/superpowers/plans/2026-06-06-kaka-pocket-agents-hermes-openclaw-consumer-runtime-ui.md`,
P2.5 production Runtime Kit pairing hardening at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-production-pairing-hardening.md`,
E.1c Action Button review handoff at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-action-button-review-handoff.md`,
E.1b WidgetKit Live Activity presentation at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-widgetkit-live-activity.md`,
E.1 App Intents/Live Activity-safe foundation at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-app-intents-live-activity.md`,
native Hermes/OpenClaw runtime packaging scaffold at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-native-runtime-packaging.md`,
C.1 Context Snapshot at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-context-snapshot-collectors.md`,
P2.4 runtime-side settings shell at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-runtime-side-settings-ui.md`,
provider-backed Recall retrieval at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-provider-backed-recall-retrieval.md`,
semantic Recall/runtime settings at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-semantic-recall-runtime-settings.md`,
Recall D.1 at `docs/superpowers/plans/2026-06-05-kaka-pocket-agents-post-e0.md`,
runtime persistence at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-runtime-persistence.md`,
and B.1 real push-to-talk voice at
`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-push-to-talk-voice.md` for
historical traceability. `docs/superpowers/` is treated as local planning
workspace, so this tracked document is the durable project-level roadmap.

## Skills And MCP For This Planning Pass

- `project-codebase-onboarding-and-roadmap`: code-first project analysis, doc drift detection, module/risk map after semantic Recall, runtime settings/status, and provider-backed retrieval landed.
- `superpowers:subagent-driven-development`: execution mode used for the E.1 system-surface foundation, E.1b WidgetKit slice, E.1c Action Button review handoff, production pairing hardening, P2.6 consumer runtime UI contract, P2.7 runtime process ownership contract, P2.8 host packaging handoff contract, P2.9 host adapter binding, P3.0 ordinary-user connection QA, P3.1 host-private command bridge, P3.2 host-private adapter conformance, P3.4b through P3.4j host-shell pilot execution slices, P3.5 Host Extension packaging/pairing UX, P3.6 Host Extension distribution readiness, P3.15 Host Plugin/Skill Devkit, P3.18 Host Codex developer plugin source, P3.19 Host Extension install experience acceptance, P3.20 Recall export artifact policy, P3.21 Recall retrieval packaging readiness, P3.22 asset retention timestamped purge, P3.23 Context Snapshot permission UX, P3.26 Recall retrieval material intake, P3.27 local renderer backend capability manifest, P3.29 Context Snapshot motion/calendar, P3.30 Voice-to-Inbox Draft, P3.32 Inbox Voice Instruction, P3.33 Inbox Instruction Polish, P3.34 Inbox Instruction Templates, P3.35 Host-Native Plugin/Skill Installation Blueprint, P3.36b Explicit Paste-to-Inbox Courier, P3.37 Inbox Result Review Provenance, P3.38 Explicit Files-to-Inbox Import, P3.39 Inbox Pending Item Discard, P3.40 Inbox Discard Confirmation, P3.41 Inbox Action Feedback Banner, and P3.42 Inbox Pending Item Review Details. The P3.30 planning pass used read-only subagents to compare Clipboard/Link Courier against Voice-to-Inbox and selected Voice-to-Inbox as the next executable product slice; P3.32 used a read-only source-provenance agent plus local TDD for ViewModel/UI/submitter integration; P3.33 used read-only multi-agent source review plus local TDD for presentation, ViewModel clear, and UI source-guard integration; P3.34 used read-only multi-agent boundary review plus local TDD for template presentation, ViewModel apply, and UI source-guard integration; P3.35 used read-only schema/write and docs-boundary agents around local TDD/schema verification; P3.36b used read-only code-boundary and docs-sync agents around local TDD/static guard verification; P3.37 used read-only roadmap/code-boundary agents around local TDD for completion context, result banner review copy, and Recall provenance handoff; P3.38 used read-only Swift-boundary and docs-boundary agents around local TDD for the importer helper, ViewModel path, UI file picker, PDF provenance, and static source guards; P3.39 used read-only Swift-boundary and docs-boundary agents around local TDD for the ViewModel discard path, visible row action, and static source guards; P3.40 used read-only Swift-boundary and docs-boundary agents around local TDD for the confirmation dialog, stale-item guard, and source guard hardening; P3.41 used read-only code/docs agents to choose between Review Details and Action Feedback, then local TDD for presentation mapping, stale progress cleanup, SwiftUI banner wiring, and static source guards; P3.42 used read-only Swift/UI and docs agents plus local TDD for pending item review presentation, row-level details wiring, and static source guards.
- `superpowers:executing-plans`: used to execute written plans step-by-step rather than inventing a parallel scope.
- `superpowers:test-driven-development`: App Intent metadata, Action Button catalog metadata, system-surface safety flags, Runtime Task Activity snapshots, Task Inbox activity sync decisions, Live Activity plist support, WidgetKit plist/project contracts, Dynamic Island short labels, entitlement allowlists, single-use pairing sessions, revoked-token auth, runtime security summaries, Swift production QR refresh fallback, `consumer_ui` sections/actions, `process_ownership` actions, `host-adapter-run`, private command bridge behavior, conformance report behavior, manifest/schema declarations, packaging examples, command path-with-spaces handling, host-shell pilot evidence refs, host-shell pilot handoff bundle behavior, host-shell pilot preflight behavior, host-shell pilot runbook behavior, host-shell pilot artifact review behavior, host-shell pilot request behavior, host-shell pilot evidence manifest behavior, Recall export artifact policy/schema behavior, Recall retrieval readiness behavior, Recall retrieval material intake behavior, runtime HTTP outbound provenance allowlisting, timestamp-aware asset retention purge behavior, Context Snapshot permission UX presentation behavior, Context Snapshot motion/calendar sampler behavior, Context Snapshot mock bridge allowlisting, Inbox voice instruction note updates, Inbox instruction clear behavior, Inbox instruction presentation copy, Inbox deterministic instruction templates, Inbox template note updates, UI source guards, and universal-intake `note`/`user_instruction` submission were added through failing tests first, then implementation.
- `superpowers:writing-plans`: used to create the completed P2.9 host adapter binding plan, the completed P3.0 ordinary-user connection QA plan, the completed P3.1 host-private command bridge implementation plan, the completed P3.2 host-private adapter dogfood/conformance plan, the completed P3.3 real host packaging/distribution integration plan, the completed P3.4a through P3.4j host-shell pilot plans, the completed P3.5 host extension packaging and pairing UX plan, the completed P3.6 host extension distribution readiness plan, the completed P3.11 native connection/recovery UI plan, the completed P3.13 Host Extension installable package handoff plan, the completed P3.15 Host Plugin/Skill Devkit plan, the completed P3.18 Host Codex developer plugin source plan, the completed P3.19 installation-experience acceptance plan, the completed P3.20 Recall export artifact policy plan, the completed P3.21 Recall retrieval packaging readiness plan, the completed P3.22 asset retention timestamped purge plan, the completed P3.23 Context Snapshot permission UX plan, the completed P3.26 Recall retrieval material intake plan, the completed P3.27 local renderer backend capability manifest plan, the completed P3.28 Host Extension material intake plan, the completed P3.29 Context Snapshot motion/calendar plan, the completed P3.30 Voice-to-Inbox Draft plan, the completed P3.32 Inbox Voice Instruction plan, the completed P3.33 Inbox Instruction Polish plan, the completed P3.34 Inbox Instruction Templates plan, the completed P3.35 Host-Native Plugin/Skill Installation Blueprint plan, the completed P3.36a Inbox Voice Capture Context Copy plan, the completed P3.36b Explicit Paste-to-Inbox Courier plan, the completed P3.37 Inbox Result Review Provenance plan, the completed P3.38 Explicit Files-to-Inbox Import plan, the completed P3.39 Inbox Pending Item Discard plan, the completed P3.40 Inbox Discard Confirmation plan, the completed P3.41 Inbox Action Feedback Banner plan, and the completed P3.42 Inbox Pending Item Review Details plan.
- `skill-creator`: used as the design guardrail for P3.15 so any future Kaka
  host-team skill stays concise, task-specific, and developer-facing instead of
  becoming a dumping ground for ordinary-user setup prose.
- `plugin-creator`: used as the design guardrail for P3.18 Host Codex developer
  plugin source. The generated source automates host-team packaging work only;
  it must not replace the actual Hermes/OpenClaw installable extension that
  ordinary users install.
- `build-ios-apps:ios-app-intents`: used to keep the App Intents surface small, foreground, and discoverable without turning Shortcuts/Siri into a background task controller.
- MCP use for this pass: tool discovery was used to confirm the multi-agent MCP surface for future execution. Multi-agent MCP split P3.2 across runtime conformance, schemas/manifests, and docs/roadmap workers, and P3.3 followed the same split pattern. For the P3.4 preflight update, one explorer agent mapped exact P3.4 requirements and in-repo readiness scope, while another explorer agent checked the local machine for real Hermes/OpenClaw shells, `HERMES_KAKA_HOST_API`, `OPENCLAW_KAKA_HOST_API`, `hermes-kaka-host-api`, and `openclaw-kaka-host-api`. P3.4b used `multi_agent_v1` explorers to confirm the remaining P3.4 blocker and identify the missing `host-shell-pilot-report` discovery path, plus a docs worker to update host-facing documentation. P3.4c used a `multi_agent_v1` explorer for request/response/example scope and a docs worker for the implementation guide. P3.4d used a `multi_agent_v1` explorer for optional evidence-ref shape/security boundaries and a docs worker for host-facing evidence-ref wording. P3.4e used a `multi_agent_v1` explorer for handoff bundle schema/CLI/test scope and a docs worker for host-facing handoff wording. P3.4f used a `multi_agent_v1` explorer for read-only preflight checks/schema/CLI/test scope and a docs worker for host-facing preflight wording. P3.4g used a `multi_agent_v1` explorer to choose a runbook shape over a narrower checklist and a docs worker for host-facing runbook wording. P3.4h used a `multi_agent_v1` explorer to confirm artifact review scope and a docs worker for host-facing artifact review wording. P3.4i used a `multi_agent_v1` explorer to confirm host-shell pilot request-bundle scope and a docs worker for host-facing request wording. P3.4j used a `multi_agent_v1` explorer to confirm evidence manifest contract scope and identify the `ok: false` artifact readiness risk before local TDD hardening. P3.5 used `multi_agent_v1` read-only review agents to verify ordinary-user install wording, `/mobile/v1` boundaries, schema/manifest consistency, and the P3.6 hardening scope that later landed here. P3.6 used `multi_agent_v1` read-only review agents to validate schema/manifest requirements and the final documentation synchronization checklist. P3.15 used `multi_agent_v1` read-only agents to audit plugin/skill devkit boundaries and a worker agent for static manifest/schema declarations. No new iOS target, plist, entitlement, App Intent, WidgetKit, SwiftUI, or UI smoke code was expected for this update.

## Current Implementation Truth

Kaka is no longer only an image-intake MVP. The working tree now contains:

- Swift Mobile Bridge support for generic asset uploads and universal intake.
- `KakaShareExtension` with App Group inbox capture for text, URL, image, and PDF payloads.
- App-side Inbox UI and submission logic.
- PDF upload from a visible main-app Inbox action.
- Real push-to-talk voice follow-up in the image conversation flow: explicit press-to-record, iOS Speech transcription, editable transcript, text submission, and short spoken reply.
- Permission-aware Context Snapshot contract and Inbox preview, defaulting off per task, refreshed after each task, and sent only when the runtime advertises support.
- Recall D.0 explicit actions: `remember`, `use_once`, and `forget` with Swift models, Mobile Bridge client methods, mock bridge endpoints, visible confirmation UI, and Inbox result entry point.
- Recall D.1 browse/search/export foundation plus semantic Recall search and P3.20 export artifact policy: queryable Recall list request, additive `POST /mobile/v1/recall/search`, policy-labeled `kaka.recall_export.v1` export response, retrieval-index deletion receipts, Recall browse ViewModel/View, semantic fallback behavior, and a connected Recall tab.
- Provider-backed Recall retrieval adapters and production packaging readiness: Runtime Kit has a `RecallSearchProvider` abstraction, deterministic local fallback, fixture/provider-backed mode, `runtime_http` development adapter behind the existing search endpoint, outbound provider provenance allowlisting, and P3.21 `recall-retrieval-readiness` for production packaging refs.
- Runtime-side Hermes/OpenClaw settings, packaging, and first-run QA shell: Runtime Kit now has `settings-preview`, `package-preview`, `host-package-preview`, `host-adapter-run`, `connection-qa-preview`, `runtime_side_ui.consumer_ui`, `runtime_side_ui.process_ownership`, and `host-package-preview.private_adapter_package` JSON contracts, static Hermes/OpenClaw manifests, shared packaging schemas, bridge enablement, LAN/Bonjour controls, local store path selection, Recall retrieval provider selection, start command, stop action, development and production QR controls, revocation action metadata, trusted local TLS status, ordinary-user sections/actions/warnings, install/start-at-login/update/uninstall/log/health/repair/supervision action metadata, P2.8 host package handoff metadata, P2.9 mock/private adapter result behavior, P3.0 first-run steps and recovery fixtures, P3.3 host-owned command package metadata, P3.4a pilot receipts, P3.4b command discovery, P3.4c host private adapter authoring docs/examples, P3.4d host-shell pilot evidence refs, P3.4e host-shell pilot handoff bundles, P3.4f read-only preflight reports, P3.4g host-shell pilot runbooks, P3.4h host-shell pilot artifact reviews, P3.4i host-shell pilot request bundles, P3.4j host-shell pilot evidence manifests, hardened host adapter result schemas, and strict phone-safe summary.
- Runtime settings/status: `GET /mobile/v1/runtime/settings` reports runtime-owned local store and semantic Recall availability without letting the phone own persistence settings.
- Runtime Task Inbox E.0: Swift task models, connected Tasks tab, and mock bridge list/cancel/approval endpoints.
- E.1 system surfaces: foreground App Intents open Kaka to Inbox or Tasks review surfaces through an App Group handoff, E.1c Action Button-recommended shortcuts reuse that same foreground review handoff, Task Inbox feeds a Live Activity-safe runtime-task projection, and E.1b renders that projection through WidgetKit on the Lock Screen and Dynamic Island.
- Deterministic tests for Swift models/ViewModels, mock bridge behavior, plist/entitlements, and iOS UI smoke.

Still not implemented:

- Non-Live-Activity widgets.
- Bundled Hermes/OpenClaw proprietary private API implementations and real host-owned command binary distribution. P3.1 provides the host-private command bridge contract; P3.2 validates host-owned commands through runtime-side conformance; P3.3 adds the Runtime Kit package contract for host-owned command binary discovery, distribution channels, signature policy, and conformance gating outside this repository. P3.4 still needs an actual Hermes/OpenClaw host shell to dogfood and release a real binary through its native channel.
- A real external `hermes-kaka-host-api` or `openclaw-kaka-host-api` private adapter command. The 2026-06-06 preflight found a local Hermes app/CLI shell, but no Kaka private adapter command, no well-known adapter path, and no `HERMES_KAKA_HOST_API` or `OPENCLAW_KAKA_HOST_API` environment variable. P3.4a-P3.4j now add readiness receipts, command discovery, authoring docs/examples, optional evidence refs, a handoff bundle, read-only preflight report, runbook, artifact review, materials request bundle, and evidence manifest; they must not be treated as P3.4 release completion.
- A real external Hermes Plugin / OpenClaw Skill product package distributed through the host's native channel. P3.5 now defines the Runtime Kit contract that hides adapter command setup from ordinary users; the actual signed host extension package remains host-owned.
- Worktree cleanup/release isolation. The 2026-06-07 P3.9 review found
  pre-existing Swift/iOS and Runtime Kit SQLite store changes in the working
  tree. They need a separate acceptance pass before any combined branch can be
  considered release-clean.

## Runtime Persistence Slice Status

The runtime persistence execution slice is implemented in the current working tree.

Implemented behavior:

- Runtime Kit owns a local SQLite store on the Mac/runtime side.
- `--runtime-store-path` is a `kaka_mobile_runtime_kit start` and bridge-server option, not a Mobile Bridge request field.
- Recall records, retrieval-index deletion receipts, runtime task records, and task events can survive bridge/server recreation when the store path is provided.
- Recall export stays JSON-first, is labeled as `kaka.recall_export.v1`, and includes only the Recall metadata, summaries, timestamps, and provenance currently retained by the runtime.
- Deletion receipts report the content records and retrieval-index records removed by the runtime.
- The iPhone continues to store only the endpoint/token, local Inbox payloads, and user-visible UI state. It does not store provider keys, production Recall data, production task history, or the runtime SQLite path.

## Module Map

| Area | Key paths | Responsibility | Current risk |
| --- | --- | --- | --- |
| Swift Core | `Sources/AgentPocketCore` | Mobile Bridge models, uploads, universal intake, Recall, runtime task models | API drift if mock/runtime contracts diverge from Swift request builders |
| SwiftUI | `Sources/AgentPocketUI` | Capture, Inbox, voice skeleton, Context Snapshot preview, Recall actions, Task Inbox, foreground App Intent handoff, ActivityKit-safe task projection | Tab growth and action surfaces can become hard to scan without a navigation hierarchy |
| iOS targets | `ios/AgentPocket.xcodeproj`, `ios/AgentPocket`, `ios/KakaShareExtension`, `ios/AgentPocketTaskActivityWidget` | App target, Share Extension, WidgetKit Live Activity extension, entitlements, App Intents package bridge, UI smoke tests | More system surfaces can increase target wiring and provisioning drift |
| Runtime/mock | `mock_bridge`, `runtime-kit` | Deterministic Mobile Bridge behavior, local runtime launcher, SQLite runtime store, semantic Recall search, provider-backed retrieval adapter, Recall retrieval packaging readiness, runtime settings/status, production pairing lifecycle, token revocation, trusted local TLS metadata, native packaging shell manifests, derived consumer UI renderer contract, runtime-side process ownership contract, P2.8 host-package handoff contract, P2.9 `host-adapter-run` action result surface, P3.0 `connection-qa-preview` first-run QA report, P3.1 host-private command bridge contract, P3.2 host-private adapter conformance report, P3.3 `private_adapter_package` metadata, P3.4a `host-shell-pilot-report` receipt, P3.4b command discovery, P3.4c authoring docs/examples, P3.4d optional pilot evidence refs, P3.4e `host-shell-pilot-handoff` bundle, P3.4f `host-shell-pilot-preflight` report, P3.4g `host-shell-pilot-runbook` artifact, P3.4h `host-shell-pilot-artifact-review` artifact, P3.4i `host-shell-pilot-request` artifact, and P3.4j `host-shell-pilot-evidence-manifest` artifact | Proprietary Hermes/OpenClaw command implementations, retrieval provider packaging, and binary distribution remain host-owned |
| Docs | `docs/mobile-bridge-api.md`, `docs/pocket-agents-direction.md`, `docs/agent-pocket-privacy.md` | API contract, product direction, privacy boundary | README and roadmap language can lag behind implemented slices |
| Tests | `Tests`, `mock_bridge/tests`, `ios/tests`, `ios/AgentPocketPickerUITests` | Swift, Python, plist, and iOS UI smoke validation | System UI tests should avoid simulator content assumptions |

## Recommended Next Roadmap

| Priority | Phase | Theme | Why now | Exit criteria |
| --- | --- | --- | --- | --- |
| Completed | P1.1 | Default durable Recall store | D.1 exposes user-facing Recall browse/search/delete/export. | Runtime Kit provides a SQLite-backed local store for Recall content, retrieval-index receipts, and JSON export. |
| Completed | P1.2 | Bridge integration for persistent Recall | The iPhone already speaks the D.1 contract. | `mock_bridge` can run with `--runtime-store-path`; remember/list/search/export/delete survive process restart and return deletion receipts. |
| Completed | P1.3 | Durable task state and events | Runtime Task Inbox E.0 is visible in app. | Task list, approval state, cancellation, completion, and event history survive bridge restart. |
| Completed | P1.4 | Contract/Docs persistence boundary | Runtime adapters need one documented storage boundary before Hermes/OpenClaw packaging. | API docs, privacy docs, runtime-kit README, and tests agree on store ownership, retention, export, and deletion behavior. |
| Completed | B.1 | Real push-to-talk voice | The transcript skeleton proved UI shape; B.1 makes voice usable without changing the Mobile Bridge audio boundary. | User can record only after an explicit press, review/edit the iOS Speech transcript, submit text through Mobile Bridge, and hear a short reply without hidden listening or raw audio upload. |
| Completed | P2.1 | Semantic Recall retrieval | D.1 search is queryable but still summary/keyword-shaped. Runtime-side semantic search improves memory usefulness without changing phone ownership. | `POST /mobile/v1/recall/search` returns ranked Recall items with match reasons; embeddings/index internals stay runtime-owned and deletion receipts still remove index records. |
| Completed | P2.2 | Runtime store settings/status | `--runtime-store-path` works for developers, but clients need a visible runtime-side persistence state. | Runtime Kit and bridge expose a non-secret settings/status response showing whether local Recall/task store and semantic Recall are enabled; iPhone never receives provider keys or owns the SQLite path. |
| Completed | P2.3 | Provider-backed retrieval adapters | The semantic contract is stable with deterministic local scoring; runtime owners can now plug in richer retrieval behind the same boundary. | Runtime Kit can rank Recall records through local fallback, fixture/provider-backed mode, or `runtime_http` without exposing raw embeddings/index rows, provider endpoints, keys, or SQLite paths to iPhone; delete receipts still remove runtime-owned index records. |
| Completed | P2.4 | Runtime-side persistence settings shell | `--runtime-store-path` and `/runtime/settings` existed, but runtime UI/plugin authors needed a stable contract. | Runtime Kit `settings-preview` exposes bridge enablement, path picker, QR/Bonjour, Recall provider selection, and start/stop actions for Hermes/OpenClaw shells while keeping phone settings read-only and non-secret. |
| Completed | C.1 | Permission-aware Context Snapshot status collectors | Current context was intentionally minimal. Conservative battery/network/motion/location/calendar sentinels improve task context without passive surveillance. | Snapshot preview shows task-scoped fields; stale previews are cleared between tasks; denied/unavailable permissions do not block intake; no snapshot persists without Recall confirmation. |
| Completed | C.1b | Context Snapshot network path | C.1 had a `network` field but the system collector only returned an unavailable sentinel. A one-shot coarse path status gives the runtime useful task context without adding surveillance or permissions. | `Network.framework` is sampled through a short-lived injectable path sampler and returns only `wifi`, `cellular`, `offline`, `constrained`, `unknown`, or `unavailable`; no SSID, BSSID, carrier, IP address, hostname, interface name, continuous monitor, new phone API, motion probe, calendar busy-window query, or automatic Recall write is added. |
| Completed | Runtime Kit | Native runtime packaging scaffold | Users should not run manual bridge commands forever. | Runtime Kit `package-preview`, Hermes/OpenClaw static manifests, shared schemas, no-autostart defaults, LAN/Bonjour opt-ins, local/private Recall endpoint guard, and phone-safe summary allowlist are implemented. |
| Completed | E.1 | App Intents and Live Activity-safe task-state foundation | System surfaces should come after in-app task state and approval semantics are stable. | Foreground App Intents open safe Inbox/Tasks review surfaces; long-running tasks can be projected to ActivityKit-safe snapshots with generic titles and without exposing secrets. |
| Completed | E.1b | WidgetKit Live Activity presentation | The ActivityKit-safe attributes and coordinator existed; the lock screen/Dynamic Island rendering target was missing. | A WidgetKit extension renders task title, phase, and approval-needed state and is embedded in the app target. |
| Completed | E.1c | Action Button review handoff | The App Intent handoff pattern is safe and tested; Action Button reuses it without adding background task control. | Action Button-reachable shortcuts open Kaka to visible Inbox/Tasks review surfaces and do not submit, approve, cancel, remember, collect context, or change runtime settings in the background. |
| Completed | P2.5 | Production runtime pairing hardening | The scaffold had development-only `pair_dev`, long-lived QR payloads, fixed development tokens, and no trusted local TLS metadata boundary. | Runtime Kit and mock bridge support short-lived single-use QR payloads, revocable mobile tokens, trusted local TLS metadata, runtime-side controls, and Swift pairing refresh fallback while preserving development compatibility. |
| Completed | P2.6 | Hermes/OpenClaw consumer runtime UI contract | Pairing/token/TLS contracts were hardened; plugin shells needed a safer ordinary-user renderer contract. | Runtime Kit exposes `runtime_side_ui.consumer_ui` from `settings-preview` and `package-preview`, static manifests declare required sections/actions, and docs set up process ownership as the next contract slice. |
| Completed | P2.7 | Runtime process ownership | The renderer contract existed, but the runtime host needed an explicit process lifecycle contract rather than asking users to manage commands. | Runtime Kit exposes `runtime_side_ui.process_ownership` from `settings-preview` and `package-preview` for install/start-at-login/update/uninstall/logs/health/port-conflict repair without auto-starting, creating login items, implementing host APIs, or moving settings to iPhone. |
| Completed | P2.8 | Consumer-ready host packaging handoff | The runtime-side contracts existed; host adapters needed one stable package handoff surface before binding private APIs. | Runtime Kit exposes `host-package-preview`, host package schema/static manifest declarations, safe command artifacts, distribution metadata, disabled install defaults, and host-owned action metadata without mutating host state or requiring private Hermes/OpenClaw APIs. |
| Completed | P2.9 | Hermes/OpenClaw host adapter binding | P2.8 defines the handoff; host shells need a testable action execution surface before the host-private command bridge lands. | Runtime Kit exposes `host-adapter-run` as a Mac/runtime-side action surface; `mock` is conformance/local QA, unconfigured `private` returns unavailable, mutating actions require explicit approval, install does not auto-start or create login items, the action-result schema is hardened, and the phone still connects only through Mobile Bridge `/mobile/v1`. |
| Completed | P3.0 | Ordinary-user connection QA and host adapter readiness | P2.9 provided the binding surface; P3.0 verified the real first-run user journey before wiring unknown private APIs. | `connection-qa-preview` and the checklist prove a normal user can install or enable the safe scaffold, explicitly start Kaka Mobile Bridge, pair iPhone by production QR or Bonjour/LAN, run health checks, verify saved-token reconnect, revoke tokens, reconnect with a new QR, and recover from expected failures without changing the phone API or requiring private Hermes/OpenClaw APIs. |
| Completed | P3.1 | Host-private command bridge contract | P3.0 produced the user journey and API readiness evidence; Runtime Kit needed the safe adapter contract behind the existing `host-adapter-run --adapter private` surface. | Private mode accepts `--private-adapter-command`, invokes it with `shell=False`, exchanges stdin/stdout JSON, returns structured safe failures for missing/failed/invalid/timeout commands, blocks disabled/unapproved actions before command execution, preserves approval gates/no-autostart defaults/schema validation, and keeps the iPhone isolated to `/mobile/v1`. Proprietary Hermes/OpenClaw APIs plug in behind the host command and are not bundled here. |
| Completed | P3.2 | Host-owned adapter dogfood and conformance | P3.1 created the contract; the next risk was whether real Hermes/OpenClaw host shells can supply a command that satisfies it across the full lifecycle matrix without moving ownership into Kaka. | Runtime Kit `host-private-adapter-conformance` validates a host-owned command through P3.1 private adapter behavior for install/login item/update/uninstall/logs/health/port repair/supervision, keeps distribution host-owned, preserves first-run QA and no-autostart safety, and leaves iPhone traffic on `/mobile/v1` only. |
| Completed | P3.3 | Real host packaging/distribution integration | P3.2 proves command behavior; the remaining user risk is turning command evidence into host-owned binary discovery, distribution, update, signature, and release gating. | Runtime Kit extends `host-package-preview` with `private_adapter_package` metadata, schemas, static manifests, docs, and tests for host-owned command naming, discovery sources, distribution/update policy, signature policy, and required conformance evidence while keeping iPhone traffic on `/mobile/v1`. |
| Completed | P3.4a | External host-shell pilot readiness receipt | The current machine has Hermes installed but no host-owned Kaka private adapter binary; Kaka needed evidence collection before the external pilot. | Runtime Kit emits a closed host-shell pilot receipt, validates real vs synthetic commands, records native distribution/signature/update/drill/release-note evidence, hardens malformed command handling, and refuses to mark P3.4 complete without a real external binary. |
| Completed | P3.4b | Host-shell pilot command discovery | P3.4a could record pilot readiness, but still required every command path to be passed manually despite P3.3 declaring env/manifest/well-known discovery sources. | `host-shell-pilot-report` resolves the host-owned command from explicit argument/config, runtime env var, manifest `host_private_adapter.command`, or well-known path, records the source in the closed receipt schema, does not search `$PATH`, and keeps missing discovery as `not_ready`. |
| Completed | P3.4c | Host private adapter authoring kit | External host teams needed one concrete implementation guide and schema-valid examples before writing the real binary. | Runtime Kit packaging includes a private adapter implementation guide, schema-checked request/response/receipt examples, an invalid extra-field response example, and direct conformance support for executable command paths containing spaces. |
| Completed | P3.4d | Host-shell pilot evidence refs | Host teams need to provide concrete audit pointers for distribution/signature/update/drill/release materials without letting those pointers bypass readiness checks. | `host-shell-pilot-report` accepts optional closed `distribution.evidence.*` and `drills.evidence.*` refs, records them in the receipt, rejects unexpected evidence keys, keeps verified booleans unchanged, does not fetch external refs, and does not expose refs to phone `/mobile/v1`. |
| Completed | P3.4e | Host-shell pilot handoff bundle | After refs existed, the external pilot still needed one submit-ready bundle that clearly separates receipt readiness from final P3.4 completion. | `host-shell-pilot-handoff` wraps the pilot receipt with deliverables, audit-ref completeness, schema/manifest declarations, and a blocked example; it returns `ready_to_submit` only when receipt readiness and all refs are present, while keeping `p3_4_complete: false` and final completion owned by the external host shell. |
| Completed | P3.4f | Host-shell pilot preflight | Before a host team runs conformance/handoff, it needs a deterministic read-only report of the local host shell and private command discovery inputs. | `host-shell-pilot-preflight` checks host shell app/CLI, explicit/env/manifest/well-known command sources, and informational `$PATH` discovery without invoking the private command, running conformance, fetching refs, mutating host state, or marking P3.4 complete. |
| Completed | P3.4g | Host-shell pilot runbook | After preflight/handoff existed, external host teams still needed one operator artifact that sequences the real pilot without running it. | `host-shell-pilot-runbook` emits a read-only brief, pilot target, preflight summary, ordered steps, command artifacts, evidence requirements, and acceptance gates while not invoking the private command, running conformance, fetching refs, mutating host state, or marking P3.4 complete. |
| Completed | P3.4h | Host-shell pilot artifact review | After a host team runs the sequence, Runtime Kit needs a read-only way to review generated artifacts without rerunning host commands. | `host-shell-pilot-artifact-review` loads preflight, conformance, receipt, and handoff JSON files, checks schema identity and cross-artifact consistency, can report `ready_for_external_review`, and still keeps `p3_4_complete: false`. |
| Completed | P3.4i | Host-shell pilot request bundle | After artifact review was available, the external team still needed one machine-readable answer to what materials they must provide before running the pilot. | `host-shell-pilot-request` emits a read-only materials request with command binary expectations, action matrix, audit refs, and expected Runtime Kit JSON artifacts while not invoking commands, probing files, fetching refs, mutating host state, or marking P3.4 complete. |
| Completed | P3.4j | Host-shell pilot evidence manifest | Once the external team provides JSON artifacts, Kaka needs one archival index without creating or owning the archive. | `host-shell-pilot-evidence-manifest` hashes local preflight/conformance/receipt/handoff/artifact-review JSON, optionally includes request/runbook JSON, blocks bad or missing artifacts, declares static Hermes/OpenClaw entrypoints, and still keeps `p3_4_complete: false`. |
| External waiting | P3.4 | External host-shell dogfood/release pilot | P3.3-P3.4j define and validate the in-repo Runtime Kit contract; the remaining proof requires a real Hermes/OpenClaw host-owned command binary and evidence outside this repo. | One host-owned Hermes or OpenClaw command binary is distributed through its native channel, passes `host-private-adapter-conformance`, supports install/update/failure drills, produces user-facing release notes, and yields ready handoff, artifact review, and evidence manifest outputs without moving binary ownership into Kaka. |
| Completed | P3.5 | Installable Host Extension and pairing UX | The remaining product risk was user experience: ordinary users should install a Hermes Plugin or OpenClaw Skill, not write adapter code or set environment variables. | Runtime Kit exposes `host-extension-preview`; Hermes/OpenClaw manifests declare host extension metadata and entrypoints; docs and tests prove plugin/skill install is disabled-by-default, adapter commands are extension-internal, dev command/env discovery is fallback only, pairing is QR/Bonjour from the host UI, and the iPhone still talks only to `/mobile/v1`. |
| Completed | P3.6 | Host Extension distribution readiness | P3.5 defines the installable shape, but host teams still need a machine-readable way to prove the real Plugin/Skill package is ready for an external install drill without asking ordinary users to configure commands. | Runtime Kit exposes `host-extension-readiness`, schema, manifests, tests, and docs that collect install command, update channel, extension-internal adapter command location, host UI entry point, signed package ref, signature/notarization ref, P3.2 conformance report ref, and P3.4 evidence manifest ref; it stays read-only, keeps manual/env fallback developer-only, hardens P3.5 schema drift risks, and keeps the iPhone on `/mobile/v1`. |
| External waiting | P3.7 | Host Extension external material intake and install drill | P3.6 can prove readiness only after real Hermes/OpenClaw package facts exist. The 2026-06-07 audit shows both runtimes are blocked on the same eight missing host-owned inputs. | One runtime is chosen, `docs/kaka-host-extension-external-materials.md` is filled with real Plugin/Skill install/update/signature/UI/conformance/evidence refs, `host-extension-readiness` returns `ready_for_external_install_drill`, and an external install drill verifies install, explicit enable, QR/Bonjour pairing, health, revoke/re-pair, update, failure recovery, logs, uninstall, and artifact archive readiness without exposing private host APIs to iPhone. |
| Completed | P3.8 | Local TLS certificate readiness | P3.7 is externally blocked, but production pairing still needs a non-secret local TLS readiness gate before ordinary-user LAN/QR flows. | Runtime Kit exposes `local-tls-readiness`, schema, CLI, and tests for certificate label/ref, public-key fingerprint, expiry, trust store ref, and renewal procedure ref; it reports `blocked` or `ready_for_production_pairing` while not generating certificates, modifying Keychain, reading private keys, starting the bridge, binding LAN, advertising Bonjour, minting tokens, or changing `/mobile/v1`. |
| Completed | P3.9 | Runtime-side retention policy controls | Retention was already advertised to the phone, but defaults were hard-coded and host shells could not configure them as ordinary-user runtime settings. | Runtime Kit controls and CLI flags configure input asset, output asset, and task-history retention days; non-default values propagate into mock bridge capabilities and phone-safe runtime settings; phone settings remain read-only; no automatic deletion or cleanup enforcement is added. |
| Completed | P3.10a | Runtime Kit local HTTPS serving | P3.8 can report metadata readiness, but production LAN/QR pairing still needs the bridge to actually serve HTTPS. | Runtime Kit accepts host-owned certificate-chain/private-key launch inputs, validates them for trusted TLS serving, wraps the local bridge socket with `ssl.SSLContext`, keeps HTTP development mode, and does not expose private paths to iPhone. |
| Completed | P3.10b | iOS trust and pinning integration | After the bridge can serve HTTPS, the phone needs production trust behavior rather than relying on metadata labels. | Runtime Kit/mock bridge pairing can carry `tls_public_key_sha256`; Swift decodes, persists, and applies HTTPS public-key pinning through a `URLSession` trust policy for pairing, restore, and saved-connection bridge clients without generating certificates in Kaka, exposing private keys, or removing the local-development HTTP exception. |
| Completed | P3.11 | Native SwiftUI connection and recovery polish | Runtime Kit now has many readiness contracts; ordinary users need a calm first-run connection surface that reflects those states without manual command copy/paste. | Native SwiftUI renders expired QR, already-used QR, revoked saved connection, offline bridge, Bonjour/local network, TLS/certificate, and host-owned recovery guidance using existing phone-safe contracts, keeps host extension recovery Mac-owned, and does not move runtime settings ownership into iPhone. |
| Completed | P3.12 | Host Extension Starter Kit | P3.5/P3.6 define the plugin/skill shape, but external materials are still blocked and ordinary users must not be asked to hand-write adapter setup. | Runtime Kit adds `host-extension-starter-kit` with schema and optional safe materialization for Hermes Plugin / OpenClaw Skill starter packages: README, manifest, extension-internal adapter command README, runtime contract command files, and release-gate metadata, without installing packages, starting listeners, invoking private adapters, or exposing private host APIs to iPhone. |
| Completed | P3.13 | Host Extension installable package handoff | P3.12 can generate a safe starter tree, but host teams still need a package handoff that looks like an installable Hermes Plugin / OpenClaw Skill rather than a developer scaffold. | Runtime Kit exposes `host-extension-install-package` with schema and optional safe materialization for plugin/skill manifest files, host UI contract files, install-drill runbook, release-gate commands, and extension-internal adapter README while keeping signing, update channels, conformance evidence, proprietary host APIs, and final distribution host-owned. |
| Completed | P3.14 | Runtime retention enforcement and purge receipts | P3.9 made retention configurable, but it intentionally did not delete anything or emit purge receipts. | Runtime Kit exposes explicit `retention-purge --dry-run` and `--apply` behavior, a closed `kaka.runtime_retention_purge_receipt.v1` schema, idempotent terminal task-history cleanup, active task preservation, and tests proving no automatic cleanup, phone-side settings writes, Mobile Bridge purge endpoint, Recall purge, secret/path leakage, or Swift UI change. P3.22 extends this receipt boundary to timestamped mock bridge input/output assets. |
| Completed | P3.15 | Host Plugin/Skill Developer Kit | P3.13 produces package-shaped handoff materials, but host teams still need a repeatable developer kit that does not turn ordinary users into adapter authors. | Runtime Kit exposes `host-plugin-skill-devkit`, a template-only host-team materials bundle with contract index, command files, acceptance gates, ordinary-user boundary metadata, adapter templates, Codex automation templates, static manifest declarations, and closed schema validation. It does not create a third install package, real Codex plugin, marketplace entry, real host `SKILL.md`, bin adapter stub, or ordinary-user install surface; phone traffic stays on `/mobile/v1`. |
| Completed | P3.16 | Local renderer backend readiness | P3.7 remains externally blocked and the existing local `recipe_local` renderer needed a host-shell proof that it can render in the current checkout before adding more backends. | Runtime Kit exposes `local-renderer-backend-readiness`, schema, CLI, and tests. The report runs a temporary synthetic `recipe_local` render probe and emits `kaka.local_renderer_backend_readiness.v1` / `ready_for_local_recipe_flow` without adding phone APIs, cloud image provider calls, persistent asset storage, bridge startup, LAN binding, Bonjour, credential inspection, or new renderer dependencies. Future Core Image, ImageMagick, OpenCV, or libvips backends can plug in behind this readiness boundary. |
| Completed | P3.17 | Photo edit capability truth | P3.16 proved the current local renderer returns two variants, but some docs and capability fixtures still implied three. | The default `recipe_local` capability advertises `photo_edit.return_variants_max: 2`, matching `variant_clean_pro` and `variant_social_pop`. This keeps variant-count truth separate from generic `/mobile/v1/assets`, vision, image intake, universal intake, cloud providers, and renderer backend expansion. |
| Completed | P3.17b | Photo edit MIME truth | P3.17 left MIME broad to avoid mixing upload boundaries, but the default local photo-edit path is JPEG-normalized and should not imply direct HEIC/PNG renderer proof. | The default `recipe_local` capability advertises `photo_edit.accepted_mime_types: ["image/jpeg"]` while `vision`, `image_intake`, generic asset upload, and universal intake remain broad. This is a capability truth fix only, not an upload pipeline, renderer, cloud provider, asset retention, or phone API change. |
| Completed | P3.18 | Host Codex developer plugin source | P3.15 produced template-only Codex automation materials, but host engineers should not have to manually assemble a Codex plugin source tree when validating Hermes/OpenClaw packaging work. | Runtime Kit exposes `host-codex-developer-plugin-source` with preview/write behavior, a closed schema, static manifest declarations, CLI tests, and docs. Optional materialization writes runtime-specific source trees only under an explicit output directory and proves no Codex install, no marketplace update, no user-home writes, no host package install, no bridge startup, no private adapter invocation, no conformance run, no ordinary-user install surface, and no phone API change. |
| Completed | P3.19 | Host Extension install experience acceptance | P3.13 produced package-shaped handoff artifacts, but the host UI, install drill, and release gates still needed acceptance-grade detail so future work would not drift back to manual adapter setup or ordinary-user Codex automation. | `host-extension-install-package` now emits host UI acceptance metadata, `host-ui/acceptance.json`, ordered install-drill steps, evidence receipt refs, TLS/readiness/evidence/Codex developer source release gates, and static manifest/schema drift protection without adding a new CLI, installing packages, starting the bridge, invoking private adapters, or changing `/mobile/v1`. |
| Completed | P3.20 | Recall export artifact policy | After P3.19, host install work remains externally blocked, so the next repo-owned product slice should strengthen user data boundaries. Recall export already existed, but it needed a machine-verifiable policy so future retrieval work cannot turn export into a runtime database dump. | `GET /mobile/v1/recall/export` keeps the same path and source-compatible Swift shape while adding `schema_version: kaka.recall_export.v1` and an `artifact_policy`; Runtime Kit now uses a shared export sanitizer plus `recall-export.schema.json` to allow only item ID, summary, created timestamp, and provenance in exported item data while excluding embeddings, retrieval-index rows, provider endpoints/keys, bearer/mobile tokens, SQLite paths, hidden prompts, raw provider responses, unrelated task logs, and unconfirmed Context Snapshot content. |
| Completed | P3.21 | Recall retrieval packaging readiness | Provider-backed Recall retrieval exists as a development boundary, but production packaging still needs a host-owned proof contract before choosing Hermes/OpenClaw-native embeddings, a sidecar adapter, or a capability-negotiated hybrid. | Runtime Kit exposes `recall-retrieval-readiness` with `kaka.recall_retrieval_readiness.v1`, strategy enum, required non-secret refs for adapter package/runtime UI/signature/conformance/privacy/fallback/release notes, safety consts, and CLI/schema tests. It stays read-only, does not invoke providers or fetch refs, keeps `/mobile/v1/recall/search` unchanged, keeps provider endpoints/keys off iPhone, and additionally allowlists outbound runtime HTTP provenance to source task, source inbox item, and source surface only. |
| Completed | P3.22 | Asset retention timestamped purge | P3.14 deliberately left mock assets untracked before P3.22 because creation metadata was absent, so retention receipts could not yet prove input/output asset deletion. | Mock bridge uploaded assets and photo-edit result assets now carry in-memory `role` and `created_at`; Runtime Kit `retention-purge` classifies timestamped input/output assets into eligible/deleted receipt groups and deletes them only on explicit apply. Untimestamped assets remain untracked; P3.22 itself did not add automatic cleanup, Mobile Bridge purge endpoint, phone settings write, Swift UI, SQLite asset table, Recall purge, or raw asset bytes in receipts. |
| Completed | P3.23 | Context Snapshot permission UX | Permission-aware Context Snapshot existed, but the Inbox preview still exposed raw sentinel values and could let a user-enabled context collection be skipped silently while still in flight. | `ContextSnapshotViewModel` now exposes readable preview rows plus `isContextSnapshotPreparing`; `ContextSnapshotPreviewView` renders those rows and a preparing state; `InboxView` disables Send only while user-enabled context is still collecting. Raw payload values and runtime gating remain unchanged; no permission prompt, background collection, Mobile Bridge field, runtime API, Recall write, provider call, entitlement, or storage change is added. |
| Completed | P3.29 | Context Snapshot motion/calendar | C.1b and P3.23 left current motion and calendar busy-window values deferred behind a separate permission boundary. | `SystemContextSnapshotFieldCollector` now uses injectable one-shot motion and calendar samplers. Motion returns only `stationary`, `walking`, `running`, `driving`, `unknown`, or permission/unavailable sentinels; calendar returns only next-30-minute `free`, `busy`, `busy_soon`, `write_only`, or permission/unavailable sentinels. The mock bridge allowlists Context Snapshot fields so unknown keys, network identifiers, coordinates, nested containers, and calendar details are not echoed. No implicit permission prompt, background collection, motion history, event detail, Mobile Bridge field, Recall write, or `/mobile/v1` change is added. |
| Completed | P3.24 | SQLite asset storage retention | P3.22 made in-memory mock assets purgeable, but configured Runtime Kit stores still could not persist uploaded input assets or photo-edit output assets across app restart. | `SQLiteRuntimeStore` now has `RuntimeAssetRecord`, `RuntimeAssetPurgeReceipt`, a `runtime_assets` table, CRUD helpers, and explicit asset purge. Mock bridge asset paths use helpers that write/read SQLite when `runtime_store` supports assets and keep in-memory behavior otherwise. Store-backed uploads and photo-edit outputs remain downloadable after reopening the store and are purged only through explicit runtime-side apply. `/mobile/v1/assets` shape is unchanged; no Mobile Bridge purge endpoint, automatic cleanup, Swift UI, Recall purge, provider call, host package change, raw bytes/path receipt leakage, or task result variant persistence is added. |
| Completed | P3.25 | Store-backed task result detail persistence | P3.24 persists uploaded and rendered asset bytes, but store-backed task detail still needed the safe result manifest after a bridge restart so users can reopen completed photo-edit results. | `GET /mobile/v1/tasks/{id}` now rehydrates phone-safe photo-edit result detail from `RuntimeTaskRecord.metadata`; task metadata stores only safe result manifests, raw bytes stay in `runtime_assets`, `download_url` is rebuilt from `asset_id`, task lists remain summary-only, completed task events expose only `variant_count`, and secret-like recipe metadata is filtered. No phone purge endpoint, automatic cleanup, Swift UI, Recall write, provider call, host package change, raw bytes/path leakage, or phone settings write was added. |
| Completed | P3.26 | Recall retrieval material intake | P3.21 had a readiness contract, but host/runtime teams still needed one local materials manifest intake step that could review refs without pretending production retrieval was implemented. | Runtime Kit exposes `recall-retrieval-material-intake` with `kaka.recall_retrieval_materials.v1` input and `kaka.recall_retrieval_material_intake.v1` output schemas. It ingests local host/runtime-owned refs, blocks missing or secret-like materials without echoing secrets, embeds the P3.21 readiness snapshot, and can return `accepted_for_external_retrieval_packaging_review`. It does not fetch refs, validate signatures, invoke providers, expose endpoints/keys, return embeddings/index rows/provider responses, include retrieval internals in Recall export, or change `/mobile/v1/recall/search`. |
| Completed | P3.27 | Local renderer backend capability manifest | P3.16 proved the current Pillow/`recipe_local` renderer, but future Core Image/ImageMagick/OpenCV/libvips work needed a manifest that names gates without accidentally implying those backends exist. | Runtime Kit exposes `local-renderer-backend-capability-manifest` with `kaka.local_renderer_backend_capability_manifest.v1` and a closed schema. It records current Pillow/`recipe_local` truth, marks Core Image, ImageMagick, OpenCV, and libvips as `future_gate_required`, links future enablement to P3.16 readiness, and does not install dependencies, import or execute future backends, add endpoints, change phone-facing capabilities, or change `/mobile/v1`. |
| Completed | P3.28 | Host Extension material intake | P3.7 still needs real Hermes/OpenClaw Plugin/Skill package facts, but host teams need one local, schema-checked way to provide those facts without turning Runtime Kit or Codex automation into the ordinary-user installer. | Runtime Kit exposes `host-extension-material-intake` with `kaka.host_extension_materials.v1` input and `kaka.host_extension_material_intake.v1` output schemas. It embeds existing `host-extension-readiness`, redacts or blocks missing/secret-like package facts and install-drill refs, emits `accepted_for_external_install_drill_review` only for complete safe local manifests, and avoids install/sign/publish/fetch/bridge-start/private-adapter/Codex-user-home side effects or `/mobile/v1` changes. |
| Completed | P3.30 | Voice-to-Inbox Draft | B.1 voice was real but lived only inside image conversation. Inbox is the natural next voice-first surface because universal intake already handles text and the user can review before sending. | `InboxView` now opens the existing `VoiceCaptureView` from a visible mic action, `InboxViewModel.appendVoiceTranscript` creates a pending `.text` Inbox item with `sourceSurface = "voice"`, and `UniversalIntakeSubmitter` submits that provenance through existing universal intake only after the user taps Inbox `Send`. Raw audio stays local; no hidden recording, automatic submission, automatic Recall, new bridge endpoint, App Intent recording, or host-private API call was added. |
| Completed | P3.32 | Inbox Voice Instruction | After P3.30, the natural voice-first next step is not another voice tab, but attaching user intent to already captured Inbox material before runtime submission. | Existing universal-intake Inbox rows can open `VoiceCaptureView`, save the reviewed transcript into `KakaInboxItem.note`, and require the normal visible Inbox `Send` action. `UniversalIntakeSubmitter` sends the note as `note` and `user_instruction`; raw audio, hidden recording, automatic submission, automatic Recall, new bridge endpoints, App Intent recording, and Host Extension packaging changes remain out of scope. |
| Completed | P3.33 | Inbox Instruction Polish | P3.32 made note attachment possible, but users needed clearer edit, clear, and send-preview affordances before submitting an instructed item. | `InboxInstructionPresentation` localizes instruction copy, `InboxView` labels saved instructions, switches the row action to edit, exposes `Clear Instruction`, and shows send-preview copy before visible `Send`; `InboxViewModel.clearVoiceInstruction` clears `KakaInboxItem.note` without submission. Runtime submission remains existing universal intake `note` / `user_instruction`; no audio upload, endpoint, automatic submission, Recall write, App Intent recording, or Host Extension change was added. |
| Completed | P3.34 | Inbox Instruction Templates | P3.33 clarified edit/clear/review, but users still needed fast deterministic instruction starts without provider suggestions or automatic runtime work. | `InboxInstructionPresentation` now exposes four localized deterministic templates for universal-intake rows; `InboxView` renders compact chips; `InboxViewModel.applyInstructionTemplate` writes selected template text into `KakaInboxItem.note` through the existing note update path. Runtime submission remains existing visible Inbox `Send` with `note` / `user_instruction`; no endpoint, audio upload, automatic submission, Recall write, App Intent recording, provider call, or Host Extension change was added. |
| Completed | P3.35 | Host-Native Plugin/Skill Installation Blueprint | Installation UX remains blocked on real P3.7 host package facts, but host teams still need one machine-readable blueprint that turns the existing install-package handoff into a clearer Hermes Plugin / OpenClaw Skill implementation target. | `host-extension-install-package` now emits `installation_blueprint`, requires `host-ui/installation-blueprint.json`, writes the artifact in `--write` output, includes it in generated host manifests, and validates schema/static drift. It adds no new command, package install/sign/publish, bridge start, private adapter invocation, Codex user-home write, public Codex install surface, or `/mobile/v1` change. |
| Completed | P3.36a | Inbox Voice Capture Context Copy | The voice sheet is now reused for both Inbox draft creation and row-level instruction editing, but fixed "Send" copy could imply runtime submission even when the action only saves local reviewed text. | `VoiceCaptureView` accepts context presentation; Inbox draft sheets say Save Draft, instruction sheets say Save Instruction, localized tests cover both contexts, and behavior remains local save plus visible Inbox Send. No endpoint, audio upload, automatic submission, automatic Recall, App Intent recorder, or Host Extension change. |
| Completed | P3.36b | Explicit Paste-to-Inbox Courier | Clipboard/link input is useful only when the user intentionally sends copied text to Kaka for transform/act/remember work; Share Extension already covers many link capture cases, and pasteboard privacy must stay explicit. | A visible Inbox Paste action reads clipboard text once, trims it, creates a pending `.text` or http/https `.url` item with `sourceSurface = "paste"`, and never auto-submits or auto-Recalls. Static guards keep `UIPasteboard` in `ClipboardCourier.swift` only. No background pasteboard read, URL fetch, binary/file paste, new `/mobile/v1` endpoint, or host installation work. |
| Completed | P3.37 | Inbox Result Review Provenance | Completed Inbox results already expose explicit Recall controls, but Remember/Use Once/Forget needed the original Inbox item provenance as well as the runtime task ID. | `InboxViewModel` now records a phone-safe `InboxSubmissionContext` only after successful visible Inbox `Send`; `InboxView` shows source/context review copy in the result banner and passes `sourceInboxItemID` to `RecallView`. Existing Recall actions carry both `source_task_id` and `source_inbox_item_id`; no automatic Recall, new endpoint, runtime schema change, Files picker, host package work, or P3.7 install drill is added. |
| Completed | P3.38 | Explicit Files-to-Inbox Import | Share Extension captures system-shared files and P3.36b covers pasted text/links, but users also need a first-party, visible way to import a PDF or image from Files into the Inbox without background file access. | `InboxView` now exposes a visible Files button and SwiftUI `.fileImporter`; `InboxFileImporter` copies one supported PDF or image into the existing App Group `SharedPayloads` store; `InboxViewModel.importFile` creates a pending `KakaInboxItem` with `sourceApp = "Files"` and `sourceSurface = "file_picker"` without submitting; images route through existing image intake and PDFs through existing universal intake after visible `Send`; tests/static guards prove no automatic upload/submission/Recall, no folder scanning, no new `/mobile/v1` endpoint, no App Intent submit path, and no Host Extension packaging change. |
| Completed | P3.39 | Inbox Pending Item Discard | Voice, paste, share, and file picker flows can create pending Inbox items before runtime submission; users need an explicit way to back out before `Send`. | `InboxView` exposes a visible row-level Discard button; `InboxViewModel.discardPendingItem(id:)` removes only the selected local pending item through `KakaInboxStoring.remove(id:)`, which deletes that item's `SharedPayloads` payload when present. Static guards prove Discard has no runtime upload/task, Recall action/delete, Mobile Bridge endpoint, App Intent, Host Extension change, folder scan, or P3.7 install drill. |
| Completed | P3.40 | Inbox Discard Confirmation | P3.39 added local pending-item discard, but a destructive local queue action needs an explicit second confirmation to prevent accidental removal before `Send`. | Tapping row-level Discard opens a visible confirmation dialog; only the destructive confirm action calls `InboxViewModel.discardPendingItem(id:)` / `KakaInboxStoring.remove(id:)`, while Cancel or dismissal leaves the Inbox item and payload untouched. No runtime upload/task/cancel, Recall action/delete, Mobile Bridge endpoint/schema, App Intent/Shortcut/Widget/Live Activity action, Host Extension packaging, folder scan, source-file deletion, or P3.7 install drill is added. |
| Completed | P3.41 | Inbox Action Feedback Banner | Inbox already tracked failed actions and submission progress in `InboxViewModel.state` / `progressText`, but the user could not see that local feedback in the review surface. | `InboxActionFeedbackPresentation` maps failed/submitting state into localized banner copy; `InboxView` renders the banner above Inbox actions; `InboxViewModel.dismissFailure()` clears failed feedback locally; submit failures clear stale progress while preserving pending items. No retry, automatic submission, runtime task cancel, Recall action/write/delete, Mobile Bridge endpoint/schema, App Intent/Shortcut/Widget/Live Activity action, Host Extension packaging, source-file deletion, or P3.7 install drill is added. |
| Completed | P3.42 | Inbox Pending Item Review Details | Voice, paste, share, and file-picker flows now create pending Inbox items, and P3.41 makes action feedback visible; users still needed one richer local review surface for item metadata before `Send`. | `InboxPendingItemReviewPresentation` maps existing local pending-item metadata into localized rows, and `InboxView` adds a row-level Review Details toggle before `Send`. It shows source/type, bounded text or URL excerpt, file name/type, copied-payload state, saved instruction, route, locale/profile when present, and Context Snapshot inclusion state. No file size is computed because it is not currently a `KakaInboxItem` field. No runtime upload/task, URL fetch, payload byte read, PDF/OCR parsing, Mobile Bridge endpoint/schema change, Recall action/write/delete, App Intent/Shortcut/Widget/Live Activity action, Host Extension/P3.7 work, folder scan, or source-file deletion was added. |

## Completed Execution Slices

Recall D.1 browse/search/export foundation is implemented in the current working tree.

D.1 implemented evidence:

- Swift Core supports queryable Recall list requests, `RecallExportResponse`, and delete responses with `deleted_index_ids`.
- Mock bridge supports query/limit filtering, policy-labeled `/mobile/v1/recall/export`, and deterministic deletion index receipts.
- SwiftUI includes `RecallBrowseViewModel`, `RecallBrowseView`, and a connected Recall tab between Inbox and Tasks.
- Documentation now records the D.1 contract and privacy boundary.

Runtime persistence implemented evidence:

- Runtime Kit includes `SQLiteRuntimeStore` for Recall records, retrieval-index receipts, task records, and task events.
- `kaka_mobile_runtime_kit start` and the bridge server accept `--runtime-store-path`.
- Store-backed Recall remember/list/search/export/delete survives reopened store instances and returns content/index deletion receipts.
- Store-backed task list, approval, cancellation, status, and event history survive reopened store instances.
- Documentation records that persistence remains runtime-owned and is not a phone API field.

Previous execution slice: semantic Recall retrieval and runtime settings/status, because B.1 voice now sends editable text through the existing Mobile Bridge boundary and Runtime Kit SQLite persistence is already complete. The agent-executable plan is `docs/superpowers/plans/2026-06-05-kaka-pocket-agents-semantic-recall-runtime-settings.md`.

## Completed Slice: Semantic Recall And Runtime Settings

This slice makes Recall more useful without changing the local-first ownership boundary.

Implemented scope:

1. Add an additive `POST /mobile/v1/recall/search` contract for semantic Recall retrieval.
2. Keep `GET /mobile/v1/recall/items?query=...` as the D.1 browse/list fallback.
3. Add runtime-store semantic search hooks in Runtime Kit, starting with deterministic local token-overlap scoring so tests are stable; provider-backed embeddings can plug into the same runtime-owned method later.
4. Return ranked Recall items, score, and a user-safe match reason. Do not return raw embeddings, hidden prompts, provider keys, SQLite rows, or unrelated task logs.
5. Add a runtime settings/status surface that says whether the local Recall/task store and semantic Recall are enabled. This belongs to the runtime/bridge side, not to a phone-owned settings database.
6. Update the Recall tab to prefer semantic search for non-empty queries and fall back to the D.1 list query when semantic search is unavailable.

Multi-agent split used:

- Swift contract/UI worker: `RecallModels`, `MobileBridgeClient`, `MobileBridgeHTTPClient`, `RecallBrowseViewModel`, `RecallBrowseView`, and Swift tests.
- Runtime worker: `SQLiteRuntimeStore` search hook and runtime-store tests.
- Bridge/settings worker: mock bridge `/mobile/v1/recall/search`, `/mobile/v1/runtime/settings`, CLI/server wiring, and Python tests.
- Docs worker: API, privacy, README, runtime-kit README, direction doc, and this roadmap.
- Reviewer: additive API compatibility, deletion/index ownership, fallback behavior, and privacy/data-boundary audit.

Completion evidence:

- Semantic search returns ranked Recall items with match reasons from both in-memory mock state and SQLite-backed Runtime Kit state.
- Deleting a Recall item still returns content and retrieval-index deletion receipts.
- Recall export remains JSON-first item metadata, now carries `kaka.recall_export.v1` artifact policy metadata, and does not include embeddings or hidden runtime internals.
- Runtime settings/status exposes local store enablement and semantic Recall availability without leaking secrets.
- `RecallBrowseViewModel` tests prove semantic search and fallback.
- Full Swift/Python/plist/diff and XcodeBuildMCP gates are required before this branch is considered ready.

## Completed Slice: Provider-Backed Recall Retrieval

P2.3 keeps the Mobile Bridge search contract stable while moving richer ranking behind runtime-owned provider adapters.

Implemented scope:

1. Add `runtime-kit/kaka_mobile_runtime_kit/recall_search.py` with `RecallSearchProvider`, `RecallSearchResult`, deterministic `TokenOverlapRecallSearchProvider`, and `RuntimeHTTPRecallSearchProvider`.
2. Make `SQLiteRuntimeStore.search_recall_semantic()` delegate to an injectable provider while keeping deterministic local scoring as default.
3. Add Runtime Kit CLI flags `--recall-search-provider` and `--recall-search-endpoint`; `runtime_http` requires an endpoint, and dry-run includes a phone-safe summary while preserving the explicit developer command.
4. Wire mock bridge/server construction so provider-backed retrieval works with in-memory development state and SQLite-backed runtime state.
5. Keep `POST /mobile/v1/recall/search` source-compatible: `mode` remains `semantic`; `retrieval_mode` is additive.
6. Allowlist mobile search result payloads to `item`, `score`, and `match_reason`, with item data restricted to user-visible Recall fields.
7. Update API, privacy, README, Runtime Kit, direction, and roadmap docs.

Completion evidence:

- Focused provider/store/CLI/bridge tests pass, including malicious provider/store sentinel coverage for provider keys, endpoints, SQLite paths, raw embeddings, hidden prompts, raw provider responses, and index rows.
- Provider errors fall back to deterministic local scoring when safe.
- Runtime settings can report `provider_backed` without exposing provider endpoint, key, SQLite path, embedding, or index internals.
- No Swift source change was required because the search response shape remained additive.

## Completed Slice: Runtime-Side Settings Shell

P2.4 gives Hermes/OpenClaw plugin authors a concrete runtime-side settings contract without moving persistence or provider settings into the phone app.

Implemented scope:

1. Add Runtime Kit `settings-preview`, a JSON plugin-shell contract for Hermes/OpenClaw runtime UI.
2. Cover bridge enabled state, start/stop action, QR URL, loopback/LAN binding, Bonjour, local Recall/task store toggle/path picker, Recall retrieval provider menu, and runtime HTTP Recall endpoint input.
3. Reuse `BridgeConfig`, `build_server_command()`, and `validate_start_config()` so `settings-preview` and `start --dry-run` share command construction and safety validation.
4. Keep `start --dry-run` developer-facing and keep `phone_safe_summary` nested, non-secret, and free of runtime store paths, provider endpoints, env files, tokens, embeddings, and index rows.
5. Keep `/mobile/v1/runtime/settings` phone-safe with allowlisted schema guards for local and provider-backed settings.
6. Update Runtime Kit, Hermes plugin, Hermes skill, OpenClaw skill, Runtime Kit plan, direction, and roadmap docs.

Completion evidence:

- Runtime Kit focused tests prove `settings-preview` outputs the runtime-side controls and exact start command.
- CLI validation rejects unsafe Bonjour and malformed/missing `runtime_http` Recall endpoints from both `start` and `settings-preview`.
- Bridge tests prove runtime-side UI values such as SQLite paths and provider endpoints do not enter phone-bound `/mobile/v1/runtime/settings`.
- No Swift source change was required because P2.4 does not change the Mobile Bridge phone API.

Follow-up status:

1. P2.7 runtime process ownership has since been executed around the hardened Runtime Kit `settings-preview`, `package-preview`, and `consumer_ui` contracts.
2. P2.8 consumer host packaging handoff has since been executed around `host-package-preview`, host package schema/static manifest declarations, and safe command artifacts.
3. P2.9 host adapter binding has since been executed around `host-adapter-run`, mock conformance/local QA behavior, and private-unavailable placeholder behavior.
4. C.1b network-only Context Snapshot has since been executed with one-shot coarse network path labels, and P3.29 has since executed one-shot current motion plus next-30-minute calendar busy-window labels behind the same opt-in preview and runtime support gate.

## Completed Slice: Production Runtime Pairing Hardening

This slice turns the current development pairing model into a production-capable runtime-owned security lifecycle without making the phone own runtime settings.

Implemented scope:

1. Add Runtime Kit pairing primitives for short-lived single-use QR payloads, exchange results, mobile token records, revocation, token/device listing, and phone-safe security summary.
2. Persist production pairing sessions and mobile tokens in `SQLiteRuntimeStore` when `--runtime-store-path` is configured.
3. Add mock bridge production routes for `GET /mobile/v1/pairing/qr`, `GET /mobile/v1/pairing/qr.html`, `POST /mobile/v1/pairing/exchange`, and `POST /mobile/v1/pairing/revoke`.
4. Make every protected mock bridge endpoint reject revoked or expired production mobile tokens.
5. Extend Runtime Kit `settings-preview` and `package-preview` with pairing mode, QR TTL, token revocation, trusted local TLS metadata, and no-secret phone-safe summaries.
6. Update server and Bonjour wiring so production mode does not advertise static `pair_dev` or 2099 expiry.
7. Add a Swift client refresh path that tries production QR payload refresh before falling back to development pairing recovery.
8. Update API, privacy, README, Runtime Kit, direction, and roadmap docs after implementation lands.

Recommended multi-agent split:

- Runtime security worker: pairing primitives and SQLite persistence.
- Bridge worker: mock bridge routes, auth, revocation, and server/Bonjour wiring.
- CLI/package worker: Runtime Kit `settings-preview` and `package-preview` security contract.
- Swift worker: production QR refresh fallback and focused pairing tests.
- Docs/review worker: API/privacy/runtime docs plus final no-secret review.

Completion evidence:

- Production QR payloads expire in 60-300 seconds and cannot be exchanged twice.
- Revoked mobile tokens return `401 unauthorized` on every bearer-protected endpoint.
- `settings-preview`, `package-preview`, `/mobile/v1/runtime/settings`, Recall export/search, and task APIs do not leak raw mobile tokens, provider secrets, auth/env files, TLS private key paths, SQLite paths, embeddings, retrieval-index rows, hidden prompts, raw provider responses, or unrelated task logs.
- Development `pair_dev` tests still pass.
- Focused Runtime Kit, mock bridge, Swift, doctor, diff, and XcodeBuildMCP gates are required before this branch is considered ready.

## Completed Slice: Hermes/OpenClaw Consumer Runtime UI Contract

P2.6 turns the hardened settings/package contracts into a stable ordinary-user
renderer model without creating a host-native process manager yet.

Implemented scope:

1. Add `runtime_side_ui.consumer_ui` to Runtime Kit `settings-preview` with schema version `kaka.runtime_consumer_ui.v1`.
2. Group raw runtime controls into Process, Connection, Pairing, Local Memory, and Recall Retrieval sections.
3. Add status badges, primary actions, warning copy, stopped-bridge empty state, and safe summary fields for Hermes/OpenClaw shells.
4. Expose the same model from `package-preview` as `consumer_ui`, derived from `settings_preview.runtime_side_ui.consumer_ui` so packaging does not gain a second source of truth.
5. Require static Hermes/OpenClaw manifests to declare the `consumer_ui` source, schema version, required sections, and required actions.
6. Update Runtime Kit, packaging, Hermes/OpenClaw skill docs, README, direction, and roadmap docs so P2.6 is completed and process ownership is next.

Multi-agent split used:

- Runtime UI contract worker: `cli.py` consumer UI builder and Runtime Kit CLI tests.
- Manifest/schema worker: packaging schemas, static Hermes/OpenClaw manifests, and manifest shape tests.
- Docs worker: Runtime Kit, Hermes/OpenClaw, README, direction, and roadmap docs.
- Reviewer agents: spec compliance, no duplicate settings source, no-autostart defaults, and phone-safe summary/privacy boundary.

Completion evidence:

- Focused Runtime Kit tests prove `consumer_ui` sections/actions/warnings, stopped empty state, and package-preview derivation.
- Static manifest tests prove required `consumer_ui` metadata and hardened controls.
- Package-preview samples show production QR/revocation/TLS state in the runtime-side renderer model while install defaults stay disabled.
- No Swift source change was required because this slice only changes runtime-side contracts and docs.

## Completed Slice: Runtime Process Ownership

P2.7 turns the consumer renderer model into an explicit runtime-side lifecycle
contract without implementing host-native process APIs.

Implemented scope:

1. Add `runtime_side_ui.process_ownership` to Runtime Kit `settings-preview` with schema version `kaka.runtime_process_ownership.v1`.
2. Derive package-preview `process_ownership` from the same settings preview source of truth.
3. Cover install, start-at-login/start-with-runtime, update, uninstall, open logs, run health check, and repair port conflict actions.
4. Extend `consumer_ui` with a Process section so ordinary users see lifecycle controls next to connection, pairing, memory, and retrieval.
5. Require static Hermes/OpenClaw manifests to declare the process ownership source, schema version, required actions, explicit approval, and no-autostart defaults.
6. Update Runtime Kit, packaging, Hermes/OpenClaw skill docs, README, direction, and roadmap docs so P2.7 is completed and host packaging handoff is next.

Boundaries:

- P2.7 does not create login items or LaunchAgents.
- P2.7 does not auto-start the bridge on install.
- P2.7 does not implement real Hermes/OpenClaw native install, update, uninstall, log, health, repair, or supervision APIs.
- Install defaults stay disabled and `start_with_runtime` defaults false.
- Lifecycle state and diagnostics stay runtime-side and are not copied into Kaka iPhone settings.

Completion evidence:

- Focused Runtime Kit tests prove `process_ownership` actions, warnings, package-preview derivation, and `consumer_ui` Process controls.
- Static manifest tests prove required process ownership metadata and no-autostart defaults.
- Docs recorded host packaging handoff as the P2.8 follow-up; P2.8 has since completed.

## Completed Slice: Consumer Host Packaging Handoff

P2.8 turns the process ownership contract into a stable host packaging handoff
without implementing private Hermes/OpenClaw host APIs.

Implemented scope:

1. Add Runtime Kit `host-package-preview` with schema version `kaka.runtime_host_package.v1`.
2. Include distribution source/channel/version metadata, disabled-by-default install policy, host-owned action metadata, safe preview command artifacts, `process_ownership`, and `consumer_ui`.
3. Add `runtime-kit/packaging/host-package.schema.json`.
4. Require static Hermes/OpenClaw manifests to declare the host package source, surface, required actions, native-adapter requirement, and `host_package_preview` entrypoint.
5. Keep mutating lifecycle actions owned by `host_native_adapter` and marked as requiring explicit user approval.
6. Update Runtime Kit, packaging, Hermes/OpenClaw skill docs, README, direction, and roadmap docs so P2.8 is completed and P2.9 private host adapter binding is active next. P2.9 has since completed as the `host-adapter-run` binding surface.

Boundaries:

- P2.8 does not call private Hermes/OpenClaw APIs.
- P2.8 does not install, update, uninstall, create login items, run updaters, open native log windows, or supervise processes.
- P2.8 does not start a listener, bind a port, advertise Bonjour, mint credentials, or enable start-at-login during package install.
- The phone connects to agents through the local Mobile Bridge `/mobile/v1` API.
- Host shell rendering and setup flow use Runtime Kit preview JSON/CLI contracts.
- Native install, login item, update, uninstall, log, health, repair, and supervision now have a P2.9 `host-adapter-run` binding surface; P3.1 defines the host-private command bridge for proprietary host APIs.

Completion evidence:

- Focused Runtime Kit tests prove `host-package-preview` output, disabled install policy, host-owned actions, safe artifacts, and phone-safe field exclusions.
- Static manifest tests prove the host package schema and Hermes/OpenClaw declarations.
- Docs recorded P2.8 as completed and P2.9 as the active next host adapter binding; P2.9 has since completed as the testable binding surface.

## Completed Slice: Hermes/OpenClaw Host Adapter Binding

P2.9 binds the P2.8 host package handoff to a testable host adapter action
surface without changing the iPhone connection API.

Implemented scope:

1. Add Runtime Kit `host-adapter-run` for Mac/runtime-side install, start-with-runtime, update, uninstall, logs, health, repair, and supervision action results.
2. Add `mock` adapter mode for conformance/local QA without mutating the actual host OS.
3. Add `private` adapter mode as a structured unavailable placeholder. P3.1 has since connected this mode to the host-private command bridge while preserving the unavailable fallback.
4. Require explicit user approval for mutating host actions.
5. Keep install safe: it does not start the bridge, bind a port, advertise Bonjour, mint credentials, or create a login item.
6. Update Runtime Kit, packaging, Hermes/OpenClaw skill docs, README, direction, and roadmap docs so P2.9 is completed and P3.0 becomes the next slice at that time. P3.0 has since completed.

Boundaries:

- P2.9 does not change the phone API. Kaka iPhone still connects to agents only through Kaka Mobile Bridge `/mobile/v1`.
- `host-adapter-run` is a Mac/runtime-side action surface, not a private host API exposed to the phone.
- Host adapter result JSON is runtime-side only and must not include provider keys, mobile tokens, TLS private key paths, host log paths, process IDs, runtime SQLite paths, raw embeddings, index rows, hidden prompts, or task logs.
- `mock` is conformance/local QA; in P2.9 `private` returns unavailable until a later host-private bridge is supplied.

Completion evidence:

- Focused Runtime Kit tests prove approval gating, mock state transitions, private unavailable behavior, CLI JSON output, and `host-package-preview` action parity.
- Static manifest tests prove host adapter metadata, `host_adapter_run` entrypoints, hardened action-result schemas, and forbidden phone-safe field coverage.
- Docs now record P2.9 as completed, P3.0 as ordinary-user end-to-end connection QA, and P3.1 as the host-private command bridge boundary.

## Completed Slice: P3.0 Ordinary-User Connection QA And Host Adapter Readiness

P3.0 validates the complete first-run experience using the safe scaffold that
already exists, before depending on host-owned Hermes/OpenClaw private commands. The
completed agent-executable plan is
`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-ordinary-user-connection-qa.md`,
and the ordinary-user checklist is `docs/kaka-ordinary-user-connection-qa.md`.

Implemented scope:

1. Added `runtime-kit/kaka_mobile_runtime_kit/connection_qa.py` and CLI `connection-qa-preview` for deterministic Runtime Kit first-run QA: package preview, host package preview, mock host adapter results, bridge start command, pairing QR, token revocation, health check, saved-token reconnect, safety notes, and P3.1 private API readiness.
2. Added Swift `ConnectionReadinessPresentation` fixtures for expired QR, revoked token, bridge unavailable, missing Bonjour host, port conflict, disabled host action, and private adapter unavailable states.
3. Added `docs/kaka-ordinary-user-connection-qa.md` with first-run checklist, failure drills, privacy boundary, and P3.1 dependency list.
4. Updated README, Runtime Kit README, and this roadmap to describe the normal Hermes/OpenClaw user flow without asking users to understand private APIs.
5. Kept the iPhone connection contract unchanged: the phone stores only endpoint/token and talks to Mobile Bridge `/mobile/v1`.

Multi-agent split used for P3.0:

- Runtime QA worker: pytest fixtures and CLI sample validation for package preview, host adapter actions, bridge start, QR pairing, token revocation, and health checks.
- Swift connection worker: connection readiness presentation and tests for user-visible recovery copy without networking/API changes.
- Docs/checklist worker: README, Runtime Kit README, roadmap, and a plain first-run QA checklist.
- Lead agent: integration review, small import cleanup, focused/broad verification, and plan/roadmap completion updates.

P3.0 validation evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge \
  python3 -m pytest -p no:cacheprovider \
  runtime-kit/tests/test_connection_qa.py \
  runtime-kit/tests/test_runtime_kit_cli.py \
  runtime-kit/tests/test_host_adapter.py -q
# 71 passed

swift test
# 336 passed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge \
  python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
# 368 passed

PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit connection-qa-preview \
  --runtime hermes \
  --bridge-enabled \
  --lan \
  --bonjour \
  --bonjour-host 192.168.1.10 \
  --pairing-mode production \
  --runtime-store-path /tmp/kaka-runtime.sqlite3 \
  --recall-search-provider fixture | python3 -m json.tool >/tmp/kaka-connection-qa.json
```

Exit criteria met:

- A first-run user can identify the right host runtime, start the bridge, pair an iPhone, run health checks, revoke tokens, and recover from the expected failure fixtures.
- `connection-qa-preview` emits deterministic first-run steps, failure fixtures, phone-safe safety notes, `private_api_called: false`, and a P3.1 private API readiness list without mutating host state.
- Hermes/OpenClaw docs describe the flow in ordinary-user terms and do not imply that the iPhone connects to private host APIs.
- All host-side mutating actions remain approval-gated and safe by default.
- The readiness report identifies exactly which host-private capabilities must be supplied behind the P3.1 command bridge.

## Completed Slice: P3.1 Host-Private Command Bridge Contract

P3.1's landing boundary is the Runtime Kit command bridge, not bundled
Hermes/OpenClaw proprietary implementation. Runtime Kit builds a sanitized
runtime-side request, invokes a configured host command with `shell=False`,
sends JSON on stdin, reads JSON on stdout, validates the response, and maps the
result into `kaka.host_adapter_action_result.v1`.

Example host-private health check:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

Boundaries:

- The iPhone continues to call only Mobile Bridge `/mobile/v1`.
- `host-adapter-run --adapter private` remains Mac/runtime-side only.
- Missing `--private-adapter-command` returns `private_host_adapter_unavailable`.
- Non-zero, invalid JSON/schema, or timed-out commands return structured safe
  failures and must not claim host mutation.
- Mutating actions still require `--approved`; disabled host actions do not
  invoke the private command.
- The request/response must not expose provider keys, raw mobile tokens, TLS
  private key paths, hidden prompts, raw embeddings, index rows, task logs,
  process IDs, host log paths, or runtime SQLite paths to the phone.
- Hermes/OpenClaw proprietary APIs plug in behind the configured command; this
  repository does not include official/private Hermes or OpenClaw API code.

Implemented scope:

1. Added `runtime-kit/kaka_mobile_runtime_kit/private_host_api.py` for the
   sanitized host-private request builder, `shell=False` command execution,
   timeout/non-zero/non-JSON/invalid-response handling, response normalization,
   and bounded detail allowlist.
2. Added `--private-adapter-command` and `--private-adapter-timeout-seconds` to
   `host-adapter-run`.
3. Routed `adapter_mode="private"` through the configured command while keeping
   missing-command unavailable fallback, disabled-action gates, and mutating
   `--approved` gates before external command execution.
4. Added request/response schemas and static manifest metadata for
   `host_private_adapter`.
5. Updated Runtime Kit/Hermes/OpenClaw docs and ordinary-user QA docs to state
   that the phone uses only `/mobile/v1` and the proprietary host API command is
   supplied by Hermes/OpenClaw outside this repository.

Completion evidence:

- Focused Runtime Kit host adapter and packaging tests passed: `27 passed`.
- Broad Python tests passed: `382 passed`.
- SwiftPM tests passed: `336 tests`.
- CLI smoke passed for configured fake private command success and missing
  command unavailable failure.
- Runtime Kit doctor passed.
- `git diff --check` passed.

## Completed Slice: P3.2 Host-Owned Adapter Dogfood And Conformance

P3.2 turns the P3.1 private command bridge into repeatable host-owned
conformance evidence. Runtime Kit still does not implement, bundle, discover, or
distribute proprietary Hermes/OpenClaw command binaries; it validates a command
supplied by the host shell.

The runtime-side conformance CLI is:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

Implemented scope:

1. Added `runtime-kit/kaka_mobile_runtime_kit/host_private_adapter_conformance.py`
   with a closed `kaka.host_private_adapter_conformance.v1` report builder.
2. Added CLI `host-private-adapter-conformance` with
   `--private-adapter-command`, `--private-adapter-timeout-seconds`, and
   optional negative-check skipping for controlled host-side dogfood.
3. Expanded the fake private host API fixture so local tests cover every
   `HOST_ADAPTER_ACTIONS` case: install, enable/disable login item, update,
   uninstall, open logs, health, port repair, and supervision.
4. Added negative checks proving unapproved install and disabled health check do
   not invoke the private command.
5. Added `host-private-adapter-conformance.schema.json` plus static
   Hermes/OpenClaw manifest declarations.
6. Updated Runtime Kit, packaging, Hermes/OpenClaw, README, and roadmap docs to
   document conformance without implying Kaka owns proprietary command binaries.

Completion evidence:

- Focused conformance, host-adapter, and packaging tests passed: `35 passed`.
- CLI smoke passed for configured fake private command success:
  `exit=0`, `summary={"total": 9, "passed": 9, "failed": 0}`.
- CLI smoke passed for missing command structured failure:
  `exit=2`, `summary={"total": 9, "passed": 0, "failed": 9}`,
  `private_api_called=false`.
- Broad Python tests passed: `390 passed`.
- SwiftPM tests passed: `336 tests`.
- Runtime Kit doctor passed.
- `git diff --check` passed.

Historical next implementation slice after P3.2:

- P3.4 should run the P3.3 package contract through an actual Hermes or
  OpenClaw host shell with a real host-owned command binary outside this
  repository, collect conformance evidence, and document install/update/failure
  drills for ordinary users.

## Completed Slice: P3.3 Real Host Packaging Distribution Integration

P3.3 is a packaging/distribution contract slice, not a private Hermes/OpenClaw
implementation slice. The completed P2.8 `host-package-preview` already
declares host package actions, P3.1 already defines how Runtime Kit calls a
configured host command, and P3.2 already validates that command. P3.3 connects
those surfaces so host shells know exactly how to discover, distribute, update,
sign, and release-gate the proprietary command binary they own.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-real-host-packaging-distribution.md`

Implemented scope:

1. Add `runtime-kit/kaka_mobile_runtime_kit/host_private_adapter_package.py`
   with `kaka.host_private_adapter_package.v1` metadata for command naming,
   host-owned discovery, distribution/update policy, conformance command
   artifacts, required capabilities, and `/mobile/v1` safety.
2. Extend `build_runtime_host_package()` and `host-package-preview` with a
   nested `private_adapter_package` object. Preview generation remains
   non-mutating and must not execute the configured private command.
3. Add `host-private-adapter-package.schema.json`, extend
   `host-package.schema.json`, and add `host_private_adapter_package`
   declarations to the Hermes/OpenClaw static shell manifests.
4. Update Runtime Kit, packaging, Hermes/OpenClaw skill docs, public README, and
   this roadmap so host shells have a clear implementation checklist.
5. Verified focused Runtime Kit packaging/conformance tests, CLI smoke, Runtime
   Kit doctor, broad Python gates, and `git diff --check`.

Non-goals:

- Do not add phone-side private API settings or endpoints.
- Do not add proprietary Hermes/OpenClaw binary code to this repository.
- Do not create real login items, LaunchAgents, updater jobs, uninstall
  deletion logic, or process supervisors in Runtime Kit.
- Do not change App Intents, WidgetKit, SwiftUI, iOS plist, or entitlement
  wiring unless a later plan explicitly expands scope.

Executed multi-agent split:

- Runtime package worker: module, CLI integration, and focused tests.
- Schema/static manifest worker: packaging schemas, static manifests, and schema
  tests.
- Docs/roadmap worker: Runtime Kit, Hermes/OpenClaw, README, and roadmap docs.
- Lead/reviewer: integration, schema validation, CLI smoke, broad regression
  gates, spec/code-quality review, and final roadmap status update.

P3.3 exit criteria:

- `host-package-preview` embeds `private_adapter_package` for Hermes and
  OpenClaw.
- Static manifests and schemas validate the new package metadata.
- Generated metadata names the host-owned binary, discovery sources, update
  policy, signature policy, conformance command, and `/mobile/v1` phone
  boundary.
- Docs clearly state that Kaka does not own or distribute proprietary command
  binaries.
- P3.4 is queued as an external host-shell dogfood/release pilot with a real
  Hermes/OpenClaw command binary outside this repository.

Completion evidence:

- Runtime artifacts present: `runtime-kit/kaka_mobile_runtime_kit/host_private_adapter_package.py`
  and `runtime-kit/packaging/host-private-adapter-package.schema.json`.
- Static Hermes/OpenClaw manifests declare `host_private_adapter_package`
  metadata sourced from `host_package.private_adapter_package`.
- Docs now describe the P3.3 package contract and host shell checklist without
  claiming Kaka owns or distributes proprietary Hermes/OpenClaw command
  binaries.
- Focused P3.3 Runtime Kit tests passed: `41 passed`.
- Expanded packaging/CLI focused tests passed: `65 passed`.
- CLI smoke passed for Hermes and OpenClaw `host-package-preview`, including
  `private_adapter_package`, `/mobile/v1`, and the forbidden phone-safe field
  superset.
- Runtime Kit doctor passed.
- Broad Python gate passed: `396 passed`.
- `git diff --check` passed.
- Spec review approved; code-quality review approved after schema and
  forbidden-field hardening.

## Completed Slice: P3.4a External Host Shell Pilot Readiness

P3.4a is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot by itself; instead, it gives Runtime Kit a
strict receipt that records whether the host has supplied enough evidence to
start or complete that pilot.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-external-host-shell-pilot-readiness.md`

Preflight finding:

- A real Hermes host shell is present on this machine:
  `/Applications/Hermes.app`, `/Applications/Hermes Setup.app`, and
  `/Users/kartz/.local/bin/hermes`.
- No Kaka private adapter command was found:
  `hermes-kaka-host-api`, `openclaw-kaka-host-api`,
  `~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api`, and
  `~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api` are all
  absent in the checked locations.
- `HERMES_KAKA_HOST_API` and `OPENCLAW_KAKA_HOST_API` are not configured.
- OpenClaw was not found as an app bundle or CLI on this machine.

Current receipt gate:

- `host-shell-pilot-report --runtime hermes` returns `status: "not_ready"`,
  `private_adapter_command.provided: false`, `conformance.ran: false`, and
  `can_mark_p3_4_complete: false`.
- `host-shell-pilot-report --runtime openclaw` returns `status: "not_ready"`,
  `private_adapter_command.provided: false`, `conformance.ran: false`, and
  `can_mark_p3_4_complete: false`.
- Remaining P3.4 evidence is external to this repository: a real host-owned
  command binary, native distribution/update channel, signature evidence,
  passing conformance against that real binary, install/update/failure-recovery
  drill receipts, and user-facing release notes.

Implemented scope:

1. Added `host-shell-pilot-report`, a Runtime Kit CLI receipt for the first
   external host-shell pilot.
2. Added `kaka.host_shell_pilot_receipt.v1`, a closed schema for real vs
   synthetic command status, native distribution evidence, signature/update-feed
   evidence, conformance results, install/update/failure drill receipts, and
   release-note readiness.
3. Extended static Hermes/OpenClaw shell manifests with a
   `host_shell_pilot_receipt` declaration and `host_shell_pilot_report`
   entrypoint.
4. Documented that fake fixture conformance is `synthetic_only` and can never
   mark P3.4 complete.
5. Kept `hermes-kaka-host-api` and `openclaw-kaka-host-api` owned and
   distributed by Hermes/OpenClaw outside this repository.
6. Hardened malformed private adapter command handling so pilot reports return
   structured `not_ready` receipts instead of crashing.
7. Tightened the receipt schema so forged `ready` receipts with blocking reasons
   or empty command paths are rejected.

P3.4a exit criteria:

- Missing command produces `status: "not_ready"` and
  `can_mark_p3_4_complete: false`.
- Repository fake fixture conformance produces `status: "synthetic_only"` and
  `can_mark_p3_4_complete: false`.
- A supplied real external command can produce `status: "ready"` only when
  conformance passes and native distribution, signature, update-feed,
  install/update/failure drills, and release notes are verified.
- Docs and roadmap continue to state that P3.4 completion requires a real
  host-owned binary outside the Kaka repository.

Executed P3.4a multi-agent split:

- Runtime worker: `host_shell_pilot.py`, CLI wiring, and focused Runtime Kit
  tests.
- Schema/static manifest worker: receipt schema, runtime shell manifest schema,
  Hermes/OpenClaw static declarations, and manifest tests.
- Docs worker: Runtime Kit, packaging, Hermes/OpenClaw shell docs, public
  README, Chinese README, and this roadmap.
- Lead/reviewer: integration, CLI smoke, focused Runtime Kit tests, broad
  Python gate, and final verification.

Completion evidence:

- Runtime artifacts present: `runtime-kit/kaka_mobile_runtime_kit/host_shell_pilot.py`,
  `runtime-kit/packaging/host-shell-pilot-receipt.schema.json`, and
  `host-shell-pilot-report` in `runtime-kit/kaka_mobile_runtime_kit/cli.py`.
- Static Hermes/OpenClaw manifests declare both `host_shell_pilot_receipt` and
  `entrypoints.host_shell_pilot_report`.
- Missing command CLI smoke returns `status: "not_ready"`,
  `can_mark_p3_4_complete: false`, and exit code `2`.
- Synthetic fixture CLI smoke returns `status: "synthetic_only"`,
  `conformance.synthetic_only: true`, `can_mark_p3_4_complete: false`, and exit
  code `2`.
- Malformed command CLI smoke returns `status: "not_ready"`,
  `conformance.ran: true`, `conformance.ok: false`, and exit code `2`; it does
  not crash.
- Receipt schema validates generated missing, synthetic, and malformed receipts
  and rejects forged `ready` receipts with missing command evidence or empty
  command paths.
- Focused P3.4a/Runtime Kit gate passed: `75 passed`.
- Broad Python gate passed: `403 passed`.
- `git diff --check` passed.
- Spec review approved after tightening `synthetic_only` status semantics.
- Quality review approved after malformed-command, manifest-entrypoint, and
  schema-consistency hardening.

Docs evidence:

- Runtime Kit packaging docs, Runtime Kit README, Hermes/OpenClaw shell docs,
  public README, and Chinese README document `host-shell-pilot-report` as a
  P3.4a receipt for the first external host-shell pilot.
- The docs state that Runtime Kit verifies and records readiness evidence only;
  it does not own, build, sign, distribute, install, update, or bundle the
  proprietary Hermes/OpenClaw private adapter binary.
- The docs state that fake fixture or local conformance evidence is
  `synthetic_only` and cannot mark P3.4 complete.
- P3.4 remains incomplete until Hermes/OpenClaw supplies a real host-owned
  `hermes-kaka-host-api` or `openclaw-kaka-host-api` binary outside this
  repository.

## Completed Slice: P3.4b Host Shell Command Discovery

P3.4b is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it aligns Runtime Kit with the command
discovery sources already declared by P3.3 so external host shells can provide a
real command without requiring every pilot report invocation to pass a path
manually.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-command-discovery.md`

Implemented scope:

1. `host-shell-pilot-report` now resolves the host-owned command in this order:
   explicit `--private-adapter-command`, runtime environment variable, manifest
   `host_private_adapter.command`, and well-known Application Support path.
2. The receipt records the discovery source as `missing`, `argument`,
   `environment_variable`, `manifest_entrypoint`, or `well_known_path`.
3. The receipt schema rejects unknown command source strings.
4. The runtime shell manifest schema allows an optional
   `host_private_adapter.command` field for external Hermes/OpenClaw host-owned
   manifests.
5. The implementation does not search `$PATH`, does not change the phone API,
   and does not bundle or implement proprietary Hermes/OpenClaw private APIs.

Completion evidence:

- TDD red run before implementation:
  `runtime-kit/tests/test_host_shell_pilot.py` failed with `4 failed, 8 passed`
  for missing env, manifest, well-known, and CLI discovery behavior.
- Focused green run after implementation passed:
  `20 passed` for `runtime-kit/tests/test_host_shell_pilot.py` and
  `runtime-kit/tests/test_packaging_manifest_shape.py`.
- Docs now state that missing discovery still returns `not_ready` and P3.4 still
  requires a real external host-owned binary plus native distribution,
  signature, update-feed, drill, and release-note evidence.

## Completed Slice: P3.4c Host Private Adapter Authoring Kit

P3.4c is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it gives external host teams the concrete
contract docs and schema-checked examples needed to implement the real
`hermes-kaka-host-api` or `openclaw-kaka-host-api` binary outside this
repository.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-private-adapter-authoring-kit.md`

Implemented scope:

1. Added `runtime-kit/packaging/HOST_PRIVATE_ADAPTER_IMPLEMENTATION.md` with
   stdio/argv, request/response schema, stderr/exit-code/timeout, 9-action
   matrix, approval, state, safe error, forbidden field, conformance, and P3.4
   ready guidance.
2. Added schema-checked examples under `runtime-kit/packaging/examples/` for
   health-check request/response, approved install request/response, host error,
   invalid extra-field response, and ready pilot receipt.
3. Added tests that validate the examples against request/response/pilot schemas
   and prove the invalid extra-field response is rejected.
4. Added semantic assertions for example action/adapter/approval metadata.
5. Hardened direct private command invocation so an executable command path with
   spaces is treated as one argv before falling back to `shlex.split`.

Completion evidence:

- Examples TDD red run failed on missing
  `runtime-kit/packaging/examples/run_health_check.request.json`.
- Command path TDD red run failed because direct conformance could not run an
  executable path under an `Application Support` directory.
- Focused P3.4c gate passed: `40 passed`.
- Broad Python gate passed: `411 passed`.
- `git diff --check` passed.

## Completed Slice: P3.4d Host Shell Pilot Evidence Refs

P3.4d is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it gives host teams a precise way to
attach audit references to the pilot receipt once they provide a real
`hermes-kaka-host-api` or `openclaw-kaka-host-api` binary outside this
repository.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-refs.md`

Implemented scope:

1. Added optional `distribution.evidence` refs for native channel, signing
   subject, notarization team ID, and update feed.
2. Added optional `drills.evidence` refs for install receipt, update receipt,
   failure recovery receipt, and release notes.
3. Added `host-shell-pilot-report` CLI flags for the eight refs.
4. Kept readiness booleans unchanged: evidence refs do not mark distribution,
   signature, update-feed, conformance, drill, or release-note checks verified.
5. Closed the pilot receipt schema so only documented evidence-ref keys are
   accepted; unexpected sensitive fields are rejected.
6. Updated the pilot-ready example and host-facing docs to show what
   Hermes/OpenClaw should provide.

Completion evidence:

- Receipt builder TDD red run failed because evidence-ref kwargs were not
  supported.
- CLI TDD red run failed because `host-shell-pilot-report` did not recognize
  the new evidence-ref flags.
- Schema TDD red run failed because `distribution.evidence` and
  `drills.evidence` were not declared.
- Focused P3.4d gate passed: `54 passed`.
- Broad Python gate passed: `413 passed`.
- P3.4 remains external: a real host-owned command binary, native distribution,
  signature/update-feed proof, install/update/failure drill receipts, and
  release notes still need to come from Hermes/OpenClaw.

## Completed Slice: P3.4e Host Shell Pilot Handoff Bundle

P3.4e is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it gives the external host shell one
machine-readable package to submit once it provides a real
`hermes-kaka-host-api` or `openclaw-kaka-host-api` binary, verified receipt, and
audit refs.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-handoff-bundle.md`

Implemented scope:

1. Added `host-shell-pilot-handoff`, a Runtime Kit CLI that wraps
   `host-shell-pilot-report` rather than changing it.
2. Added `kaka.host_shell_pilot_handoff.v1`, a closed handoff schema with
   embedded `pilot_receipt`, `audit_refs`, `deliverables`, `release_handoff`,
   and safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   handoff command.
4. Added `runtime-kit/packaging/examples/pilot_handoff.blocked.json`.
5. Required all eight P3.4d audit refs for handoff `ready_to_submit` while
   keeping the embedded receipt readiness unchanged.
6. Kept `p3_4_complete: false` and
   `p3_4_completion_owner: "external_host_shell"` in every handoff.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_handoff` did not exist.
- Schema/manifest TDD red run failed because
  `runtime-kit/packaging/host-shell-pilot-handoff.schema.json` did not exist.
- Focused P3.4e gate passed: `7 passed`.
- Focused Runtime Kit adjacent gate passed: `114 passed`.
- Current no-real-binary CLI smoke prints
  `kaka.host_shell_pilot_handoff.v1 incomplete False False`.
- Broad Python gate passed: `419 passed`.
- P3.4 remains external: the handoff can become `ready_to_submit`, but final
  completion still requires the host-owned external pilot/release.

## Completed Slice: P3.4f Host Shell Pilot Preflight

P3.4f is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it makes the local preflight state
machine-readable before a host team runs conformance, pilot report, or handoff.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-preflight.md`

Implemented scope:

1. Added `host-shell-pilot-preflight`, a read-only Runtime Kit CLI.
2. Added `kaka.host_shell_pilot_preflight.v1`, a closed schema with host shell,
   private adapter command discovery, handoff command, release preflight, next
   actions, and safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   preflight command.
4. Added `runtime-kit/packaging/examples/pilot_preflight.blocked.json`.
5. Checked host shell app/CLI presence plus explicit argument, runtime env var,
   manifest entrypoint, and well-known private adapter command sources.
6. Reported `$PATH` command discovery as informational only so it cannot satisfy
   pilot discovery.
7. Proved preflight does not invoke the private adapter command, run
   conformance, fetch audit refs, mutate host state, or mark P3.4 complete.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_preflight` did not exist.
- Schema/manifest TDD red run failed because
  `runtime-kit/packaging/host-shell-pilot-preflight.schema.json` did not exist.
- Focused P3.4f gate passed: `9 passed`.
- Focused Runtime Kit adjacent gate passed: `122 passed`.
- Current local Hermes preflight smoke prints
  `kaka.host_shell_pilot_preflight.v1 blocked False True missing missing_private_adapter_command`.
- Broad Python gate passed: `427 passed`.
- P3.4 remains external: `ready_for_conformance` only means the host can run the
  next conformance step, not that the external pilot is complete.

## Completed Slice: P3.4g Host Shell Pilot Runbook

P3.4g is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it turns the remaining host-owned pilot
work into one read-only operator artifact before anyone runs conformance,
receipt, or handoff commands.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-runbook.md`

Implemented scope:

1. Added `host-shell-pilot-runbook`, a read-only Runtime Kit CLI.
2. Added `kaka.host_shell_pilot_runbook.v1`, a closed schema with brief, pilot
   target, preflight summary, ordered steps, command artifacts, evidence
   requirements, acceptance gates, and safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   runbook command.
4. Added `runtime-kit/packaging/examples/pilot_runbook.blocked.json`.
5. Reused P3.4f preflight as the only composed status source so the runbook
   does not call `host-shell-pilot-report` or `host-shell-pilot-handoff`.
6. Proved runbook generation does not invoke the private adapter command, run
   conformance, fetch audit refs, mutate host state, submit handoff, or mark
   P3.4 complete.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_runbook` did not exist.
- Focused P3.4g gate passed: `6 passed`.
- Focused Runtime Kit adjacent gate passed: `127 passed`.
- Current local Hermes runbook smoke prints
  `kaka.host_shell_pilot_runbook.v1 blocked False True missing missing_private_adapter_command`.
- P3.4 remains external: `ready_for_conformance` only means the host can run
  the next conformance step, not that the handoff is ready or the external pilot
  is complete.

## Completed Slice: P3.4h Host Shell Pilot Artifact Review

P3.4h is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it reviews already generated pilot JSON
artifacts before an external host review without invoking or rerunning anything.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-artifact-review.md`

Implemented scope:

1. Added `host-shell-pilot-artifact-review`, a read-only Runtime Kit CLI.
2. Added `kaka.host_shell_pilot_artifact_review.v1`, a closed schema with
   artifact load/schema summaries, consistency checks, release review gates, and
   safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   artifact review command.
4. Added `runtime-kit/packaging/examples/pilot_artifact_review.blocked.json`.
5. Checked preflight, conformance, receipt, and handoff JSON artifacts for
   runtime alignment, embedded conformance summary, embedded receipt command,
   audit-ref completeness, private command consistency, and synthetic
   conformance blocking.
6. Proved artifact review does not invoke the private adapter command, run
   conformance, fetch audit refs, mutate host state, submit handoff, or mark
   P3.4 complete.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_artifact_review` did not exist.
- Focused P3.4h gate passed: `6 passed`.
- Focused Runtime Kit adjacent gate passed: `132 passed`.
- Broad Python gate passed: `437 passed`.
- Current missing-artifact smoke prints
  `kaka.host_shell_pilot_artifact_review.v1 blocked False missing_artifact:preflight,missing_artifact:conformance,missing_artifact:receipt,missing_artifact:handoff`.
- P3.4 remains external: `ready_for_external_review` only means the generated
  artifacts are internally consistent for external host review, not that the
  external pilot is complete.

## Completed Slice: P3.4i Host Shell Pilot Request Bundle

P3.4i is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it creates the machine-readable request
that tells the external host team exactly which materials to provide before the
pilot can move through preflight, conformance, receipt, handoff, and artifact
review.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-request-bundle.md`

Implemented scope:

1. Added `host-shell-pilot-request`, a read-only Runtime Kit CLI.
2. Added `kaka.host_shell_pilot_request.v1`, a closed schema with pilot request
   metadata, target host discovery expectations, required action IDs,
   required capabilities, host deliverables, audit refs, Runtime Kit artifact
   expectations, acceptance gates, and safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   request command.
4. Added `runtime-kit/packaging/examples/pilot_request.hermes.json`.
5. Listed required host-owned materials: private adapter command binary,
   request/response contract acknowledgement, 9-action matrix, native
   distribution channel, signature/notarization evidence, update feed,
   install/update/failure-recovery drill receipts, release notes, and audit
   refs.
6. Proved request generation does not invoke the private adapter command, run
   preflight or conformance, read pilot artifacts, fetch audit refs, mutate host
   state, submit handoff, expose phone `/mobile/v1`, or mark P3.4 complete.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_request` did not exist.
- Focused P3.4i gate passed: `5 passed`.
- Focused Runtime Kit adjacent gate passed: `136 passed`.
- Broad Python gate passed: `441 passed`.
- Current request smoke prints
  `kaka.host_shell_pilot_request.v1 ready_to_send True False 10 5`.
- P3.4 remains external: `ready_to_send` only means the materials request
  package can be sent to the host team, not that any requested material exists
  or that the external pilot is complete.

## Completed Slice: P3.4j Host Shell Pilot Evidence Manifest

P3.4j is implemented in the current working tree. It does not complete the
external Hermes/OpenClaw release pilot; it gives Runtime Kit a read-only,
machine-readable index of the JSON artifacts produced by the host-owned pilot
sequence.

Agent-executable plan:

`docs/superpowers/plans/2026-06-06-kaka-pocket-agents-host-shell-pilot-evidence-manifest.md`

Implemented scope:

1. Added `host-shell-pilot-evidence-manifest`, a Runtime Kit CLI that reads and
   hashes local JSON artifact files only.
2. Added `kaka.host_shell_pilot_evidence_manifest.v1`, a closed schema with
   package metadata, artifact summaries, artifact review summary, archive gates,
   and safety fields.
3. Added Hermes/OpenClaw static manifest declarations and entrypoints for the
   evidence manifest command.
4. Added `runtime-kit/packaging/examples/pilot_evidence_manifest.blocked.json`.
5. Indexed required artifacts: preflight, conformance, pilot receipt, handoff,
   and artifact review. Optional request and runbook JSON may be included when
   supplied.
6. Blocked archive readiness when required artifacts are missing, oversized,
   invalid JSON, schema/surface/runtime mismatched, or `ok: false`.
7. Preserved the P3.4 boundary: the command does not invoke the private adapter,
   run conformance, fetch audit refs, submit handoff, mutate host state, create
   the external archive, expose phone `/mobile/v1`, or mark P3.4 complete.

Completion evidence:

- Builder/CLI TDD red run failed because
  `kaka_mobile_runtime_kit.host_shell_pilot_evidence_manifest` did not exist.
- Additional TDD red run failed because an artifact with `ok: false` was still
  incorrectly allowed to become archive-ready.
- Focused P3.4j gate passed: `7 passed`.
- Adjacent Runtime Kit/P3.4 gate passed: `142 passed`.
- Broad Python gate passed: `447 passed`.
- Missing-artifact CLI smoke prints
  `kaka.host_shell_pilot_evidence_manifest.v1 blocked_missing_artifacts False False missing_artifact:preflight,missing_artifact:conformance`.
- `git diff --check` passed.
- Final read-only multi-agent review found no correctness or safety issue and no
  doc language that treats `ready_for_archive` as P3.4 completion.
- P3.4 remains external: `ready_for_archive` only means local JSON artifacts can
  be archived by the external host shell; Runtime Kit still does not create that
  archive or complete the release pilot.

## Completed Slice: Native Runtime Packaging Scaffold

This slice turns the Runtime Kit settings shell into machine-readable packaging scaffolding without assuming unpublished Hermes/OpenClaw native APIs.

Implemented scope:

1. Add Runtime Kit `package-preview`, a native runtime package shell contract derived from `settings-preview`.
2. Freeze `settings-preview` top-level keys, controls, spawnable actions, no-spawn preview behavior, and phone-safe summary allowlist through pytest.
3. Add `runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json` as a disabled-by-default Hermes shell manifest.
4. Add `runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json` as a disabled-by-default OpenClaw sidecar manifest.
5. Add shared packaging schemas and lifecycle/security documentation under `runtime-kit/packaging/`.
6. Restrict `runtime_http` Recall search endpoints to localhost or private LAN targets by default.
7. Keep runtime store paths, provider endpoints, env/auth files, credentials, bearer/mobile tokens, embeddings, index rows, and raw provider responses out of `phone_safe_summary`.

Completion evidence:

- Focused Runtime Kit packaging tests prove `package-preview`, static manifests, schemas, exact phone-safe allowlist, and no-autostart defaults.
- `settings-preview` and `package-preview` do not spawn the bridge process.
- LAN/Bonjour remain explicit opt-ins and unsafe Bonjour preview is still rejected.
- Production QR/token/TLS work, the `consumer_ui` renderer contract, the `process_ownership` runtime-side contract, and the P2.8 `host-package-preview` handoff are implemented; private Hermes/OpenClaw host adapter binding is the follow-up.

## Completed Slice: App Intents And Live Activity-Safe Task State

This slice adds safe iOS system entry points without turning the phone into an autonomous runtime controller.

Implemented scope:

1. Add `Sources/AgentPocketUI/AppIntents/KakaAppIntents.swift` with foreground App Intents for Inbox and Tasks review surfaces, App Shortcuts metadata, and an `AppIntentsPackage`.
2. Add `ios/AgentPocket/AgentPocketAppIntentsPackage.swift` so the app target exposes the package-defined intents.
3. Add an App Group handoff store and root-tab selection so system invocations open Kaka to Inbox or Tasks.
4. Add `RuntimeTaskActivitySnapshot` and `RuntimeTaskActivityAttributes` with a strict phone-safe field allowlist: `task_id`, client-generated generic `title`, `phase`, and `approval_needed`.
5. Add `RuntimeTaskActivityCoordinating` and ActivityKit adapter hooks from `TaskInboxViewModel`, with no-op fallback for platforms without ActivityKit.
6. Add `NSSupportsLiveActivities` to the app plist while keeping entitlements limited to App Groups.
7. Update API, privacy, README, direction, and roadmap docs to record the system-surface boundary.

Completion evidence:

- Swift tests prove App Intent metadata and safety flags, task activity phase labels, phone-safe snapshot fields, and Task Inbox activity sync decisions.
- Python plist tests prove Live Activity support is declared and no Siri/APNs entitlement was added.
- App Intents are foreground handoff actions only; they do not submit inbox items, approve/cancel tasks, configure providers, collect Context Snapshots, or read hidden inputs.
- WidgetKit lock screen/Dynamic Island presentation is implemented in the completed E.1b follow-up slice.

## Completed Slice: WidgetKit Live Activity Presentation

This slice adds the visible system presentation for the E.1 phone-safe task-state projection without turning system surfaces into task controllers.

Implemented scope:

1. Add `ios/AgentPocketTaskActivityWidget/AgentPocketTaskActivityWidget.swift` with a WidgetKit `WidgetBundle` and `ActivityConfiguration` for `RuntimeTaskActivityAttributes`.
2. Add `ios/AgentPocketTaskActivityWidget/Info.plist` declaring `com.apple.widgetkit-extension` without an extension principal class.
3. Add `RuntimeTaskActivityPhase.shortLabel` so Dynamic Island compact regions use short, safe labels.
4. Wire `AgentPocketTaskActivityWidget.appex` into `ios/AgentPocket.xcodeproj` as an app extension target embedded by the main app.
5. Keep the widget surface limited to `task_id`, client-generated generic title, phase, and approval-needed state; approval and cancellation still happen in the visible Kaka Task Inbox.

Completion evidence:

- Swift tests prove Dynamic Island short labels for queued, running, review, done, fail, and stop states.
- Python plist tests prove the WidgetKit extension point and app embed wiring.
- XcodeBuildMCP simulator build and UI smoke tests pass with the widget extension target included.

## Completed Slice: Action Button Review Handoff

This slice makes Action Button setup safer and more discoverable without creating a hidden execution surface.

Implemented scope:

1. Add Action Button catalog metadata for the two recommended shortcuts: `open_inbox` and `open_tasks`.
2. Add `KakaActionButtonShortcutMetadata` and `KakaSystemSurface.isActionButtonRecommended` so tests can prove only top-level visible review surfaces are recommended.
3. Keep Action Button support on the existing `OpenKakaSurfaceIntent(destination:)` foreground handoff path.
4. Add review-oriented App Shortcut phrases for Inbox and Tasks while preserving user-visible labels and system images.
5. Add an Action Button-named entitlement guardrail proving no Siri/APNs/background entitlement was introduced.

Completion evidence:

- Swift tests prove Action Button catalog metadata, shortcut labels, recommended surfaces, and foreground-only safety flags.
- Python plist tests prove Action Button handoff did not add new entitlements.
- Action Button support reuses Kaka's foreground App Intent handoff and only opens visible Inbox or Tasks review surfaces. It does not submit inbox items, approve or cancel runtime tasks, remember Recall items, collect Context Snapshot data, start microphone or camera capture, configure providers, or change runtime settings in the background.

## B.1 Completed Shape

B.1 is implemented as a phone-owned, transcript-first voice loop:

1. The voice state machine wraps `VoiceCaptureViewModel`.
2. `SystemVoiceTranscriber` uses visible microphone recording plus iOS Speech transcription.
3. The iOS app declares microphone and speech-recognition usage descriptions.
4. `VoiceCaptureView` supports explicit Record, Stop, retry, editable transcript, Cancel, and Send states.
5. The first integration stays inside `ImageConversationView`, where voice transcripts route through the prompt path.
6. `VoiceReplySpeaker` uses system speech synthesis for short explicit replies.
7. The mock bridge advertises `supports_voice_followup: true` without adding raw audio upload.
8. API/privacy/README docs describe on-device transcription, text submission, temporary local audio, and no hidden listening.

B.1 did not add a standalone Voice tab. The existing image-conversation voice sheet gives the smallest complete path for recording, review, submission, and spoken reply. A standalone Voice tab can follow once the real voice primitives have more product mileage.

B.1 execution ownership record:

- Voice state/UI worker: `VoiceCaptureViewModel`, `VoiceCaptureView`, and UI tests.
- Speech adapter worker: `SystemVoiceTranscriber`, `VoiceReplySpeaker`, `Info.plist`, and focused compile/plist checks.
- Conversation integration worker: `ImageConversationViewModel`, `ImageConversationView`, and image-conversation tests.
- Bridge/docs worker: mock bridge capability, API docs, privacy docs, README, and this roadmap.
- Reviewer: microphone privacy boundary, no raw audio upload, transcript editability, test coverage, and XcodeBuildMCP gate.

## Runtime Persistence Execution Record

Implementation order followed:

| Order | Slice | Primary owner | Key paths | Completion signal |
| --- | --- | --- | --- | --- |
| 1 | Baseline and contract freeze | Lead agent | `docs/mobile-bridge-api.md`, `docs/agent-pocket-privacy.md`, existing D.1 tests | D.1 contract remains source-compatible; no Swift UI changes are required for storage work. |
| 2 | Runtime SQLite store | Runtime worker | `runtime-kit/kaka_mobile_runtime_kit/runtime_store.py`, `runtime-kit/tests/test_runtime_store.py` | Recall items, index entries, export payloads, tasks, and task events persist across reopened store instances. |
| 3 | Bridge wiring | Mock bridge worker | `mock_bridge/agent_pocket_mock_bridge/app.py`, `mock_bridge/agent_pocket_mock_bridge/server.py`, `runtime-kit/kaka_mobile_runtime_kit/cli.py` | `--runtime-store-path` starts a bridge whose Recall and Tasks endpoints survive process/app recreation. |
| 4 | Swift contract guard | Swift worker | `Sources/AgentPocketCore`, `Tests/AgentPocketCoreTests` | Existing D.1 request/response tests still pass; only additive model fields are allowed. |
| 5 | Docs and privacy hardening | Docs worker | `docs/mobile-bridge-api.md`, `docs/agent-pocket-privacy.md`, `runtime-kit/README.md`, `README.md`, `README.zh-CN.md`, `docs/pocket-agents-direction.md`, `docs/kaka-pocket-agents-next-development-plan.md` | Public docs say Recall/task persistence is runtime-owned, opt-in, locally stored, exportable, and erasable. |
| 6 | Review and gates | Reviewer agent | Full repo | Swift, Python, doctor, plist, diff, and XcodeBuildMCP gates pass where applicable. |

Multi-agent split used:

- Runtime worker owns `runtime-kit/kaka_mobile_runtime_kit/runtime_store.py` and runtime-kit tests.
- Bridge worker owns mock bridge integration and CLI/server flags.
- Swift worker owns source-compatible contract checks only; no UI redesign in this slice.
- Reviewer agent checks API drift, deletion semantics, restart behavior, privacy boundaries, and test coverage.

Execution defaults preserved by the slice:

- Use SQLite in Runtime Kit as the default local store before Hermes/OpenClaw-specific packaging.
- Treat `--runtime-store-path` as the development opt-in that enables store-backed Recall and task behavior. It must not become a phone API field.
- Keep `GET /mobile/v1/recall/items?query=...&limit=...` for simple search.
- Keep export JSON-only for P1.1/P1.2; copied/redacted artifacts can wait until artifact retention policy exists.
- Keep provider-backed retrieval behind `POST /mobile/v1/recall/search`; the phone must not configure provider endpoints or receive provider internals.
- Do not persist Context Snapshot content into Recall unless a user explicitly confirms a Recall action.

## Execution Boundaries

Keep these boundaries intact:

- The iPhone never stores model-provider keys.
- Recall remains opt-in. No automatic remembering of Inbox, image conversation, or Context Snapshot content.
- Search/browse may list remembered metadata, but runtime owns storage, embeddings, retrieval index, and deletion receipts.
- Export must be explicit and user-triggered.
- Runtime task state and task events remain runtime-owned. The phone displays task state from Mobile Bridge and does not become the durable task database.
- App Intents remain foreground handoff actions unless a later plan adds visible, freshly confirmed execution.
- Live Activity state remains a phone-safe projection and must not include task logs, provider settings, asset bytes, Context Snapshot fields, Recall internals, tokens, endpoints, or runtime store paths.
- Production persistence work must not introduce hidden cloud storage, provider keys on iPhone, passive remembering, or automatic Context Snapshot retention.

## Validation Gates

Run these before marking a phase complete:

```bash
swift test
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge \
  python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
plutil -lint ios/KakaShareExtension/Info.plist \
  ios/KakaShareExtension/KakaShareExtension.entitlements \
  ios/AgentPocketTaskActivityWidget/Info.plist \
  ios/AgentPocket/Info.plist \
  ios/AgentPocket/AgentPocket.entitlements \
  ios/AgentPocket.xcodeproj/project.pbxproj
git diff --check
```

Before iOS target, plist, entitlement, App Intent, ActivityKit, WidgetKit, SwiftUI, or UI smoke changes, configure and use XcodeBuildMCP:

```text
session_show_defaults
discover_projs(workspaceRoot: "/Users/kartz/Development/Kaka", scanPath: "/Users/kartz/Development/Kaka", maxDepth: 4) when defaults are missing
list_schemes(projectPath: "/Users/kartz/Development/Kaka/ios/AgentPocket.xcodeproj")
list_sims(enabled: true)
session_set_defaults(projectPath: "/Users/kartz/Development/Kaka/ios/AgentPocket.xcodeproj", scheme: "AgentPocket", simulatorName: "iPhone 17", simulatorId: "52C38F02-6CCF-4FCA-A135-E5F30601B7DF", simulatorPlatform: "iOS Simulator", persist: false)
build_sim(extraArgs: ["-skipMacroValidation"])
test_sim(progress: false, extraArgs: ["-skipMacroValidation"])
```

## Open Decisions

- Production provider-backed retrieval adapter shape: P3.21 now provides readiness strategies for Hermes/OpenClaw-native embeddings, sidecar adapters, and capability-negotiated hybrids, but the actual production choice and provider package remain host/runtime-owned.
- Recall export artifact policy: P3.20 resolves the JSON-only first step with `kaka.recall_export.v1`, shared Runtime Kit sanitization, and a closed schema. Decide later whether copied/redacted files belong in a separate export artifact once asset retention is defined.
- Embedding provider: deterministic local scoring and runtime-owned provider adapter hooks are implemented. Production embeddings remain runtime-owned and should stay outside the phone contract.
- Voice transcription owner: B.1 is on-device Speech first. Runtime-side transcription should be a separate capability-negotiation slice if a provider-owned audio path becomes necessary.
- Voice-to-Inbox P3.30: implemented as a phone-owned draft creation flow first. The reviewed transcript becomes a pending text Inbox item with voice provenance; runtime execution still waits for visible Inbox `Send`. Audio upload, background microphone, standalone Voice tab, and runtime-side transcription remain separate future decisions.
- Inbox Voice Instruction P3.32: implemented as a phone-owned note update on
  existing universal-intake Inbox items. The reviewed transcript becomes
  `KakaInboxItem.note` and is sent only through existing universal intake after
  visible `Send`; P3.33 now adds edit/clear controls and submit-preview polish
  without adding new endpoints or audio transport.
- Context Snapshot P3.29: implemented as one-shot, permission-gated current motion and next-30-minute calendar availability on top of C.1b's network-only coarse path status. It does not add background collection, motion history, calendar event details, new bridge fields, or automatic Recall writes.
- Local renderer backend readiness: P3.16 is implemented as a runtime-side `local-renderer-backend-readiness` contract that proves the existing `recipe_local` PIL renderer path with a synthetic local probe. It does not add a phone API, cloud image provider path, persistent asset storage, or new renderer backend dependency.
- Photo edit capability truth: P3.17 aligns the default local `photo_edit`
  capability to `return_variants_max: 2`; P3.17b aligns default
  `photo_edit.accepted_mime_types` to `["image/jpeg"]`. Generic asset upload,
  vision, image intake, and universal intake stay broad.
- External Hermes/OpenClaw host-shell pilot: P3.3 defines command binary naming, install/update channel metadata, signature policy, and conformance gates inside Runtime Kit packaging contracts. P3.4a through P3.4j now cover the pilot receipt, command discovery, authoring docs/examples, optional audit refs, submit-ready handoff bundle, preflight, operator runbook, post-run artifact review, host-team materials request, and evidence manifest. P3.4 now waits on an actual host-owned Hermes/OpenClaw binary and native distribution channel outside this repository; adding another repo-only wrapper/checklist would not advance the release proof.
- Pilot host selection: decide whether the first real external dogfood target is Hermes or OpenClaw, then provide the binary path or discovery source, native distribution channel ref, signature subject/notarization team ref, update-feed ref, install/update/failure drill receipt refs, release notes ref, conformance report, generated P3.4i request package, and generated P3.4j evidence manifest for `host-shell-pilot-handoff` and external archive review.
- Host extension distribution details: P3.5 now defines the Runtime Kit `host-extension-preview` contract, schema, manifest metadata, and ordinary-user install boundary. P3.6 now consumes exact Hermes Plugin and OpenClaw Skill/sidecar install commands, update channel names, bundled adapter command locations, host UI entry points, signed package refs, signature/notarization refs, P3.2 conformance report refs, and P3.4 evidence manifest refs through a read-only `host-extension-readiness` contract. P3.12 now adds `host-extension-starter-kit` so host teams can generate safe starter packages while external materials are still blocked. P3.19 now strengthens the P3.13 install-package handoff with host UI acceptance, ordered install drill, evidence receipts, and release gates. The 2026-06-07 audit shows both Hermes and OpenClaw are still blocked on all eight P3.7 inputs. The external host teams still need to provide real values before an external install drill can report ready; use `docs/kaka-host-extension-external-materials.md` as the external handoff. The ordinary-user answer should remain "install the plugin/skill and scan QR," not "write a command and export an environment variable."
- Follow-up installation slice shape: P3.35 Host-Native Plugin/Skill
  Installation Blueprint now improves package manifest, host UI, lifecycle
  receipt, and evidence-gate clarity for Hermes/OpenClaw teams while staying
  read-only/generative. It did not become a public Codex plugin/skill, install a
  package, write Codex user-home roots, start the bridge, invoke private
  adapters, or change `/mobile/v1`.
- Host Plugin/Skill Developer Kit shape: P3.15 resolved this as a Runtime Kit
  `host-plugin-skill-devkit` command plus template-only Codex automation
  materials. It does not ship a live Codex plugin/skill or marketplace entry.
  The ordinary-user install surface stays host-native and plugin/skill-based;
  manual adapter command authoring remains a host-team development fallback only.
- Local TLS readiness and pinning: P3.8 now defines the Runtime Kit `local-tls-readiness` contract for non-secret certificate label/ref, public-key fingerprint, expiry, trust store ref, and renewal procedure ref. P3.10a serves local HTTPS with host-owned certificate files, and P3.10b carries the public-key fingerprint into iOS pinning. Certificate creation, trust installation, renewal, and private key storage remain host-owned work.

## Resolved Decisions

- Runtime Recall storage starts with Runtime Kit SQLite behind `--runtime-store-path`; it is not a phone API field.
- B.1 voice transcription starts on device with iOS Speech and sends editable text through Mobile Bridge; raw microphone audio is not uploaded.
- P3.30 reuses B.1 voice primitives for Inbox draft creation before adding any broader voice surface.
- P3.32 reuses B.1 voice primitives for attaching instructions to existing
  universal-intake Inbox items. The reviewed transcript is stored in
  `KakaInboxItem.note` and sent only after visible Inbox `Send` as existing
  `note`/`user_instruction` text; it does not create a raw-audio bridge path,
  hidden recording path, automatic runtime submit, automatic Recall write, App
  Intent recorder, or Host Extension packaging change.
- Semantic Recall starts with deterministic runtime-owned local scoring behind `POST /mobile/v1/recall/search`; raw embeddings and index rows are not returned to iPhone.
- Provider-backed Recall retrieval now plugs into that same endpoint through Runtime Kit provider adapters; mobile search responses are allowlisted to `item`, `score`, and `match_reason`.
- Context Snapshot C.1 includes battery/network/motion/location/calendar status or permission sentinels, refreshed per task and runtime-gated; C.1b upgrades network to a one-shot coarse path probe, and P3.29 upgrades motion/calendar to one-shot current-state and busy-window probes without changing `/mobile/v1`.
- Native runtime packaging starts with shared Runtime Kit `settings-preview`/`package-preview`/`host-package-preview`, static Hermes/OpenClaw manifests, and no-autostart defaults rather than host-specific private APIs.
- Production pairing starts with Runtime Kit-owned short-lived QR sessions, revocable mobile tokens, trusted local TLS metadata, and development `pair_dev` compatibility rather than a phone-owned runtime settings database.
- Hermes/OpenClaw consumer runtime UI starts with `settings_preview.runtime_side_ui.consumer_ui`, and process lifecycle starts with `settings_preview.runtime_side_ui.process_ownership`, both derived from Runtime Kit settings/package preview rather than a second host-specific settings source.
- P3 sequencing starts with ordinary-user end-to-end connection QA and host adapter readiness, then P3.1 lands as a host-private command bridge contract, then P3.2 lands conformance evidence for host-owned commands, then P3.3 extends `host-package-preview` with a runtime-side `private_adapter_package` contract for host-owned command binaries. P3.4a through P3.4j add `host-shell-pilot-report`, explicit/env/manifest/well-known command discovery, external authoring docs/examples, optional audit refs, `host-shell-pilot-handoff`, `host-shell-pilot-preflight`, `host-shell-pilot-runbook`, `host-shell-pilot-artifact-review`, `host-shell-pilot-request`, and `host-shell-pilot-evidence-manifest`. P3.4 remains queued for external host-shell dogfood with a real Hermes/OpenClaw binary outside this repository. P3.5 resolves the user-facing install shape by making Hermes Plugin / OpenClaw Skill the ordinary-user entry point and keeping manual adapter commands as developer/pilot fallback only. P3.6 adds a read-only Host Extension distribution readiness contract for real Plugin/Skill package facts and schema hardening before an external install drill. P3.12 and P3.13 make host-team starter and install-package handoff artifacts available while external facts are blocked. P3.14 adds explicit runtime retention purge receipts. P3.15 adds the template-only Host Plugin/Skill Devkit for repeatable host extension packaging support and optional Codex developer automation materials. P3.16/P3.17/P3.17b cover local renderer readiness and default photo-edit capability truth. P3.18 now adds source-only Host Codex developer plugin generation without making Codex the ordinary-user installer. P3.19 now strengthens the existing install-package handoff with acceptance-grade host UI, drill, evidence, and release-gate artifacts. P3.20 now makes Recall export policy-labeled and machine-verifiable, P3.21 now adds read-only production Recall retrieval packaging readiness without changing `/mobile/v1/recall/search`, P3.22 now makes mock bridge input/output asset purge receipts timestamp-aware without adding phone-triggered cleanup, P3.23 now makes Context Snapshot permission states readable without changing payload contracts, P3.24 now persists input/output assets in Runtime Kit SQLite when configured while preserving explicit runtime-side purge only, P3.25 now persists phone-safe store-backed photo-edit result details, P3.26 now adds local Recall retrieval material intake/review without fetching refs or invoking providers, P3.27 now adds local renderer backend capability planning without installing or executing future backends, P3.28 adds host-extension materials review for real package facts, P3.29 adds one-shot motion/calendar Context Snapshot sampling, P3.30 adds Voice-to-Inbox Draft, P3.31 is the install-package quickstart/user-journey acceptance refinement that keeps the ordinary-user path host-native, P3.32 adds Inbox Voice Instruction on existing universal-intake items through the current `note`/`user_instruction` path, P3.33 adds local edit/clear plus send-preview polish for those instructions, P3.34 adds deterministic Inbox instruction templates / action chips, P3.35 adds the host-native Plugin/Skill installation blueprint to the existing install-package handoff, P3.36a adds context-specific Inbox voice capture copy without behavior changes, P3.36b adds explicit Paste-to-Inbox with one-shot pasteboard text import and visible Inbox Send, P3.37 adds result-banner provenance for explicit Recall actions after successful Inbox submission, P3.38 adds explicit one-shot Files-to-Inbox import before visible Send, P3.39 adds local pending-item Discard before visible Send, P3.40 adds visible confirmation before the local pending-item Discard path executes, P3.41 renders existing failed/submitting Inbox state as local visible action feedback, and P3.42 adds local row-level pending item Review Details before visible Send.
- If a real host package candidate bundle arrives, review it through P3.28, rerun P3.6 readiness, then run P3.7. If installation remains blocked, do not build another install wrapper; choose the next separately permissioned product slice.
