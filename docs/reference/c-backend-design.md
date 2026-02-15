# L0 C Backend Design

This is the canonical backend implementation document for Stage 1.

Related docs:

- Stage 1 architecture and pass flow: [reference/architecture.md](architecture.md)
- Language/runtime rationale and future evolution: [reference/design-decisions.md](design-decisions.md)
- Stage 1 contract/index: [specs/compiler/stage1-contract.md](../specs/compiler/stage1-contract.md)

## Overview

Stage 1 code generation is split into:

- `compiler/stage1_py/l0_backend.py`: orchestration and lowering policy (`WHAT`/`WHEN`)
- `compiler/stage1_py/l0_c_emitter.py`: C99 syntax emission (`HOW`)
- `compiler/stage1_py/l0_string_escape.py`: shared literal escape decode/encode utilities

Input is a fully-typed `AnalysisResult`. Output is one C99 translation unit.

## Responsibilities Split

### Backend (`l0_backend.py`)

- Validates generation preconditions (`CompilationUnit` exists, no semantic errors).
- Orders type emission using a dependency graph + topological sort.
- Lowers statements/expressions to emitter calls.
- Manages scope/lifetime state and ARC cleanup scheduling.
- Handles retain-on-copy for ownership-sensitive assignments/initialization sites.
- Emits function bodies and decides where cleanup runs on normal/early exits.

### C emitter (`l0_c_emitter.py`)

- Emits C includes, declarations, definitions, and formatting.
- Implements name mangling and identifier hygiene for C keywords.
- Converts semantic types to C types.
- Emits C for operators, constructors, casts, loops, switch/case, labels/gotos.
- Emits runtime helper calls (checked arithmetic, unwrap helpers, retain/release, allocation/drop).
- Lowers string literals (const and non-const) through one canonical decode/encode path, emitted via
  `L0_STRING_CONST(...)`.

## Generated Unit Layout

The generated C file is organized in this order:

1. File header and includes (`stdint.h`, `stdbool.h`, `stddef.h`, `l0_siphash.h`, `l0_runtime.h`), with optional
   trace defines (`L0_TRACE_ARC`, `L0_TRACE_MEMORY`) emitted before `l0_runtime.h` when enabled via CLI
2. Forward declarations for all structs/enums
3. Optional wrapper typedefs (early phase: builtins)
4. Struct/enum definitions in dependency order
5. Optional wrapper typedefs (late phase: user-defined value types)
6. Top-level `let` declarations (`static` globals)
7. Function declarations (including extern declarations)
8. Non-extern function definitions
9. C `main(int argc, char **argv)` wrapper when entry module defines `main`

Current backend target is a **single C translation unit**.

## Type Lowering

### Builtins

- `int` -> `l0_int`
- `byte` -> `l0_byte`
- `bool` -> `l0_bool`
- `string` -> `l0_string`
- `void` -> `void`

(typedefs/runtime definitions live in `compiler/stage1_py/runtime/l0_runtime.h`.)

### Structs and enums

- Structs lower to `struct l0_{module}_{Name}`.
- Enums lower to tagged unions:
    - `enum l0_{module}_{Enum}_tag`
    - `struct l0_{module}_{Enum} { tag; union data { ... } }`
- Zero-field structs/variants emit dummy fields to stay C99-valid.

### Pointers and nullable

- `T*` lowers to pointer type in C.
- `T*?` uses niche representation: also a pointer type, `NULL` represents `none`.
- Value nullable (`T?`, where `T` is not pointer-shaped) lowers to wrapper typedef:
    - `typedef struct { l0_bool has_value; T value; } l0_opt_*;`

Wrapper typedefs are emitted in two phases so dependencies are valid.

## Name Mangling and Symbol Rules

- User-defined type/function names: `l0_{module_path_with_underscores}_{name}`
- Top-level lets: `l0_{module}_{let_name}`
- Local identifiers conflicting with C/runtime-reserved names are suffixed (`__v`).
- `extern func` names are intentionally **not mangled** (FFI boundary).

## Statement and Expression Lowering

### Expressions

Implemented lowering includes:

- Literals, var refs, unary/binary ops, calls, field/index access, casts, constructors
- String literals are decoded from token escapes to bytes, then emitted as `L0_STRING_CONST("...", len)` values
  (cast to `l0_string` where required by expression context), with bytes C-escaped from decoded content.
- `new` heap allocation (`_rt_alloc_obj`) + initialization
- `try` (`expr?`) lowering to checked unwrap with early return on empty
- Checked int arithmetic uses runtime helpers (`_rt_iadd`, `_rt_isub`, `_rt_imul`, `_rt_idiv`, `_rt_imod`)
- Checked narrowing casts use runtime helpers (`_rt_narrow_*`)

### Statements

Implemented lowering includes:

- `let`, assignment, expression statements
- `if/else`, `while`, `for`
- `match` over enum tags (switch-based)
- `case` (scalar switch or string equality chain)
- `with` (inline or block cleanup forms)
- `break`, `continue`, `return`
- `drop` (runtime deallocation + owned-field cleanup)

## Ownership and Cleanup Model

The backend schedules cleanup, while emitter produces concrete cleanup code.

Key points:

- ARC types (notably `string`) use runtime `rt_string_retain`/`rt_string_release`.
- Copying from place expressions at ownership-creating sites performs retain-on-copy.
- `return expr;` is an ownership-creating site. Returning a place expression retains before scope cleanup runs.
- Direct `return local_var;` for owned locals is lowered as a move: cleanup skips that binding instead of retaining.
- Scope exit cleanup runs in reverse declaration order.
- Early exits (`return`, `break`, `continue`, `try` early return) run pending `with` cleanup first, then owned var
  cleanup.
- Enum/struct-by-value cleanup recursively cleans owned fields of active values.

## Entry Point Behavior

If entry module defines `main`, backend emits C wrapper:

- Signature: `int main(int argc, char **argv)`
- Initializes runtime argv state via `_rt_init_args(argc, argv)`
- Calls mangled L0 main
- Returns L0 `int` or `bool` result as C `int`, other result types are discarded and return `0` after call

## Debuggability

- Generated code is sectioned and comment-labeled.
- `#line` directives are emitted when enabled in compile context (default on, can be disabled with
  `--no-line-directives`) for accurate source mapping in debuggers and error messages.
- Runtime tracing can be enabled from codegen with `--trace-arc` and `--trace-memory`; generated C emits
  preprocessor toggles consumed by `l0_runtime.h`.
- Escape decoding used by `case` literal semantic checks is shared with codegen to avoid divergence.

Tracing details and runtime log contract are specified in [specs/runtime/trace.md](../specs/runtime/trace.md).

## Current Constraints and Known Gaps

1. Backend emits one `.c` file (no header/source split, no separate object emission strategy).
2. Function type emission as first-class C function pointers is not implemented.
3. Runtime/ABI surface is C-only and assumes C99-compatible toolchains.
4. Advanced optimizations are delegated to the underlying C compiler (focus is correctness and explicit lowering).

## Testing Coverage

Primary backend/codegen tests live under `compiler/stage1_py/tests/`, including:

- `test_l0_codegen_basic.py`
- `test_l0_codegen_advanced.py`
- `test_l0_codegen_semantics.py`
- `test_l0_codegen_overflow_and_control_flow.py`
- `test_l0_codegen_lvalue_caching.py`
- `test_l0_codegen_constructors.py`
- `test_l0_codegen_type_ordering.py`
- `test_l0_driver_cross_module_runtime.py`

Golden expected C outputs are in `compiler/stage1_py/tests/codegen/*.expected`.
