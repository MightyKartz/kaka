# Kaka Pocket Agents Direction

Updated: 2026-06-05

## Purpose

This document captures the product discussion and current recommendation for evolving Kaka from a single-capture visual agent client into a voice-first Pocket Agents front end.

The near-term implementation truth is now Phase A plus the original camera loop: Kaka focuses on iPhone capture or library selection, `image_intake`, suggested image skills, local vision tasks, local recipe photo editing, Share Extension inbox capture, a transcript-first voice follow-up skeleton, an opt-in Context Snapshot preview, a Recall v0 explicit-action contract, and an in-app Runtime Task Inbox foundation through a user-owned runtime. Pocket Agents remains the next product direction; real microphone transcription, richer device context collectors, Recall search/browse/export, App Intents, Live Activity, passive context, and production-grade long-running task orchestration are still future phases.

Current UI prototype artifacts:

- presentation visual: `docs/ui/kaka-pocket-agents-presentation.html`
- presentation screenshot: `docs/ui/kaka-pocket-agents-presentation.png`
- `docs/ui/kaka-pocket-agents-prototype.html`
- desktop screenshot: `docs/ui/kaka-pocket-agents-prototype-desktop.png`
- mobile screenshot: `docs/ui/kaka-pocket-agents-prototype-mobile.png`
- app handoff prototype: `docs/ui/kaka-pocket-agents-app-handoff.html`
- app handoff desktop screenshot: `docs/ui/kaka-pocket-agents-app-handoff-desktop.png`
- app handoff mobile screenshot: `docs/ui/kaka-pocket-agents-app-handoff-mobile.png`

## Product Thesis

Kaka should become the phone-side front end for local agents.

The phone should own:

- capture from camera, screenshots, share sheet, paste, files, and microphone
- permissioned context collection
- voice interaction
- user confirmation
- result preview, save, share, and recall controls

The local runtime should own:

- model/provider credentials
- model choice and routing
- tool execution
- long-running jobs
- memory and retrieval
- retention policy
- approvals that outlive the current app session

This keeps Kaka aligned with the existing local-first Mobile Bridge boundary: the iPhone is the personal sensor, input, and consent surface; the Mac/runtime is the thinking and execution surface.

## External Signals

The research and open-source landscape supports this direction, but also argues for careful scope.

- Smartphone GUI-agent papers such as AppAgent and Mobile-Agent show that multimodal agents can operate mobile apps by observing screens and producing bounded actions. They also show why full autonomy should be treated carefully.
- AndroidWorld gives a reality check: mobile-agent benchmarks are still difficult, so Kaka should start with user-approved intake, guidance, and confirmations instead of unsupervised cross-app control.
- UI-understanding work such as Ferret-UI and OmniParser supports screenshot Q&A and interface guidance as a practical intermediate step.
- High-star tools such as scrcpy, LocalSend, Home Assistant, Termux, and mobile-agent projects show demand for device-to-device control, local automation, file/link movement, and phone-as-compute-node workflows.
- Apple's platform direction favors explicit extension points: Share/Action Extensions, App Intents, Speech, ActivityKit, Core Location, Core Motion, EventKit, and system share sheets. Kaka should use these system surfaces rather than background scraping.

Reference links:

- AppAgent: https://arxiv.org/abs/2312.13771
- Mobile-Agent: https://arxiv.org/abs/2401.16158
- AndroidWorld: https://arxiv.org/abs/2405.14573
- OmniParser: https://github.com/microsoft/OmniParser
- Apple App Extensions: https://developer.apple.com/documentation/technologyoverviews/app-extensions
- Apple App Intents: https://developer.apple.com/documentation/appintents
- Apple Speech: https://developer.apple.com/documentation/speech/
- Apple ActivityKit: https://developer.apple.com/documentation/activitykit

## Candidate Capabilities

### 1. Share To Kaka Inbox

This is the highest-value next expansion after image intake.

Users should be able to share text, links, screenshot images, PDFs, images, and small files into Kaka from any app. Kaka turns each input into an inbox item, asks the runtime to classify it, then offers actions such as summarize, translate, extract tasks, explain visible UI, enhance photo, save to Recall, or continue by voice.

Why it matters:

- It turns Kaka into a system-wide entry point without requiring global app control.
- It fits iOS well through Share/Action Extensions.
- It generalizes the current `image_intake` pattern into universal intake.

Phase A implementation shape:

- iOS Share Extension target `KakaShareExtension`.
- App Group inbox store using `group.dev.kartz.Kaka`.
- Share Extension captures text, URL, image, and PDF-visible file payloads into local JSON plus copied payload files. Screenshots shared from Photos or Files are captured as image payloads in this slice.
- Main app exposes an Inbox tab while connected to a runtime.
- Text and URL inbox items submit through `POST /mobile/v1/tasks/intake`.
- Shared image payloads, including screenshots represented as images, route through the existing `image_intake` path so image conversation behavior is preserved.
- Shared PDFs are captured locally in the inbox; after a visible main-app Send action, Kaka uploads the PDF as a generic asset and submits it through universal intake with the returned `asset_id`.
- The extension does not silently upload shared content.

### 2. Permissioned Context Snapshot

Context Snapshot is not just recording information. Its job is to tell the agent the user's current situation so it can make better decisions with fewer follow-up questions.

Examples:

- If the user is walking or driving, replies should be shorter and voice-first.
- If the battery is low, Kaka should prefer quick local actions and avoid long background workflows.
- If the calendar has a short free window, the agent can suggest a small task instead of a deep workflow.
- If a screenshot came from a share action, the agent can connect source, time, and current conversation without asking the user to re-explain.
- If the user is near a place where a receipt was captured, Recall can later label it more usefully.

Recommended boundary:

- Make snapshots explicit and per-task by default.
- Show a compact preview of what will be sent.
- Keep coarse location and state labels unless the user asks for precise data.
- Separate `use once` from `remember this`.
- Do not make passive background tracking part of the MVP.

Potential snapshot fields:

- timestamp, locale, timezone
- coarse location label or user-approved precise location
- motion state, such as stationary, walking, driving, or unknown
- network and battery state
- current Kaka conversation and source surface
- optional calendar availability, not full calendar contents by default
- optional user note spoken during capture

### 3. Clipboard And Link Courier

Kaka should not compete with Apple's Universal Clipboard. The value is not moving text between devices; the value is transforming, acting on, and remembering what the user intentionally sends.

Examples:

- Paste copied text into Kaka and ask for rewrite, translation, tone adjustment, or extraction.
- Share a link and ask the runtime to summarize, compare, archive, or add it to Recall.
- Paste an error message from the phone and ask a Mac-side coding agent to investigate.
- Send a copied address, event text, or tracking number to the local runtime for structured handling.

Privacy boundary:

- Use explicit paste controls, share sheet, or user actions.
- Do not poll or read the general pasteboard in the background.
- Treat pasteboard content as sensitive by default.

### 4. Voice Walkie-talkie

Voice should be the main interaction style for Pocket Agents.

Recommended MVP:

- push-to-talk inside Kaka
- live transcription or recorded transcription
- short voice replies through system speech synthesis
- transcript always visible and editable before high-impact actions
- runtime confirmation cards for actions like remember, send, delete, or execute

What not to do first:

- no always-on wake word
- no background microphone listener
- no hidden transcription
- no autonomous action from ambiguous speech

This gives the user the feeling of talking to a pocket agent while staying inside iOS permission and trust boundaries.

### 5. Screenshot Q&A And UI Guidance

Screenshot Q&A is safer and more useful than full cross-app automation on iOS.

Flow:

1. User shares a screenshot to Kaka.
2. Kaka runs screenshot intake.
3. The runtime identifies visible UI, text, controls, and likely task intent.
4. Kaka replies with guidance such as "tap Settings, then Subscriptions" or explains an error message.
5. The user decides whether to follow the guidance.

This pairs well with existing `image_intake` and `vision` work. It can use OCR and UI parsing without requiring Kaka to control other apps.

### 6. Personal Recall

Recall should be local-first, explicit, inspectable, and erasable.

Recommended rule:

- Nothing goes into long-term memory by default.
- Every item starts as an inbox or conversation artifact.
- The user can choose `Remember`, `Use Once`, or `Forget`.

Runtime-side storage should own:

- original artifact or a redacted pointer
- extracted text
- summary
- embeddings or retrieval index
- source type
- permission state
- deletion state
- provenance back to the task that created it

iPhone-side UI should own:

- browse/search
- "why is this remembered?"
- delete/forget controls
- export request entrypoint

## Proposed Architecture

```mermaid
flowchart LR
  Inputs["Camera / Share / Paste / Voice / Screenshot"] --> Phone["Kaka iPhone app"]
  Phone --> Consent["Preview and Consent"]
  Consent --> Bridge["Mobile Bridge /mobile/v1"]
  Bridge --> Runtime["Hermes, OpenClaw, or sidecar"]
  Runtime --> Router["Intake Router"]
  Router --> Skills["Vision / Photo Edit / Text / Link / Document / Voice"]
  Router --> Memory["Local Recall Store"]
  Skills --> Bridge
  Memory --> Bridge
  Bridge --> Phone
  Phone --> Outputs["Conversation / Task Inbox / Save / Share / Speak"]
```

The current `image_intake` task can become the first specialization of a broader `intake` family. The future API should preserve the same shape: upload or attach an artifact, start an intake task, receive a structured result with suggestions, then let the user choose the next action.

## Recommended Roadmap

### Phase A: Universal Intake And Share To Kaka

Goal: let Kaka receive content from outside the camera flow.

Status as of 2026-06-05: implemented as the first share inbox slice.

Deliverables:

- iOS Share Extension for text, URL, image, and PDF capture; screenshots are captured as images in this slice
- app-side `KakaInboxItem` and App Group-compatible `FileKakaInboxStore`
- runtime-side `intake` protocol and mock bridge endpoint for text, URL, image, and PDF asset intake
- basic action suggestions for text, URL, image, and PDF intake results
- main app Inbox tab for connected runtimes
- tests for plist/entitlements, inbox persistence, bridge submission, and image route preservation

Exit criteria:

- A URL shared from Safari can become an inbox item and submit to `/mobile/v1/tasks/intake`.
- Shared text can submit to `/mobile/v1/tasks/intake` and return summary/action suggestions.
- A screenshot shared as an image keeps the existing `image_intake` route.
- A PDF shared to Kaka is captured into the App Group inbox, then uploads from a visible main-app Send action and submits to `/mobile/v1/tasks/intake` with an `asset_id`.

### Phase B: Voice-first Conversation

Goal: make Kaka feel like a pocket agent rather than a form-based tool.

Deliverables:

- push-to-talk capture
- transcription state model
- text submit to the current image or inbox conversation
- spoken response for short answers
- confirmation cards for high-impact actions

Exit criteria:

- User can share or capture an item, speak a follow-up, hear a short answer, and see the transcript.
- Potentially destructive or persistent actions still require visible confirmation.

### Phase C: Permissioned Context Snapshot

Goal: give the runtime situational context without background surveillance.

Status as of 2026-06-05: contract-first slice implemented for Inbox universal intake. The preview defaults off, denied collectors do not block intake, and snapshots are sent only when the runtime advertises `supports_context_snapshot`. The current collector is intentionally minimal: timestamp, timezone, locale, and source surface.

Deliverables:

- context preview sheet
- coarse location, time, device state, and source surface fields
- per-task `include_context` control
- bridge payload schema for context
- privacy doc and tests proving denied permissions do not block core intake

Exit criteria:

- User can include a one-time context snapshot with a task.
- Kaka can explain exactly what context was sent.
- No snapshot is written to Recall unless the user confirms.

### Phase D: Recall v0

Goal: let the user explicitly save useful artifacts and retrieve them later.

Status as of 2026-06-05: D.0 explicit actions are implemented. `remember`, `use_once`, and `forget` have Mobile Bridge contracts, Swift client models, mock bridge endpoints, visible confirmation UI, and an Inbox result entry point. This is not the full Recall exit yet: search/retrieval, export, and retrieval-index deletion remain future D.1 work.

Deliverables:

- runtime-side local memory store: D.0 mock bridge in-memory store implemented; production runtime store still required
- inbox/result `Remember`, `Use Once`, and `Forget` actions: D.0 implemented for Inbox results
- mobile bridge actions: D.0 implements `POST /mobile/v1/recall/actions`, `GET /mobile/v1/recall/items`, `DELETE /mobile/v1/recall/items/{item_id}`
- standalone iPhone Recall action ViewModel/View for visible confirmation: D.0 implemented
- search and retrieval endpoint: future D.1
- iPhone Recall browsing UI: future D.1 beyond the current action entry point
- deletion and export paths: delete action exists in D.0; export and retrieval-index deletion are future D.1

Exit criteria:

- D.0: User can confirm `Remember`, `Use Once`, or `Forget` from an Inbox result, including results produced from shared links and screenshots.
- D.1: Later voice or text search retrieves remembered items with provenance.
- D.1: Delete removes both content and retrieval index entries.

### Phase E: Task Inbox, App Intents, And Live Activity

Goal: make local runtime jobs visible and controllable from the phone.

Status as of 2026-06-05: E.0 Runtime Task Inbox foundation is implemented. Kaka has Swift task summary models, a connected Tasks tab, and mock Mobile Bridge endpoints for listing, cancelling, and approving runtime tasks. App Intents and Live Activity remain future E.1 work after in-app task state is stable.

Deliverables:

- task inbox for running, waiting, failed, and completed jobs: E.0 implemented
- approval cards/actions for runtime work: E.0 approval endpoint and in-app action implemented
- Live Activity for long-running agent tasks where appropriate: future E.1
- App Intents for starting common actions through Siri, Shortcuts, Spotlight, widgets, or Action Button: future E.1

Exit criteria:

- E.0: Runtime tasks can be viewed from iPhone.
- E.0: User can approve or cancel a task from Kaka.
- E.1: Shortcuts/App Intents can start safe intake actions without opening hidden listeners.

## Product Boundaries

Do first:

- explicit share, paste, camera, screenshot, and voice input
- local-first runtime execution
- user-visible confirmation
- local Recall with clear controls
- guidance over autonomous cross-app control

Avoid in MVP:

- always-on microphone
- background clipboard reading
- passive location tracking
- automatic reading of all notifications
- autonomous posting, messaging, purchasing, or payment
- unsupervised control of other apps

## First Implementation Slice

The first Pocket Agents slice is now:

1. Share a URL, text, screenshot image, or image to Kaka.
2. Kaka creates an inbox item.
3. The runtime returns summary plus suggested actions.
4. Image payloads, including screenshots represented as images, continue through the existing image conversation path.
5. Voice follow-up plus `Remember`, `Use Once`, and `Forget` confirmation UI remain the next layer.

This slice is big enough to prove Pocket Agents, but small enough to stay aligned with the current Mobile Bridge and privacy boundary.

## Open Decisions

- Should the external brand remain Kaka while the category becomes Pocket Agents, or should Pocket Agents become a visible product name?
- Should Recall live entirely in Hermes/OpenClaw first, or should the Runtime Kit provide a default local store?
- Should voice transcription run on-device first, runtime-side first, or support both through capabilities?
- Should the PDF upload size limit remain the Phase A.1 default of 25 MB, or move to runtime capability negotiation?
- Should context snapshots default to off per task, or should Kaka ask once and remember a scoped preference?
