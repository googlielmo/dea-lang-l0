# L0 Project Status

Version: 2026-02-14

This document summarizes what is implemented in this repository today and what remains open.

## Scope and Canonical References

Use this file as a status snapshot. For implementation details, use:

- [reference/architecture.md](architecture.md) for pass structure and data flow.
- [specs/compiler/stage1-contract.md](../specs/compiler/stage1-contract.md) for external interfaces and guarantees.
- [reference/c-backend-design.md](c-backend-design.md) for backend lowering and generated C behavior.
- [specs/runtime/trace.md](../specs/runtime/trace.md) for tracing flags and runtime trace semantics.
- [reference/grammar/l0.md](grammar/l0.md) for accepted concrete syntax.
- [reference/standard-library.md](standard-library.md) for current std/sys module APIs.

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
- Optional runtime tracing toggles emitted during codegen (`--trace-arc`, `--trace-memory`).

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
- Build/codegen: `-NLD/--no-line-directives`, `--trace-arc`, `--trace-memory`, `-c/--c-compiler`, `-C/--c-options`,
  `-I/--runtime-include`,
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

Stage 2 lives in `compiler/stage2_l0` and is in active development.

Current implemented assets:

- Core sources:
    - `src/tokens.l0`
    - `src/lexer.l0`
    - `src/ast.l0`
    - `src/parser.l0`
    - `src/main.l0`
- Utility modules:
    - `src/util/array.l0`
    - `src/util/vector.l0`
    - `src/util/linear_map.l0`
    - `src/util/text.l0`
- Test suite under `compiler/stage2_l0/tests` and test runner `run_tests.sh`.
- Current Stage 2 test runner status: `8/8` tests passing.

Stage 2 parser status:

- Module/import parsing is implemented (`module`, dotted `import` names).
- Top-level declarations are implemented: `extern func`, `func`, `struct`, `enum`, `type`, top-level `let`.
- Statement parsing is implemented: block, `let`, assignment, expression statements, `if/else`, `while`, `for`,
  `match`, `case`, `with`, `drop`, `break`, `continue`, `return`.
- Pattern parsing is implemented: `_` wildcard and variant patterns (including qualified names).
- Expression parsing is implemented with precedence and postfix forms:
  literals, `new`, calls, indexing, field access, cast (`as`), postfix try (`expr?`), unary ops, binary ops.
- Type-expression call arguments are implemented for unambiguous intrinsic-style contexts (e.g. `sizeof(int*)`).
- Qualified names are implemented in types, expressions, and patterns.
- Parser diagnostics mirror Stage 1 error-code style (`PAR-xxxx`) for covered paths.

Stage 2 AST storage status:

- Hybrid representation is implemented:
  pointer-owned metadata nodes plus arena-backed expression/statement/pattern nodes.
- Arena IDs (`ExprId`, `StmtId`, `PatternId`) are used for graph edges in parsed trees.
- Parser API returns `ParseResult` with arenas and module root.
- `parse_result_free` deep cleanup is implemented for parser-owned allocations.

## Known Limitations and Constraints

These remain true in Stage 1:

1. Backend output is one C translation unit (no multi-object/header split pipeline yet).
2. Arrays/slices are not implemented; indexing syntax exists but unsupported targets are rejected.
3. No address-of (`&`) operator in language semantics.
4. No generics, traits, or macros.
5. Reserved/future keywords and operators are lexed for diagnostics and staged evolution.

Current Stage 2 limitations:

1. Semantic passes are not implemented yet (name resolution, signature resolution, local scopes, expression type
   checking).
2. Stage 2 backend/codegen pipeline is not implemented yet.
3. Some language constraints intentionally remain staged in parser diagnostics (for example, array types and
   bitwise/shift operators).

## Short Roadmap

Near-term project direction, consistent with current docs/code:

1. Continue Stage 2 from parser baseline into semantic passes (name/signature/local-scope/type checking).
2. Connect Stage 2 semantic outputs to backend/codegen milestones.
3. Keep Stage 1 behavior deterministic and contract-documented while Stage 2 grows.
4. Expand language features only once semantics and diagnostics are decision-complete.
