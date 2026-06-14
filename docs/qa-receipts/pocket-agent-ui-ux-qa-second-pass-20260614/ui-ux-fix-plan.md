# Pocket Agent UI/UX QA Second Pass Fix Plan

Date: 2026-06-14
Branch: `codex/pocket-agent-ui-ux-qa-second-pass`

## One Issue To One Fix

| Issue | Evidence | Fix | Files | Verification |
| --- | --- | --- | --- | --- |
| Disabled dark-sheet primary actions looked like active mint CTAs in Video Intake and Voice, even though they were not tappable. | `iphone-17-pro-max-video-intake-second-pass.jpg`, `iphone-17-pro-max-voice-sheet-second-pass.jpg`; XcodeBuildMCP snapshots omitted the disabled send/save actions from tap targets. | Make disabled dark primary buttons use neutral dark fill and muted light label instead of strong mint. | `Sources/AgentPocketUI/AgentPocketDesignTokens.swift`; `Tests/AgentPocketUITests/DarkControlContrastTests.swift` | Red/green focused tests; fixed screenshots `iphone-17-pro-max-video-intake-fixed-second-pass.jpg`, `iphone-17-pro-max-voice-sheet-fixed-second-pass.jpg`. |
| Activity list could surface the generic runtime fallback title `Runtime task` in a Chinese UI. | `iphone-17-pro-max-activity-history-second-pass.jpg` showed `Runtime task` among Chinese chrome. | Add a small Task Inbox presentation helper that localizes blank/default runtime titles while preserving specific runtime-provided/user titles. | `Sources/AgentPocketUI/TaskInboxPresentation.swift`; `Sources/AgentPocketUI/TaskInboxView.swift`; `Tests/AgentPocketUITests/TaskInboxPresentationTests.swift` | Focused presentation tests verify `Runtime task` and blank titles become `运行时任务`; specific titles remain unchanged. |

## QA Findings Kept As Evidence Only

| Finding | Decision |
| --- | --- |
| iPhone 16 / iPhone 16 Plus simulators were not installed. | Used iPhone 17 Pro Max as the Plus-like simulator. |
| iPhone 16e appeared in the first XcodeBuildMCP list but became unavailable to build/run after enabled simulators refreshed to iOS 26.5 only. | Used iPhone 17e as the closest small-screen available substitute and recorded the mismatch in this receipt. |
| Simulator cannot validate real camera Scanner, VisionKit document capture, microphone recording, camera video capture, or Dynamic Island hardware behavior. | Kept as retained risk for real iPhone 16 Plus QA. |
| Activity tab remains a light, Apple-native review surface while Lens Hub uses a dark camera-first surface. | Left unchanged; this is existing screen-level design direction and not a narrow bug. |
