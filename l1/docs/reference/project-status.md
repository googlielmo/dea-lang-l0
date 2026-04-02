# L1 Project Status

Version: 2026-04-02

This document summarizes what is implemented in the Dea/L1 subtree today.

Dea/L1 is currently in bootstrap status:

- the runnable compiler is `compiler/stage1_l0/`, implemented in Dea/L0
- the current shared assets are `compiler/shared/l1/stdlib/` and `compiler/shared/runtime/l1_runtime.h`
- `compiler/stage2_l1/` exists only as a placeholder for a future self-hosted compiler

L0 remains the active release line. The L1 subtree is the current home for bootstrap compiler work, copied library
surface, and future language growth beyond L0.

## Scope and Canonical References

Use this file as the status snapshot. For implementation details, use:

- [architecture.md](architecture.md) for pass structure and data flow
- [c-backend-design.md](c-backend-design.md) for backend lowering and generated C behavior
- [design-decisions.md](design-decisions.md) for language and runtime rationale
- [grammar.md](grammar.md) for accepted concrete syntax
- [ownership.md](ownership.md) for ownership and cleanup behavior
- [standard-library.md](standard-library.md) for current std/sys module APIs

## Current Status

### Compiler

`compiler/stage1_l0/` is the only implemented L1 compiler today. It provides the bootstrap frontend, semantic analysis,
C generation, and host build/run integration for `.l1` inputs.

The implementation sources remain `.l0`, while user-facing L1 source inputs, examples, and copied stdlib modules use
`.l1`.

### Runtime and Standard Library

The current L1 tree includes:

- copied L1 stdlib modules under `compiler/shared/l1/stdlib/`
- runtime headers under `compiler/shared/runtime/`
- the current bootstrap test suite under `compiler/stage1_l0/tests/`

This gives the subtree a complete bootstrap environment without claiming a self-hosted L1 compiler yet.

## Language and Library Coverage

The current implemented language surface matches the bootstrap subset exercised by the copied compiler and tests,
including:

- functions, structs, enums, type aliases, and top-level `let`
- modules/imports with qualified-name disambiguation
- structured control flow including `if`, `while`, `for`, `match`, `case`, and `with` / `cleanup`
- explicit nullability, `new` / `drop`, ARC-managed `string`, casts, and postfix `expr?`

The copied stdlib currently includes the core bootstrap modules for I/O, strings, text, paths, filesystem access, time,
randomness, assertions, optionals, and the current container set.

## Delivery and Validation

The practical local workflow today is:

```bash
make -C ../l0 use-dev-stage2
make build-stage1
source build/l1/bin/l1-env.sh
l1c --version
make test-stage1
```

Validation is currently centered on:

- the `compiler/stage1_l0/tests/` suite
- bootstrap trace tests and helper scripts under `compiler/stage1_l0/`
- keeping the copied stdlib/runtime tree usable by the bootstrap compiler

## Platform Support

Current bootstrap expectations remain aligned with the host/toolchain assumptions inherited from the upstream L0
bootstrap path:

- Linux and macOS are the primary local-development hosts
- builds require a C99-compatible host compiler
- the bootstrap compiler itself depends on an upstream `l0c-stage2` unless `L1_BOOTSTRAP_L0C` is set explicitly

## Known Constraints

These remain true today:

1. There is no implemented `stage2_l1` compiler yet.
2. Backend output is one C translation unit.
3. Arrays/slices are not implemented as general language features.
4. Address-of (`&`), generics, traits, and macros are not part of the current active language surface.
5. L1 docs and specs are still being established; `l1/docs/reference/` is the main current reference home.

## Near-Term Direction

Near-term L1 work should focus on:

1. stabilizing the bootstrap compiler and copied stdlib/runtime surface
2. improving L1-local documentation and tests
3. preparing the subtree for a later self-hosted `stage2_l1` implementation without claiming it exists today
