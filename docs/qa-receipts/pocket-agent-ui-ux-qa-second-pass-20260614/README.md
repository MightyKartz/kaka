# Pocket Agent UI/UX QA Receipt · Second Pass · 2026-06-14

## Scope

- Local Agent Lens Hub / home capture tab.
- Scanner, Document Scan, Video Intake, Voice / Record.
- Inbox Review, Activity / Live Activity phone-safe expression.
- Connection, offline, and recovery surfaces.
- Small-screen clipping, tab bar overlap, Chinese / English copy, Pocket Agent naming, and quiet mint / teal visual direction.

## Devices

- Requested: iPhone 16 / iPhone 16 Plus.
- Available Plus-like simulator used: iPhone 17 Pro Max, iOS 26.5.
- Small-screen substitute used: iPhone 17e, iOS 26.5.
- iPhone 16 / iPhone 16 Plus were not installed. iPhone 16e initially appeared in XcodeBuildMCP output, but build/run failed with `No available simulator matched` and the refreshed enabled list no longer included iOS 26.1 devices.

## Baseline

- `baseline-swift-test.log`: `swift test` passed with 453 tests before this slice.
- `baseline-pytest.log`: pytest passed with 653 tests before this slice.
- `xcodebuildmcp-baseline-build-run.log`: XcodeBuildMCP build/run passed on iPhone 17 Pro Max.

## Fix Evidence

- `ui-ux-fix-plan.md`: one issue to one fix mapping, file ownership, and verification.
- `red-focused-ui-tests.log`: focused UI tests failed before implementation.
- `focused-ui-tests.log`: focused UI tests passed after implementation.
- `xcodebuildmcp-fixed-build-run.log`: fixed app build/run passed on iPhone 17 Pro Max.

## Final Verification

- `final-swift-test.log`: `swift test` passed with 456 tests.
- `final-pytest.log`: pytest passed with 653 tests.
- `xcodebuildmcp-final-build-run.log`: XcodeBuildMCP `build_run_sim -skipMacroValidation` passed on iPhone 17 Pro Max.
- `final-git-diff-check.log`: `git diff --check` result.

## Screenshot Index

- `iphone-17-pro-max-hub-connected-second-pass-baseline.jpg`: connected Hub.
- `iphone-17-pro-max-scanner-unavailable-second-pass.jpg`: Simulator scanner limitation state.
- `iphone-17-pro-max-document-simulator-limited-second-pass.jpg`: VisionKit Simulator limitation state.
- `iphone-17-pro-max-video-intake-second-pass.jpg`: baseline Video disabled submit looked too primary.
- `iphone-17-pro-max-video-intake-fixed-second-pass.jpg`: fixed Video disabled submit is neutral/inactive.
- `iphone-17-pro-max-voice-sheet-second-pass.jpg`: baseline Voice disabled save looked too primary.
- `iphone-17-pro-max-voice-sheet-fixed-second-pass.jpg`: fixed Voice disabled save is neutral/inactive.
- `iphone-17-pro-max-inbox-empty-second-pass.jpg`: Inbox empty state.
- `iphone-17-pro-max-activity-history-second-pass.jpg`: Activity history with mixed runtime-provided/default titles.
- `iphone-17-pro-max-activity-empty-fixed-second-pass.jpg`: connected fresh mock Activity empty state.
- `iphone-17-pro-max-connection-connected-second-pass.jpg`: connected runtime sheet.
- `iphone-17-pro-max-connection-recovery-second-pass.jpg`: offline/recovery sheet.
- `iphone-17e-first-screen-second-pass.jpg`: small-screen first connection state.
- `iphone-17e-capture-ready-second-pass.jpg`: small-screen connected smoke capture-ready state.

## Remaining Risks

- Simulator cannot validate real QR scanning, VisionKit document scanning, microphone recording, camera video capture, or Dynamic Island behavior.
- A real iPhone 16 Plus pass is still needed for hardware Scanner / Document / Video / Voice paths.
- iPhone 16e was not available for build/run after XcodeBuildMCP refreshed enabled simulators; iPhone 17e was used for small-screen coverage.
