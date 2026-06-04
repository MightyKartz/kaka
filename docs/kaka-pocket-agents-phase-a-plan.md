# Kaka Pocket Agents Phase A Development Plan

Updated: 2026-06-05

This document is the project-level handoff for the next Kaka development slice. The detailed task-by-task agent plan is saved at:

`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-phase-a.md`

That detailed plan lives under `docs/superpowers/`, which is ignored by git in this repository, so this tracked document records the durable project direction and verification gates.

## Current Truth

Kaka currently has a working image-first loop:

1. iPhone captures or selects a photo.
2. The app uploads the image to Mobile Bridge.
3. The runtime starts `image_intake`.
4. The app opens an image conversation with suggested skills.
5. Skill taps or typed requests route to `photo_edit` or `vision`.
6. Results render locally on the phone.

The Pocket Agents direction is broader, but not yet implemented. Share Extension, App Group inbox storage, voice transcription, Context Snapshot, Recall, App Intents, and Live Activity are still future work.

## Phase A Goal

Build the first Pocket Agents slice:

- Share text, URL, image, screenshot, and PDF items to Kaka.
- Store shared items in an explicit App Group inbox.
- Add a universal `/mobile/v1/tasks/intake` contract for non-image inputs.
- Preserve the existing `image_intake` image conversation path for shared images and screenshots.
- Show pending inbox items in the connected app and submit them to the local runtime only after visible user intent.

## Implementation Plan

1. Baseline hygiene
   - Confirm dirty worktree state.
   - Keep unrelated user edits.
   - Run Swift, Python, and Runtime Kit doctor checks.

2. Universal intake contract
   - Add Swift core models for `UniversalIntakeKind`, `UniversalIntakeTaskRequest`, `UniversalIntakeResult`, and suggestions.
   - Decode `tasks.image_intake`, `tasks.intake`, and `TaskStatusResponse.intake`.
   - Add `/mobile/v1/tasks/intake` request builders and HTTP client method.

3. Mock Bridge/runtime support
   - Advertise `intake` capability.
   - Add `POST /mobile/v1/tasks/intake`.
   - Return deterministic summaries and suggestions for text, URL, screenshot, image, and PDF.
   - Document the tested API in `docs/mobile-bridge-api.md`.

4. App Group inbox storage
   - Add `KakaInboxItem`.
   - Add `FileKakaInboxStore`.
   - Keep storage explicit and local.

5. iOS Share Extension
   - Add a `KakaShareExtension` target.
   - Use the proposed development App Group `group.dev.kartz.Kaka` unless signing requires a different value.
   - Capture the first supported shared item.
   - Write it to the inbox store.
   - Do not upload from the extension.

6. Main app Inbox UI
   - Add `InboxViewModel` and `InboxView`.
   - Submit non-image items through universal intake.
   - Submit image/screenshot items through the existing image intake path.
   - Keep voice as a visible future capability, not a hidden implementation.

7. Verification and receipts
   - Run `swift test`.
   - Run Python tests across `runtime-kit`, `mock_bridge`, `photo-pack`, and `ios/tests`.
   - Use XcodeBuildMCP for simulator validation after Share Extension target wiring.
   - Record `docs/qa-receipts/pocket-agents-phase-a-latest.json`.

## Required Tooling

- `project-codebase-onboarding-and-roadmap`: use when reconciling docs with code reality.
- `superpowers:writing-plans`: used to create the detailed task plan.
- `superpowers:test-driven-development`: use before implementation tasks.
- `superpowers:subagent-driven-development` or `superpowers:executing-plans`: use when starting execution.
- `superpowers:verification-before-completion`: use before marking Phase A complete.
- XcodeBuildMCP: use `session_show_defaults` before simulator build/test calls.
- `multi_agent_v1`: optional, only after explicit approval for subagent-driven work.

## Confirmation Gates

- Confirm App Group identifier before touching entitlements and Xcode project settings.
- Confirm whether PDF is public in Phase A or development-only.
- Confirm whether external branding remains Kaka while Pocket Agents is the product category.
- Confirm voice transcription direction before Phase B: on-device, runtime-side, or capability-negotiated.

## Roadmap After Phase A

| Phase | Theme | Exit criteria |
| --- | --- | --- |
| B | Voice-first Conversation | Push-to-talk, editable transcript, short spoken reply, no hidden transcription |
| C | Permissioned Context Snapshot | User previews task-scoped context; denied permissions do not block intake |
| D | Recall v0 | Remember, Use Once, Forget, provenance, search, delete, export |
| E | Task Inbox, App Intents, Live Activity | Long-running jobs are visible and controllable from iPhone |

## Validation Commands

```bash
swift test
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge \
  python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
```
