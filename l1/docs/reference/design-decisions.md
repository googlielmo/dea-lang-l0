# L1 Language and Runtime Design Decisions

Version: 2026-04-13

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

Current policy also distinguishes between:

- conservative C99 usage that is acceptable as a lowering vehicle
- host/compiler behavior that is too vague to define L1 semantics directly

Where L1 semantics depend on properties not guaranteed uniformly by every C99 target, the backend must validate those
properties and reject unsupported targets rather than silently inheriting implementation-defined or underspecified host
behavior.

## 4. C ABI Naming Policy

Current L1 C ABI policy uses:

- `dea_*` for public generated/runtime C identifiers
- `DEA_*` for public generated/runtime preprocessor names
- `rt_*` for stable runtime API functions
- `_rt_*` for private runtime helpers

Historical `l0_*`, `L0_*`, `_l0_*`, and `_L0_*` names are not part of the current L1 ABI and should not be introduced in
new L1-emitted names. The emitter reserves both the historical prefixes and the current `dea` prefixes when mangling
user/source identifiers so generated C cannot collide with backend/runtime-owned namespaces.

One temporary exception remains: `l0_siphash.h` is still used as an internal include name until the shared cross-level
SipHash include migration lands.

## 5. Future Evolution

Near-term L1 evolution should preserve the current bootstrap implementation and semantics unless a targeted bug fix or a
decision-complete feature addition requires a deliberate change.

When `stage2_l1` is eventually implemented, it should preserve these language/runtime decisions unless the L1 reference
docs are intentionally revised.

## 6. Bootstrap Adaptation Strategy

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

## 7. Pointer and Ownership Policy

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

## 8. Nullability, Casts, and Introspection

Current policy:

- `T?` is the nullable form of `T`
- `null` is the only empty value of a nullable type
- casts with `as` are explicit and checked by the type system/runtime helpers where required
- `expr?` is the null-propagation operator

For non-pointer nullable values, generated C uses wrapper representations rather than exposing host-specific niche
assumptions.

## 9. The `dea` Prelude Module

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

## 10. Integer and Failure Semantics

The bootstrap compiler keeps integer behavior defined rather than inheriting host-C vagueness:

- implemented builtin integer names are `tiny`, `short`, `int`, `long`, `byte`, `ushort`, `uint`, and `ulong`
- `tiny` is 8-bit signed semantics
- `byte` is 8-bit unsigned semantics
- `short` is 16-bit signed semantics
- `ushort` is 16-bit unsigned semantics
- `int` is 32-bit signed semantics
- `uint` is 32-bit unsigned semantics
- `long` is 64-bit signed semantics
- `ulong` is 64-bit unsigned semantics
- overflow-sensitive arithmetic and narrowing go through checked runtime helpers
- integer literals that fit `int` remain ordinary `int` literals
- integer literals outside `int` are carried as opaque bigint payloads until a contextual `uint`, `long`, or `ulong`
  target is known
- fitting integer literals may be used in narrower typed integer contexts without a runtime check, while nonliteral
  narrowing and cross-signedness conversions require an explicit cast
- integer division by zero is a defined runtime error, not host-C undefined behavior

That policy is part of the language contract even though the current implementation is lowered through C.

At the stdlib layer, shared integer helper contracts belong in `std.math`; copied modules such as `std.time` may consume
those helpers, but they should not own general-purpose arithmetic utilities. Floating-point helper policy remains
separate from this integer-focused surface.

## 11. Floating-Point Semantics and Backend Contract

L1 now includes builtin `float` and `double` types and floating-point (FP) literals. Their semantic contract is
intentionally narrow and must not be left as an accident of generated C.

Current policy:

- `float` and `double` are builtin noninteger numeric types
- unsuffixed real literals denote `double`
- a trailing `f` or `F` denotes `float`
- floating arithmetic is non-panicking
- floating division by zero is defined and does not panic
- on supported targets, floating arithmetic uses IEEE-style non-trapping behavior with signed zero, infinities, and NaNs
- integer checked arithmetic and floating arithmetic remain distinct lowering paths
- floating `/` does not route through checked integer helpers
- the language-level meaning of floating operations belongs to L1 and is not delegated to unspecified host C behavior

Current conversion and typing policy stays intentionally narrow:

- implicit `float -> double` widening is allowed
- implicit `double -> float` is not allowed
- implicit `int -> float` and `int -> double` are not generally allowed
- implicit `float -> int` and `double -> int` are not allowed
- mixed integer and real binary arithmetic requires an explicit cast to a matching floating type
- explicit numeric `as` casts among `int`, `float`, and `double` are part of the current bootstrap surface

Direct integer literal conversion is a narrow contextual rule:

- an integer literal expression may be used directly in a typed `float` or `double` context when the literal value is
  representable by the target real type
- this rule applies to parenthesized integer literals and unary-minus integer literals
- this rule applies to annotated `let` initializers, function call arguments, return expressions, and constructor
  arguments where the destination type is known
- this rule does not apply to nonliteral integer expressions or variables
- this rule does not create general implicit `int -> float` or `int -> double` promotion
- mixed integer and real binary arithmetic still requires an explicit cast to a matching floating type

Current operator policy for real values:

- unary `-` is allowed for `float` and `double`
- binary `+`, `-`, `*`, and `/` require matching real types after the allowed `float -> double` widening step
- `float op double` and `double op float` widen to `double`
- comparison operators on real values follow the same narrow compatibility rule and yield `bool`

Current backend contract for FP-using programs:

- `float` lowers to C `float`
- `double` lowers to C `double`
- the lowered C types must have the required binary-radix representation and precision expected by the L1 types they
  stand for
- the target must provide infinities and NaNs for the lowered types
- floating arithmetic must be non-trapping in ordinary execution
- backend modes or optimization assumptions that would invalidate NaN, infinity, signed-zero, or ordinary ordered
  comparison semantics relied on by L1 are not valid for FP-using programs
- if these requirements are not met, the backend must reject programs that use `float` or `double`

Rationale:

- Dea/L1 wants defined behavior rather than ambient host-language folklore
- plain C lowering is acceptable only when the target contract that makes it sound is stated explicitly
- rejecting unsupported FP targets is cleaner than pretending every C99 target means the same thing
- keeping the conversion lattice narrow avoids accidental promotion creep in the bootstrap compiler

Consequences:

- floating `/ 0.0` is a language-defined non-panicking operation on supported targets
- FP support is conditional on backend validation rather than assumed on every possible C99 target
- future backend or optimization changes must preserve the stated FP contract rather than silently weakening it

## 12. I/O and Runtime API Shape

Bootstrap-stage tooling intentionally favors simple whole-file and console APIs over richer streaming abstractions. That
is sufficient for compiler bootstrapping, diagnostics, and current examples while keeping the language/library surface
narrow.

## 13. Name Disambiguation

Qualified references (`module.path::Name`) are the current cross-module disambiguation mechanism.

The compiler also synthesizes one implicit module, `dea`, for language-level primitives. Its exports are opened into
every module at the lowest precedence, so user locals and explicit imports shadow `dea` with the normal `RES-0021`
warning. `dea::sizeof` and `dea::ord` remain the stable qualified escape hatch when user code intentionally reuses those
names.

Rationale:

- keep open imports ergonomic for simple programs
- provide an explicit escape hatch for ambiguity
- avoid introducing more namespace surface before it is needed

## 14. Numeric Literal Representation in L1

L1 introduces numeric types that are not native to the L0 implementation language, including implemented integer forms
such as `uint`, `long`, and `ulong`, plus still in-progress floating-point forms such as `float` and `double`.

Current decision:

- integer literals outside native bootstrap `int` are represented inside the compiler as opaque bigint payloads carrying
  sign, significant digits, and base (`2`, `8`, `10`, or `16`)
- the compiler does not perform compile-time arithmetic on those payloads; it only performs textual range checks where a
  contextual integer target is known
- generated C reconstructs equivalent literal spellings from the stored payload/base pair and adds destination-aware C
  suffixes or macros where required
- IR and semantic nodes remain typed, so the payload encoding is an internal implementation detail rather than a
  language-level contract

For floating-point literals and expressions, the current bootstrap compiler adds the following rule:

- Stage 1 does not perform arithmetic evaluation of floating-point expressions unless it can guarantee results identical
  to the L1 floating-point contract

Rationale:

- C99 literal syntax such as `1L`, `1.0f`, and `1.0` is already well-defined
- correctness and constant folding can be delegated to the downstream C compiler in the bootstrap stage only where that
  delegation remains consistent with the stated L1 contract
- this keeps the implementation surface small and avoids blocking L1 feature work on arbitrary-precision constant
  infrastructure
- a later structured constant representation can be introduced without changing the typed IR shape

Consequences:

- compile-time constant folding for non-native numeric types is intentionally unavailable in the current bootstrap
  compiler
- code generation must preserve literal value/base information and emit an equivalent typed C spelling faithfully
- the compiler and emitted C must not disagree about the meaning of floating literals, arithmetic, division by zero, or
  non-finite results

Future direction:

- when L1 needs target-independent constant evaluation or richer compile-time semantics, migrate the payload
  representation to an APInt/APFloat-style structured form that carries explicit type/width/value information
