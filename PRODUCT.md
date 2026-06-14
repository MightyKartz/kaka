# Product

## Register

product

## Users

Pocket Agent serves people who want an iPhone to act as an explicit capture, share, voice, and consent surface for a user-owned local agent runtime. Early users are developers and operators of Hermes, OpenClaw, or a local Mobile Bridge runtime. Later users are privacy-conscious phone users who want useful agent help without moving model credentials, routing, memory, or retention policy onto the phone.

## Product Purpose

Pocket Agent turns the phone into a small, trusted front end for local agents. The phone captures or receives user-selected inputs such as photos, screenshots, links, text, clipboard content, voice notes, and permissioned context snapshots. The local runtime decides how to reason, which tools to call, what to remember, and what to retain.

The current product loop is camera and image intake: connect the phone to a local runtime, capture or choose an image, send it to Pocket Agent, receive suggested skills, continue by tap or typed request, and view the local agent result on the phone.

The near-term Pocket Agent direction expands that loop into a voice-first inbox: share URL, text, screenshot, or image to Pocket Agent; create an inbox item; let the runtime summarize and propose actions; continue by voice; choose whether the item should be remembered, used once, or forgotten.

## Brand Personality

Calm, trustworthy, capable.

## Product Boundaries

The phone stores only the runtime endpoint and mobile bearer token. Model keys, provider routing, task execution, Recall data, approvals, and retention rules stay runtime side.

Inputs should be user-visible and task-scoped unless the user explicitly saves them to Recall. Pocket Agent should not poll the pasteboard, run an always-on microphone, hide transcription, or passively track background context.

## Anti-References

- Cloud-first AI photo apps that obscure where data goes.
- Unsafe autonomous phone controllers that act before the user understands the action.
- Background listeners and surveillance-like context collection.
- Flashy generated-image tools that alter real-world details the user needs to inspect.
- Generic SaaS dashboards that make a personal phone companion feel like an operations console.

## Design Principles

1. Make user intent visible before anything leaves the phone.
2. Keep the runtime trust boundary visible.
3. Prefer guidance, preview, and confirmation over hidden automation.
4. Show provenance, retention state, and permission scope in plain language.
5. Design for repeated daily use, not a marketing demo.
6. Keep controls familiar, compact, and reliable under one-handed mobile use.

## Accessibility And Inclusion

Pocket Agent should target WCAG AA contrast, visible focus states, large mobile hit targets, non-color-only status indicators, and reduced-motion alternatives. Voice flows must show listening, transcribing, sending, speaking, and confirmation-needed states. The user should see or edit the transcript before high-impact actions. Permission-denied states should explain recovery without blocking unrelated intake paths.
