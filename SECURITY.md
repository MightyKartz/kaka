# Security Policy

Kaka is an early-stage local-first photo agent client. Please treat all security and privacy behavior as under active development until a stable release is tagged.

## Supported Versions

Only the current `main` branch is supported during the MVP phase.

## Credential Boundary

Kaka is designed so the iPhone app does not store model-provider API keys.

- The iPhone stores only a Mobile Bridge endpoint and mobile bearer token.
- Hermes, OpenClaw, or a compatible runtime owns model choice and provider credentials.
- Runtime plugins or skills must not auto-start a LAN listener during installation.
- LAN exposure, Bonjour advertisement, and start-at-login behavior must be explicit user opt-ins.
- Logs, doctor commands, QA reports, and screenshots must not include API keys, bearer tokens, auth files, or private device identifiers.

## Reporting A Vulnerability

Please do not publish secrets, exploit details, private device IDs, or private network information in a public issue.

Use GitHub's private vulnerability reporting flow for this repository when available. If it is not available, contact the maintainer through GitHub and share only the minimum detail needed to establish a secure reporting channel.

Useful reports include:

- a short description of the issue
- affected commit or file path
- reproduction steps without private credentials
- expected impact
- suggested fix, if known

## Local Receipts

Local QA receipts often contain machine paths, runtime profile names, local IPs, simulator IDs, or physical device identifiers. They are intentionally excluded from the public repository. Commit only redacted or synthetic receipts.
