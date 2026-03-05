# Feature Plan

## Release-Oriented Docs Publishing Automation

- Date: 2026-03-04
- Status: Implemented
- Title: Release-oriented automation for publishing generated HTML, Chirpy-integrated Markdown, and PDF API documentation
- Kind: Feature
- Severity: Medium (Tooling/Docs)
- Stage: Shared
- Subsystem: Documentation / CI
- Modules:
    - `.github/workflows/docs-validate.yml`
    - `.github/workflows/docs-publish.yml`
    - `compiler/docgen/l0_docgen_blog.py`
    - `scripts/gen-docs.sh`
    - `README.md`
    - `CLAUDE.md`
    - `docs/README.md`
- Test modules:
    - `compiler/stage1_py/tests/cli/test_docgen_cli.py`
    - `compiler/stage1_py/tests/cli/test_docgen_markdown_renderer.py`
    - `compiler/stage1_py/tests/cli/test_docgen_latex.py`
    - `compiler/stage1_py/tests/cli/test_docgen_blog.py`

## Summary

Add practical release-oriented documentation publishing automation with three outputs built from the existing docs
pipeline:

1. A standalone static HTML API site published from this repository to GitHub Pages
2. A transformed Markdown export synchronized into a separate Jekyll/Chirpy blog repository as a dedicated non-post API
   section
3. A generated PDF (`refman.pdf`) published both as a GitHub Release asset and under the Pages site

The system validates docs generation in CI without publishing on pull requests, and publishes on GitHub Release
publication plus manual trigger.

## Implementation Notes

### Validation workflow

- `.github/workflows/docs-validate.yml` validates the docs pipeline on pull requests and selected pushes to `main`.
- The workflow installs the docs toolchain, runs `./scripts/gen-docs.sh --strict`, and then runs the Chirpy export step.
- Validation does not publish any artifacts and does not build the PDF.

### Publish workflow

- `.github/workflows/docs-publish.yml` builds docs once, then fans out to:
  - GitHub Pages deployment for standalone HTML + PDF
  - Release asset upload for `refman.pdf`
  - direct synchronization into the separate Chirpy blog repository
- Publishing runs on `release.published` and on `workflow_dispatch`.

### Chirpy export

- `compiler/docgen/l0_docgen_blog.py` transforms the generated Markdown tree into a Jekyll/Chirpy-compatible export.
- Exported pages receive front matter, stable permalinks, and rewritten internal links using `relative_url`.
- The exporter generates `_tabs/api.md` plus an `api/reference/**` subtree suitable for a dedicated Chirpy section.

### Renderer parity hardening

- Published HTML uses the curated browse surface (`stage1.html`, `stage2.html`, `shared.html`) instead of raw Doxygen
  hierarchy pages.
- Raw hierarchy pages are compatibility-only:
  - raw file pages redirect to curated `/api/...` pages
  - raw directory pages redirect to stage/shared hubs
  - raw symbol leaf pages remain for compatibility/search
- Search targets are stabilized for publishing:
  - result URLs are resolved from docs root so nested `/api/...` pages do not generate relative-path 404s
  - pruned raw directory compounds are excluded from search results
- Shared browse output is source-only (`compiler/shared/**`) and excludes generated helper pages.
- Stage/Shared browse entries use a responsive two-column layout so file paths remain primary while dense reference
  lists stay readable.

Detailed rendering and syntax-normalization rules remain documented in
`docs/plans/features/2026-03-02-doxygen-mcss-docs-system.md`.

### Ownership model

- This repository owns the build, the standalone Pages site, the PDF, and the generated Chirpy export subtree.
- The separate blog repository continues to own its theme, posts, and navigation outside the generated API section.

### Configuration

Publishing expects these repository settings:

- Variables:
  - `BLOG_REPO`
  - `BLOG_BRANCH`
  - `BLOG_DOCS_PREFIX`
  - `BLOG_TAB_TITLE`
  - `BLOG_TAB_ICON`
  - `BLOG_TAB_ORDER`
  - `DOCS_SITE_URL`
- Secret:
  - `BLOG_PUSH_TOKEN`

## Verification

Run:

```bash
pytest \
  compiler/stage1_py/tests/cli/test_docgen_cli.py \
  compiler/stage1_py/tests/cli/test_docgen_markdown_renderer.py \
  compiler/stage1_py/tests/cli/test_docgen_latex.py \
  compiler/stage1_py/tests/cli/test_docgen_blog.py

./scripts/gen-docs.sh --strict
python -m compiler.docgen.l0_docgen_blog \
  --input build/docs/markdown \
  --output build/docs/blog-export
```

Success criteria:

1. `build/docs/html/` is generated and suitable for GitHub Pages publishing.
2. `build/docs/pdf/refman.pdf` is generated via `./scripts/gen-docs.sh --pdf`.
3. `build/docs/blog-export/_tabs/api.md` is generated for the Chirpy API section.
4. Exported blog pages under `build/docs/blog-export/api/reference/` contain Jekyll front matter and rewritten internal
   links.
5. The publish workflow can deploy Pages, upload the PDF, and synchronize only the managed API subtree into the blog
   repository.
