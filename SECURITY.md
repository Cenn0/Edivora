# Security Policy

Edivora is an experimental, local-first desktop application. No stable release is currently supported for security fixes. The public source tree is not a security certification of bundled codecs, Qt components or machine-learning models.

## Reporting a vulnerability

Do **not** publish exploitable details, private media, credentials, machine identifiers or crash dumps containing personal information in public issues or pull requests. Prefer GitHub's **Report a vulnerability** / private vulnerability reporting feature, if enabled for this repository. If it is unavailable, contact the repository owner privately via GitHub and request a confidential reporting channel before sharing a proof of concept. Public issues are suitable for ordinary bugs without sensitive exploit details.

Please include affected commit/version, reproducible steps with synthetic files where possible, security impact, and a safe proposed mitigation. No guaranteed response time or coordinated disclosure window is promised.

## Security boundaries

Media decoders, ONNX inference and worker subprocesses are **not sandboxes**. Handle media from untrusted sources cautiously. The app is designed for offline use; no deployment of a network service is intended. Report suspected unexpected network access or destructive file overwrites as security issues.
