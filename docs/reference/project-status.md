# L0 Project Status

Version: 2026-03-24

This document summarizes what is implemented in this repository today and what defines the Dea/L0 `1.0.0` stabilization
target.

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
- release packaging plus docs/PDF publishing automation through the repository workflows.

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

## Platform Support

The `1.0.0` support promise is:

- Tier 1 hosts: Linux and macOS for Stage 1 and Stage 2 workflows.
- Tier 1 Windows toolchain: MSYS2 `MINGW64` with MinGW-w64/GCC for build, test, install, and distribution workflows.
- Tier 2 / experimental: MSVC-family builds remain outside the `1.0.0` validated matrix.

## Known Limitations and Constraints

These remain true in the `1.0.0` language/compiler contract:

1. Backend output is one C translation unit (no multi-object/header split pipeline yet).
2. Arrays/slices are not implemented; indexing syntax exists but unsupported targets are rejected.
3. No address-of (`&`) operator in language semantics.
4. No generics, traits, or macros.
5. Reserved/future keywords and operators are lexed for diagnostics and staged evolution.

## 1.0 Stabilization Notes

The remaining `1.0.0` work is release-definition work, not major compiler-surface expansion:

1. Keep the current Stage 1/Stage 2 CLI, semantics, and stdlib surface stable for the `1.0.x` line.
2. Keep the existing validation gates (`make test-all`, `make triple-test`, workflow/distribution checks, and strict
   docs generation) as release criteria.
3. Treat the limitations listed above as explicit L0 scope boundaries, not deferred `1.0.0` blockers.

## Post-1.0 Direction

After Dea/L0 `1.0.0`, further language growth belongs to later levels of the language family:

1. Bitwise operators, top-level `const`, and further language extensions are deferred to Dea/L1.
