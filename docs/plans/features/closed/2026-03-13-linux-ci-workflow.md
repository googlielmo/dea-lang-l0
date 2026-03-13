# Feature Plan

## Linux CI Workflow for `make test-all`

- Date: 2026-03-13
- Status: Closed (implemented)
- Title: Linux GitHub Actions CI workflow for full validation
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / CI
- Modules:
    - `.github/workflows/ci.yml`
    - `docs/plans/features/2026-03-11-windows-build-support.md`
- Test modules:
    - `Makefile`
    - `compiler/stage1_py/tests/`
    - `compiler/stage2_l0/tests/`

## Summary

The repository had documentation publishing workflows, but no general-purpose CI workflow for compiler validation.
This feature adds a Linux-only GitHub Actions workflow that runs the existing top-level validation entrypoint
`make test-all`.

The initial rollout is intentionally narrow:

- run on `ubuntu-latest`
- trigger on `pull_request`
- trigger on `workflow_dispatch`
- do not trigger automatically on `push`
- default non-manual runs to `gcc`
- allow manual runs to choose `gcc` or `clang`

The workflow should include a commented-out `push` section so automatic branch builds can be enabled later without
restructuring the file. Windows CI remains a follow-up and is tracked in the separate Windows build support plan.

## Goals

1. Run the full Stage 1 + Stage 2 validation suite on Linux in GitHub Actions.
2. Reuse `make test-all` as the single CI entrypoint instead of duplicating test commands in YAML.
3. Support both manual runs and PR validation.
4. Avoid automatic push-triggered builds in the initial rollout.
5. Keep the workflow easy to extend later with Windows support.

## Non-Goals

- Add Windows CI in this change.
- Add artifact publishing, caching, or release behavior.
- Add path filters or branch-specific policy beyond the requested trigger set.
- Change the underlying test commands or Make targets.

## Implementation

### Workflow file

Create `.github/workflows/ci.yml` with:

- SPDX/license header matching existing workflow files
- `name: CI`
- `on.pull_request`
- `on.workflow_dispatch`
- a commented-out `push` trigger block targeting `main`

### Linux validation job

Add one Linux job:

- `runs-on: ubuntu-latest`
- checkout via `actions/checkout@v4`
- Python setup via `actions/setup-python@v5` with `python-version: "3.14"`
- `uv` setup via `astral-sh/setup-uv@v6`
- install Linux native build prerequisites with `apt-get`
- expose a manual `workflow_dispatch` compiler choice input
- use `gcc` for non-manual runs
- execute `make test-all`

### Windows follow-up alignment

Update the active Windows build support plan so it no longer assumes the first CI rollout is cross-platform.
The Windows plan should treat the Linux workflow as the baseline and describe Windows runner support as a future
extension of `.github/workflows/ci.yml`.

## Verification Criteria

1. `.github/workflows/ci.yml` is valid YAML.
2. The workflow triggers on `pull_request` and `workflow_dispatch`.
3. The workflow does not trigger on `push`, aside from the commented-out future block.
4. The Linux job installs the required toolchain, defaults non-manual runs to `gcc`, and runs `make test-all`.
5. The Windows support plan reflects Linux-first CI rollout.

## Risks and Notes

- The workflow depends on GitHub-hosted Ubuntu runners providing compatible system packages for the current build path.
- `make test-all` remains the source of truth for CI behavior; any future CI expansion should continue to prefer that
  top-level entrypoint where practical.
- Windows CI should be added as a follow-up, not by expanding this change ad hoc.

## Related Documents

- [Windows build support](../2026-03-11-windows-build-support.md)
- [Project status](../../../reference/project-status.md)
- [Architecture](../../../reference/architecture.md)
