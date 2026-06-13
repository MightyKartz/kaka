# Kaka Agent Guide

This file is the first stop for Codex, Claude, and other agentic workers in this repository.

## Required First Reads

1. Read `docs/KAKA-DEVELOPMENT-CHARTER-2026-06-13.md`.
2. Read the latest entries in `docs/PROGRESS.md`.
3. For API or runtime contract changes, read `docs/mobile-bridge-api.md`.
4. For product positioning, read `PRODUCT.md` and `docs/pocket-agents-direction.md`.

If older docs conflict with the charter, follow the charter. If the Mobile Bridge API conflicts with a proposed change, update or review the API contract first.

## Current Product Direction

Kaka is a local-first iPhone front end for user-owned agent runtimes such as Hermes and OpenClaw.

The current main line is **Local Agent Lens**:

- local Wi-Fi / LAN connection first;
- QR / Bonjour / Mobile Bridge `/mobile/v1` as the normal runtime path;
- phone-native actions: capture, scan, document scan, short video intake, voice, Share, Paste, Files, Inbox, Recall controls, task approvals, Live Activities, and Dynamic Island status;
- Hermes/OpenClaw/runtime owns model credentials, routing, tools, memory, task state, and retention.

Do not turn Kaka into a generic chat client, a cloud relay, or a public-internet remote desktop path unless the user explicitly changes the product direction.

## Hard Confirmation Lines

Wait for explicit user confirmation before:

- spending real money or calling paid providers/cloud services;
- deploying to cloud, App Store, TestFlight, or production;
- deleting user data, runtime stores, Recall data, installed apps, or unrelated files;
- changing model IDs, provider routing, fallback chains, or profile-persisted secrets;
- installing, signing, publishing, updating, or uninstalling real Hermes/OpenClaw Host Extension packages;
- performing sensitive real-device actions beyond the user-requested dev app install/run flow.

## Default Allowed Work

You may proceed without extra confirmation when the action is local, reversible, and free:

- edit code, tests, and docs on the current branch;
- run local tests, lint, SwiftPM, pytest, Xcode local builds, and mock/runtime-kit smoke tests;
- start local development bridges for verification;
- install and launch the current Kaka dev app on the already connected test iPhone when the user asks for real-device testing;
- update `docs/PROGRESS.md` after meaningful decisions, implementation slices, and QA.

## Development Discipline

- Keep changes scoped to the current user request and the current charter milestone.
- Prefer small, testable slices over broad refactors.
- Do not ask ordinary users to paste long `runtime-kit` commands, export env vars, write adapter code, or install Codex skills/plugins as the normal Kaka setup path.
- Keep Share, Paste, Files, Voice, Scanner, Document, Video, Recall, and Context Snapshot flows visible and user-confirmed before runtime submission.
- Do not silently upload content, poll the pasteboard, record in the background, or write Recall automatically.
- Host Extension work and Local Agent Lens work should remain separate slices.
- Update `docs/PROGRESS.md` after each completed slice.

## Verification Commands

Swift changes:

```bash
swift test
```

Runtime Kit / mock bridge / photo-pack / iOS source guard changes:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=runtime-kit:mock_bridge \
python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
```

iOS generic build:

```bash
xcodebuild -project ios/AgentPocket.xcodeproj \
  -scheme AgentPocket \
  -destination 'generic/platform=iOS' \
  -skipMacroValidation build
```

Real-device install is allowed only when the user asks for it. Current test device:

```text
iPhone 16 Plus
UDID: 00008140-000835003EEB001C
Bundle: com.kartz.agentpocket.dev
```

## Important Paths

- `Sources/AgentPocketCore/`: Mobile Bridge models, requests, trust, uploads, runtime tasks, Recall, Inbox models.
- `Sources/AgentPocketUI/`: SwiftUI screens, connection flow, capture, Inbox, Recall, voice, App Intents, Live Activity coordination.
- `ios/`: iOS app target, Share Extension, WidgetKit Live Activity target, project files.
- `mock_bridge/`: deterministic local bridge and provider behavior for QA.
- `runtime-kit/`: bridge launcher, Hermes/OpenClaw packaging scaffold, runtime-side tooling.
- `docs/qa-receipts/`: screenshots, logs, and real-device/runtime QA evidence.

## Current Default Next Step

Unless the user redirects, continue the Local Agent Lens plan:

`docs/superpowers/plans/2026-06-13-kaka-local-agent-lens.md`

Start with the smallest contract and UI slices, verify locally, then real-device QA when requested.
