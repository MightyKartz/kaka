# Kaka Pocket Agents Post-E0 Development Plan

Updated: 2026-06-05

This document records the next development direction after the current Pocket Agents foundation work. It is based on code-first analysis of the working tree, not only on earlier roadmap text.

Detailed agent-executable plan:

`docs/superpowers/plans/2026-06-05-kaka-pocket-agents-post-e0.md`

That detailed plan follows the `superpowers:writing-plans` format. It is stored under `docs/superpowers/`, which this repository treats as local planning workspace, so this tracked document is the durable project-level roadmap.

## Skills And MCP Used

- `project-codebase-onboarding-and-roadmap`: code-first project analysis, doc drift detection, module/risk map.
- `superpowers:writing-plans`: agent-executable task plan format.
- XcodeBuildMCP: project discovery and iOS validation planning.
  - Project: `/Users/kartz/Development/Kaka/ios/AgentPocket.xcodeproj`
  - Main scheme: `AgentPocket`
  - Available iOS simulator target used for planning: `iPhone 17`, iOS 26.5, `52C38F02-6CCF-4FCA-A135-E5F30601B7DF`

## Current Implementation Truth

Kaka is no longer only an image-intake MVP. The working tree now contains:

- Swift Mobile Bridge support for generic asset uploads and universal intake.
- `KakaShareExtension` with App Group inbox capture for text, URL, image, and PDF payloads.
- App-side Inbox UI and submission logic.
- PDF upload from a visible main-app Inbox action.
- Transcript-first voice follow-up skeleton in the image conversation flow.
- Context Snapshot contract and Inbox preview, defaulting off per task and sent only when the runtime advertises support.
- Recall D.0 explicit actions: `remember`, `use_once`, and `forget` with Swift models, Mobile Bridge client methods, mock bridge endpoints, visible confirmation UI, and Inbox result entry point.
- Runtime Task Inbox E.0: Swift task models, connected Tasks tab, and mock bridge list/cancel/approval endpoints.
- Deterministic tests for Swift models/ViewModels, mock bridge behavior, plist/entitlements, and iOS UI smoke.

Still not implemented:

- Real microphone recording, Speech framework transcription, and spoken replies.
- Rich Context Snapshot collectors for battery, network, motion, calendar availability, or coarse/precise location.
- Recall D.1 browse/search/retrieve/export and production retrieval-index deletion.
- App Intents, Live Activity, widgets, and Action Button surfaces.
- Production runtime persistence for Recall and runtime tasks.
- Consumer-ready Hermes/OpenClaw plugin packaging.

## Module Map

| Area | Key paths | Responsibility | Current risk |
| --- | --- | --- | --- |
| Swift Core | `Sources/AgentPocketCore` | Mobile Bridge models, uploads, universal intake, Recall, runtime task models | API drift if mock/runtime contracts diverge from Swift request builders |
| SwiftUI | `Sources/AgentPocketUI` | Capture, Inbox, voice skeleton, Context Snapshot preview, Recall actions, Task Inbox | Tab growth and action surfaces can become hard to scan without a navigation hierarchy |
| iOS targets | `ios/AgentPocket.xcodeproj`, `ios/AgentPocket`, `ios/KakaShareExtension` | App target, Share Extension, entitlements, UI smoke tests | App Intents/ActivityKit will add entitlement and target complexity |
| Runtime/mock | `mock_bridge`, `runtime-kit` | Deterministic Mobile Bridge behavior and local runtime launcher | Mock in-memory stores prove contracts but not production persistence |
| Docs | `docs/mobile-bridge-api.md`, `docs/pocket-agents-direction.md`, `docs/agent-pocket-privacy.md` | API contract, product direction, privacy boundary | README and roadmap language can lag behind implemented slices |
| Tests | `Tests`, `mock_bridge/tests`, `ios/tests`, `ios/AgentPocketPickerUITests` | Swift, Python, plist, and iOS UI smoke validation | System UI tests should avoid simulator content assumptions |

## Recommended Next Roadmap

| Priority | Phase | Theme | Why now | Exit criteria |
| --- | --- | --- | --- | --- |
| P1 | D.1 | Recall browse/search/retrieve/export foundation | D.0 can remember items, but the memory loop is incomplete until the user can find, inspect, export, and erase them with provenance. | Kaka has a Recall tab or browse surface; search filters remembered items; delete removes content and retrieval-index pointers in the contract; export returns a user-visible package. |
| P1 | Runtime | Production Recall/task persistence | Mock stores are deterministic but ephemeral. Runtime-owned memory and task state need durable local persistence before user trust work expands. | Runtime Kit or Hermes/OpenClaw-compatible sidecar stores Recall/task records locally with deletion receipts. |
| P1 | B.1 | Real push-to-talk voice | The transcript skeleton proves UI shape, but Pocket Agents needs real recording/transcription to feel alive. | User can record, review/edit transcript, submit, and hear a short reply without hidden listening. |
| P2 | C.1 | Rich Context Snapshot collectors | Current context is intentionally minimal. Battery/network/motion/source metadata can improve responses without passive surveillance. | Snapshot preview shows every field; denied permissions do not block intake; no snapshot persists without Recall confirmation. |
| P2 | E.1 | App Intents and Live Activity | System surfaces should come after in-app task state and approval semantics are stable. | Safe intake/task commands appear in Shortcuts/Siri/Spotlight; long-running jobs can expose Live Activity when appropriate. |
| P2 | Runtime Kit | Consumer plugin packaging | Users should not run manual bridge commands forever. | Hermes/OpenClaw flow can enable Kaka Mobile Bridge, show short-lived QR, and opt into LAN/Bonjour explicitly. |
| P3 | Docs/UX | README and native UI consolidation | Product state has advanced faster than the top-level story. | README, API docs, privacy docs, and native tabs agree on what exists now and what remains planned. |

## Recommended First Execution Slice

Start with Recall D.1 browse/search/export foundation.

Reasoning:

- It builds directly on the implemented D.0 contracts instead of opening a new permission-heavy subsystem.
- It makes the local-first trust promise tangible: users can see what was remembered, search it, export it, and delete it.
- It forces the runtime contract to clarify retrieval-index deletion before production persistence hardens around the wrong shape.
- It can be built and tested through Swift unit tests plus mock bridge tests without needing real microphone permissions or App Intents entitlement work.

## Execution Boundaries

Keep these boundaries intact:

- The iPhone never stores model-provider keys.
- Recall remains opt-in. No automatic remembering of Inbox, image conversation, or Context Snapshot content.
- Search/browse may list remembered metadata, but runtime owns storage, embeddings, retrieval index, and deletion receipts.
- Export must be explicit and user-triggered.
- App Intents and Live Activity wait until D.1 and runtime task persistence are stable.

## Validation Gates

Run these before marking a phase complete:

```bash
swift test
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge \
  python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit doctor
plutil -lint ios/KakaShareExtension/Info.plist \
  ios/KakaShareExtension/KakaShareExtension.entitlements \
  ios/AgentPocket/AgentPocket.entitlements \
  ios/AgentPocket.xcodeproj/project.pbxproj
git diff --check
```

Before iOS target, entitlement, App Intent, ActivityKit, or UI smoke changes, configure and use XcodeBuildMCP:

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

- Recall D.1 endpoint shape: keep `GET /mobile/v1/recall/items?query=...` for simple search, or add a separate `POST /mobile/v1/recall/search` for richer retrieval filters.
- Export shape: JSON-only first, or JSON plus copied/redacted artifacts.
- Voice transcription owner: on-device Speech first, runtime-side first, or runtime capability negotiation for both.
- Context collectors: which of battery, network, motion, location, and calendar should be included in C.1.
- Runtime packaging: Hermes plugin first, OpenClaw sidecar first, or Runtime Kit default store first.
