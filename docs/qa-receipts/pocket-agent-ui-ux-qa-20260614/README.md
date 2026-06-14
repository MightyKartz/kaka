# Pocket Agent UI/UX QA Receipt · 2026-06-14

## Scope

- Local Agent Lens Hub / home capture tab.
- Scanner, Document Scan, Video Intake, Voice / Record.
- Inbox Review, Activity / Live Activity phone-safe expression.
- Connection, offline, and recovery surfaces.
- Small-screen clipping, tab bar overlap, Chinese / English copy, Pocket Agent naming, and quiet mint / teal visual direction.

## Devices

- Preferred devices requested: iPhone 16 / iPhone 16 Plus.
- Simulator availability: neither iPhone 16 nor iPhone 16 Plus was installed.
- Closest Plus-like simulator used: iPhone 17 Pro Max, iOS 26.5.
- Small-screen simulator used: iPhone 16e, iOS 26.1.

## Baseline

- `baseline-swift-test.log`: `swift test` passed with 447 tests before this slice.
- `baseline-pytest.log`: pytest passed with 653 tests before this slice.
- Baseline screenshots captured for Hub, Scanner, Document Scan, Video Intake, Voice, Inbox, Activity, and iPhone 16e first-run / connected states.

## Fix Evidence

- `ui-ux-fix-plan.md`: one issue to one fix mapping, file ownership, and verification.
- `red-focused-ui-tests.log`: focused tests failed before implementation.
- `focused-ui-tests.log`: focused UI tests passed after implementation.
- `final-swift-test.log`: `swift test` passed with 453 tests.
- `final-pytest.log`: pytest passed with 653 tests.
- `xcodebuildmcp-final-build-run.log`: XcodeBuildMCP iPhone 17 Pro Max build / install / run succeeded.
- `xcodebuildmcp-final-runtime.log`, `xcodebuildmcp-final-os.log`: final runtime logs.

## Screenshot Index

- `iphone-17-pro-max-hub-connected-clean-baseline.jpg`: baseline connected Hub with tab-bar clipping.
- `iphone-17-pro-max-hub-connected-fixed.jpg`: fixed connected Hub with no clipped control text under the tab bar.
- `iphone-17-pro-max-scanner-baseline.jpg`: baseline Scanner with English controls and black simulator surface.
- `iphone-17-pro-max-scanner-fixed.jpg`: fixed localized Scanner unavailable state on Simulator.
- `iphone-17-pro-max-voice-sheet-baseline.jpg`: baseline Voice sheet with dark title contrast issue.
- `iphone-17-pro-max-voice-sheet-fixed.jpg`: fixed Voice sheet with dark navigation chrome.
- `iphone-17-pro-max-video-sheet-baseline.jpg`: baseline Video Intake placeholder / disabled action contrast issue.
- `iphone-17-pro-max-video-sheet-fixed.jpg`: fixed Video Intake placeholder and disabled action contrast.
- `iphone-17-pro-max-document-camera-permission-baseline.jpg`: baseline camera permission prompt in English.
- `iphone-17-pro-max-document-simulator-limited-baseline.jpg`: Simulator VisionKit media capture limitation.
- `iphone-17-pro-max-inbox-empty-baseline.jpg`: Inbox empty-state check.
- `iphone-17-pro-max-activity-empty-baseline.jpg`: Activity empty-state / phone-safe check.
- `iphone-16e-first-launch-baseline.jpg`: small-screen first launch.
- `iphone-16e-hub-connected-baseline.jpg`: small-screen connected Hub.
- `iphone-16e-manual-connection-save-failed-baseline.jpg`: transient first manual credential save failure, retry succeeded.

## Remaining Risks

- Simulator cannot validate real camera Scanner, VisionKit document scanning, microphone recording, or camera video capture.
- A real iPhone 16 Plus pass is still needed for hardware Scanner / Document / Video / Voice paths and Dynamic Island behavior.
- The first iPhone 16e manual connection save attempt failed once, then retry succeeded; keep an eye on keychain timing during real-device QA.
- `NSCameraUsageDescription` is now aligned with the Chinese app path; a future localization pass can add per-locale `InfoPlist.strings` if English system prompts become a release requirement.
