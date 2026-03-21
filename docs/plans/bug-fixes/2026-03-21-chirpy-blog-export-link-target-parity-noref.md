# Bug Fix Plan

## Chirpy blog export link-target parity

- Date: 2026-03-21
- Status: In Progress
- Title: Fix Chirpy blog export fragment-target mismatches and operational defaults for the API sync workflow
- Kind: Bug Fix
- Severity: High (published API section blocked by blog CI failure)
- Stage: Shared
- Subsystem: Documentation / Blog Export
- Modules:
  - `.github/workflows/docs-publish.yml`
  - `compiler/docgen/l0_docgen_blog.py`
  - `compiler/stage1_py/tests/cli/test_docgen_blog.py`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_docgen_blog.py`
- Repro: publish generated API Markdown into `googlielmo/gwz-blog` and run its `pages-deploy.yml` / `bash tools/test.sh`

## Summary

The Chirpy export path used for blog publishing diverged from the generated Markdown and standalone HTML behavior in a
few ways that block publication into the `gwz-blog` repository:

1. Manual `docs-publish.yml` runs enabled blog sync by default, making it easy to trigger blog updates unintentionally.
2. The default exported tab order collided with the existing Chirpy `About` tab in `gwz-blog`.
3. Exported API pages preserved raw anchor-only HTML tags such as `<a id="..."></a>`, which `htmlproofer` rejects.
4. Exported API pages did not preserve file-level `file-*` fragment targets expected by some generated cross-page links,
   causing internal-link hash failures such as `#file-iol0`.

These are Chirpy-export-specific issues. The source Markdown under `build/docs/markdown/` and the standalone API Pages
site remain the canonical generated surfaces and must not be changed just to satisfy the blog pipeline.

## Root Cause

The Chirpy exporter currently transforms generated Markdown into a Jekyll/Chirpy tree, but that transformation was not
fully target-compatible with the `gwz-blog` validation stack:

- Chirpy/Jekyll preserves raw `<a id>` elements into the built HTML, and `htmlproofer` treats those as invalid links
  because they have no `href`.
- The exporter strips the original file-page H1 from generated Markdown. That is correct for page presentation, but it
  also removed the implicit file-level fragment target that some generated cross-page links still reference.
- Workflow defaults were oriented toward convenience during implementation rather than safe day-to-day operation against
  a real Chirpy blog repository.

## Scope Of This Fix

1. Keep manual blog publication opt-in by default in `docs-publish.yml`.
2. Default the generated Chirpy API tab order to `5` to match the current `gwz-blog` tab ordering.
3. Rewrite anchor-only HTML fragment markers to non-link fragment targets during Chirpy export.
4. Preserve a file-level fragment target on every exported page so generated `#file-*` links resolve.
5. Keep all of the above confined to the Chirpy export path rather than changing the base generated Markdown.

## Progress To Date

Already implemented in this repo:

1. `docs-publish.yml` manual dispatch now defaults `publish_blog=false`, so blog sync is no longer active by default.
2. The exporter default tab order and workflow fallback were changed from `4` to `5`.
3. The Chirpy export rewrites anchor-only tags such as `<a id="function-foo"></a>` to `<span id="function-foo"></span>`.
4. The Chirpy export now injects a file-level fragment target derived from the source filename so links such as
   `#file-iol0` resolve on exported pages.
5. Blog export tests were extended to cover the tab-order default, anchor rewriting, and file-anchor preservation.

External configuration clarified during this work:

1. The correct blog target repo is `googlielmo/gwz-blog`, not the public rendered `googlielmo/googlielmo.github.io`
   repository.
2. `gwz-blog` already owns the build-to-public-site deployment into `googlielmo.github.io`.

## Remaining Work

1. Push the latest exporter fix and rerun the L0 `docs-publish.yml` workflow with `publish_blog=true`.
2. Confirm the downstream `gwz-blog` `pages-deploy.yml` workflow passes `bash tools/test.sh` without `htmlproofer`
   failures.
3. Spot-check the published blog API section at `/api/` and a few representative deep links, including:
   - file-level fragment links such as `#file-iol0`
   - symbol-level fragment links such as `#function-present`
   - the top-level tab entry and links to the standalone HTML site / PDF
4. Close and move this plan under `docs/plans/bug-fixes/closed/` once the end-to-end publish path is green.

## Verification

Local verification for the exporter changes:

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_blog.py
./scripts/gen-docs.sh --strict
uv run python -m compiler.docgen.l0_docgen_blog \
  --input build/docs/markdown \
  --output build/docs/blog-export
```

End-to-end verification:

1. Run `Publish Documentation` from this repository with `publish_blog=true`.
2. Confirm the sync commit lands in `googlielmo/gwz-blog`.
3. Confirm the `gwz-blog` publish workflow succeeds.
4. Confirm `https://googlielmo.github.io/api/` and representative deep links load successfully.

## Assumptions

1. `gwz-blog` remains the Chirpy source repository and continues to deploy into `googlielmo/googlielmo.github.io`.
2. The generated Markdown under `build/docs/markdown/` remains a shared intermediate for standalone HTML and Chirpy
   export, so Chirpy-specific normalization belongs only in `l0_docgen_blog.py`.
3. The current Chirpy tab ordering in `gwz-blog` keeps `About` at order `4`, so the API tab default should remain `5`
   unless that repo changes its navigation structure.
