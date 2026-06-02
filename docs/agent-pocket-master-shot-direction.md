# Agent Pocket Master Shot Direction

## Product Thesis

Agent Pocket should not become a generic visual assistant or another closed AI photo editor. The strongest first product is a private-runtime **Master Shot Agent**:

1. iPhone captures or selects a real photo.
2. The photo goes to the user's compatible local runtime through Mobile Bridge.
3. The runtime's configured multimodal model reads the image like a photographer.
4. The runtime returns a strict local edit recipe.
5. The Mac renders deterministic edits: crop, tone, local contrast, denoise, sharpen, optional upscale, and platform-ready variants.
6. iPhone shows an obvious before/after result and opens the system share sheet.

This keeps the phone simple, protects provider keys, and preserves faces, products, text, logos, and real-world detail because Phase 1 does not regenerate pixels.

## Positioning

Chinese positioning:

> Agent Pocket：把 iPhone 变成你私有智能体的摄影成片入口。

English positioning:

> Agent Pocket turns your iPhone into a private-agent camera that produces share-ready master shots.

## Why This Is The Wedge

General visual assistants already exist in system products and chat apps. Generic mobile clients for local AI also exist. Agent Pocket's useful wedge is narrower and more concrete:

- **Not generic Q&A:** the first job is "make this photo look professionally finished."
- **Not cloud-first AI retouching:** the user-owned runtime owns model calls, rendering, assets, and retention.
- **Not raw workflow remote control:** the iPhone gives one-tap capture, result review, save, and share.
- **Not generative replacement first:** Phase 1 uses bounded edits so faces, products, text, and scene truth survive.

## Phase 1 Product Loop

1. Pair to a compatible runtime with QR or local discovery.
2. Capture or choose a photo.
3. Tap one primary action: **Make Master Shot**.
4. Runtime analyzes the image and chooses crop plus edit recipe.
5. Mac renders:
   - `Master`: the best realistic, professional version.
   - `Social`: stronger crop/color/contrast for social platforms.
6. iPhone compares Original / Master / Social.
7. User saves or shares through the iOS system share sheet.

The first screen should be the usable capture/result surface, not a marketing landing page or a chat interface.

## Scene Packs

Keep four Kaka scene packs for Phase 1:

- `natural_enhance`: everyday photos that should look intentionally edited but still natural.
- `portrait_polish`: people photos with face-safe lighting, skin tone correction, and identity preservation.
- `product_shot`: product or object photos with cleaner whites, sharper edges, and logo/text preservation.
- `social_cover`: platform-ready crop, stronger color, and title-safe composition.

The user does not need to see technical sliders. Advanced controls can stay inside the runtime recipe and QA receipts.

## Recipe Requirements

`PhotoEditRecipe` is metadata. It is not a pixel JSON file and not a generative prompt. The source photo remains the canonical image.

The recipe should support:

- global tone: exposure, contrast, highlights, shadows, white balance, vibrance, saturation;
- local polish: subject boost, background falloff, clarity, sharpen, denoise, skin-safe smoothing;
- composition: crop candidates, selected crop, aspect ratio, title-safe area, subject bounding hint;
- optional upscale: only when crop output would be too small for the target;
- preservation flags: identity, text, logo, product color, object count;
- platform targets: original, 4:5, 1:1, 16:9, or runtime-advertised presets;
- aesthetic score and short explanation for ranking variants.

## Renderer Requirements

Start with deterministic rendering through Pillow/OpenCV/ImageMagick/libvips in the mock/runtime path. Core Image can become the preferred native renderer later.

The renderer must:

- clamp every model-suggested value;
- reject arbitrary code, provider URLs, and unsupported filter graphs;
- preserve source subject, identity, text, logos, and object count;
- create two visibly different variants;
- fail closed rather than silently returning a no-op image;
- produce QA metrics such as dimensions, crop rectangle, basic image-difference score, and output file size.

## Development Roadmap

### Phase 1A: Master Shot MVP

- Implement `recipe_local` fixture mode.
- Render `Master` and `Social` variants.
- Add simulator local-recipe smoke.
- Prove before/after, save, and share-sheet handoff.

### Phase 1B: Smart Crop

- Add crop candidates for original, 4:5, and 1:1.
- Use subject/saliency hints from the runtime model first, with CV fallback later.
- Return crop metadata so iPhone can explain or switch variants.

### Phase 1C: Optional Upscale

- Add `upscale_policy`.
- Upscale only when crop resolution is below target output.
- Prefer conservative local upscaling first; Real-ESRGAN/Core ML can be later adapters.

### Phase 1D: Aesthetic Ranking

- Score candidates with the runtime model or a local aesthetic scorer.
- Default to the highest-ranked Master result.
- Keep "try another crop" as a simple user action.

### Phase 2: Agentic Expansion

After Master Shot is reliable, the same Mobile Bridge can support follow-up instructions, batch album polish, product listing assets, receipts/doc capture, or video. Do not dilute Phase 1 with generic visual assistant chat.

## Research Anchors

- MIT-Adobe FiveK shows the value of learning from expert retouching decisions: https://data.csail.mit.edu/graphics/fivek/
- NIMA frames image quality as learned aesthetic assessment: https://arxiv.org/abs/1709.05424
- Deep Photo Cropper and Enhancer supports joint crop and enhancement as a meaningful visual-quality path: https://arxiv.org/abs/2008.00634
- Real-ESRGAN is a practical reference for real-world image restoration/upscaling: https://arxiv.org/abs/2107.10833
- Topaz Photo AI Autopilot validates the "automatic detect and enhance" product pattern: https://docs.topazlabs.com/topaz-photo/functions/autopilot-and-configuration
- Google Lens and Apple Visual Intelligence show why generic visual understanding is already a platform-level battleground: https://lens.google/ and https://support.apple.com/en-gb/guide/iphone/iph12eb1545e/ios
