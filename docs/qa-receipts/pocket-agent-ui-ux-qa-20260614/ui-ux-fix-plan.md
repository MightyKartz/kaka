# Pocket Agent UI/UX QA Fix Plan · 2026-06-14

| Issue | Fix | Files | Verification |
| --- | --- | --- | --- |
| Connected Hub leaked half-visible capture instruction under the floating tab bar on iPhone 17 Pro Max. | Moved initial empty capture controls fully below the first viewport while preserving immediate controls for prepared uploads and task states. | `Sources/AgentPocketUI/CaptureView.swift`, `Tests/AgentPocketUITests/CaptureLayoutPolicyTests.swift` | Focused layout test, XcodeBuildMCP `build_run_sim`, `iphone-17-pro-max-hub-connected-fixed.jpg`. |
| Voice / Record sheet used dark content with light navigation defaults, making the sheet title hard to read. | Added a presentation-level dark navigation chrome flag and applied an iOS toolbar color scheme / background for voice sheets. | `Sources/AgentPocketUI/VoiceCapturePresentation.swift`, `Sources/AgentPocketUI/VoiceCaptureView.swift`, `Tests/AgentPocketUITests/VoiceCapturePresentationTests.swift` | Focused voice presentation test, `iphone-17-pro-max-voice-sheet-fixed.jpg`. |
| Scanner sheet had English controls and a black unsupported-camera surface on Simulator. | Added localized `AgentScannerCopy`, localized close / instruction text, and a clear Simulator unavailable state instead of an empty scanner surface. | `Sources/AgentPocketUI/AgentScanner/AgentScannerView.swift`, `Tests/AgentPocketUITests/AgentScannerPresentationTests.swift` | Focused scanner copy tests, `iphone-17-pro-max-scanner-fixed.jpg`. |
| Video Intake placeholder and disabled send action were too faint in the dark sheet. | Added a controlled placeholder layer and raised disabled dark-control contrast while preserving disabled semantics. | `Sources/AgentPocketUI/VideoIntake/VideoIntakePickerView.swift`, `Sources/AgentPocketUI/AgentPocketDesignTokens.swift`, `Tests/AgentPocketUITests/DarkControlContrastTests.swift` | Focused contrast test, `iphone-17-pro-max-video-sheet-fixed.jpg`. |
| Camera permission prompt mixed English into the Chinese app path. | Updated the camera permission string to Pocket Agent Chinese copy that names capture / scan and pre-submit confirmation. | `ios/AgentPocket/Info.plist` | XcodeBuildMCP build/run, `iphone-17-pro-max-document-camera-permission-baseline.jpg` as baseline comparison. |
| Document Scan cannot be fully evaluated on Simulator. | Recorded the Simulator VisionKit limitation as residual risk instead of changing product behavior. | QA receipt only | `iphone-17-pro-max-document-simulator-limited-baseline.jpg`. |
| Activity / Inbox empty states needed a quiet, phone-safe sanity check. | No code change; current surfaces stayed within quiet native style and did not expose runtime-controlled titles in Live Activity tests. | QA receipt only | `iphone-17-pro-max-inbox-empty-baseline.jpg`, `iphone-17-pro-max-activity-empty-baseline.jpg`, existing Activity tests. |
| iPhone 16e first manual connection save failed once before retry succeeded. | No code change in this slice; logged as a residual keychain / simulator timing risk for real-device QA. | QA receipt only | `iphone-16e-manual-connection-save-failed-baseline.jpg`. |

## Final Verification

- `swift test`: passed, 453 tests.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q`: passed, 653 tests.
- `git diff --check`: passed.
- XcodeBuildMCP `build_run_sim`: passed on iPhone 17 Pro Max / iOS 26.5 with `com.kartz.agentpocket.dev`.
