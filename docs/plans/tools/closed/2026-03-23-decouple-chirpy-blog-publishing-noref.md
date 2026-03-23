# Tool Plan

## Decouple Chirpy Blog Publishing from Destination Repo

- Date: 2026-03-23
- Status: Closed (implemented)
- Title: Replace direct blog-repo push with release-asset archive and optional `repository_dispatch`
- Kind: Tooling
- Severity: Medium
- Stage: Shared
- Subsystem: CI / docs publishing
- Modules:
  - `.github/workflows/docs-publish.yml`
  - `docs/reference/blog-poll-workflow.yml`

## Summary

The `sync-blog` job in `docs-publish.yml` directly checks out a configured Chirpy blog repository, copies exported
Markdown into it, and pushes. This tightly couples the public Dea repo to a specific destination and requires a PAT with
write access to that repo on every release.

## Problem

- Tight coupling of the export process to a specific blog repo and push mechanism.
- Hard failure when `BLOG_REPO` or `BLOG_PUSH_TOKEN` are not configured.
- No way to use the Chirpy export independently of the push target.

## Solution

### Dea repo (`docs-publish.yml`)

Replace the `sync-blog` job with `upload-blog-export`:

1. Run the existing `l0_docgen_blog` Chirpy export transform (unchanged).
2. Create `blog-export.tar.gz` from the export output.
3. Upload the archive as a **workflow artifact** (always available).
4. Upload the archive as a **GitHub Release asset** (when a release tag is resolvable).
5. Optionally fire a `repository_dispatch` event to `vars.BLOG_REPO` — guarded by
   `vars.BLOG_REPO != '' && secrets.BLOG_PUSH_TOKEN != ''`, so it is a no-op when unconfigured.

Removed:

- Blog repo checkout, file sync, commit, and push steps.
- Hard validation that fails on missing `BLOG_REPO` / `BLOG_PUSH_TOKEN`.
- `BLOG_BRANCH` variable (the blog repo decides its own branch).

### Blog repo (`blog-poll-workflow.yml`)

New reference workflow at `docs/reference/blog-poll-workflow.yml`, to be copied into the blog repo:

- **Scheduled poll** (cron every 4 hours): queries Dea's latest release via the GitHub API, compares against a
  `.dea-docs-version` marker file, downloads and unpacks the archive if new.
- **`repository_dispatch`** (`blog-docs-update`): receives the release tag from Dea's optional dispatch.
- **`workflow_dispatch`**: manual trigger with optional `release_tag` or `run_id` override.

The `run_id` input allows syncing from a Dea workflow run artifact (via `gh run download`), covering the case where
`publish_blog` is run manually without a release.

Version marker: `.dea-docs-version` in the blog repo root stores the last-synced tag (or a timestamped value for manual
archive imports).

## Variables and Secrets

### Dea repo

| Name               | Type     | Required                      | Purpose                               |
| ------------------ | -------- | ----------------------------- | ------------------------------------- |
| `BLOG_DOCS_PREFIX` | variable | No (default: `api/reference`) | Docs prefix in export                 |
| `BLOG_TAB_TITLE`   | variable | No (default: `API`)           | Chirpy tab title                      |
| `BLOG_TAB_ICON`    | variable | No (default: `fas fa-book`)   | Chirpy tab icon                       |
| `BLOG_TAB_ORDER`   | variable | No (default: `5`)             | Chirpy tab order                      |
| `DOCS_SITE_URL`    | variable | No                            | Override HTML site URL                |
| `BLOG_REPO`        | variable | No                            | Target repo for `repository_dispatch` |
| `BLOG_PUSH_TOKEN`  | secret   | No                            | PAT for `repository_dispatch`         |

**Can be deleted** (no longer used): `BLOG_BRANCH`.

### Blog repo

| Name               | Type     | Required                      | Purpose                         |
| ------------------ | -------- | ----------------------------- | ------------------------------- |
| `DEA_SOURCE_REPO`  | variable | Yes                           | Source repo for release polling |
| `BLOG_DOCS_PREFIX` | variable | No (default: `api/reference`) | Where to unpack docs            |

## Verification

1. Run `workflow_dispatch` with `publish_blog=true` on Dea — archive artifact and release asset are produced; no failure
   on missing `BLOG_REPO`.
2. Run `workflow_dispatch` on the blog repo with a `release_tag` — archive is downloaded and committed.
3. Run `workflow_dispatch` on the blog repo with a `run_id` — artifact is downloaded via `gh run download` and committed
   with a timestamped marker.
4. Scheduled poll exits early when `.dea-docs-version` matches the latest release.
5. `docs-validate.yml` continues to pass (Chirpy export step unchanged).
