# Feature Plan

## Move SipHash to a monorepo-global shared include

- Date: 2026-04-09
- Status: Closed (will not implement)
- Title: Move SipHash to a monorepo-global shared include
- Kind: Feature
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - `l0`
  - `l1`
- Origin: Shared runtime header naming and include-path policy
- Porting rule: Keep SipHash physically level-local in each runtime tree until a later runtime/distribution plan defines
  a real shared-artifact contract
- Target status:
  - `l0`: Deferred: keep `l0/compiler/shared/runtime/dea_siphash.h` level-local and rename consumers in place
  - `l1`: Deferred: keep `l1/compiler/shared/runtime/dea_siphash.h` level-local and rename consumers in place
- Subsystem: Shared runtime headers / C backend includes / build layout

## Closure decision

This plan is closed without implementation. A monorepo-root shared include would create a new build/layout contract that
the current tree does not have, and this repo is not ready to invent that distribution model yet.

## Rationale

The current L1 bootstrap story is explicitly level-local: the runnable compiler lives in `compiler/stage1_l0/`, shared
assets already live under `compiler/shared/...`, and backend output is still a single C translation unit compiled by the
host toolchain.

A root-level shared include would therefore drag in either new top-level include-path plumbing or repo-relative include
spellings that assume a monorepo root exists at consumption time. That is exactly the wrong time to invent a
distribution model.

The rename-only direction is cleaner. The docs already state that the old `l0_siphash.h` name was only a temporary
internal legacy name rather than part of the intended public L1 ABI. Renaming it in place to `dea_siphash.h` removes the
bogus level-specific prefix now without forcing a fake shared-root abstraction before the repo is ready for one.

## Replacement direction

1. Rename `l0/compiler/shared/runtime/l0_siphash.h` and `l1/compiler/shared/runtime/l0_siphash.h` in place to
   `dea_siphash.h`.
2. Update current consumers and generated-output expectations to include `dea_siphash.h`.
3. Keep the file physically level-local for now so existing layout assumptions, `make dist`, and current bootstrap flows
   stay simple.
