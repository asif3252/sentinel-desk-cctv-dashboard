# Local access and sensitive data

Sentinel Desk is a single-computer prototype. The backend binds to loopback, validates the Host header and requires a session token with an allowed Origin for mutations. These controls are not a substitute for multi-user authentication or a hardened deployment.

- Keep `127.0.0.1` as the bind address. Do not expose this server through a public tunnel or router forwarding.
- Enter recorder credentials only in local dashboard fields. They are not intentionally persisted or returned by status APIs.
- Credentials and settings clear on restart; disconnect clears the active configuration after the worker stops. Immutable strings may remain in process memory until reclaimed.
- Event snapshots and CSV remain on disk. Restrict access locally and manage retention; this version does not automatically delete old evidence.
- Keep actual NVR addresses, credentials, snapshots, footage, model files and local environments out of commits.
- Use only authorized camera streams. Review alerts as evidence requiring human interpretation.

For a suspected vulnerability, do not post sensitive reproduction details in public issues. Use a private contact channel you have independently verified with the maintainer, or GitHub private vulnerability reporting if it is enabled. This document does not claim that a private reporting feature is configured.
