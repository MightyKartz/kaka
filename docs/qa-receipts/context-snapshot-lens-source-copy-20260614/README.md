# Context Snapshot Lens Source Copy QA

Date: 2026-06-14
Branch: `codex/context-snapshot-lens-source-copy`

## Scope

- Polished the Context Snapshot preview Source row for Local Agent Lens source surfaces.
- `agent_scanner`, `document_scanner`, and `video_capture` now render as user-facing names instead of generic prettified bridge strings.
- No Mobile Bridge, runtime, provider, Recall, upload, App Intent, or Host Extension behavior changed.

## TDD Evidence

- First attempted red run hit a local SwiftPM test-bundle code-signature cache issue before assertions; `swift package clean` cleared generated build artifacts.
- Red: `swift test --filter ContextSnapshotViewModelTests/testPreviewRowsUseUserFacingLocalAgentLensSources` then failed because the preview did not contain `Scanner`, `Document Scan`, or `Video`.
- Green: `swift test --filter ContextSnapshotViewModelTests` passed after adding the local source copy mapping.

## Verification

- `swift test --filter ContextSnapshotViewModelTests`: 15 tests, 0 failures.
- `swift test`: 459 tests, 0 failures.
- `git diff --check`: passed with empty output.

## Logs

- `swift-test-context-snapshot-view-model.log`
- `swift-test.log`
- `git-diff-check.log`

## Residual Risk

- This is a presentation-copy unit-test slice. No simulator screenshot or real-device hardware path was exercised.
