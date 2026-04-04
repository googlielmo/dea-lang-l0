# Tool Plan

## Document current GitHub workflow set

- Date: 2026-03-20
- Status: Closed (implemented)
- Title: Document the current GitHub workflow set
- Kind: Tooling
- Severity: Low
- Stage: Shared
- Subsystem: GitHub Actions / CI / release automation
- Modules:
  - `.github/workflows/ci.yml`
  - `.github/workflows/copyright-headers.yml`
  - `.github/workflows/docs-validate.yml`
  - `.github/workflows/docs-publish.yml`
  - `.github/workflows/release.yml`
  - `.github/workflows/snapshot.yml`
  - `.github/workflows/check_copyright_headers.py`
- Test modules:
  - `none (retrospective documentation-only plan)`

## Summary

The repository already ships several GitHub Actions workflows covering validation, documentation publishing, release
packaging, snapshot releases, and copyright-header enforcement.

Some of these workflows were introduced through dedicated plans, but the current workflow set as implemented in
`.github/workflows/` no longer has one concise plan document describing the whole system at a glance. This closed plan
fills that gap so the repository remains even with the implemented automation.

## Current Workflow Set

### General validation

- `ci.yml` runs the main compiler-validation workflow.
- It currently supports Linux, macOS Intel, macOS arm64, and Windows.
- Normal `push` runs target `main`; pull requests and manual dispatch are also supported.
- Manual dispatch can narrow the platform matrix and choose the Linux C compiler and Make target.
- The workflow delegates validation to top-level Make targets rather than duplicating test logic in YAML.

### Documentation

- `docs-validate.yml` validates the documentation pipeline on matching pull requests, selected pushes, and manual
  dispatch.
- It installs the docs toolchain, runs `./scripts/gen-docs.sh --strict`, and verifies the blog-export step.
- `docs-publish.yml` builds the docs once and fans out to Pages deployment, PDF upload, Markdown artifact retention, and
  optional blog synchronization.

### Release packaging

- `release.yml` builds multi-platform distribution archives for version tags matching `v*`.
- It injects a `VERSION` file, builds `make dist`, smoke-tests the resulting archive, builds the docs artifacts, deploys
  the generated Pages site, uploads the release PDF and Chirpy blog export, generates checksums and release notes, and
  publishes or updates the GitHub Release.
- `snapshot.yml` performs the same multi-platform distribution flow for manual snapshot releases, creating a snapshot
  tag and publishing the result as a pre-release.

### Repository policy enforcement

- `copyright-headers.yml` runs the copyright-header checker on pull requests and on pushes to `main` and `dea-dev`.
- The workflow uses `.github/workflows/check_copyright_headers.py` as the enforcement entrypoint.

## Relationship to Existing Plans

This plan does not replace the narrower implementation plans already in `work/plans/`. Instead, it records the current
top-level workflow inventory after those changes landed.

Existing related plans include:

- `work/plans/tools/closed/2026-03-13-linux-ci-workflow.md`
- `work/plans/tools/closed/2026-03-11-windows-build-support.md`
- `work/plans/tools/closed/2026-03-04-release-oriented-docs-publishing-automation-noref.md`
- `work/plans/tools/closed/2026-03-16-github-release-workflow-noref.md`

## Verification

The implemented workflow set is visible directly in `.github/workflows/`:

```bash
ls -1 .github/workflows
```

The workflows covered by this plan are:

- `ci.yml`
- `copyright-headers.yml`
- `docs-validate.yml`
- `docs-publish.yml`
- `release.yml`
- `snapshot.yml`
