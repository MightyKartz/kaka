# Host Private Adapter Implementation Guide

This guide is for external Hermes/OpenClaw host-shell teams that implement the
private adapter command consumed by Kaka Runtime Kit.

Runtime Kit defines the command contract, schemas, conformance runner, and pilot
readiness receipt. It does not implement, bundle, distribute, sign, or own any
proprietary Hermes/OpenClaw private API. The host team supplies that behavior
behind a host-owned command.

## Boundary

The private adapter is a runtime-side command bridge:

- Runtime Kit invokes the configured command with `shell=False`.
- Runtime Kit sends one sanitized JSON request on stdin.
- The command writes one JSON response on stdout.
- The command may write diagnostics to stderr.
- The iPhone never invokes this command.
- The phone API remains Kaka Mobile Bridge `/mobile/v1`.
- Host-native install, login-item, update, uninstall, log, health, port repair,
  and supervision behavior belongs to the host shell.

Do not add Hermes/OpenClaw proprietary API calls to Runtime Kit. Put those calls
inside the external host-owned command, for example
`hermes-kaka-host-api` or `openclaw-kaka-host-api`.

For production, that command should be bundled or internally discovered by the
Hermes Plugin or OpenClaw Skill/sidecar Host Extension. Asking ordinary users to
write this command, export `HERMES_KAKA_HOST_API` / `OPENCLAW_KAKA_HOST_API`, or
paste Runtime Kit command chains is a development/pilot fallback only, not the
intended install experience.

## Stdio And Argv Contract

Runtime Kit treats `--private-adapter-command` as a shell-style command string,
parses it with `shlex.split`, then launches the resulting argv with
`shell=False`.

Implementation requirements:

- Provide an executable command path, optionally followed by fixed arguments.
- Read the complete stdin payload as UTF-8 JSON.
- Write exactly one JSON object to stdout.
- Do not print banners, progress logs, prompts, or human text to stdout.
- Use stderr only for diagnostics that are safe for local host logs.
- Do not require interactive input.
- Return before the configured timeout.

Example invocation shape:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-adapter-run \
  --runtime hermes \
  --adapter private \
  --private-adapter-command "/path/to/hermes-kaka-host-api" \
  --action-id run_health_check \
  --installed \
  --bridge-enabled
```

## Stdin Request Schema

The stdin payload conforms to `kaka.host_private_adapter_request.v1`, frozen by
`runtime-kit/packaging/host-private-adapter-request.schema.json`.

Top-level fields:

- `schema_version`: always `kaka.host_private_adapter_request.v1`.
- `surface`: always `hermes_openclaw_host_private_adapter_command`.
- `runtime`: `hermes` or `openclaw`.
- `action_id`: one of the 9 host adapter actions below.
- `adapter`: the host-native adapter binding for the action.
- `approved`: whether the user explicitly approved this invocation.
- `runtime_side_only`: always `true`.
- `state`: the current safe runtime-side state.
- `host_action`: the safe action descriptor from the host package.
- `safety`: invariant safety flags.
- `forbidden_phone_safe_fields`: fields that must never cross into phone-safe
  summaries.

The `state` object contains exactly:

- `installed`: boolean.
- `start_with_runtime`: boolean.
- `process_state`: `stopped`, `running`, `unhealthy`, or `unknown`.
- `process_supervision`: `not_configured`, `host_managed`, or `misconfigured`.
- `health_status`: `unknown`, `healthy`, or `unhealthy`.
- `port_conflict`: boolean.

The `host_action` object is allowlisted to:

- `id`
- `owner`
- `adapter`
- `mutates_host_state`
- `requires_explicit_user_approval`
- `runtime_side_only`
- `enabled`
- `label`
- `style`
- `target`
- `url`

Do not depend on any field outside the request schema. Runtime Kit intentionally
does not pass private paths, tokens, credentials, raw logs, process IDs, prompts,
or retrieval rows to this command.

## Stdout Response Schema

The stdout payload must be a single JSON object conforming to
`kaka.host_private_adapter_response.v1`, frozen by
`runtime-kit/packaging/host-private-adapter-response.schema.json`.

Required top-level fields:

- `schema_version`: always `kaka.host_private_adapter_response.v1`.
- `ok`: boolean success indicator.
- `mutated_host_state`: boolean. Use `true` only when the command successfully
  changed host state for an approved mutating action.
- `state`: complete state object with the same six fields and enum values as the
  request state.
- `detail`: object with at least `private_api_called`.

Optional top-level field:

- `error`: object with `code` and `message`, used when `ok` is `false`.

The `detail` object is allowlisted to:

- `private_api_called`: boolean, required.
- `private_api_provider`: string up to 64 characters.
- `host_api_level`: string up to 64 characters.
- `url`: string up to 2048 characters.
- `target`: string up to 64 characters.
- `checked_bridge`: boolean.
- `enabled`: boolean.

Runtime Kit normalizes successful private responses and records
`private_api_called: true`. Extra top-level fields, extra detail fields, invalid
types, invalid enum values, or invalid JSON cause a safe invalid-response
failure.

## Stderr, Exit Codes, And Timeouts

Stdout is machine JSON only. Stderr is diagnostic text only and must not contain
tokens, credentials, private prompts, raw provider responses, raw retrieval data,
or host-private internals.

Exit rules:

- Exit code `0`: Runtime Kit parses stdout as the adapter response.
- Non-zero exit: Runtime Kit returns a safe
  `private_host_adapter_command_failed` result with `mutated_host_state: false`.
- Missing or invalid command: Runtime Kit returns
  `private_host_adapter_command_failed`.
- Timeout: Runtime Kit returns `private_host_adapter_timeout`.
- Invalid stdout JSON or invalid response schema: Runtime Kit returns
  `private_host_adapter_invalid_response`.

The default timeout is 10 seconds unless the caller supplies
`--private-adapter-timeout-seconds`. The command must either complete within
that window or fail fast with a valid JSON error response.

## Action Semantics

There are 9 action IDs. The host command must implement the private host API
behavior behind each action without changing the phone API.

| action_id | adapter | Mutates | Semantics |
| --- | --- | --- | --- |
| `install_runtime_package` | `host_native_install` | Yes | Install or stage the runtime package. Must not start the bridge, bind a port, advertise Bonjour, mint mobile credentials, or create a login item. |
| `enable_start_with_runtime` | `host_native_enable_login_item` | Yes | Enable the host-owned start-with-runtime/login-item setting after explicit approval. |
| `disable_start_with_runtime` | `host_native_disable_login_item` | Yes | Disable the host-owned start-with-runtime/login-item setting after explicit approval. |
| `update_runtime_package` | `host_native_update` | Yes | Run the host-owned update flow for the runtime package. |
| `uninstall_runtime_package` | `host_native_uninstall` | Yes | Remove the host-owned runtime package and reset lifecycle state. |
| `open_runtime_logs` | `host_native_open_logs` | No | Open or reveal safe host-side logs for the local user. Do not return log contents. |
| `run_health_check` | `host_native_health_check` | No | Check bridge/process/package health and update `health_status`, `process_state`, and related safe state. |
| `repair_port_conflict` | `host_native_repair_port` | Yes | Attempt host-owned remediation for a detected port conflict. |
| `supervise_bridge` | `host_native_supervisor` | Yes | Configure host-owned bridge process supervision. |

## Approval Rules

Mutating actions must require explicit user approval. Runtime Kit blocks
mutating actions before the private command is called when `approved` is false.
The command should still enforce the same rule defensively.

Mutating actions:

- `install_runtime_package`
- `enable_start_with_runtime`
- `disable_start_with_runtime`
- `update_runtime_package`
- `uninstall_runtime_package`
- `repair_port_conflict`
- `supervise_bridge`

Non-mutating actions:

- `open_runtime_logs`
- `run_health_check`

For an unapproved mutating request, return either a valid JSON error response
with `ok: false` and `mutated_host_state: false`, or rely on Runtime Kit's
pre-call block. Never mutate host state when `approved` is false.

## State Update Rules

Every response must include a complete state object. Preserve incoming state for
fields the action did not change, and update only the fields the host command can
truthfully observe or mutate.

Recommended state behavior:

- Install success sets `installed: true`, keeps `start_with_runtime: false`
  unless separately approved, and does not imply the bridge is running.
- Enable start-with-runtime success sets `start_with_runtime: true`.
- Disable start-with-runtime success sets `start_with_runtime: false`.
- Update success keeps or sets `installed: true`.
- Uninstall success sets `installed: false`, `start_with_runtime: false`,
  `process_state: stopped`, `process_supervision: not_configured`,
  `health_status: unknown`, and `port_conflict: false`.
- Health check success may set `health_status`, `process_state`,
  `process_supervision`, and `port_conflict` based on observed host facts.
- Port repair success should set `port_conflict: false` only after remediation
  actually succeeded.
- Supervision success should set `process_supervision: host_managed` when the
  host supervisor is actually configured.

Set `mutated_host_state: true` only when `ok: true`, the action is mutating, and
the host command actually changed host state. For failed responses, set
`mutated_host_state: false`.

## Error Response Rules

When the host command can return JSON, prefer a schema-valid error response:

```json
{
  "schema_version": "kaka.host_private_adapter_response.v1",
  "ok": false,
  "mutated_host_state": false,
  "state": {
    "installed": false,
    "start_with_runtime": false,
    "process_state": "stopped",
    "process_supervision": "not_configured",
    "health_status": "unknown",
    "port_conflict": false
  },
  "detail": {
    "private_api_called": true,
    "private_api_provider": "hermes",
    "host_api_level": "v1"
  },
  "error": {
    "code": "host_install_failed",
    "message": "Host install failed."
  }
}
```

Error codes must be lowercase safe identifiers using letters, digits,
underscore, colon, or hyphen, up to 64 characters. Error messages are local
runtime-side diagnostics up to 256 characters. Runtime Kit intentionally
normalizes private host error messages before returning the higher-level
host-adapter result, so do not rely on private details surviving the boundary.

## Forbidden Phone-Safe Fields

These fields must not appear in phone-safe summaries, stdout detail, stderr
diagnostics intended for users, pilot receipts, or any mobile-facing payload:

- `runtime_store_path`
- `recall_search_endpoint`
- `provider_keys`
- `auth_env_files`
- `mobile_tokens`
- `tls_private_key_paths`
- `env_file`
- `auth_file`
- `auth_files`
- `provider_credentials`
- `mobile_bearer_token`
- `tls_private_key_path`
- `hidden_prompt`
- `hidden_prompts`
- `raw_embeddings`
- `index_rows`
- `retrieval_index_rows`
- `task_logs`
- `raw_provider_responses`
- `process_ids`
- `host_log_paths`

The private adapter response schema has a narrow detail allowlist. Keep private
paths, credentials, process identifiers, raw logs, raw model/provider output, and
retrieval internals out of the response.

## Conformance Command

Before preflight or conformance, generate the P3.4i host-shell pilot request
bundle from the Kaka repository root and send it to the external host shell
team:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime hermes \
  --request-id P3.4-hermes \
  --pilot-owner "Hermes host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --artifact-root artifacts/hermes
```

For OpenClaw:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-request \
  --runtime openclaw \
  --request-id P3.4-openclaw \
  --pilot-owner "OpenClaw host team" \
  --expected-private-adapter-command-path "~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api" \
  --artifact-root artifacts/openclaw
```

`host-shell-pilot-request` emits
`kaka.host_shell_pilot_request.v1` on surface
`hermes_openclaw_host_shell_pilot_request`. It is a read-only materials request
bundle answering what the host team must provide before the pilot can be
completed. It lists the host-owned private adapter command binary,
request/response contract acknowledgement, the 9-action matrix, native
distribution channel, signature/notarization material, update feed,
install/update/failure-recovery drill receipts, and release notes. The required
audit refs are `native_channel_ref`, `signature_subject`,
`notarization_team_id`, `update_feed_ref`, `install_receipt_ref`,
`update_receipt_ref`, `failure_recovery_receipt_ref`, and
`release_notes_ref`. The expected Runtime Kit artifacts are the P3.4f
preflight JSON, P3.2 conformance JSON, P3.4b pilot receipt JSON, P3.4e handoff
JSON, P3.4h artifact review JSON, and P3.4j evidence manifest JSON.

`request_status: "ready_to_send"` and `ok: true` mean only that the request
package was generated successfully. The command always reports
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`. It does not invoke the private
adapter command, run preflight, run conformance, read artifacts, fetch audit
refs, mutate host state, submit handoff, or change the iPhone `/mobile/v1`
surface.

After sending the request and collecting the host-owned materials, run the
P3.4f preflight from the Kaka repository root to check local host inputs without
invoking the private command:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-preflight \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

The preflight emits `kaka.host_shell_pilot_preflight.v1` on
`hermes_openclaw_host_shell_pilot_preflight`. It checks host shell app/CLI
presence, explicit/env/manifest/well-known private adapter command discovery,
and PATH command availability as informational-only. It does not run
conformance, does not invoke the private adapter command, does not fetch audit
refs, does not mutate host state, and does not expose phone `/mobile/v1`.
`ok: true` with `status: "ready_for_conformance"` means the host can run the
conformance command next; it is not P3.4 completion and keeps
`p3_4_complete: false`.

Before conformance/report/handoff, generate the P3.4g host operator runbook:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

For OpenClaw:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-runbook \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api"
```

The runbook emits `kaka.host_shell_pilot_runbook.v1` on
`hermes_openclaw_host_shell_pilot_runbook`. It includes the brief, pilot target,
preflight summary, ordered steps, command artifacts, evidence requirements, and
acceptance gates. It composes P3.4f preflight only: it does not invoke the
private adapter command, run conformance, fetch evidence refs, mutate host
state, or expose phone `/mobile/v1`. `ok: true` with
`runbook_status: "ready_for_conformance"` means the host can run conformance
next; it is not handoff submission readiness and not P3.4 completion. It always
keeps `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

P3.4h artifact review comes after the request, preflight, conformance report,
pilot receipt, and handoff JSON files have already been generated; it is not a
substitute for the request, runbook, or conformance execution.

Run conformance from the Kaka repository root after the external command exists:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime hermes \
  --private-adapter-command "/path/to/hermes-kaka-host-api"
```

For OpenClaw:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-private-adapter-conformance \
  --runtime openclaw \
  --private-adapter-command "/path/to/openclaw-kaka-host-api"
```

The conformance report schema is `kaka.host_private_adapter_conformance.v1`.
It validates the 9 required action IDs plus negative checks for unapproved
install and disabled health-check behavior. Passing conformance proves only that
the external command satisfies the Runtime Kit command boundary; it does not
make Kaka the owner or distributor of the host binary.

## P3.4 Pilot Ready Command

P3.4 pilot readiness requires a real external host-owned command outside the
Kaka repository, a passing conformance run, verified native distribution,
verified signature, verified update feed, install/update/failure drills, and
release notes.

Evidence reference flags are optional host-supplied pointers for review. They
do not set the verified booleans automatically, and Runtime Kit does not
download, open, read, or validate the referenced material.

Hermes example:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-report \
  --runtime hermes \
  --private-adapter-command "/Users/kartz/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --distribution-source signed_download \
  --distribution-channel stable \
  --package-version 1.0.0 \
  --host-api-level v1 \
  --native-channel-verified \
  --signature-verified \
  --update-feed-verified \
  --install-verified \
  --update-verified \
  --failure-recovery-verified \
  --release-notes-verified \
  --native-channel-ref "Hermes stable channel receipt #2026-06-06" \
  --signature-subject "Developer ID Application: Example Hermes Team" \
  --notarization-team-id TEAMID1234 \
  --update-feed-ref "https://updates.example.invalid/hermes/kaka/appcast.xml" \
  --install-receipt-ref "qa://hermes/install/2026-06-06" \
  --update-receipt-ref "qa://hermes/update/2026-06-06" \
  --failure-recovery-receipt-ref "qa://hermes/recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/hermes/kaka/release-notes/1.0.0"
```

OpenClaw example:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-report \
  --runtime openclaw \
  --private-adapter-command "/Users/kartz/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api" \
  --distribution-source signed_download \
  --distribution-channel stable \
  --package-version 1.0.0 \
  --host-api-level v1 \
  --native-channel-verified \
  --signature-verified \
  --update-feed-verified \
  --install-verified \
  --update-verified \
  --failure-recovery-verified \
  --release-notes-verified \
  --native-channel-ref "OpenClaw stable channel receipt #2026-06-06" \
  --signature-subject "Developer ID Application: Example OpenClaw Team" \
  --notarization-team-id TEAMID1234 \
  --update-feed-ref "https://updates.example.invalid/openclaw/kaka/appcast.xml" \
  --install-receipt-ref "qa://openclaw/install/2026-06-06" \
  --update-receipt-ref "qa://openclaw/update/2026-06-06" \
  --failure-recovery-receipt-ref "qa://openclaw/recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/openclaw/kaka/release-notes/1.0.0"
```

The receipt must report `status: "ready"` and
`release_readiness.can_mark_p3_4_complete: true` before the external pilot is
considered ready.

For release review, wrap the same receipt in the P3.4e handoff package:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-handoff \
  --runtime hermes \
  --private-adapter-command "/Users/kartz/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api" \
  --distribution-source signed_download \
  --distribution-channel stable \
  --package-version 1.0.0 \
  --host-api-level v1 \
  --native-channel-verified \
  --signature-verified \
  --update-feed-verified \
  --install-verified \
  --update-verified \
  --failure-recovery-verified \
  --release-notes-verified \
  --native-channel-ref "Hermes stable channel receipt #2026-06-06" \
  --signature-subject "Developer ID Application: Example Hermes Team" \
  --notarization-team-id TEAMID1234 \
  --update-feed-ref "https://updates.example.invalid/hermes/kaka/appcast.xml" \
  --install-receipt-ref "qa://hermes/install/2026-06-06" \
  --update-receipt-ref "qa://hermes/update/2026-06-06" \
  --failure-recovery-receipt-ref "qa://hermes/recovery/2026-06-06" \
  --release-notes-ref "https://example.invalid/hermes/kaka/release-notes/1.0.0"
```

`host-shell-pilot-handoff` emits schema
`kaka.host_shell_pilot_handoff.v1` on surface
`hermes_openclaw_host_shell_pilot_handoff`. It preserves the embedded
`host-shell-pilot-report` readiness result, requires every P3.4d audit ref for
`handoff_status: "ready_to_submit"`, and otherwise reports
`handoff_status: "incomplete"`. The bundle includes deliverables,
`release_handoff`, audit-ref completeness, and safety flags, but it does not
fetch audit refs, expose phone `/mobile/v1`, or bundle the proprietary command
binary. It always reports `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell` because final P3.4 completion is
owned by the external host shell.

After those four JSON artifacts are written to disk, the P3.4h review command
checks whether they are ready for external review:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-artifact-review \
  --runtime hermes \
  --preflight-json artifacts/hermes/preflight.json \
  --conformance-json artifacts/hermes/conformance.json \
  --receipt-json artifacts/hermes/pilot-receipt.json \
  --handoff-json artifacts/hermes/handoff.json
```

Use `--runtime openclaw` with the corresponding OpenClaw artifact paths for an
OpenClaw review. `host-shell-pilot-artifact-review` emits schema
`kaka.host_shell_pilot_artifact_review.v1` on surface
`hermes_openclaw_host_shell_pilot_artifact_review`. It summarizes load/schema
status and cross-checks runtime, embedded conformance, embedded receipt,
audit refs, and private command consistency. It reports
`review_status: "ready_for_external_review"` only when the artifacts are ready
and consistent. It does not invoke the private adapter command, run
conformance, fetch refs, mutate host state, or expose phone `/mobile/v1`; it
always keeps `p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

After artifact review is ready, generate the P3.4j evidence manifest for the
external host-owned archive:

```bash
PYTHONPATH=runtime-kit python3 -m kaka_mobile_runtime_kit host-shell-pilot-evidence-manifest \
  --runtime hermes \
  --package-id P3.4-hermes \
  --artifact-root artifacts/hermes \
  --request-json artifacts/hermes/request.json \
  --runbook-json artifacts/hermes/runbook.json \
  --archive-filename kaka-p3.4-hermes-pilot-evidence.zip
```

Use `--runtime openclaw` and `artifacts/openclaw` for an OpenClaw archive index.
`host-shell-pilot-evidence-manifest` emits schema
`kaka.host_shell_pilot_evidence_manifest.v1` on surface
`hermes_openclaw_host_shell_pilot_evidence_manifest`. It reads local JSON files,
records byte sizes and SHA-256 hashes, blocks missing, oversized,
schema-mismatched, or `ok: false` artifacts, and can report
`manifest_status: "ready_for_archive"` when the artifact set is ready for an
external host-owned archive. It does not invoke the private adapter command,
run conformance, fetch refs, submit handoff, mutate host state, create the
archive, or expose phone `/mobile/v1`; it always keeps
`p3_4_complete: false` and
`p3_4_completion_owner: external_host_shell`.

If `--private-adapter-command` is omitted, Runtime Kit discovers the command in
this order:

1. Runtime environment variable: `HERMES_KAKA_HOST_API` or
   `OPENCLAW_KAKA_HOST_API`.
2. Runtime manifest entrypoint: `host_private_adapter.command`.
3. Well-known path under `~/Library/Application Support/<Runtime>/Kaka/`.

## Fake Fixtures

The fake private host API fixture is a conformance-only behavior model. It is
useful for Runtime Kit regression checks and for understanding expected state
transitions, but it is not a pilot binary, not a distribution artifact, and not a
Hermes/OpenClaw private API implementation.

A pilot receipt that uses the fake fixture is `synthetic_only` and cannot mark
P3.4 complete. P3.4 requires a real external command owned and distributed by
the host team.
