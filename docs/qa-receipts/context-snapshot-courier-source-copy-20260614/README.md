# Context Snapshot Courier Source Copy QA

Date: 2026-06-14
Branch: `codex/context-snapshot-courier-source-copy`

## Scope

- Polished the Context Snapshot preview Source row for explicit Paste and Files courier surfaces.
- `paste` renders as `Paste`; `file_picker` and `document_picker` render as `Files`.
- No Mobile Bridge, runtime, provider, Recall, upload, App Intent, Host Extension, or real-device behavior changed.

## TDD Evidence

- Red: `swift test --filter ContextSnapshotViewModelTests/testPreviewRowsUseInboxFacingCourierSourceNames` failed with two expected assertions because `file_picker` and `document_picker` did not render as `Files`.
- Green: the same focused test passed after adding the local source copy mapping.

## Verification

- `swift test --filter ContextSnapshotViewModelTests`: 16 tests, 0 failures.
- `swift test`: 460 tests, 0 failures.
- `git diff --check`: passed with empty output.

## Logs

- `swift-test-context-snapshot-view-model.log`
- `swift-test.log`
- `git-diff-check.log`

## Residual Risk

- This is a presentation-copy unit-test slice. No simulator screenshot or real-device hardware path was exercised.
