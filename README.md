# Banas Chat

Banas Chat is a private chat deployment built on [Open WebUI](https://github.com/open-webui/open-webui), with additional configuration and scripts for access control, local model access, GPU coordination, and encrypted backups.

Rafał Banaś defined the requirements and maintains the deployment. The repository's additional scripts, configuration, and documentation were generated and adapted with assistance from OpenAI Codex.

## Project scope and attribution

Open WebUI provides the chat interface, backend, accounts, multi-factor authentication (MFA), conversation history, Markdown rendering, and export features. Those components were not developed from scratch for this project.

Open WebUI is developed by Open WebUI Inc., Timothy Jaeryang Baek, and the project's contributors. The [third-party notices](THIRD_PARTY_NOTICES.md) describe component origins and applicable terms. The [MIT license](LICENSE) applies only to this repository's additions; it does not replace the Open WebUI license or claim authorship of upstream components.

The branding customization was prepared for a single-user deployment. Larger deployments require a review of the applicable Open WebUI terms.

This repository documents a specific deployment rather than providing a universal installer. Other installations require their own environment configuration, credentials, storage, certificates, and integration settings. Administrator contact details, server addresses, filesystem locations, and other deployment-specific infrastructure information are omitted from this README.

## Features

- A customized Open WebUI interface backed by local Ollama models.
- Persistent conversation history associated with the authenticated account.
- Mandatory MFA and disabled public registration.
- A policy gateway that restricts model access, request parameters, and concurrent generation.
- Optional model thinking, displayed separately from the response.
- Conversation exports in Markdown or JSON.
- GPU coordination with CV Tailor.
- Encrypted backups with restore verification.

## Access and security

The deployment is intended for private use. Account creation is restricted to the administrator, and anonymous requests for conversation history, model listings, and generation are rejected.

MFA enrollment requires an authenticator application and recovery codes. A valid password alone does not grant access to the chat. Accurate device time is required for time-based authentication codes.

The configuration includes secure session cookies, origin validation, restricted cross-origin access, a content security policy, and rate limits. Remote code execution, API keys, and direct browser connections to model providers are disabled.

Credentials, MFA secrets, recovery codes, environment files, and backup encryption keys belong in private administrator storage and are excluded from repository documentation. Conversation data requires the same protection as private correspondence.

## Models and conversation history

The policy gateway exposes only approved models already installed in Ollama. It does not permit model downloads, deletion, creation, or generation through alternative endpoints. Open WebUI model presets configure the application without modifying the underlying Ollama models.

The gateway enforces context and output limits that client parameters cannot increase. A conservative UTF-8 byte budget limits the conversation history sent for generation. Requests exceeding that budget receive an HTTP 413 error; saved conversation history is not silently truncated. This approximation can reject a conversation earlier than an exact tokenizer would.

Thinking is disabled by default and can be enabled through Open WebUI's advanced Ollama parameters. Thinking and response content remain separate in the stream. Both consume the output budget, so a model may exhaust that budget before producing a final answer.

Individual conversations support Markdown and JSON export. Bulk export is available through the data settings.

## GPU coordination

A separate status process reports whether CV Tailor has queued or running work. The gateway rejects new generation while that work is active and interrupts its own stream when new work is detected. Missing or stale status also prevents generation. CV contents are not exposed to the chat.

Coordination uses polling rather than a shared atomic lock. Brief overlap remains possible before a new job is detected. Limited concurrency, conservative context limits, and model unloading after each response help reduce resource contention. Subsequent messages require the model to load again.

The integration preserves CV Tailor's existing behavior and does not change global Ollama settings.

## Operations and maintenance

The deployment includes container health checks, automatic restarts, and rotated logs. Request-content audit logging is disabled. Debug logging and request-body logging should remain disabled during normal operation.

The acceptance scripts in `ops/` were created during bootstrap, before mandatory MFA enrollment. They do not bypass MFA and are not intended for unattended use against an existing production installation.

Routine maintenance covers service health, storage capacity, authentication, MFA, conversation history, streaming, cancellation, and GPU coordination. Operational commands and environment-specific settings belong in the administrator's private runbook.

## Backups and recovery

The backup process creates a consistent SQLite online backup, including committed data from the write-ahead log, and archives the remaining application data and configuration. Archives are encrypted and verified through an isolated restore, hash checks, and SQLite integrity checks.

The backup encryption key is excluded from the archive and requires a separate, secure copy. Losing that key prevents recovery. Backups on a separate volume do not provide an off-site copy; external storage requires separate configuration.

Recovery requires a verified archive, a copy of the current state, and a maintenance window for the chat application. The restored database, configuration, and application image must be compatible. The application secret key must remain stable because it is also required to read stored MFA secrets.

## Updates and limitations

Updates require a pinned application image, a verified backup, configuration validation, and post-update checks. Automatic updates without a recovery plan are unsuitable for this deployment.

A rollback after a database migration requires both the previous application image and a database backup from before the migration. Reusing an older image with a migrated database is not a safe rollback procedure.

A full host restart was not tested. GPU coordination remains subject to polling delays, and an off-site backup destination has not been configured.

## References

- [Open WebUI repository](https://github.com/open-webui/open-webui)
- [Open WebUI hardening documentation](https://docs.openwebui.com/getting-started/advanced-topics/hardening/)
- [Open WebUI MFA documentation](https://docs.openwebui.com/features/authentication-access/mfa/)
- [Third-party notices](THIRD_PARTY_NOTICES.md)
- [License for repository additions](LICENSE)
