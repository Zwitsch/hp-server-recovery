# Changelog

All notable changes to HP Server Recovery will be documented in this file.

The project is currently preparing its first stable OSS release.

## Unreleased

### Added

- Public sanitized source tree for the reusable recovery engine.
- Synthetic runtime catalog, image-lock contracts and application-release fixtures.
- Isolated realtest configuration templates using documentation-only network addresses and reserved example domains.
- GitHub Actions CI on Ubuntu 24.04 with Python 3.12.
- Architecture, safety and contribution documentation.

### Changed

- Generalized isolated realtest host and protected-path bindings so production identities are not hard-coded.
- Separated repository metadata from recovery-package manifest coverage.
- Excluded Git checkout metadata from recovery-package validation.
- Updated the README to reflect the public pre-release state and provide a reproducible external test command.

### Security

- Destructive recovery logic remains fail-closed when required target identity or safety bindings are missing.
- Public fixtures contain no production credentials, backup data, personal domains, machine UUIDs or private-LAN topology.
- The sanitized release tree currently passes 183 automated tests.

## 0.1.0

Planned as the first stable public OSS release after final release-readiness review. No tag has been published yet.
