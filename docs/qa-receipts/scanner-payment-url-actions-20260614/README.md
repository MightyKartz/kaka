# Scanner Payment URL Actions QA

Date: 2026-06-14
Branch: `codex/scanner-payment-url-actions`

## Scope

- Tightened the local Agent Scanner action policy for payment-like HTTPS URLs.
- A scanned URL such as `https://example.com/pay/invoice?id=42` now stays on the visible URL review path: ask the local agent, copy, or save to Inbox.
- The Open action is withheld for payment-like HTTPS URLs. No Mobile Bridge, runtime, provider, Recall, upload, or Host Extension behavior changed.

## TDD Evidence

- Red: `swift test --filter AgentScanActionPolicyTests/testPaymentLikeHTTPSURLCanBeReviewedWithoutOpenAction` initially failed because the existing policy returned text actions (`askAgentAboutText`, `copy`) for the HTTPS payment URL.
- Green: `swift test --filter AgentScanActionPolicyTests` passed after the policy change.

## Verification

- `swift test --filter AgentScanActionPolicyTests`: 7 tests, 0 failures.
- `swift test`: 457 tests, 0 failures.
- `git diff --check`: passed with empty output.

## Logs

- `swift-test-agent-scan-policy.log`
- `swift-test.log`
- `git-diff-check.log`

## Residual Risk

- This is a deterministic policy/test slice only. No simulator or real-device camera scan was run in this pass.
- Payment-like URL detection remains heuristic; Conversation B should review whether the withheld-Open set is too broad or too narrow for common payment/checkout links.
