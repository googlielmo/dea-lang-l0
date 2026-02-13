# L0 Project Status

Version: 2026-02-13

This document summarizes what is implemented in this repository today and what remains open.

## Scope and Canonical References

Use this file as a status snapshot. For implementation details, use:

- [architecture](architecture.md) for pass structure and data flow.
- [stage1_compiler_contract](stage1_compiler_contract.md) for external interfaces and guarantees.
- [c_backend_design](c_backend_design.md) for backend lowering and generated C behavior.
- [l0_grammar](l0_grammar.md) for accepted concrete syntax.
- [standard_library](standard_library.md) for current std/sys module APIs.

## Stage 1 Compiler (Python) - Current Implementation

Stage 1 is implemented in `compiler/stage1_py` and drives:

1. `Lexer.tokenize()`
2. `Parser.parse_module()`
3. `NameResolver.resolve()`
4. `SignatureResolver.resolve()`
5. `LocalScopeResolver.resolve()`
6. `ExpressionTypeChecker.check()`
7. `Backend.generate()`

### Frontend and Language Surface

The lexer/parser/AST currently support:

- Top-level declarations: `func`, `extern func`, `struct`, `enum`, `type`, `let`.
- Module system: `module` + open `import` of dotted module names.
- Statements: block, `let`, assignment, `if/else`, `while`, `for`, `with` (inline and cleanup-block forms), `match`,
  `case`, `drop`, `break`, `continue`, `return`.
- Patterns: enum variant patterns and `_` wildcard.
- Expressions: literals (`int`, `byte`, `string`, `bool`, `null`), calls, field access, indexing syntax, `new`,
  unary/binary ops, casts (`as`), postfix try (`expr?`), and type-position intrinsic arguments (`TypeExpr` for
  intrinsics such as `sizeof`).
- Qualified names (`module.path::Name`) in types, expressions, and patterns.

Notes:

- Top-level `let` is implemented and part of signature resolution/codegen.
- `const` is still reserved/future (tokenized as a future-extension keyword, not implemented as a declaration form).
- Bitwise/shift operators are lexed/reserved and parsed in precedence scaffolding, but semantic enablement remains
  staged.

### Semantic Analysis State

`AnalysisResult` currently includes:

- `module_envs`
- `func_types`, `struct_infos`, `enum_infos`, `let_types`
- `func_envs`
- `expr_types`
- `var_ref_resolution`
- `intrinsic_targets`
- `diagnostics`

Module-level symbols include:

- `FUNC`, `STRUCT`, `ENUM`, `ENUM_VARIANT`, `TYPE_ALIAS`, `LET` (plus reserved `MODULE` kind).

Implemented semantic checks include:

- Name resolution with open-import ambiguity diagnostics.
- Signature/type resolution for top-level declarations, aliases, and top-level `let`.
- Local scope construction for non-extern functions.
- Expression/statement type checking, including control-flow return checks.
- Match exhaustiveness and overlap diagnostics.
- Flow-sensitive dropped-variable checks for `drop`.

### Backend and Code Generation State

Stage 1 backend is implemented and emits a single C99 translation unit for the whole compilation unit.

Current backend behavior includes:

- Struct/enum lowering (tagged unions for enums).
- Top-level `let` emission as static globals.
- Lowering for `if/while/for`, `match`, `case`, `with`, `drop`, and early exits.
- Runtime-assisted checked integer operations and narrowing conversions.
- ARC-aware ownership cleanup for string-containing values.
- Main-wrapper emission for entry module `main`.
- `#line` directives enabled by default (disable with `--no-line-directives`).

## Stage 1 CLI and Workflow Status

CLI entry point: `compiler/stage1_py/l0c.py` (wrapper: `./l0c`).

Commands and aliases:

- `run`
- `build`
- `gen` (`codegen`)
- `check` (`analyze`)
- `tok` (`tokens`)
- `ast`
- `sym` (`symbols`)
- `type` (`types`)

Common supported options:

- Roots and logging: `-P/--project-root`, `-S/--sys-root`, `-v/--verbose`, `-l/--log`
- Build/codegen: `-NLD/--no-line-directives`, `-c/--c-compiler`, `-C/--c-options`, `-I/--runtime-include`,
  `-L/--runtime-lib`, `-o/--output`, `--keep-c`
- Dumps: `-a/--all-modules` for `tok|ast|sym|type`, `-I/--include-eof` for `tok`

## Standard Library Status

Current std/sys modules in tree:

- `std.assert`
- `std.hash`
- `std.io`
- `std.math`
- `std.optional`
- `std.rand`
- `std.string`
- `std.system`
- `std.unit`
- `sys.rt`
- `sys.unsafe`

## Stage 2 Compiler (L0-in-L0) - Current State

Stage 2 lives in `compiler/stage2_l0` and is in early active development.

Current implemented assets:

- Core sources:
    - `src/tokens.l0`
    - `src/lexer.l0`
    - `src/main.l0`
- Utility modules:
    - `src/util/array.l0`
    - `src/util/vector.l0`
    - `src/util/linear_map.l0`
    - `src/util/text.l0`
- Test suite under `compiler/stage2_l0/tests` and test runner `run_tests.sh`.

Current focus is token model + lexer implementation + foundational utility data structures.

## Known Limitations and Constraints

These remain true in Stage 1:

1. Backend output is one C translation unit (no multi-object/header split pipeline yet).
2. Arrays/slices are not implemented; indexing syntax exists but unsupported targets are rejected.
3. No address-of (`&`) operator in language semantics.
4. No generics, traits, or macros.
5. Reserved/future keywords and operators are lexed for diagnostics and staged evolution.

## Short Roadmap

Near-term project direction, consistent with current docs/code:

1. Continue Stage 2 from lexer/util foundations toward parser + semantic passes.
2. Keep Stage 1 behavior deterministic and contract-documented while Stage 2 grows.
3. Expand language features only once semantics and diagnostics are decision-complete.
