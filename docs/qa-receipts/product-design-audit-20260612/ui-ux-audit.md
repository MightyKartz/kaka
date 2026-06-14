# Kaka UI/UX Audit

Date: 2026-06-12
Scope: AgentPocket iOS UI, current local build, Product Design audit pass.

## Evidence

Screenshots captured from a local simulator build:

- `01-connect-failed.png` - failed connection state
- `02-discovery-confirm.png` - discovered runtime / connect state
- `03-capture-ready.png` - capture ready state
- `04-result-gallery-downloaded.png` - result gallery state

Supplemental runtime evidence from the same QA session confirmed the physical iPhone flow reached Hermes task completion, but this visual audit is based on the screenshots above rather than physical-device screenshots.

## Executive Summary

Kaka's core journey is promising: connect a local runtime, capture an image, send it to Kaka, and review variants. The current UI does not yet make that journey feel simple or trustworthy. It looks like a functional prototype that exposes internal runtime concepts, debug surfaces, and mixed-language labels directly to the user.

The highest-impact redesign should focus on three screens first:

1. Connect
2. Capture
3. Result review

Those three screens are enough to make the product feel coherent. Inbox, Recall, and Tasks can follow after the primary path has a stronger product shell.

## Key Findings

### 1. Connection UX Is Confusing

The connection screens use multiple competing concepts at once: failed state, discovered runtime, local network, pending confirmation, manual endpoint, QR scan, and retry. The result is technically informative but emotionally unclear.

Observed issues:

- The failed state still shows a large card that looks connectable.
- "Change Endpoint" and "Scan Pairing QR" appear in English inside an otherwise Chinese experience.
- The discovered-runtime state has duplicate connection actions: one in the hero card and one in the runtime list.
- Secondary text is very low contrast on the light background.
- Technical language like "runtime" and endpoint leaks into the first-run flow too early.

Recommendation:

Use one state-specific primary card per connection state:

- No runtime found: "扫码连接电脑" + "手动输入地址"
- Runtime discovered: show the machine name and one primary "连接" button
- Connecting: progress with cancel
- Connected: brief success state, then move to capture
- Failed: plain reason + retry + QR/manual fallback

### 2. Visual System Is Not Stable Yet

The app currently alternates between light gradient glass, dark camera UI, dark result UI, native SwiftUI lists, and internal task panels. Some screens are pleasant in isolation, but they do not yet feel like the same product.

Observed issues:

- Large glass cards with high blur and very rounded corners dominate the connection flow.
- Capture and Result are much stronger because they focus on the image, but their typography and controls do not fully match Connect.
- Recall uses native List styling and English empty states, which makes it feel like a different app.
- The mint accent is useful, but it needs tighter rules so it does not become the only visual identity.

Recommendation:

Create a small design system before broad redesign work:

- Background surfaces: app background, camera background, elevated panel, input field
- Text colors: primary, secondary, muted, disabled with contrast thresholds
- Accent roles: primary action, success, pending, warning, destructive
- Component rules: buttons, icon buttons, status pills, input fields, runtime rows, media cards
- Radius and elevation rules: reserve large radii for media and sheets; keep routine controls tighter

### 3. Language And Information Architecture Need Cleanup

The product appears localized to Chinese in important places, but root navigation and several controls still use English. This makes the app feel unfinished and makes the mental model harder to form.

Observed source areas:

- `Sources/AgentPocketUI/AgentPocketRootView.swift` uses English tab labels: Capture, Inbox, Recall, Tasks.
- `Sources/AgentPocketUI/RecallBrowseView.swift` uses English titles and empty states.
- `Sources/AgentPocketUI/ConnectView.swift` includes English recovery actions.

Recommendation:

Use Chinese labels consistently for the current audience:

- Capture -> 拍照
- Inbox -> 收件箱
- Recall -> 记忆
- Tasks -> 活动 or move into a status/activity drawer
- Scan Pairing QR -> 扫描配对码
- Change Endpoint -> 更换地址

More importantly, Tasks feels like an internal runtime surface. It should probably become an activity/status sheet rather than a main tab.

### 4. Capture Screen Has The Right Direction But Needs Workflow Clarity

The capture screen is the strongest signal that this can become a polished product. It centers the camera and gives the user a clear send action. However, it still blends camera controls and AI submission into one dense bottom area.

Observed issues:

- The status text is truncated in the screenshot: "照片已准备好，Kaka 会先判断适合做什么..."
- The send button is visually dominant, but the user does not get enough preview of what Kaka will do next.
- Camera controls, zoom controls, AI mode, and submit action are not clearly separated.

Recommendation:

Split the lower surface into three predictable regions:

- Capture controls: shutter, retake, gallery/import
- Kaka intent: auto / OCR / identify / enhance / translate
- Submit/action: send to Kaka with a compact progress state

The default can stay smart/automatic, but the UI should say what will happen after submission and allow a lightweight override.

### 5. Result Gallery Is The Best Current Screen

The result screen has a clear task: compare original and output, switch variants, save, or share. It already feels more product-like than the connection screens.

Observed issues:

- The simulator fixture shows a flat mint block as the edited image, which is acceptable as test data but makes the product look less real in visual QA.
- The top-right ellipsis appears to be an empty button in source and should not ship unless it opens a real menu.
- Variant names like "大师" and "社交" are compact, but users may need a short result summary or applied-edit explanation.
- Save and Share need stronger feedback states.

Recommendation:

Keep the before/after comparison as the hero. Add:

- A one-line "Kaka 做了什么" summary
- Variant cards with thumbnails or purpose labels
- Explicit saved/shared confirmation states
- A real overflow menu or no overflow button

## Priority Fix List

### P0 - Trust And Legibility

- Fix low-contrast secondary text on the connection screens.
- Remove or implement the empty result overflow menu.
- Make all visible labels Chinese in the Chinese locale.
- Fix the truncated capture status text with wrapping and stable layout constraints.
- Ensure all primary actions have distinct state labels.

### P1 - Core Flow Redesign

- Redesign Connect around one active state and one primary action.
- Redesign Capture as a camera-first tool with a clear "what Kaka will do" layer.
- Strengthen Result with real image states, edit summary, and save/share feedback.

### P2 - Product Architecture

- Reconsider the bottom tab model.
- Move Tasks into an activity/status surface unless it is meant for power users.
- Give Recall a product-specific empty state and visual treatment.
- Introduce shared tokens/components so future screens do not drift.

## Suggested Redesign Direction

Kaka should feel like a calm local AI camera companion rather than a runtime dashboard.

Design tone:

- Camera-first
- Local/private by default
- Direct, Chinese-native copy
- Technical power available, but not exposed first
- Confident dark media surfaces paired with restrained light setup screens

Primary journey:

1. Connect to this Mac
2. Take or import a photo
3. Let Kaka decide the best action
4. Review the result
5. Save, share, or continue asking

## Next Product Design Steps

1. Create a three-screen redesign for Connect, Capture, and Result.
2. Define a compact token/component sheet for colors, typography, controls, status pills, and panels.
3. Validate the redesign on iPhone 16/17 viewport sizes with long Chinese strings.
4. Implement the redesign behind the existing runtime behavior.
5. Run physical-device QA again through the same Hermes path.

## Known Limits

- This audit used simulator screenshots for visual evidence.
- The connected physical iPhone Hermes flow was verified separately in runtime QA, but no physical-device screenshots were captured for this audit.
- Accessibility was visually inspected but not measured with a full WCAG contrast report.
