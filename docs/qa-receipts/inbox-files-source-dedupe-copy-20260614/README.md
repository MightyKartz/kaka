# Inbox Files Source Dedupe Copy QA

Date: 2026-06-14
Branch: `codex/inbox-files-source-dedupe-copy`

## Scope

- Polished Inbox pending item Review Details source copy for Files imports.
- Files-picked items now show `Files` instead of the duplicated `Files from Files`.
- Other source app provenance remains visible when it adds information, such as `Paste from Safari`.
- No Mobile Bridge, runtime, provider, Recall, upload, App Intent, Host Extension, or real-device behavior changed.

## TDD Evidence

- Red: `swift test --filter InboxPendingItemReviewPresentationTests` failed because the Files import source row returned `Files from Files`.
- Green: the same focused suite passed after suppressing duplicate source app copy.

## Verification

- `swift test --filter InboxPendingItemReviewPresentationTests`: 6 tests, 0 failures.
- `swift test`: 460 tests, 0 failures.
- `git diff --check`: passed with empty output.

## Logs

- `swift-test-inbox-pending-review-presentation.log`
- `swift-test.log`
- `git-diff-check.log`

## Residual Risk

- This is a presentation-copy unit-test slice. No simulator screenshot or real-device hardware path was exercised.
