# Kaka / Agent Pocket Development Plan

Updated: 2026-06-02

This is the execution-level development plan for Kaka / Agent Pocket. It reconciles the current codebase, the current product direction, and the tools that should be used to implement the next milestones.

## Goal

Ship the first credible Kaka product loop:

1. iPhone pairs with a user-owned compatible local runtime.
2. iPhone captures or selects a photo.
3. iPhone sends the photo to the local Mobile Bridge.
4. The runtime uses its configured multimodal model to create a strict edit recipe.
5. The Mac renders deterministic `Master` and `Social` variants locally.
6. iPhone shows an obvious before/after result.
7. User saves or shares through the iOS system share sheet.

The Phase 1 path is local recipe editing, not cloud image generation. The iPhone must not hold model-provider keys. The runtime can be Hermes, OpenClaw, or another compatible Mobile Bridge implementation.

## Current Truth

The codebase is already a working Agent Pocket MVP foundation, but the current shippable product loop is not complete.

| Area | Current state | Evidence |
| --- | --- | --- |
| Swift package | Swift 6 package with core and UI targets | `Package.swift`, `Sources/AgentPocketCore`, `Sources/AgentPocketUI` |
| iOS app | App target exists with connection, capture, result screens | `ios/AgentPocket` |
| Mobile Bridge client | Pairing, capabilities, upload, task, polling, asset download are modeled | `Sources/AgentPocketCore` |
| Mock bridge | Local mock runtime exists with fixture, script, and OpenAI adapter paths | `mock_bridge/agent_pocket_mock_bridge` |
| Photo Pack | `script` and `openai_image` adapters exist | `photo-pack/adapters` |
| Local recipe adapter | Implemented for fixture/local renderer mode | `photo-pack/adapters/recipe_local.py`, `photo-pack/tests/test_recipe_local_adapter.py` |
| Provider registry | `recipe_local` registered for mock bridge use | `mock_bridge/agent_pocket_mock_bridge/photo_providers.py`, `mock_bridge/agent_pocket_mock_bridge/qa.py` |
| Runtime Kit | Development scaffold for explicit-start Kaka Mobile Bridge packaging exists; Hermes/OpenClaw plugin packaging is planned, not production-ready | `runtime-kit`, `docs/kaka-runtime-kit-plan.md` |
| QA CLI | `provider-preflight --photo-provider recipe_local`, `simulator-local-recipe-smoke`, and `simulator-share-sheet-smoke` exist | `PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa --help` |
| Test receipts | Python `196 passed`; Swift `142 tests, 0 failures` | `docs/qa-receipts/python-tests-latest.json`, `docs/qa-receipts/swift-test-latest.json` |
| Readiness | Gates A-E passed; Gate F redirected and still open | `docs/agent-pocket-readiness.md` |
| UI prototype | Master Shot HTML prototype exists with zh/en language switching; second polish pass generated zh/en screenshots, prioritizes the three main flow screens, and keeps settings as an auxiliary configuration screen; SwiftUI connect local/trusted badges, runtime-neutral local-agent copy, capture scene-pack/badge, and result recipe presentation have started, broader native visual port is still pending | `docs/ui/kaka-master-shot-ui-prototype.html`, `docs/ui/kaka-master-shot-ui-prototype-zh.png`, `docs/ui/kaka-master-shot-ui-prototype-en.png` |

## Direction Decisions

- Keep iPhone as a thin, camera-first client.
- Keep provider/model credentials inside the selected runtime.
- Do not hardcode GPT-5.5 or any single model name in Kaka. The runtime decides which multimodal model to use.
- Do not make Hermes the only target. Treat Hermes and OpenClaw as first compatible runtimes behind the Mobile Bridge API.
- Make `recipe_local` the Phase 1 proof path.
- Keep OpenAI Images, ComfyUI, object removal, background replacement, and direct social SDK posting as later optional adapters.
- Phase 1 must produce a visibly better photo using parameterized edits: crop, tone, local contrast, denoise, sharpen, subject separation, optional conservative upscale.
- Do not make normal users paste long terminal commands to connect. The consumer path should be a Hermes/OpenClaw plugin or skill UI with a visible **Kaka Mobile Bridge** enable/start control. Install must not auto-start a LAN bridge.

## Tooling Plan

Use these plugins, skills, and MCP tools deliberately. They are part of the implementation workflow, not decoration.

| Work type | Tooling | How to use |
| --- | --- | --- |
| Codebase orientation | `project-codebase-onboarding-and-roadmap` skill | Re-run when docs and implementation drift, especially before changing milestone docs. |
| Implementation planning | `superpowers:writing-plans` skill | Keep detailed task plans under `docs/superpowers/plans/`. The active child plan is `docs/superpowers/plans/2026-06-01-agent-pocket-gate-f-completion.md`. |
| Task execution | `superpowers:executing-plans` or `superpowers:subagent-driven-development` | Use one of these before implementing the Gate F tasks. Subagent-driven is preferred when splitting renderer, QA, iOS UI, and docs work. |
| TDD | `superpowers:test-driven-development` | Use for `recipe_local`, QA CLI commands, and SwiftUI result/share behavior. Write failing tests first where practical. |
| Completion checks | `superpowers:verification-before-completion` | Required before declaring Gate F or Phase 1 complete. Receipts must prove the claim. |
| Architecture lookup | Codegraph MCP | Use `codegraph_context` before changing a workflow, `codegraph_trace` for request-to-result flows, and `codegraph_impact` or callers/callees before shared API edits. |
| iOS simulator/device debugging | Build iOS Apps plugin, especially `ios-debugger-agent` and SwiftUI skills | Use for simulator launch, screenshots, result/share smoke, and SwiftUI view alignment. |
| SwiftUI implementation | `build-ios-apps:swiftui-ui-patterns`, `build-ios-apps:swiftui-view-refactor` | Use when turning the HTML prototype into native SwiftUI screens. |
| HTML/UI prototype work | `app-ui-implementer` skill plus Browser plugin | Use for visual comparison, screenshot capture, zh/en prototype verification, and iteration before SwiftUI porting. |
| Local HTML visual QA | Browser plugin or Playwright skill | Open `file:///Users/kartz/Development/Kaka/docs/ui/kaka-master-shot-ui-prototype.html`, capture screenshots, and compare regions. |
| OpenAI API details | `openai-docs` skill only when needed | Not required for `recipe_local` fixture mode. Use only when implementing an actual OpenAI API integration. |

## Architecture Map

| Area | Key paths | Responsibility | Current risk |
| --- | --- | --- | --- |
| iPhone core client | `Sources/AgentPocketCore` | Mobile Bridge models, auth boundary, upload/task/download clients | Contract drift if result metadata expands without tests |
| iPhone UI | `Sources/AgentPocketUI`, `ios/AgentPocket` | Connect, capture, progress, result gallery, save/share | Result UX does not yet prove Master/Social local-recipe flow |
| Mock Mobile Bridge | `mock_bridge/agent_pocket_mock_bridge/app.py`, `server.py`, `qa.py` | Local runtime simulation and QA receipts | Legacy OpenAI smoke commands remain historical; local-recipe and share-sheet commands exist, but receipts are still missing |
| Provider bridge | `mock_bridge/agent_pocket_mock_bridge/photo_providers.py` | Adapter loading and manifest-to-variant mapping | Recipe metadata now propagates through task/QA status; still needs local-recipe simulator receipt |
| Photo Pack adapters | `photo-pack/adapters` | Runtime-side image provider implementations | `recipe_local` fixture renderer exists; runtime-vision recipe mode is implemented at adapter level and now sends Kaka scene-profile defaults; real Hermes/OpenClaw runtime receipt remains missing |
| Runtime Kit | `runtime-kit/kaka_mobile_runtime_kit`, `runtime-kit/hermes-plugin`, `runtime-kit/openclaw-skill` | Explicit-start local bridge launcher plus packaging notes for runtime integrations | Public Hermes/OpenClaw packaging, token revocation UI, login item, and production pairing codes are still planned |
| Product docs | `docs/agent-pocket-master-shot-direction.md`, `docs/mobile-bridge-api.md`, `docs/agent-pocket-readiness.md` | Direction, API contract, readiness evidence | Must keep implemented commands distinct from missing receipt evidence |
| UI docs | `docs/ui` | Visual prototype and product screen direction | HTML second polish pass is done; connect local/trusted badges, capture scene-pack/badge, and result recipe presentation are partially ported to SwiftUI; broader SwiftUI port remains pending |

## Phase Plan

### Phase 0: Lock The Execution Baseline

Purpose: prevent old OpenAI Images Gate F assumptions from leaking into the new local-recipe path.

Deliverables:

- This total development plan.
- Existing child plan kept as the detailed Gate F implementation plan.
- Explicit statement that Phase 1 uses the runtime-selected model and local renderer.

Validation:

```bash
rg -n "recipe_local|Local Recipe|Mobile Bridge|Hermes|OpenClaw|GPT-5.5|OpenAI Images" docs photo-pack mock_bridge Sources Tests ios
```

Expected:

- Docs describe local recipe as Phase 1.
- Any OpenAI Images references are marked legacy or optional.
- No iPhone client path requires provider API keys.

### Phase 1: Implement `recipe_local` Fixture Renderer

Status: implemented for fixture/local renderer mode on 2026-06-01. The `simulator-local-recipe-smoke` command exists, but the real receipt is not proven because no iOS Simulator was booted during the latest run. The adapter-level `runtime_vision` client is implemented: it posts photo context and Kaka scene-profile defaults to a compatible local recipe endpoint, validates strict `PhotoEditRecipe` JSON, and renders locally. The local renderer now also proves distinct scene defaults and `only_if_crop_below_target` upscale behavior with bounded scale metadata. A real Hermes/OpenClaw runtime receipt remains future work.

Purpose: prove Kaka can make a photo visibly better without any cloud image generation.

Primary files:

- Create `photo-pack/adapters/recipe_local.py`.
- Add `photo-pack/tests/test_recipe_local_adapter.py`.
- Modify `mock_bridge/agent_pocket_mock_bridge/photo_providers.py`.
- Modify or add `mock_bridge/tests/test_photo_pack_provider.py`.

Implementation requirements:

- Accept the existing Photo Pack adapter contract.
- Support fixture mode first.
- Support `runtime_vision` mode through a compatible local recipe endpoint without moving provider credentials into iPhone.
- Send Kaka scene-profile defaults in runtime recipe requests so compatible runtimes can align model output with the selected scene pack.
- Validate a strict `PhotoEditRecipe` shape.
- Clamp all numeric edit parameters.
- Render two variants:
  - `variant_clean_pro` labeled `Master`.
  - `variant_social_pop` labeled `Social`.
- Include crop metadata, recipe summary, renderer metadata, share caption, and basic image-difference metrics in `manifest.json`.
- Apply optional upscale only when the crop output is below target size, bounded by `max_scale`, and record input/output sizes plus scale.
- Fail closed on invalid recipes, unsupported style, unsafe crop, or missing renderer dependency.

Preferred first renderer:

- Use Pillow first because it is easy to test in the current Python QA lane.
- Keep the API neutral so ImageMagick, OpenCV, libvips, or Core Image can be swapped later.

Verification:

```bash
PYTHONPATH=mock_bridge python3 -m pytest photo-pack/tests/test_recipe_local_adapter.py -q
PYTHONPATH=mock_bridge python3 -m pytest mock_bridge/tests/test_photo_pack_provider.py -q
```

Exit criteria:

- Fixture image produces two nonblank output files.
- Output bytes differ from the source.
- `Master` and `Social` differ from each other.
- Manifest includes crop metadata and no-op detection metrics.

### Phase 2: Integrate Local Recipe Into Mock Bridge And QA

Status: mostly implemented for fixture/local renderer mode. `recipe_local` is registered in the provider registry, `provider-preflight --photo-provider recipe_local` passes, task/QA status preserves crop/renderer/QA/share metadata, and `simulator-local-recipe-smoke` uses a strict local-recipe evaluator. The adapter also supports `runtime_vision` recipe fetch/validate/render for compatible local runtimes. The actual simulator local-recipe receipt is still missing because it requires a booted Simulator.

Purpose: make `recipe_local` a first-class Mobile Bridge provider and produce receipts.

Primary files:

- Modify `mock_bridge/agent_pocket_mock_bridge/photo_providers.py`.
- Modify `mock_bridge/agent_pocket_mock_bridge/app.py` if task/result metadata needs to carry crop, recipe, renderer, or share captions.
- Modify `mock_bridge/agent_pocket_mock_bridge/qa.py`.
- Add or modify `mock_bridge/tests/test_qa_cli.py`.

Implementation requirements:

- Add `recipe_local` to `PROVIDER_ADAPTERS`.
- Preserve compatibility with existing `variant_clean_pro` and `variant_social_pop` IDs.
- Extend task completion metadata enough for iPhone result display. Current implementation exposes `renderer`, `composition`, `qa`, `recipe_summary`, and `share_caption`.
- Add QA commands or adapt existing commands so the documented local-recipe receipts are real, not planned-only. Current implementation adds `simulator-local-recipe-smoke`; remaining work is to run it against a booted Simulator and save the receipt.

Target receipts:

- `docs/qa-receipts/recipe-provider-preflight-latest.json`
- `docs/qa-receipts/simulator-local-recipe-photo-flow.json`

Verification:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight \
  --photo-provider recipe_local \
  --photo-pack-root photo-pack

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa test-receipt \
  --name python \
  --receipt-file docs/qa-receipts/python-tests-latest.json \
  --timeout 600 \
  -- python3 -m pytest mock_bridge/tests photo-pack/tests ios/tests -q
```

Exit criteria:

- Provider preflight for `recipe_local` does not ask for `OPENAI_API_KEY`.
- Python receipt passes.
- Simulator local-recipe receipt proves provider, variants, crop metadata, renderer metadata, difference metrics, and downloaded assets.

### Phase 3: Upgrade iPhone Result And Share UX

Status: partially implemented. Swift models decode local-recipe renderer, crop, QA, recipe summary, share caption, and `recommended_for` metadata. `CaptureFlowViewModel` preserves an original preview asset through task completion. The result view model prefers `recipe_summary` over legacy `explanation`, auto-downloads the selected result variant when a connection is available, auto-downloads newly selected missing Master/Social variants, exposes a comparison presentation for Original / selected Master or Social with save/share recommendation, difference score, and preview availability, turns local recipe metadata into Master Shot recipe chips/note, and `ResultGalleryView` renders available original/result image data, recipe chips/note, and the caption-backed iOS `ShareLink`. The downloaded result-gallery QA receipt now requires a nonempty share caption. `simulator-share-sheet-smoke` is implemented and validates a Debug `UIActivityViewController` handoff receipt. Remaining work is Simulator/manual visual evidence and generating the actual share-sheet receipt.

Purpose: make the iPhone feel like a real product: capture, process, compare, save, share.

Primary files:

- Modify `Sources/AgentPocketUI/ResultGalleryView.swift`.
- Modify `Sources/AgentPocketUI/ResultGalleryViewModel.swift`.
- Modify `Sources/AgentPocketUI/PhotoSaveFlow.swift` if share handoff needs a small native wrapper.
- Add or modify `Tests/AgentPocketUITests/ResultGalleryViewModelTests.swift`.
- Add UI-test coverage under `ios/AgentPocketPickerUITests` if reliable.

Implementation requirements:

- Show Original / Master / Social clearly.
- Keep Save and Share as the two primary post-result actions.
- Use iOS system share sheet first.
- Pass image plus generated caption when available.
- Keep direct WeChat, Xiaohongshu, X SDK posting out of Phase 1.

Verification:

```bash
swift test
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-downloaded-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-result-gallery-downloaded.png \
  --receipt-file docs/qa-receipts/simulator-result-gallery-downloaded-latest.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-share-sheet-smoke \
  --bundle-id com.kaka.AgentPocket \
  --screenshot-file /tmp/agent-pocket-simulator-share-sheet.png \
  --receipt-file docs/qa-receipts/share-sheet-flow-latest.json
```

Exit criteria:

- Result screen can switch variants.
- Share button is enabled only after selected variant is available.
- Receipt proves the selected variant is downloaded and a share caption is available.
- `simulator-share-sheet-smoke` or manual QA receipt proves share-sheet handoff was attempted and the system share controller was presented.

### Phase 4: Runtime Compatibility Path For Hermes And OpenClaw

Status: mock bridge and iPhone model support landed on 2026-06-02. `/mobile/v1/capabilities` now advertises `provider`, `renderer`, variant labels/IDs, crop aspects, crop-candidate support, and upscale-policy support; Swift decodes those fields while remaining compatible with older capability responses. SwiftUI connection/capture/result recovery copy now uses runtime-neutral local-agent wording instead of presenting Hermes as the only target, and capture-ready QA smoke writes `Send to Local Agent`, `send_to_local_agent_enabled`, and `sendToLocalAgentButton` while accepting older `Send to Hermes` receipts for compatibility. A new `runtime-kit/` scaffold now provides `doctor`, `start`, and `pairing-url` commands for explicit-start bridge packaging. Real Hermes/OpenClaw runtime adapters still need to implement and serve the same contract through a plugin, skill, native command, or sidecar.

Purpose: keep Kaka compatible with user-owned agents instead of becoming tied to one runtime or one model.

Primary files:

- Modify `docs/mobile-bridge-api.md`.
- Modify `photo-pack/skills/photo-edit/SKILL.md`.
- Add runtime adapter docs under `docs/` if needed.

Implementation requirements:

- Runtime reports capabilities through `/mobile/v1/capabilities`.
- Runtime owns model credentials and model choice.
- Recipe JSON is validated before rendering.
- The same Mobile Bridge contract works for Hermes, OpenClaw, or a sidecar.
- Runtime plugin/skill install does not start a listener; users explicitly enable **Kaka Mobile Bridge**.

Validation:

- Capability response advertises:
  - `provider: "recipe_local"`
  - `renderer: "local_parametric"`
  - `variant_labels: ["Master", "Social"]`
  - supported crop aspects
  - no provider key requirement on iPhone

Exit criteria:

- Docs, mocks, and Swift models describe a runtime-neutral contract.
- No UI copy says the only target is Hermes.
- Pairing copy can display a friendly runtime name, but the architecture remains compatible.
- Runtime Kit dry-run and tests prove the bridge defaults to loopback, `recipe_local`, and explicit LAN/Bonjour exposure.

### Phase 5: UI Prototype Polish And SwiftUI Port

Status: second HTML polish pass applied on 2026-06-02. The prototype now prioritizes the three main flow screens, keeps settings as a smaller auxiliary configuration screen, adds local/trusted pairing state, adds capture composition/focus affordances, improves the result comparison with a safer frame and slider affordance, and has refreshed Chinese/English screenshots. Native SwiftUI port has started with connect local/trusted badges, runtime-neutral local-agent copy, capture scene-pack labels, 4:5 composition badge, and result recipe chips/note; broader connect/capture/result visual port remains pending.

Purpose: turn the current visual direction into a usable, native iPhone interface.

Primary files:

- Modify `docs/ui/kaka-master-shot-ui-prototype.html`.
- Generate updated screenshots under `docs/ui/`.
- Port patterns into `Sources/AgentPocketUI` and `ios/AgentPocket/Features`.

Use `app-ui-implementer` for:

- Comparing the generated UI reference image with current HTML.
- Checking zh/en language isolation.
- Capturing current prototype screenshots.
- Reducing web-demo artifacts before SwiftUI porting.

Current UI improvement targets:

- Reduce the web-style top bar so phones become the visual focus.
- Make the capture screen feel more like a native camera surface.
- Improve photo crop positioning so the subject and mountains feel intentional.
- Keep settings available as a real configuration screen without letting it compete with the three main product screens.
- Use icon-first controls for camera, library, save, and share where SwiftUI has good system symbols.

Verification:

```bash
python3 /Users/kartz/.codex/skills/app-ui-implementer/scripts/compare_ui_screenshots.py \
  --reference "/Users/kartz/Downloads/已生成图像 1 (4).png" \
  --candidate docs/ui/kaka-master-shot-ui-prototype-zh.png \
  --out-dir /tmp/kaka-ui-compare \
  --prefix kaka-master-shot
```

Exit criteria:

- Chinese screenshot has no English UI labels except brand/runtime names.
- English screenshot has no Chinese UI labels.
- Phone screens look like implementation guidance, not a marketing poster.

### Phase 6: Real iPhone Gate F Closure

Purpose: prove the complete local-recipe flow on a physical iPhone when the device is available.

Target device evidence already exists:

- iPhone 16 Plus is paired and available in current readiness evidence.
- CLI build path is ready.

Primary receipt:

- `docs/qa-receipts/local-recipe-photo-flow.json`
- `docs/qa-receipts/share-sheet-flow-latest.json`

Verification:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan \
  --host <mac-ip-or-tailscale-ip> \
  --port 8765 \
  --device-id <coredevice-id> \
  --bundle-id com.kaka.AgentPocket \
  --no-bonjour \
  --photo-provider recipe_local \
  --receipt-file docs/qa-receipts/local-recipe-photo-flow.json

PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt \
  --file docs/qa-receipts/local-recipe-photo-flow.json \
  --phase photo-flow \
  --photo-provider recipe_local
```

Exit criteria:

- Real iPhone uploads a photo to the local runtime.
- Runtime produces local `Master` and `Social` variants.
- iPhone downloads and displays the result.
- Share handoff is proven.
- `docs/agent-pocket-readiness.md` reports Local Recipe Photo Flow passed.

## Recommended Workstreams

Use subagent-driven execution only after the plan is accepted or when implementation begins.

| Workstream | Scope | Primary files | Tooling |
| --- | --- | --- | --- |
| A. Recipe Renderer | `recipe_local` adapter, schema, clamp, fixture render | `photo-pack/adapters`, `photo-pack/tests` | `superpowers:test-driven-development`, Codegraph if provider integration is touched |
| B. Mock Bridge QA | Provider registry, QA commands, receipts | `mock_bridge/agent_pocket_mock_bridge`, `mock_bridge/tests` | Codegraph MCP, pytest, `superpowers:verification-before-completion` |
| C. iOS Result/Share | Master/Social result state, share sheet | `Sources/AgentPocketUI`, `Tests/AgentPocketUITests`, `ios/AgentPocket` | Build iOS Apps plugin, SwiftUI skills, `swift test` |
| D. Runtime Compatibility | Hermes/OpenClaw neutral contract and docs | `docs/mobile-bridge-api.md`, `photo-pack/skills/photo-edit/SKILL.md` | `project-codebase-onboarding-and-roadmap`, `openai-docs` only if provider-specific APIs are added |
| F. Runtime Kit Packaging | Explicit bridge launcher and Hermes/OpenClaw install path | `runtime-kit`, `docs/kaka-runtime-kit-plan.md` | pytest, Hermes/OpenClaw docs checks |
| E. Visual Product Polish | HTML prototype and SwiftUI visual direction | `docs/ui`, later `Sources/AgentPocketUI` | `app-ui-implementer`, Browser, Playwright if needed |

Merge order:

1. A first, because the renderer produces the artifact every later phase needs.
2. B second, because QA receipts make local-recipe evidence real.
3. C third, because result/share UX needs real metadata and assets.
4. D can run in parallel if it only edits docs and contracts.
5. E can run in parallel for prototype polish, but SwiftUI port should wait until C has stable state models.

## Risk Map

| Priority | Risk | Mitigation |
| --- | --- | --- |
| P0 | Provider/model credentials leak into iPhone | Keep credential-boundary scan in every release audit. |
| P0 | Recipe allows arbitrary code, URLs, provider calls, or generative edits | Strict schema, allowlisted operations, hard clamps, fail closed. |
| P0 | Renderer returns no-op images but claims success | Difference metrics and fixture visual receipts are required. |
| P1 | Smart crop cuts faces, text, product, or logos | Start conservative, add crop metadata, keep original/uncropped variant available. |
| P1 | Docs mention local-recipe commands before QA implements them | Update QA CLI and docs together; label planned commands until they exist. |
| P1 | First-run connection still feels like a developer tool | Package Runtime Kit as a visible Hermes/OpenClaw bridge toggle; keep long commands as internal diagnostics only. |
| P1 | UI promises social-platform posting that Phase 1 cannot deliver | Use system share sheet first; direct SDK posting is later. |
| P2 | UI prototype remains too poster-like for SwiftUI implementation | Iterate HTML with `app-ui-implementer`, then port only stable patterns. |
| P2 | Renderer dependency becomes hard to install | Start with Pillow; keep adapter interface neutral for ImageMagick/OpenCV/libvips/Core Image. |
| P3 | Naming drift between Kaka, Agent Pocket, Hermes, runtime | Brand externally as Kaka; keep Agent Pocket as module/app identifier until renamed intentionally. |

## Phase 1 Completion Gates

Phase 1 is complete only when every item below is proven by current artifacts.

| Gate | Required evidence |
| --- | --- |
| F1 Recipe provider proof | `recipe_local` exists, tests pass, preflight receipt does not require provider key |
| F2 Renderer proof | Master/Social outputs exist, differ from source, include crop metadata and QA metrics |
| F3 Simulator local recipe | `docs/qa-receipts/simulator-local-recipe-photo-flow.json` passes |
| F4 iOS result/share | Result UI switches variants; share-sheet handoff receipt or manual QA evidence exists |
| F5 Real iPhone proof | `docs/qa-receipts/local-recipe-photo-flow.json` passes with `recipe_local` |
| F6 Release audit | Python and Swift receipts pass; credential-boundary receipt passes; readiness doc is refreshed |

## Next Executable Sprint

Continue with Phase 2/3 evidence closure, then return to Phase 5 visual polish.

1. Boot an iOS Simulator manually or through the normal Xcode workflow, then run `simulator-local-recipe-smoke`.
2. Run `simulator-share-sheet-smoke` and save `docs/qa-receipts/share-sheet-flow-latest.json`.
3. Re-run Python and Swift receipts only if code changes again.
4. Package `runtime-kit/` behind a Hermes/OpenClaw visible bridge control so first-run users do not need terminal commands.
5. Continue using `app-ui-implementer` for targeted HTML checks, then port only stable patterns into SwiftUI.
6. When the iPhone is available, run `run-lan --photo-provider recipe_local` and verify `docs/qa-receipts/local-recipe-photo-flow.json`.
7. Refresh `docs/agent-pocket-readiness.md` after the receipts exist.

Suggested next commands:

```bash
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-local-recipe-smoke --host 127.0.0.1 --port 8769 --receipt-file docs/qa-receipts/simulator-local-recipe-photo-flow.json --screenshot-file /tmp/agent-pocket-simulator-local-recipe.png
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-share-sheet-smoke --bundle-id com.kaka.AgentPocket --screenshot-file /tmp/agent-pocket-simulator-share-sheet.png --receipt-file docs/qa-receipts/share-sheet-flow-latest.json
PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan --host <mac-ip-or-tailscale-ip> --device-id <coredevice-id> --photo-provider recipe_local --hermes-profile dev-lead --receipt-file docs/qa-receipts/local-recipe-photo-flow.json
```

Expected after the next sprint:

- Simulator local-recipe receipt exists and proves the rendered Master/Social result.
- Share-sheet receipt exists and proves the system share controller handoff.
- Real iPhone receipt exists when the physical device is available again.

## Stop Conditions

Stop and investigate rather than papering over evidence when:

- iPhone code would need a model-provider key.
- Runtime recipe output can bypass schema validation.
- Local renderer cannot produce visible improvements.
- Crop logic damages faces, text, logos, or product colors in fixtures.
- QA receipts fail but docs are about to be edited as though they passed.
- A social sharing requirement implies silent direct posting instead of user-controlled system share sheet.

## Open Product Decisions

These do not block Phase 1, but they should be decided before broader launch:

- Whether Kaka keeps Agent Pocket as the internal module name or renames modules later.
- Whether the first native renderer after Pillow should be Core Image, ImageMagick, OpenCV, or libvips.
- Whether `Social` defaults to 4:5, 1:1, or runtime-ranked output.
- Whether OpenClaw compatibility should be a sidecar first or native OpenClaw plugin first.
- Whether direct WeChat/Xiaohongshu/X sharing should be SDK-based or remain system-share based for privacy and simplicity.
