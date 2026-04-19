# L1 Language and Runtime Design Decisions

Version: 2026-04-19

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
- a value of type `T` may be used in a `T?` context, including returns, assignments, and arguments; generated code wraps
  the value as present
- casts with `as` are explicit and checked by the type system/runtime helpers where required
- integer casts may target nullable integer types directly when the same cast to the nullable inner type is valid; for
  example, `0 as ulong?` and `9999999999 as long?` are accepted and apply the same range-checking behavior as
  `0 as ulong` and `9999999999 as long` before wrapping
- the current nullable-integer cast rule unwraps exactly one nullable layer and is scoped to builtin integer payload
  types; it does not yet mean that every implicit widening conversion composes with `as`
- `expr?` is the null-propagation operator

For non-pointer nullable values, generated C uses wrapper representations rather than exposing host-specific niche
assumptions.

Future direction: broaden the cast rule so `expr as U` is valid whenever there is an explicit cast target `V` for the
operand and `V` can be implicitly widened to `U`. That would make the current integer-to-optional-integer behavior one
instance of a general "explicit conversion followed by implicit widening" rule, covering future cases such as broader
numeric widenings or nullable pointer-family widenings when those conversions are deliberately added.

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
- explicit integer casts to nullable integer targets, such as `0 as ulong?`, use the same checked conversion policy as
  casts to the inner type and then produce a present nullable value
- binary `&`, `|`, `^`, `<<`, and `>>` use the same common-integer-type lattice as the other integer binary operators
- unary `~` preserves the operand's integer type; the backend casts the promoted C result back to that L1 type
- right shift follows the signedness of the normalized operand type, so signed shifts are arithmetic and unsigned shifts
  are logical on supported targets
- integer division by zero is a defined runtime error, not host-C undefined behavior

That policy is part of the language contract even though the current implementation is lowered through C.

At the stdlib layer, integer helper contracts belong in `std.math`; copied modules such as `std.time` may consume those
helpers, but they should not own general-purpose arithmetic utilities. The unsuffixed helper names remain the shared
`int` surface. L1-only `uint`, `long`, and `ulong` helpers use explicit `_ui`, `_l`, and `_ul` suffixes so wider fixed
widths do not shadow or blur the shared API. Signed `long` helpers follow the same checked representability policy as
the `int` helpers, while unsigned helpers use plain `div_*` / `mod_*` names and omit signed-only concepts such as
`sign`, `abs`, `ediv`, and `emod`.

Floating-point helpers belong in `std.real` with their runtime C FFI backed by `sys.real`. Explicit `_f` and `_d`
suffixes prevent shadowing and ambiguity between `float` and `double`. To minimize runtime footprints, the host math
library (`-lm`) and the `l1_real.h` C wrapper are only linked and included when the compilation unit actually uses
`sys.real`, rather than treating every float-using program as a math-library consumer.

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

Current `std.io` numeric output policy follows the same explicit suffix convention as the rest of the L1 numeric stdlib
surface:

- `int`, `string`, and `bool` keep the copied ergonomic spellings such as `print_i`, `print_s`, and `print_b`
- L1-only fixed-width integer output uses `_ui`, `_l`, and `_ul` for `uint`, `long`, and `ulong`
- floating output uses `_f` and `_d` for `float` and `double`
- stdout and stderr expose the same one-value numeric families, with newline variants using the existing `printl_*` /
  `err_printl_*` naming pattern
- pair-print helpers are not expanded cartesian-style for every numeric type; callers can compose labels with
  single-value print helpers

Current stdin token policy keeps parsing layered:

- `read_delim`, `read_delim_any`, and `read_delim_ws` own token extraction from stdin
- typed integer reads use `read_delim_ws` plus the matching `std.text` parser
- integer parsing remains in `std.text`, not in `std.io`
- float/double reads are deferred until the library has an explicit floating-point parsing contract

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
such as `uint`, `long`, and `ulong`, plus the implemented floating-point forms `float` and `double`.

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

## 15. String Value Semantics

`string` is an ARC-managed value type. Two `string` values are language-equivalent when their byte contents are equal;
their runtime representation (static versus heap, deduplicated or not) is not observable through the language.

Current policy:

- equality (`==`, `!=`) on `string` compares by content bytes, backed by the runtime helper `rt_string_equals`
- equality is consistent across `==`, `case` arms over `string`, and `std.string::eq_s`
- ordered comparisons (`<`, `<=`, `>`, `>=`) on `string` use byte-wise lexicographic ordering through
  `rt_string_compare`
- ordered comparisons are consistent across the operators and `std.string::cmp_s`
- string identity, meaning whether two values refer to the same runtime instance, is intentionally not exposed through
  any operator, cast, or intrinsic
- any future need for instance equality will be satisfied through an explicit `sys.*` helper with documented
  implementation-defined semantics, not through a new operator

Rationale:

- identity-based equality would leak backend representation choices such as literal deduplication and static-versus-heap
  selection into user-observable semantics, contradicting the UB-free/defined-semantics policy stated in §1
- value equality is the only semantic consistent with existing `case`-over-string behavior and with the backend's
  freedom to evolve dedup and arena strategies

The top-level `==`, `!=`, `<`, `<=`, `>`, and `>=` operators are now wired for `string` operands in the current
bootstrap compiler. String concatenation via `+` remains deferred in the roadmap.

## 16. Top-level `const` versus `let`

L1 now distinguishes between two top-level binding forms:

- `const NAME: T = EXPR;` for compile-time-known bindings whose initializer must stay inside the existing static
  initializer subset
- `let NAME [: T] = EXPR;` for ordinary top-level bindings, which remain the path that the active non-constant-`let`
  plan is widening toward module-init lowering

Current policy:

- top-level `const` requires an explicit type annotation
- top-level `const` initializers must be literals, `null`, or constructor calls whose arguments are themselves constant
- top-level `const` lowers to `static const` generated C declarations under the existing `dea_*` ABI naming scheme
- assignment to a top-level `const` binding, including field assignment through a value-typed `const`, is rejected
- block-local `const` is still deferred; only top-level `const` is accepted today

Rationale:

- this keeps the current compile-time-known path explicit while the separate non-constant-`let` work lifts top-level
  runtime initialization into module-init functions
- requiring an explicit type keeps the accepted constant subset deterministic during bootstrap and avoids depending on a
  broader compile-time evaluator before that design is ready

## 17. Comparison Operator Scope

The grammar admits `==`, `!=`, `<`, `<=`, `>`, `>=` between any operand types. The type checker intentionally restricts
which operand types each operator accepts; this section records the deliberate rejections.

Ordered comparison on `bool` is not accepted:

- `bool < bool`, `bool <= bool`, `bool > bool`, and `bool >= bool` are rejected as non-numeric operands
- the rejection is a design choice, not a deferred feature: booleans are two labels, not a scalar ordering, and a
  defined `true > false` meaning would add a footgun without a corresponding use case
- the rejection diagnostic is `TYP-0170`, consistent with other non-numeric operand rejections on the relational
  operators
- callers who want to route on a boolean value should use `if` / `case (b) { true => ...; false => ...; }` or compare
  equality (`b == true`, `b != false`, or the simpler `b` / `!b` expressions)

Equality on `bool` remains accepted, unchanged:

- `bool == bool` and `bool != bool` return `bool`
- this matches `case (b) { true => ...; }` dispatch and the general policy of treating `bool` as a scalar tag for
  equality but not for ordering

Rationale:

- The Dea policy prefers a compile-time rejection over a defined-but-misleading ordering
