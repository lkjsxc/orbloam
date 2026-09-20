# Security scope

This is a local/trusted cooperative experiment, not a hardened public MMO. It has typed input validation, ownership checks, explicit per-owner sequence receipts, transactional completion, digest-indexed recovery keys, finite request/queue/data limits, and no public operator endpoint. Those mechanisms are not a penetration test or an availability guarantee.

The browser generates a 256-bit recovery key with `crypto.getRandomValues`. Keys are bearer credentials: anyone possessing one can operate that colony. The browser can store it in localStorage after explicit visible consent; this is not an encrypted vault and is unsuitable for a shared or compromised browser profile. Export the key privately. Server data backups remain independently necessary. Registration repeats with the same key recover the same core after a lost response.

Keys do not expire and cannot currently be revoked through the UI. There is no email reset, multi-factor authentication, administrative identity recovery or automated lockout. Untrusted callers can consume the 64 registration slots or demand native work. Put a public deployment behind TLS, an access gate and rate/request limits; do not expose the operator's filesystem, local fixture commands or store directories.

The default listener is loopback. `--lan` is plaintext HTTP on every IPv4 interface. The application itself does not terminate TLS. Same-origin relative URLs are not arbitrary cross-origin access. Do not add wildcard CORS as a fix. Credentials are sent in an Authorization header (and in the registration JSON), never in a URL. Avoid request-body/header logging at the proxy.

HTML output uses text nodes for untrusted names. Static code is embedded; no CDN or external JavaScript is required. The native response includes a restrictive CSP, nosniff and no-referrer. The current environment denied ordinary Chromium navigation, so the browser-bridge acceptance does **not** verify CSP, CORS, TLS, clipboard or native browser-storage permissions. Inspect these on the actual deployment.

The native runtime is pinned by the exact official archive and executable SHA-256. Initial acquisition trusts the selected GitHub HTTPS source plus the repository's pinned hash; the local installer is not an independent signing authority. The launcher verifies the executable, artifact and descriptor hashes. A new runtime release is not an automatic application/save migration.

Never solve corruption or schema mismatch by deleting a live save. Stop the server, retain the original runtime/artifact/data and diagnose offline. A failed HTTP response can follow committed effects; preserve exact action intent until the result is reconciled. See OPERATIONS.md.
