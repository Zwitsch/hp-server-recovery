# Security Policy

## Scope

HP Server Recovery performs disaster-recovery and restore operations that may interact with filesystems, storage devices, service configuration and backup data. Safety checks are therefore part of the product contract, not optional convenience features.

## Public repository policy

Do not commit or publish:

- passwords, API tokens, private keys or session credentials
- real production `.env` files
- backup archives or restored application data
- real hostnames, private domains or personal e-mail addresses
- machine UUIDs, filesystem UUIDs, device serials or other deployment identities
- production database dumps
- private container registry credentials
- Pushover or other notification credentials
- production recovery evidence containing identifying data

Use sanitized examples and placeholders instead.

## Destructive operations

Restore functionality should fail closed. A destructive action must not proceed when the expected target identity, required source data, manifest integrity or explicit authorization cannot be established.

Generic examples must not embed the identity of the original development server.

## Reporting a vulnerability

Please open a GitHub issue for non-sensitive security design concerns. Do not include credentials, private infrastructure details or exploit material containing third-party secrets in a public issue.

For an accidentally committed secret, revoke or rotate the credential first. Removing it from the current tree alone is not sufficient because Git history may retain it.
