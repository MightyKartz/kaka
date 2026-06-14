# Inbox Result Source Copy QA

Date: 2026-06-14

Branch: `codex/inbox-result-source-copy`

## Scope

- Extracted Inbox completed-result banner copy into `InboxResultPresentation`.
- Kept the existing title, summary, and Context Snapshot copy behavior.
- Added user-facing source names for Local Agent Lens result banners:
  - `agent_scanner` -> Scanner / 扫描
  - `document_scanner` -> Document Scan / 文档扫描
  - `video_capture` -> Video / 视频
- Wired `InboxView.resultBanner` to the presentation type so the tested copy is the UI path.

## TDD Notes

- Initial focused run failed because `InboxResultPresentation` did not exist yet.
- After extracting the old mapping, the focused test failed on raw sources such as `Source: agent_scanner`.
- Final focused and full Swift test runs passed after adding the Lens source mapping.
- Conversation B validation later found the Python iOS source guard still expected the Context Snapshot copy in `InboxView.swift`.
- The guard now checks that `InboxView` uses `InboxResultPresentation`, that Recall still receives `sourceInboxItemID`, and that Context Snapshot copy lives in `InboxResultPresentation.swift`.

## Verification

- `swift test --filter InboxResultPresentationTests`
  - Log: `swift-test-inbox-result-presentation.log`
  - Result: 2 tests passed.
- `swift test`
  - Log: `swift-test.log`
  - Result: 462 tests passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider ios/tests/test_inbox_result_review_provenance_source.py -q`
  - Log: `pytest-ios-source-guard.log`
  - Result: 1 test passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q`
  - Log: `pytest-runtime-mock-ios-photo-pack.log`
  - Result: 653 tests passed.
- `git diff --check`
  - Log: `git-diff-check.log`
  - Result: passed with no output.

## Not Run

- Simulator and real-device screenshots were not taken because this is a test-covered result banner copy slice with no layout or runtime contract change.
