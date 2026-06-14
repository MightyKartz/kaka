# Simulator UI/UX Fix Receipt

Date: 2026-06-13
Device: iPhone 17 Simulator
Build: XcodeBuildMCP `build_run_sim`, scheme `AgentPocket`, bundle `com.kartz.agentpocket.dev`

## One-to-One Fix Map

| QA finding | Fix | Evidence |
| --- | --- | --- |
| Hub bottom row was occluded by the floating tab bar. | Compact-height Hub now uses a shorter media preview, denser Lens tiles, and a blank buffer before capture controls. | `01-hub-bottom-safe-area.jpg` |
| Agent Scanner had no obvious escape path. | Added a visible top-left Close control and wired it through `AgentPocketRootView`. | `02-scanner-close-affordance.jpg` |
| Video Intake used English copy in a Chinese session. | Added localized Video Intake copy for title, buttons, prompt, state, limit, and error text. | `03-video-intake-localized.jpg` |
| Voice sheet mixed English status/actions and crowded the bottom row. | Localized visible Voice sheet status/actions and applied compact dark button styling with single-line submit text. | `04-voice-sheet-localized-actions.jpg` |
| Activity cards showed English `Completed.` in Chinese UI. | Localized common runtime task messages at presentation time. | `05-activity-localized-status.jpg` |
| Recall empty state used a dark surface unlike Inbox/Activity review pages. | Switched Recall browse/empty/list rows to the shared light review surface. | `06-recall-light-empty-state.jpg` |
| Connected runtime sheet was still photo-specific. | Replaced photo-specific readiness and primary action copy with Local Agent Lens / phone-action copy. | `07-connected-runtime-lens-copy.jpg` |
| First-pairing privacy note was too low-emphasis. | Increased privacy line icon/text size and changed copy to explicit input/secret boundaries. | `07-connected-runtime-lens-copy.jpg` |

## Verification

- `swift test --filter ConnectScreenCopyTests` passed.
- `swift test --filter ConnectionStateTests` passed.
- `swift test --filter VoiceCapturePresentationTests` passed.
- `swift test --filter LocalAgentLensPresentationTests` passed after layout tuning.
- `swift test` passed: 447 tests.
- `git diff --check` passed.
- XcodeBuildMCP `build_run_sim -skipMacroValidation` passed on iPhone 17 Simulator.

## Notes

- Simulator cannot validate real camera, document camera, microphone capture, or video recording hardware paths.
- This receipt focuses on the UI/UX regressions observed in `docs/qa-receipts/simulator-ui-ux-20260613-185716/`.
