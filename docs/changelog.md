# Changelog for idempotent-payment-ledger

## [Unreleased]
- Added `docs/decisions.md` to document architectural trade-offs.
- Added `docs/runbook.md` with explicit startup and diagnostic steps.
- Identified known limitations in README for transparency.

### Post-Release Hotfixes
- Resolved lingering CI/CD failures introduced during portfolio elevation.
- Fixed Docker build and permission errors across client/server components.
- Corrected Kubernetes controller GroupVersionKind mismatches and E2E Vault addressing.
- Repaired broken property-based test configurations.
