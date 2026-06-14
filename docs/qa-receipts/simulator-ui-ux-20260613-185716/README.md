# Simulator UI/UX QA Receipt · 2026-06-13 18:57

Scope: systematic iPhone Simulator UI/UX sweep for the current Kaka Local Agent Lens build.

Skills used:

- `build-ios-apps:ios-debugger-agent` for XcodeBuildMCP simulator build/run, UI snapshots, taps, and screenshots.
- `design-review` for visual hierarchy, spacing, localization, and interaction QA.

Targets:

- iPhone 16e, iOS 26.1, fresh install / first pairing.
- iPhone 17, iOS 26.5, saved connected local runtime state.
- Project: `ios/AgentPocket.xcodeproj`
- Scheme: `AgentPocket`
- Bundle: `com.kartz.agentpocket.dev`

Build/run result:

- XcodeBuildMCP `build_run_sim` succeeded on iPhone 16e.
- XcodeBuildMCP `build_run_sim` succeeded on iPhone 17.
- No XcodeBuildMCP build diagnostics were reported.

Screenshots:

- `01-iphone16e-first-pairing.jpg` — first-pairing screen on a fresh small iPhone simulator.
- `02-iphone17-connected-lens-hub.jpg` — connected Local Agent Lens Hub.
- `03-iphone17-agent-scanner.jpg` — Agent Scanner simulator view.
- `04-iphone17-video-intake.jpg` — Video Intake sheet.
- `05-iphone17-document-scan-simulator-limit.jpg` — VisionKit Document Scan simulator hardware limit.
- `06-iphone17-voice-record-sheet.jpg` — Record / voice draft sheet.
- `07-iphone17-inbox-empty.jpg` — Inbox empty review state.
- `08-iphone17-recall-empty.jpg` — Recall empty state.
- `09-iphone17-activity-list.jpg` — Activity list with task progress.
- `10-iphone17-connected-runtime-sheet.jpg` — connected runtime management sheet.

Findings:

1. P2 — Local Agent Lens Hub bottom row is partly occluded by the floating tab bar on iPhone 17. The Video/Record tiles are still tappable, but the tab bar visually covers the bottom of the grid. Evidence: `02-iphone17-connected-lens-hub.jpg`.
2. P2 — Agent Scanner has no obvious visible close or back affordance. In the simulator it presents a full black camera surface with only the bottom instruction, so QA had to restart the app to return to Hub. Evidence: `03-iphone17-agent-scanner.jpg`.
3. P2 — Voice sheet has mixed Chinese/English copy and crowded bottom actions. `Ready for push-to-talk`, `Record`, and `Cancel` appear inside a Chinese UI, and `保存草稿` wraps in the trailing button. Evidence: `06-iphone17-voice-record-sheet.jpg`.
4. P2 — Connected runtime sheet copy is still photo-specific: `已准备好处理照片`. Local Agent Lens now supports scan, document, video, voice, and Inbox flows, so this should become broader. Evidence: `10-iphone17-connected-runtime-sheet.jpg`.
5. P3 — Video Intake sheet is English-only in the Chinese app context. The layout is stable, but localized copy would better match the rest of the product. Evidence: `04-iphone17-video-intake.jpg`.
6. P3 — Activity cards show English status body text `Completed.` under Chinese status labels. Evidence: `09-iphone17-activity-list.jpg`.
7. P3 — First-pairing privacy note is small and low-emphasis on iPhone 16e. It is readable, but near the lower contrast edge for a trust boundary. Evidence: `01-iphone16e-first-pairing.jpg`.
8. P3 — Recall uses a dark empty state while Inbox and Activity use light review surfaces. This is not a blocker, but it makes the review/management areas feel less unified. Evidence: `08-iphone17-recall-empty.jpg`.

Passes:

- First-pairing layout is clean on iPhone 16e, with no obvious text overflow.
- Connected Lens Hub establishes the intended dark media-capture direction and mint/teal accent.
- Video Intake controls are clear and stable; `Close`, `Choose Video`, `Record`, optional prompt, disabled send state, and 100 MB limit are visible.
- Inbox empty state is clean, light, and readable.
- Activity list is readable, with visible progress bars and phone-safe status fields.
- Connected runtime sheet is visually polished and clearly indicates online/trusted state.

Simulator limitations:

- Scanner camera feed is black on simulator; real QR/text recognition still needs physical-device QA.
- VisionKit Document Scan opens, but simulator reports `无法捕捉媒体`; real PDF draft creation still needs physical-device QA.
- Video recording and real Photos picker asset selection were not exercised to completion.
- Share Extension, Action Button, and Dynamic Island states were not covered in this simulator sweep.

Recommendation:

Do a small polish follow-up focused on bottom safe-area spacing, Scanner dismissal, localization consistency, and broadening connection copy from photo-specific to Local Agent Lens language. Then run the iPhone 16 Plus real-device QA for scanner, document scan, video intake, Share Extension, Action Button, and Dynamic Island.
