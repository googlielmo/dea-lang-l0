# L0 Language and Runtime Design Decisions

This document records rationale and policy decisions.

Canonical ownership boundaries:

- Compiler architecture and pass flow: [reference/architecture.md](architecture.md)
- C backend implementation/lowering details: [reference/c-backend-design.md](c-backend-design.md)
- Stage 1 contract/index: [specs/compiler/stage1-contract.md](../specs/compiler/stage1-contract.md)

## 1. Scope and Goals

The language aims to be:

- small,
- practical for a self-hosting compiler,
- explicit about safety constraints,
- portable via conservative C99 lowering.

Core policy: language-level behavior should avoid undefined behavior; failures are rejected statically or become defined
runtime aborts.

## 2. Runtime Boundary Model

We keep a layered boundary:

1. L0 language + compiler.
2. L0 std/runtime libraries.
3. Small C kernel/runtime interface (`runtime/l0_runtime.h`).

Design intent:

- language semantics stay stable,
- platform-specific behavior stays quarantined in the C runtime boundary,
- generated C remains conservative and portable.

## 3. Pointer Model and Address-of Decision

### 3.1 Current pointer model

Current Stage 1/2 model includes:

- pointer types (`T*`, nullable `T*?`),
- dereference (`*expr`),
- field access with pointer auto-deref behavior (`ptr.field`).

### 3.2 No address-of operator in Stage 1

`&` is intentionally excluded in Stage 1.

Rationale:

- avoids exposing stack-address lifetime hazards,
- keeps ownership/lifetime rules simpler during bootstrap,
- keeps boundary complexity concentrated in runtime/kernel APIs.

### 3.3 No raw pointer arithmetic contract

Pointer arithmetic is not part of Stage 1 surface semantics.

Index syntax exists in the frontend AST/checker, but array/slice types are not yet implemented in Stage 1; indexing is
therefore currently rejected for unsupported targets.

## 4. Nullability, Casts, and Introspection

### 4.1 Nullability policy

- `T?` encodes nullable/optional values.
- Non-pointer nullable values are represented by wrapper forms in generated C.
- Nullable pointers use pointer-null representation.

### 4.2 Cast policy (`as`)

Casts are explicit and checked by type rules and runtime helpers where needed.

Important intent:

- narrowing/wrapping/unwrap semantics are explicit,
- invalid casts are compile-time errors,
- runtime checks are used for defined-failure cases (panic), not UB.

### 4.3 Try operator (`expr?`)

Try-propagation provides nullable short-circuiting behavior with explicit type semantics.

### 4.4 `sizeof`

`sizeof` exists as a language intrinsic and returns `int` in Stage 1.

## 5. Early I/O Model

Stage-1/early-stage tooling intentionally prefers whole-file and simple console operations over complex streaming APIs.

Rationale:

- enough for compiler bootstrapping and diagnostics,
- avoids premature API surface complexity.

Concrete runtime API names are documented in `compiler/stage1_py/l0/stdlib/sys/rt.l0` and implemented in
`compiler/stage1_py/runtime/l0_runtime.h`.

## 6. Name Disambiguation via Qualified References

Qualified names (`module.path::Name`) are used for cross-module disambiguation when open imports conflict.

Rationale:

- preserve open-import ergonomics for simple programs,
- provide explicit escape hatch for ambiguity,
- avoid introducing aliases/namespaces too early.

## 7. Integer Model Rationale

Stage 1 semantics intentionally avoid inheriting host-C integer vagueness.

Policy:

- `int` is defined as 32-bit signed semantics,
- `byte` is 8-bit semantics,
- runtime helpers enforce defined behavior for overflow/division/mod edge cases.

Implementation details of generated helpers and typedef mapping are canonical
in [reference/c-backend-design.md](c-backend-design.md) and
`runtime/l0_runtime.h`.

## 8. Toolchain and Portability Policy

Policy-level decision:

- generated C should stay within conservative C99 usage,
- backend behavior should be deterministic and easy to reason about,
- platform/compiler specifics should be isolated to runtime boundary code.

Operational backend rules belong in [reference/c-backend-design.md](c-backend-design.md).

## 9. Future Evolution

Planned direction:

1. Keep Stage 1 minimal and stable.
2. Expand language features in Stage 2 when semantics are decision-complete.
3. Continue keeping unsafe/platform-specific details behind explicit runtime boundaries.

---

# Addendum: Planned Stage 2 Language Extensions

These are design intentions, not guaranteed implementation commitments.

## A. Bitwise operators for `int`

Planned scope:

- unary `~`
- binary `&`, `|`, `^`, `<<`, `>>`

Planned semantic policy:

- defined behavior for valid shift ranges,
- panic (defined failure) for invalid shift counts,
- no UB exposure through shift edge cases.

## B. Top-level `const`

Planned scope:

- immutable top-level compile-time declarations.

Planned semantic policy:

- restricted constant-expression subset,
- compile-time errors for invalid constant evaluation,
- clear initialization/order rules before enabling cross-module complexity.
