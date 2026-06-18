# Audit And Accountability

## Scope

This repository is a public single-repository GitHub project. GitHub
organization or enterprise audit-log export is not available from the current
repository settings. Do not describe normal Git history as "GitHub audit logs."

## Available GitHub Security Signals

Verified repository settings on 2026-06-17:

- Dependabot security updates: enabled.
- Secret scanning: enabled.
- Secret scanning push protection: enabled.
- Issues: enabled.
- Discussions: enabled.

Branch protection for `main` was not enabled when checked on 2026-06-17.

## Repository-Level Accountability

Use these controls to reconstruct who changed what and which checks ran:

- Git commit history and signed tags or commits where practical.
- Pull-request timeline, review history, and linked issues.
- CODEOWNERS owner review routing.
- GitHub Actions logs for CI, security, release, Docker, and dependency review.
- Release artifacts, SHA-256 checksums, SBOM, and provenance attestations.
- HDF5 event hash chains and HMAC attestations for field evidence files.
- Turnover notes named `TURNOVER_YYYY-MM-DD_<topic>.md`.

## Required Review Procedure

Before merge, verify:

- A Conventional Commit title or commit message.
- CI validation on Python 3.10 through 3.14.
- Simulator tests pass without physical hardware.
- CodeQL, Dependency Review, and Docker/Trivy checks have no unresolved blocking
  findings.
- Hardware claims are either backed by captured command output or marked as not
  run.
- Security-sensitive changes fail closed and preserve secondary forensic output.

## Recommended Branch Protection

Configure `main` to require pull requests and these checks before merge:

- `DSLV-ZPDI CI / Validate (py3.10)`
- `DSLV-ZPDI CI / Validate (py3.11)`
- `DSLV-ZPDI CI / Validate (py3.12)`
- `DSLV-ZPDI CI / Validate (py3.13)`
- `DSLV-ZPDI CI / Validate (py3.14)`
- `DSLV-ZPDI CI / Package build`
- `Security Scanning / codeql`
- `Dependency Review / Dependency diff`
- `Conventional Commit Validation / PR title`
- `Multi-Architecture Container Build / docker`

Also enable:

- Require approval from CODEOWNERS.
- Dismiss stale approvals when new commits are pushed.
- Require conversation resolution.
- Require linear history if compatible with the maintainer workflow.
- Block force pushes and branch deletion.

## Signed Releases

Prefer signed annotated tags for releases:

```bash
git tag -s v5.0.0 -m "v5.0.0"
git push origin v5.0.0
```

If tag signing is not available on the release host, document that limitation in
the release notes and rely on GitHub release provenance, attached artifacts, and
checksums.
