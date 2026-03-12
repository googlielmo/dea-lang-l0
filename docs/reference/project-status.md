# L0 Project Status

Version: 2026-03-12

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

CLI entry point: `compiler/stage1_py/l0c.py` (source-tree wrapper: `./scripts/l0c`).
Recommended developer-facing `l0c`: the repo-local alias under `dist/bin`, selected with `make use-dev-stage1` or
`make use-dev-stage2` and activated with `source dist/bin/l0-env.sh`.

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

- Roots and logging: `-P/--project-root`, `-S/--sys-root`, `--version`, `-v/--verbose`, `-l/--log`
- Build/codegen: `-NLD/--no-line-directives`, `--trace-arc`, `--trace-memory`, `-c/--c-compiler`, `-C/--c-options`,
  `-I/--runtime-include`,
  `-L/--runtime-lib`, `-o/--output`, `--keep-c`
  - C compiler flags can also be provided via `$L0_CFLAGS`; effective order is `$L0_CFLAGS` first, then `--c-options`.
- Dumps: `-a/--all-modules` for `tok|ast|sym|type`, `-I/--include-eof` for `tok`

CLI identity/help behavior:

- `--version` prints one stage-specific line and exits (`Dea language / L0 compiler (Stage 1)` or
  `Dea language / L0 compiler (Stage 2)`).
- `--help` uses the same stage-specific identity text as the help description heading.
- `-v` also emits the same identity text on stderr through the normal info-level logging path, including CLI usage
  failures such as invoking `l0c -v` without a target.

## Standard Library Status

Current std/sys modules in tree:

- `std.assert`
- `std.io`
- `std.math`
- `std.optional`
- `std.rand`
- `std.string`
- `std.system`
- `std.time`
- `std.unit`
- `sys.hash`
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
    - `src/types.l0`
    - `src/symbols.l0`
    - `src/analysis.l0`
    - `src/sem_context.l0`
    - `src/name_resolver.l0`
    - `src/signatures.l0`
    - `src/type_resolve.l0`
    - `src/locals.l0`
    - `src/expr_types.l0`
    - `src/codegen_options.l0`
    - `src/scope_context.l0`
    - `src/string_escape.l0`
    - `src/c_emitter.l0`
    - `src/backend.l0`
    - `src/build_driver.l0`
    - `src/l0c_lib.l0`
    - `src/l0c.l0`
- Utility modules:
    - `src/util/array.l0`
    - `src/util/vector.l0` (includes `vi_sort` for int vectors and `vs_sort` for string vectors)
    - `src/util/linear_map.l0`
    - `src/util/text.l0`
- Test suite under `compiler/stage2_l0/tests` plus `run_tests.py` and `run_trace_tests.py`.

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

Stage 2 diagnostics status:

- Parser/lexer diagnostics preserve `PAR-*`/`LEX-*` code families.
- Driver diagnostics reuse Stage 1 `DRV-*` codes for equivalent conditions (`DRV-0010`, `DRV-0020`, `DRV-0030`) and
  add `DRV-0011` for resolved-path read failures.
- CLI diagnostics reuse Stage 1 `L0C-*` codes where equivalent (`L0C-0011`, `L0C-0040`, `L0C-0070`), keep `L0C-2xxx`
  for Stage 2 parser/validation errors without Stage 1 code counterparts, and use `L0C-9510` for Stage 2 NYI mode
  diagnostics.

Stage 2 AST storage status:

- Hybrid representation is implemented:
  pointer-owned metadata nodes plus arena-backed expression/statement/pattern nodes.
- Arena IDs (`ExprId`, `StmtId`, `PatternId`) are used for graph edges in parsed trees.
- Parser API returns `ParseResult` with arenas and module root.
- `parse_result_free` deep cleanup is implemented for parser-owned allocations.

Stage 2 semantic status:

- `AnalysisResult` owns `DriverState`, combined diagnostics, name-resolution environments,
  signature tables, local-scope environments, and expression typing results.
- Module-level name resolution is implemented with Stage 1-aligned `RES-*` behavior.
- Top-level signature resolution is implemented for functions, structs, enums, aliases, and
  top-level lets.
- Local scope construction is implemented for non-extern functions over the arena-backed AST.
- Expression and statement type checking is implemented with feature parity with Stage 1,
  including control-flow checks, assignment compatibility, and pattern variable typing.
- Stage 2 `l0c --check`, `--type`, and `--sym` are implemented with Stage 1-aligned output.

Stage 2 backend/codegen status:

- Stage 2 `backend_generate()` is implemented and emits a single C99 translation unit from typed `AnalysisResult`.
- Stage 2 `l0c --gen` is implemented, including `--output`, `--no-line-directives`, `--trace-arc`, and
  `--trace-memory`.
- Stage 2 `l0c --build` and `--run` are implemented on top of the same analysis plus backend path, using
  `std.system.system()` for host compiler and program execution.
- Stage 2 `l0c --help` and `--version` are implemented with Stage 2-specific identity text, and `-v` preserves that
  identity output even on CLI usage failures.
- Stage 2 can now be bootstrapped into a repo-local artifact via `./scripts/build-stage2-l0c.sh`, producing
  `build/stage2/bin/l0c-stage2` and `l0c-stage2.native` by default.
- Phase 2 now adds a repo-local `dist/bin` workflow via `make install-dev-stages`, explicit `make use-dev-stage1` /
  `make use-dev-stage2` alias switching, and `source dist/bin/l0-env.sh`.
- The strict stage2/stage3 fixed-point bootstrap regression is available directly via `make triple-test`.
- Stage 2 backend lowering now covers the Stage 1 language surface, including ownership-sensitive lowering for
  `new`, `drop`, `try`, `with`, `match`, `case`, `break`, `continue`, and ARC cleanup.
- Exact-text parity for `--gen --no-line-directives` is enforced against a committed curated Stage 1 golden corpus via
  `compiler/stage2_l0/tests/l0c_codegen_test.sh`.
- Stage 2 trace validation is green for the current test suite via `compiler/stage2_l0/run_trace_tests.py`.

## Known Limitations and Constraints

These remain true in Stage 1:

1. Backend output is one C translation unit (no multi-object/header split pipeline yet).
2. Arrays/slices are not implemented; indexing syntax exists but unsupported targets are rejected.
3. No address-of (`&`) operator in language semantics.
4. No generics, traits, or macros.
5. Reserved/future keywords and operators are lexed for diagnostics and staged evolution.

Current Stage 2 limitations:

1. Some language constraints intentionally remain staged in parser diagnostics (for example, array types and
   bitwise/shift operators).

## Short Roadmap

Near-term project direction, consistent with current docs/code:

1. Keep Stage 1/Stage 2 backend and driver behavior deterministic and parity-tested as Stage 2 takes on more direct use.
2. Extend parity coverage beyond the current curated golden corpus as new backend-sensitive cases are added.
3. Continue the shared-runtime bootstrap plan, including the later general subprocess API deferred in
   `docs/plans/features/2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md`.
