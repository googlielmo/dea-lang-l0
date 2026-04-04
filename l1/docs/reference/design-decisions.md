# L1 Language and Runtime Design Decisions

Version: 2026-04-04

This document records current design rationale and policy decisions for Dea/L1 as implemented by the bootstrap compiler.

Related docs:

- compiler structure and pass flow: [architecture.md](architecture.md)
- backend lowering details: [c-backend-design.md](c-backend-design.md)
- ownership and cleanup rules: [ownership.md](ownership.md)
- standard library surface: [standard-library.md](standard-library.md)

## 1. Scope and Goals

The current L1 bootstrap language aims to be:

- small but expressive
- practical for bootstrapping a later self-hosted compiler
- suitable for systems/runtime-oriented code
- explicit about safety boundaries
- portable through conservative C99 lowering

Policy: language-level behavior should avoid undefined behavior. Invalid programs should be rejected statically where
possible and otherwise fail in defined runtime ways.

## 2. Runtime Boundary Model

The current stack is intentionally layered:

1. L1 language and compiler
2. L1 stdlib modules under `compiler/shared/l1/stdlib/`
3. C runtime boundary in `compiler/shared/runtime/l1_runtime.h`

This keeps platform-specific behavior concentrated at the runtime boundary instead of leaking into core language
semantics.

## 3. Portability Policy

Generated code should stay within conservative C99 usage. Platform/compiler quirks belong in the runtime boundary, not
in the language definition.

## 4. Future Evolution

Near-term L1 evolution should preserve the current bootstrap implementation and semantics unless a targeted bug fix or a
decision-complete feature addition requires a deliberate change.

When `stage2_l1` is eventually implemented, it should preserve these language/runtime decisions unless the L1 reference
docs are intentionally revised.

## 5. Bootstrap Adaptation Strategy

The current L1 subtree is intentionally bootstrapped from the mature L0 toolchain rather than started from a blank
implementation.

Current policy:

- the runnable L1 compiler starts from copied L0 Stage 2 compiler sources and is retargeted inside `compiler/stage1_l0/`
- the current L1 reference set starts from copied L0 reference material and is rewritten to describe the real L1
  bootstrap tree
- copied implementation and docs are allowed to retain historical internal names when those names are merely bootstrap
  artifacts rather than user-facing semantics

Rationale:

- this keeps the first L1 compiler runnable early
- it preserves a known-good baseline while L1-specific divergence is still small
- it favors incremental retargeting over speculative greenfield design

## 6. Pointer and Ownership Policy

Current bootstrap policy includes:

- pointer types (`T*`, nullable `T*?`)
- dereference (`*expr`)
- pointer field access through the current compiler's auto-deref behavior
- postfix pointer indexing syntax (`ptr[index]`) in expressions
- explicit `new` / `drop` for heap object lifetime
- ARC-managed `string`

No design decision has been finalized yet on:

- whether address-of (`&`) will become part of the L1 language surface
- the final semantic contract for postfix pointer indexing (`ptr[index]`)

Current bootstrap status:

- `&` is reserved in the current implementation and is not yet assigned address-of semantics
- postfix indexing is implemented today for current pointer-based use cases, but its long-term language status and
  precise semantic contract are not being frozen by this document

These docs should not be read as excluding either feature from L1 going forward.

## 7. Nullability, Casts, and Introspection

Current policy:

- `T?` is the nullable form of `T`
- `null` is the only empty value of a nullable type
- casts with `as` are explicit and checked by the type system/runtime helpers where required
- `expr?` is the null-propagation operator

For non-pointer nullable values, generated C uses wrapper representations rather than exposing host-specific niche
assumptions.

## 8. The `dea` Prelude Module

The compiler synthesizes one implicit module, `dea`, for language-level primitives.

Current contents:

- `dea::sizeof`
- `dea::ord`

Current policy:

- `dea` is a virtual module owned by the compiler, not a source file loaded from disk
- `dea` is opened into every module automatically
- `dea` has the lowest import precedence, so user locals and explicit imports shadow it normally
- `dea::sizeof` and `dea::ord` remain the stable qualified escape hatch when user code intentionally reuses those names
- this behavior does not change the surface grammar: `dea` is a semantic prelude mechanism, not a special import syntax
- qualified `dea::sizeof` and `dea::ord` are always available even when unqualified `sizeof` or `ord` are shadowed
- shadowing uses the normal name-resolution rules and warning behavior rather than bespoke intrinsic-specific fallback

Rationale:

- keep intrinsics in the normal symbol/module system instead of hard-coding bare names
- avoid hijacking user-defined functions named `sizeof` or `ord`
- preserve ergonomic unqualified use for bootstrap-stage code while keeping an explicit disambiguation path
- leave room for future compiler-owned type aliases and other prelude-level symbols without introducing a synthetic
  source file

## 9. Integer and Failure Semantics

The bootstrap compiler keeps integer behavior defined rather than inheriting host-C vagueness:

- planned builtin integer names are `tiny`, `short`, `int`, `long`, `byte`, `ushort`, `uint`, and `ulong`
- `tiny` is 8-bit signed semantics
- `byte` is 8-bit unsigned semantics
- `int` is 32-bit signed semantics
- overflow-sensitive arithmetic and narrowing go through checked runtime helpers

That policy is part of the language contract even though the current implementation is lowered through C. Some planned
integer builtin names are documented in the grammar before the current bootstrap compiler implements them.

## 10. I/O and Runtime API Shape

Bootstrap-stage tooling intentionally favors simple whole-file and console APIs over richer streaming abstractions. That
is sufficient for compiler bootstrapping, diagnostics, and current examples while keeping the language/library surface
narrow.

## 11. Name Disambiguation

Qualified references (`module.path::Name`) are the current cross-module disambiguation mechanism.

The compiler also synthesizes one implicit module, `dea`, for language-level primitives. Its exports are opened into
every module at the lowest precedence, so user locals and explicit imports shadow `dea` with the normal `RES-0021`
warning. `dea::sizeof` and `dea::ord` remain the stable qualified escape hatch when user code intentionally reuses those
names.

Rationale:

- keep open imports ergonomic for simple programs
- provide an explicit escape hatch for ambiguity
- avoid introducing more namespace surface before it is needed

## 12. Numeric Literal Representation in L1

L1 introduces numeric types that are not native to the L0 implementation language, including planned forms such as
`long`, `float`, and `double`.

Current decision:

- numeric literals of non-native L1 numeric types are represented inside the bootstrap compiler as opaque strings
- the compiler does not perform compile-time arithmetic on those payloads
- the generated C99 output emits those literal spellings verbatim
- IR and semantic nodes remain typed, so the payload encoding is an internal implementation detail rather than a
  language-level contract

Rationale:

- C99 literal syntax such as `1L`, `1.0f`, and `1.0` is already well-defined
- correctness and constant folding can be delegated to the downstream C compiler in the bootstrap stage
- this keeps the implementation surface small and avoids blocking L1 feature work on arbitrary-precision constant
  infrastructure
- a later structured constant representation can be introduced without changing the typed IR shape

Consequences:

- compile-time constant folding for non-native numeric types is intentionally unavailable in the current bootstrap
  compiler
- code generation must preserve literal spellings and suffixes faithfully

Future direction:

- when L1 needs target-independent constant evaluation or richer compile-time semantics, migrate the payload
  representation to an APInt/APFloat-style structured form that carries explicit type/width/value information
