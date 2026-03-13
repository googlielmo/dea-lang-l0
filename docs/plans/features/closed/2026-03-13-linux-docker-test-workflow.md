# Feature Plan

## Linux Docker Test Workflow

- Date: 2026-03-13
- Status: Closed (implemented)
- Title: Explicit Linux Docker workflow for repository validation
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / Docker
- Modules:
    - `Dockerfile`
    - `.dockerignore`
    - `Makefile`
    - `README.md`
    - `CLAUDE.md`
- Test modules:
    - `compiler/stage1_py/tests/`
    - `compiler/stage2_l0/tests/`

## Summary

The repository now supports an explicit Linux Docker workflow for running the existing validation targets in a
reproducible container environment. The feature is intended for developer-triggered use only and does not replace the
default host-side workflow.

The blessed entrypoint is:

```shell
make docker CMD=test-all
```

This keeps Docker opt-in, preserves the existing host defaults, and provides a maintained Linux test environment rooted
at the repository top level.

## Goals

1. Provide a repo-owned Linux container workflow for running existing `make` targets.
2. Keep Docker execution explicit rather than implicit in normal development commands.
3. Reuse the existing top-level test entrypoints instead of inventing Docker-only commands.
4. Allow Docker-only compiler selection without coupling it to host `L0_CC`.

## Non-Goals

- Make Docker a required dependency for normal local development.
- Change the default host compiler-selection behavior.
- Add automatic Docker execution to CI or default `make` targets.

## Implementation

### Container definition

Keep a single root-level `Dockerfile` and `.dockerignore` as the supported Linux test environment for the repository.
The image should:

- install the Linux-native build prerequisites used by the test suite
- preinstall the Python `dev` and `docs` dependency groups
- remain neutral on `L0_CC` unless an explicit Docker-only override is provided

### Developer entrypoint

Expose Docker use through `make docker`:

- require `CMD=<target>`
- document `make docker CMD=test-all` as the blessed full-validation command
- allow `DOCKER_L0_CC=<compiler>` to pass a container-only `L0_CC` override (`gcc` or `clang`)

### Documentation

Document the Docker workflow in the main developer docs and clarify that:

- Docker is opt-in
- host-side `make` targets do not invoke Docker automatically
- Docker compiler selection is separate from host `L0_CC`

## Verification Criteria

1. `make help` documents the Docker entrypoint and Docker-specific compiler override.
2. `make docker CMD=help` builds the image and runs the container successfully.
3. `make docker CMD=test-all` runs the full validation suite under Linux in the container.
4. A plain container run does not implicitly execute the full test suite by default.

## Risks and Notes

- The Docker image only guarantees the compilers intentionally installed in the image; host compiler availability is not
  relevant inside the container.
- The workflow should stay thin and continue to delegate behavior to existing `make` targets rather than duplicating
  test orchestration in shell snippets.

## Related Documents

- [Project status](../../../reference/project-status.md)
- [Architecture](../../../reference/architecture.md)
