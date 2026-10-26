# Changelog

## [0.2.1] - 2026-10-27
### Added
- **Declarative GitOps Deployment:** Standardized `deploy/k8s/` base and environment overlays (`dev`, `staging`, `prod`) adhering to CNCF restricted pod security standards (non-root UID 10001, dropped capabilities, read-only rootfs).
- **ArgoCD Continuous Delivery:** Added declarative ArgoCD application manifests (`deploy/argocd/application.yaml`, `application-dev.yaml`, `application-prod.yaml`, `values-override.yaml`).
- **Multi-Cluster Orchestration:** Integrated with `multi-cluster-gitops-promotion` catalog for automated zero-drift self-healing in development/staging and gated PR promotion in production.

for idempotent-payment-ledger

## [0.2.0] - 2026-10-20
### Added
- **Progressive Credential Loading (PCL):** Dynamic auto-promotion between zero-dependency mock fallbacks and live production backends based on environment credentials.
- **Dual Distribution:** Universal OCI container publishing to GitHub Container Registry (`ghcr.io/sumitdalavi/idempotent-payment-ledger`) and Helm OCI registries alongside GitHub Release tarballs.
- **Health Reporting:** Exposed `/health` or `/healthz` endpoint with PCL status detection (`mock` vs `live`).
- **Dynamic Reloading:** Support for atomic ConfigMap / secret reloads without requiring pod restarts.
- **Supply Chain Security:** Trivy vulnerability scan gates and SPDX JSON SBOM (`sbom.spdx.json`) generation for all releases.

## [0.1.0] - 2026-10-18
### Added
- Initial baseline service implementation, unit test suites, and CI workflows.

## [Unreleased]
- Added `docs/decisions.md` to document architectural trade-offs.
- Added `docs/runbook.md` with explicit startup and diagnostic steps.
- Identified known limitations in README for transparency.

### Post-Release Hotfixes
- Resolved lingering CI/CD failures introduced during portfolio elevation.
- Fixed Docker build and permission errors across client/server components.
- Corrected Kubernetes controller GroupVersionKind mismatches and E2E Vault addressing.
- Repaired broken property-based test configurations.
