# Hermes Local Integration Notes

Date: 2026-06-12

This is a read-only reconnaissance note for adding a future Kaka `hermes`
provider. No Hermes configuration was changed, no bridge/runtime code was
changed, and no mutating HTTP requests or payload uploads were sent during this
survey. Any credential-like values observed in command output were omitted or
redacted.

## Summary

- Hermes Agent is installed locally at `~/.hermes/hermes-agent`, with CLI
  wrappers at `~/.local/bin/hermes` and `~/.local/bin/Hermes`.
- Version observed: `Hermes Agent v0.16.0 (2026.6.5)`, upstream `a2d7f538`.
- Active profile: `jiqimao`.
- Several `gateway run` processes are running under launchd for named profiles,
  but they do not expose local TCP agent endpoints. They keep SQLite state files,
  logs, gateway locks, Unix sockets, and outbound TLS connections.
- A Hermes dashboard is running on `127.0.0.1:9120`. It is a FastAPI/uvicorn web
  dashboard, not the OpenAI-compatible agent API.
- The installed Hermes code and local docs include an OpenAI-compatible API
  server platform on default port `8642`, but this machine does not currently
  have it enabled for the active profile. It requires `API_SERVER_KEY` even on
  loopback.
- Hermes also ships `hermes proxy`, a local OpenAI-compatible raw-model
  credential-attaching proxy on default port `8645`. It is not the Hermes agent
  API, is not currently running, and the available upstream adapters reported
  "not logged in".
- Hermes supports MCP both as a client and as a stdio MCP server via
  `hermes mcp serve`. No resident HTTP MCP endpoint was discovered.

## Read-Only Probe Log

### Process And Port Shape

Commands:

```bash
ps auxww | rg -i 'hermes'
lsof -nP -iTCP -sTCP:LISTEN | rg -i 'hermes|COMMAND|python|node|uvicorn|gunicorn|bun|deno|java|go|agent|runtime'
lsof -nP -p <hermes-pids>
```

Observed:

- `~/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile <name> gateway run --replace`
  processes for `cfo`, `daxiong`, `dev-lead`, `jiqimao`, `xiaojing`, and
  `xiaoqiang`.
- `~/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main -p default dashboard --port 9120 --host 127.0.0.1 --open-profile jiqimao --no-open`.
- TCP listeners: `127.0.0.1:9120` owned by the dashboard process. No Hermes
  listener was observed on `8642` or `8645`.
- Gateway processes held profile `state.db` files, `gateway.lock`, logs, Unix
  sockets, and outbound TLS connections. They did not listen on local TCP ports.

`hermes gateway list`:

```text
default stopped
cfo running
daxiong running
dev-lead running
impl-worker stopped
jiqimao running
review-worker stopped
xiaojing running
xiaoqiang running
```

`hermes profile list` reported `jiqimao` as current, model `claude-fable-5`,
gateway running. Other running profiles mostly reported `gpt-5.5`.

### Install, CLI, And Config Shape

Commands:

```bash
command -v hermes
command -v Hermes
hermes --version
hermes --help
hermes gateway --help
hermes dashboard --help
hermes proxy --help
hermes mcp --help
hermes acp --help
find ~/.hermes -maxdepth 3 -type f -o -type d
```

Observed:

- `hermes` and `Hermes` are small shell wrappers that unset `PYTHONPATH` and
  `PYTHONHOME`, then exec `~/.hermes/hermes-agent/venv/bin/hermes`.
- `/Applications/Hermes.app` is installed. Its bundle id is
  `com.nousresearch.hermes`, version `0.16.0`, category developer tools.
- `~/.hermes/active_profile` contains `jiqimao`.
- Hermes profile directories exist under `~/.hermes/profiles/`.
- LaunchAgent plists exist under `~/Library/LaunchAgents/ai.hermes.gateway-*.plist`.
  They set `HERMES_HOME` per profile and run `python -m hermes_cli.main
  --profile <name> gateway run --replace`.
- Root/profile `.env` files contain Feishu-related variables, `HERMES_AUTH_FILE`,
  proxy bypass variables, and in some profiles `DEEPSEEK_API_KEY`. Values were
  not read into this note.
- No `API_SERVER_KEY`, `API_SERVER_ENABLED`, `API_SERVER_HOST`, or
  `API_SERVER_PORT` entry was observed in the inspected `.env` key names.
- The active profile config has `platforms.feishu` only; no `platforms.api_server`
  block was observed.

`hermes status` summary:

- Project: `~/.hermes/hermes-agent`.
- Python: `3.11.13`.
- Model: `claude-fable-5`.
- Provider displayed as `GitHub Copilot`.
- API keys table showed Anthropic/OpenAI/OpenRouter unset and one DeepSeek key
  present; the key value was redacted from command output and is not included
  here.
- Gateway service: running, launchd-managed, active profile PID reported.

### Dashboard HTTP Probe

Commands used only GET/OPTIONS:

```bash
/usr/bin/curl -i http://127.0.0.1:9120/
/usr/bin/curl -i http://127.0.0.1:9120/api/health
/usr/bin/curl -i http://127.0.0.1:9120/openapi.json
/usr/bin/curl -i http://127.0.0.1:9120/api/status
/usr/bin/curl -i http://127.0.0.1:9120/v1/models
/usr/bin/curl -i http://127.0.0.1:9120/v1/chat/completions
/usr/bin/curl -i -X OPTIONS http://127.0.0.1:9120/v1/chat/completions
```

Observed:

- `GET /` returned HTML for the Hermes web dashboard. A dashboard session token
  appeared in the HTML and was redacted from local output; it is not recorded
  here.
- `GET /api/health` and `GET /api/profiles` returned `401 Unauthorized`.
- `GET /api/status` returned JSON including version `0.16.0`, release date
  `2026.6.5`, `hermes_home`, config path, env path, and dashboard-side status.
- `GET /openapi.json` returned a FastAPI OpenAPI document for the dashboard web
  app.
- `GET /v1/models` and `GET /v1/chat/completions` returned dashboard HTML due to
  SPA fallback. That confirms `9120` is not a useful OpenAI-compatible API base.
- `OPTIONS /`, `/openapi.json`, `/v1/models`, and `/v1/chat/completions`
  returned `405 Method Not Allowed`; `OPTIONS /api/profiles` returned `401`.

### Hermes API Server Capability From Local Code And Docs

Primary sources inspected:

- `~/.hermes/hermes-agent/gateway/platforms/api_server.py`
- `~/.hermes/hermes-agent/website/docs/user-guide/features/api-server.md`
- `~/.hermes/hermes-agent/website/docs/developer-guide/programmatic-integration.md`
- `~/.hermes/hermes-agent/website/docs/reference/environment-variables.md`

Facts:

- `gateway/platforms/api_server.py` defines an OpenAI-compatible HTTP adapter.
- Default bind is `127.0.0.1:8642`.
- It refuses to start without `API_SERVER_KEY`, including loopback-only binds.
- Environment variables:
  - `API_SERVER_ENABLED=true` enables it.
  - `API_SERVER_KEY` is the bearer token.
  - `API_SERVER_HOST` overrides host.
  - `API_SERVER_PORT` overrides port.
  - `API_SERVER_MODEL_NAME` overrides the model name advertised by `/v1/models`.
  - `API_SERVER_CORS_ORIGINS` controls browser CORS.
- Routes in code include:
  - `GET /health`
  - `GET /health/detailed`
  - `GET /v1/health`
  - `GET /v1/models`
  - `GET /v1/capabilities`
  - `GET /v1/skills`
  - `GET /v1/toolsets`
  - `POST /v1/chat/completions`
  - `POST /v1/responses`
  - `GET /v1/responses/{response_id}`
  - `DELETE /v1/responses/{response_id}`
  - `POST /v1/runs`
  - `GET /v1/runs/{run_id}`
  - `GET /v1/runs/{run_id}/events`
  - `POST /v1/runs/{run_id}/approval`
  - `POST /v1/runs/{run_id}/stop`
  - session endpoints under `/api/sessions`
- `GET /v1/capabilities` advertises features including chat completions,
  streaming, Responses API, run submission, run events SSE, run stop, approval
  response, session resources, skills API, and toolsets API. The source shows
  `memory_write_api: false`.
- `GET /v1/models` returns one model. The advertised name defaults to the active
  profile name unless `API_SERVER_MODEL_NAME` is set.
- Chat Completions and Responses both accept inline image inputs:
  - Chat Completions: `messages[].content` can include `{"type":"text"}` and
    `{"type":"image_url","image_url":{"url":"..."}}`.
  - Responses: `input[].content` can include `{"type":"input_text"}` and
    `{"type":"input_image","image_url":"..."}`.
  - Supported image URLs are `http(s)` URLs or `data:image/...` URLs.
  - Uploaded files, `file_id`, and non-image `data:` URLs return
    `400 unsupported_content_type`.
- Source comments and local docs describe streaming via SSE and Hermes custom
  tool progress events.

### Hermes Proxy Capability

Commands:

```bash
hermes proxy --help
hermes proxy start --help
hermes proxy status
hermes proxy providers
```

Observed:

- `hermes proxy start` runs a foreground OpenAI-compatible HTTP forwarder.
- Default bind is `127.0.0.1:8645`.
- Providers listed: `nous`, `xai`.
- `hermes proxy status` reported both available upstream adapters as not logged
  in on this machine.
- The proxy accepts any client bearer token and attaches the real upstream
  credential itself. It is intended for raw model inference through an external
  subscription, not for exposing the Hermes agent.

This is probably not the first Kaka provider target. It may be useful only as a
fallback if the goal is raw model completion and the user explicitly starts and
authenticates the proxy.

### MCP And Other Protocols

Commands:

```bash
hermes mcp --help
hermes acp --help
rg -n 'Programmatic Integration|MCP|API server' ~/.hermes/hermes-agent/website/docs
```

Observed:

- `hermes mcp serve` runs Hermes as a stdio MCP server exposing conversation
  tools such as conversation listing, reading messages, sending messages, and
  approval handling.
- Hermes can also connect to local stdio and remote HTTP MCP servers configured
  under `mcp_servers`.
- `hermes acp` starts a JSON-RPC-over-stdio ACP server for IDE integration.
- Hermes has a TUI gateway JSON-RPC protocol over stdio and WebSocket for the
  embedded TUI/dashboard path.
- No always-on MCP HTTP endpoint was discovered during this survey.

## Answers For Kaka

### Is There A Resident HTTP API?

Partly.

- Currently running: dashboard HTTP on `127.0.0.1:9120`.
- Currently not running: Hermes agent API server on `127.0.0.1:8642`.
- Available if enabled: `gateway/platforms/api_server.py`, started as part of
  `hermes gateway` when `API_SERVER_ENABLED=true` or `API_SERVER_KEY` is set.

The dashboard is not sufficient for Kaka provider work. It has authenticated
management endpoints and SPA fallback, and `/v1/*` on `9120` is not the model or
agent API.

### Is It OpenAI-Compatible?

Yes, if the Hermes API server platform is enabled. The relevant base URL would
be `http://127.0.0.1:8642/v1` by default, authenticated with
`Authorization: Bearer <API_SERVER_KEY>`.

`hermes proxy` is also OpenAI-compatible, but it is a raw upstream credential
proxy rather than the Hermes agent runtime. It should not be the default Kaka
Hermes target.

### Does It Support Multimodal Image Input?

Yes, in the API server path. It accepts OpenAI-style image content blocks with
`image_url`. For Kaka uploads, a provider can convert uploaded bytes to a
`data:image/<type>;base64,...` URL and include it in Chat Completions or
Responses input.

Limitations:

- Image bytes must be embedded as image data URLs or made available as `http(s)`
  image URLs.
- Uploaded files and non-image data URLs are rejected.
- PDF input is not accepted as a native file part by the API server. Kaka should
  extract text before sending, or treat PDF support as a later extension.

### What Is The Auth Model?

- Hermes API server: bearer token via `API_SERVER_KEY`. Required at startup even
  on loopback.
- Dashboard: dashboard session auth; not suitable for Kaka provider calls.
- Proxy: accepts any client bearer and attaches the real upstream credential.
  That means the proxy must not be exposed casually; it is not an authorization
  boundary.

For Kaka, keep the Hermes bearer only on the runtime side, mirroring the
Anthropic-provider boundary: no token in iPhone requests/responses, no token in
logs, no token in docs.

### How Are Models Configured Or Selected?

- Active Hermes profile currently reports model `claude-fable-5`.
- Root config observed `model.provider: openai-codex` and
  `model.default: gpt-5.5`; active profile state and CLI status may override
  that for `jiqimao`.
- API server `/v1/models` advertises a single model id. The source defaults it
  to the active profile name, or `hermes-agent` for default profile, unless
  `API_SERVER_MODEL_NAME` is set.
- Local programmatic integration docs state API server callers may include a
  `model` field in the request body or set `X-Hermes-Model`.

Recommendation for Kaka: use the Hermes API server advertised model if model
discovery succeeds; allow `KAKA_MODEL` or `KAKA_HERMES_MODEL` override later,
but keep provider startup explicit and fail fast if base URL/key are missing.

### Is There MCP Or Another Protocol Endpoint?

Yes:

- `hermes mcp serve` exposes Hermes conversations as a stdio MCP server.
- `hermes acp` exposes ACP over stdio.
- `tui_gateway/server.py` exposes JSON-RPC over stdio; there is also a WebSocket
  path used by the TUI/dashboard stack.

For Kaka's near-term mock_bridge provider, HTTP API server is the simplest
shape. MCP/ACP/TUI gateway are useful future options if Kaka needs richer
session control, approval events, or conversation management beyond the
existing `/mobile/v1` task abstraction.

## Recommended Kaka `hermes` Provider Shape

### Preferred: HTTP Adapter To Hermes API Server

Add a provider that calls a user-started Hermes API server:

- `KAKA_HERMES_BASE_URL`, default `http://127.0.0.1:8642/v1`.
- `KAKA_HERMES_API_KEY`, required for this provider.
- `KAKA_MODEL` or `KAKA_HERMES_MODEL`, optional. If unset, call
  `GET /v1/models` at provider startup or first request and use the returned id.
- Optional `KAKA_HERMES_TIMEOUT_SECONDS`.

Do not start or configure Hermes from Kaka. The provider should fail clearly if
`GET /health` or `GET /v1/models` cannot be authenticated, rather than silently
falling back to fake behavior.

Use `POST /v1/chat/completions` for the minimal implementation:

- It is familiar, OpenAI-compatible, and enough for image intake, vision skills,
  and universal intake.
- It can return non-streaming final assistant content for task results.
- Kaka can ask for strict JSON in the prompt and parse it into the existing
  Mobile Bridge result structures.

Consider `POST /v1/responses` later if Kaka wants server-side response chaining
or richer tool-call/state preservation. Consider `POST /v1/runs` if Kaka wants
SSE progress and cancellation semantics mapped into mobile task state.

### Secondary: OpenAI-Compatible Client Reuse

If Kaka already grows an OpenAI-compatible adapter for another provider, Hermes
can share most of that transport:

- Base URL: `http://127.0.0.1:8642/v1`.
- Auth: `Authorization: Bearer <KAKA_HERMES_API_KEY>`.
- Endpoint: `/chat/completions`.
- Image input: OpenAI `image_url` content blocks with `data:image/...`.

Keep Hermes-specific health/capability probing separate because `/v1/capabilities`
is useful and because the dashboard/proxy can otherwise be mistaken for the
agent API.

### Fallback: CLI Subprocess

`hermes -z/--oneshot` can run a prompt and print final text, but it is a weaker
provider target:

- It is text-oriented and harder to feed image bytes without writing temp files
  or relying on TUI/CLI attachment behavior.
- Structured JSON output is possible only by prompting and parsing stdout.
- Error mapping, timeouts, cancellation, and profile/session control are less
  predictable than HTTP.

Use CLI only if the HTTP API server is unavailable and Kaka needs a temporary
local-only proof of concept. It should remain opt-in.

## Capability Mapping

### `image_intake`

Input: image bytes and MIME type from Kaka upload storage.

Mapping:

1. Encode bytes as a data URL:
   `data:<mime-type>;base64,<base64>`.
2. Send a non-streaming `POST /v1/chat/completions` request with:
   - a system prompt that asks for the exact existing Kaka `image_intake` JSON
     shape,
   - a user content array containing text instructions and one `image_url` part.
3. Parse assistant content as JSON.
4. On parse failure, return a structured task failure in Kaka's existing task
   result surface.

Prompt should request the same fields Kaka fake/Anthropic image intake already
returns: summary and suggested skills, with no provider-specific leakage.

### Vision Skills

For OCR, translate, identify, and food:

1. Reuse the same data URL image block.
2. Change only the instruction text per skill:
   - OCR: extract visible text and return structured text blocks if Kaka expects
     them.
   - Translate: extract source text and target-language translation.
   - Identify: identify objects/entities and concise context.
   - Food: identify food items, likely ingredients, and useful caveats.
3. Ask Hermes for strict JSON matching the current Kaka task result structures.
4. Treat non-JSON, API errors, timeouts, and validation errors as task failures,
   not HTTP-layer exceptions.

Hermes API server supports image inputs, but the chosen active model/profile must
also be capable enough. A startup probe against `/v1/capabilities` and a small
manual real-image smoke test should gate release.

### Universal Intake

For text:

- Send text in a normal user message and ask for Kaka's universal intake summary
  and suggested skills JSON.

For URLs:

- Preferred first pass: send the URL as text and let Hermes use its configured
  web/tooling if the API server toolset allows it.
- Safer deterministic alternative: Kaka fetches/extracts the URL content and
  sends extracted text to Hermes. This avoids depending on Hermes tool
  configuration but moves fetch policy into Kaka.

For screenshots:

- Treat as image input using `data:image/...` and the same universal-intake JSON
  prompt.

For PDFs:

- Do not send as `input_file`; Hermes API server rejects file parts.
- Extract text on the Kaka/mock_bridge side, then send text. If page images are
  important, convert selected pages to images and use image blocks in a later
  provider version.

### Recall

Kaka's existing Recall behavior should remain on the Kaka/runtime side for the
first Hermes provider. Hermes API server has session and conversation continuity
headers:

- `X-Hermes-Session-Id`
- `X-Hermes-Session-Key`

Those can help scope Hermes-side memory or transcripts, but local source
capabilities show `memory_write_api: false`. Do not map Kaka Recall
Remember/Forget directly onto Hermes until there is a clear, tested Hermes API
for explicit memory writes/deletes.

## Risks And Unknowns

- The Hermes API server is present in code/docs but not enabled on this machine.
  A future implementation needs one manual enablement smoke:
  `API_SERVER_ENABLED=true API_SERVER_KEY=<redacted> hermes gateway`.
- Current running dashboard at `9120` can look superficially useful because it
  exposes OpenAPI and `/api/status`, but it is not the agent API and must not be
  used for Kaka provider calls.
- The API server allows tools to execute on the Hermes host. Kaka should treat
  the Hermes base URL/key as a high-trust runtime-side configuration, not as a
  phone-visible setting.
- Multimodal support is input-shape supported by the API server, but actual
  quality depends on the active Hermes model/provider and auxiliary vision
  routing.
- PDF handling is not native through the API server file parts. Kaka needs text
  extraction or page rendering before provider calls.
- `hermes proxy` has no meaningful client auth boundary; any bearer is accepted.
  It should not be exposed on LAN for Kaka unless wrapped by separate auth.
- The active profile currently reports `claude-fable-5`, while root config shows
  `openai-codex`/`gpt-5.5`; provider implementation should rely on API server
  model discovery or explicit env override, not parse config files.
- Dashboard HTML includes a transient session token for its own UI. Kaka should
  never scrape dashboard pages or reuse dashboard auth.
- More protocol-rich alternatives exist (`mcp serve`, ACP, TUI gateway), but they
  add subprocess/session complexity and do not map as cleanly to Kaka's current
  `/mobile/v1` task model.

## Suggested Manual Smoke For Future Implementation

After a Hermes provider exists, use a manually enabled API server:

```bash
API_SERVER_ENABLED=true \
API_SERVER_KEY=<redacted> \
API_SERVER_HOST=127.0.0.1 \
API_SERVER_PORT=8642 \
hermes gateway
```

Then probe only read endpoints first:

```bash
curl -H 'Authorization: Bearer <redacted>' http://127.0.0.1:8642/health
curl -H 'Authorization: Bearer <redacted>' http://127.0.0.1:8642/v1/models
curl -H 'Authorization: Bearer <redacted>' http://127.0.0.1:8642/v1/capabilities
```

Only after those pass should Kaka send task payloads to
`POST /v1/chat/completions`.
