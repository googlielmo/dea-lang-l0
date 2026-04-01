# L0 Project Status

Version: 2026-04-01

This document summarizes what is implemented in this repository today and what defines the current Dea/L0 `1.0.0.dev0`
development branch after the `l0-v0.9.2` release. L0 now lives as one language subtree inside the Dea monorepo; monorepo
release tags use the `l0-vX.Y.Z` namespace while historical pre-monorepo bare tags remain legacy references.

## Scope and Canonical References

Use this file as a status snapshot. For implementation details, use:

- [reference/architecture.md](architecture.md) for pass structure and data flow.
- [specs/compiler/stage1-contract.md](../specs/compiler/stage1-contract.md) for external interfaces and guarantees.
- [reference/c-backend-design.md](c-backend-design.md) for backend lowering and generated C behavior.
- [specs/runtime/trace.md](../specs/runtime/trace.md) for tracing flags and runtime trace semantics.
- [reference/grammar.md](grammar.md) for accepted concrete syntax.
- [reference/standard-library.md](standard-library.md) for current std/sys module APIs.
- [specs/compiler/cli-contract.md](../specs/compiler/cli-contract.md) for the shared CLI contract across stages.
- [specs/compiler/stage2-contract.md](../specs/compiler/stage2-contract.md) for Stage 2 contract and provenance.

## Current Status

### Stage 1

Stage 1 (`compiler/stage1_py`) is complete and remains the reference implementation for language behavior, diagnostics,
and C generation.

At a high level, it provides:

- the full current frontend pipeline from lexing through type checking,
- C99 code generation for the implemented L0 language surface,
- the shared public CLI surface documented in [cli-contract.md](../specs/compiler/cli-contract.md),
- tracing support via `--trace-arc` and `--trace-memory`.

### Stage 2

Stage 2 (`compiler/stage2_l0`) is self-hosted and currently the main delivery vehicle for normal developer, install,
distribution, and release workflows.

At a high level, it provides:

- full public CLI parity with Stage 1 across `--check`, `--tok`, `--ast`, `--sym`, `--type`, `--gen`, `--build`, and
  `--run`,
- self-hosted C99 generation, build, and run flows,
- repo-local, install-prefix, and distribution delivery paths,
- strict triple-bootstrap validation via `make triple-test`,
- embedded provenance in artifact-producing Stage 2 binaries via `--version`,
- release packaging plus docs/PDF publishing automation through the repository workflows,
- current parity fixes for Stage 2 return diagnostics, drop-liveness checks, and trace-runner behavior on Windows.

Stage 1 remains the behavioral oracle for equivalent Stage 2 paths.

## Language and Library Coverage

The current implemented language surface covers the core bootstrap subset used throughout this repository:

- functions, structs, enums, type aliases, and top-level `let`,
- modules/imports with qualified-name disambiguation,
- structured control flow including `if`, `while`, `for`, `match`, `case`, and `with`/`cleanup`,
- explicit nullability, `new`/`drop`, ARC-managed `string`, casts, and postfix `expr?`.

The standard library now includes the core runtime-facing and bootstrap-facing modules for I/O, strings, text, paths,
filesystem access, time, randomness, assertions, optionals, and the current container set. Use
[standard-library.md](standard-library.md) for the canonical module-by-module reference.

## Delivery and Validation

The current repository state supports three practical ways to use L0:

- source-tree Stage 1 usage through `./scripts/l0c`,
- repo-local Dea builds under `build/dea/bin` via `make use-dev-stage1` / `make use-dev-stage2`,
- install-prefix and relocatable distribution archives built from the self-hosted Stage 2 compiler.

Validation is centered on:

- Stage 1 and Stage 2 test suites,
- strict triple-bootstrap reproducibility checks,
- workflow/distribution regression tests for build metadata, archives, and release-tag policy,
- strict docs generation and packaged-reference validation.

## Platform Support

The current development support baseline remains:

- Tier 1 hosts: Linux and macOS for Stage 1 and Stage 2 workflows.
- Tier 1 Windows toolchain: MSYS2 `MINGW64` with MinGW-w64 GCC or Clang for build, test, install, and distribution
  workflows, plus generated native `cmd.exe` launchers for invoking the packaged toolchain outside the MSYS2 shell.
- Tier 2 / experimental: MSVC-family builds remain outside the validated release matrix.

## Known Limitations and Constraints

These remain true on the current `1.0.0.dev0` development branch:

1. Backend output is one C translation unit (no multi-object/header split pipeline yet).
2. Arrays/slices are not implemented; indexing syntax exists but unsupported targets are rejected.
3. No address-of (`&`) operator in language semantics.
4. No generics, traits, or macros.
5. Reserved/future keywords and operators are lexed for diagnostics and staged evolution.

## Post-0.9.2 Development Notes

The current `1.0.0.dev0` branch starts from the `0.9.2` release baseline:

1. Keep the current Stage 1/Stage 2 CLI, semantics, stdlib surface, and monorepo release wiring stable unless a bug fix
   requires a targeted correction.
2. Keep the existing validation gates (`make test-all`, `make triple-test`, workflow/distribution checks, and strict
   docs generation) as the default bar for release-readiness.
3. Carry forward the recent Windows/MSYS2 fixes, trace-runner hardening, and Stage 2 diagnostic-parity work as part of
   the normal development baseline.
4. Treat the limitations listed above as explicit L0 scope boundaries unless a narrowly-scoped `1.0.0` blocker demands
   otherwise.

## Path to 1.0

After `l0-v0.9.2`, the remaining work toward `1.0.0` is expected to stay focused on documentation and residual bug fixes
rather than new language surface.

Once Dea/L0 `1.0.0` is cut, further language growth belongs to later levels of the language family:

1. Bitwise operators, top-level `const`, and further language extensions are deferred to Dea/L1.
