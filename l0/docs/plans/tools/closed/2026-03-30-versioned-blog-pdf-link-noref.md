# Tool Plan

## Version-Aware PDF Link and Release Display in Blog Export

- Date: 2026-03-30
- Status: Closed (implemented)
- Title: Pin blog export PDF link to the release asset and display version on tab page
- Kind: Tooling
- Severity: Low
- Stage: Shared
- Subsystem: CI / docs publishing
- Modules:
  - `l0/compiler/docgen/l0_docgen_blog.py`
  - `.github/workflows/l0-docs-publish.yml`

## Problem

The blog export tab page links to the GitHub Pages PDF (`/pdf/dea_l0_api_reference.pdf`), which is overwritten on every
release. A blog snapshot for v0.9.1 silently points to a newer PDF after the next release. The page also shows no
version information.

Additionally, the PDF release asset name changed across versions (`refman.pdf` for v0.9.1,
`dea_l0_api_reference-<tag>.pdf` going forward), so the URL cannot be hardcoded.

## Solution

- Add `--release-tag` CLI argument to `l0_docgen_blog.py`; render `**Release <tag>**` on the tab page when provided.
- In the workflow, resolve the PDF URL dynamically via `gh release view` to find whatever `.pdf` asset is attached to
  the target release. Fall back to the Pages URL when no release tag or no PDF asset exists.
- Add `upload-release-pdf` to `upload-blog-export` dependencies so the PDF asset is available before querying.
- Pass `--release-tag "$TARGET_RELEASE_TAG"` from the workflow to the export script.
- Decouple the `upload-blog-export` checkout from `source_ref`: always check out the default branch so the current
  export script runs even when backfilling legacy tags (e.g. `v0.9.1`) whose code predates `--release-tag`.
- Add `build_pdf` input to `l0-docs-build.yml`: skip TeX installation and PDF generation when only the blog export is
  needed. The caller in `l0-docs-publish.yml` sets `build_pdf: false` for blog-only dispatches.

## Verification

- `pytest compiler/stage1_py/tests/cli/test_docgen_blog.py` — covers release tag display, baseline omission, and arg
  parsing.
- Manual `workflow_dispatch` against `v0.9.1` to confirm the blog picks up `refman.pdf` and shows the release line.
