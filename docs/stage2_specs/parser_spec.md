# Stage 2 Parser Specification

Version: 2026-02-14

This document captures the detailed specification to implement Stage 2 parser work in `compiler/stage2_l0` as a
straightforward port of Stage 1 parser behavior.

## 1. Goals

1. Port `compiler/stage1_py/l0_parser.py` behavior into Stage 2 (`src/parser.l0`) with matching parse structure and
   diagnostic style.
2. Keep Stage 2 implementation pragmatic and simple (no premature abstractions).
3. Use an AST storage model that is safe under L0 ownership semantics and practical for later semantic/codegen passes.
4. Preserve Stage 1 grammar/constraints where already decided.

## 2. Chosen AST Storage Model: Hybrid Arena

We selected a hybrid approach.

1. Pointer-owned metadata nodes for declaration-level and shared structures.
2. Arena-backed nodes for high-volume graph data (`Expr`, `Stmt`, `Pattern`) addressed by integer IDs.
3. IDs replace pointer edges between arena nodes.

Rationale:

1. Expression/statement/pattern graphs are dense and benefit from contiguous storage and stable integer handles.
2. Declaration and type metadata are easier to construct/manipulate as direct pointer-owned structs.
3. This keeps initial implementation straightforward while reducing pointer graph complexity in hot parse paths.

## 3. String and Vector Ownership Constraints

Required constraint used in this plan:

1. Any vector element type containing `string` is stored as pointer elements (or via dedicated string vector utilities).
2. Strings in L0 are value types with compiler-inserted retain/release.
3. No raw `memcpy` ownership shortcuts for string-containing values.

Implementation consequence:

1. Prefer `VectorBase*` of pointers for complex structs that include strings.
2. Use `VectorString` (`vs_*`) for string lists (`module_path`, qualifiers, pattern vars, etc.).
3. Ensure cleanup functions release nested string/vector ownership deterministically.

## 4. Parser Porting Strategy

Porting policy:

1. Keep Stage 1 recursive-descent shape and function boundaries.
2. Preserve Stage 1 error-code behavior (`PAR-xxxx`) for equivalent paths.
3. Avoid semantic/type-check logic in parser (syntax-only responsibility).

Core parser structure planned and implemented:

1. Token utilities: `peek/last/advance/check/match/expect` with identifier and literal helpers.
2. Module parser: `module`, dotted imports, top-level declaration loop.
3. Top-level declaration parsers:
    1. `extern func`
    2. `func`
    3. `struct`
    4. `enum`
    5. `type`
    6. top-level `let`
4. Statement parsers:
    1. block
    2. let
    3. assign/expr stmt split
    4. if/while/for
    5. match/case
    6. with
    7. return/drop/break/continue
5. Pattern parsers:
    1. wildcard `_`
    2. variant patterns with optional payload vars
6. Expression parsers:
    1. precedence chain (`or -> and -> equality -> rel -> add -> mul -> unary -> cast -> postfix -> primary`)
    2. postfix chain (call/index/field/try)
    3. `new` constructor parsing
    4. type-expression call arguments in unambiguous contexts
    5. reserved operator diagnostics for staged ops (`~`, `&`, `|`, `^`, `<<`, `>>`)
7. Type parser:
    1. qualified names
    2. pointer depth and nullable suffix
    3. staged array-type diagnostic

## 5. Direct Predicate vs Tag-Based Matching

Decision used:

1. Prefer direct `match` on enum variants when payload extraction is needed.
2. Use ordinal tag checks (`ord(...)`) for hot token-kind predicate helpers and compact utility checks.
3. Do not add an extra `TokenKindTag` enum layer or similar, unless profiling proves a need.

Rationale:

1. Direct variant matching is clearer and safer for payload-bearing tokens.
2. `ord(Variant)` provides efficient tag comparison without additional type duplication.
3. Keeps code size and maintenance burden low.

## 6. Memory Lifecycle Plan

`ParseResult` ownership contract:

1. `parse_module_source` / `parse_module_tokens` return parser-owned module + arenas.
2. Caller releases with `parse_result_free`.

Cleanup requirements:

1. Free module declarations and nested metadata pointers.
2. Free expression/statement/pattern arenas and nested vectors/pointers.
3. Release lexer/token temporary ownership in source-entry parse path after conversion to parser-owned AST.

## 7. Incremental Milestones Used

1. Establish AST scaffolding and arenas (`ast.l0`).
2. Port parser skeleton and top-level declaration parsing (`parser.l0`).
3. Port statements/patterns.
4. Port full precedence and postfix expression logic.
5. Re-enable full cleanup path after Stage 1 ARC fix.
6. Expand parser tests to cover newly enabled paths and diagnostics.

## 8. Test Strategy

Baseline rule:

1. Keep `compiler/stage2_l0/run_tests.sh` green at each milestone.

Parser-specific coverage targets used:

1. Valid module/declaration parse.
2. Module header failures.
3. Reserved identifier/future-extension variable-name diagnostics.
4. Reserved operator diagnostics.
5. `with` form constraints.
6. `case` structure constraints.
7. Precedence correctness path.
8. Postfix chain path.
9. Type-expression call-argument path.
10. Qualified name/type path.
11. `parse_result_free` exercised in both success and error paths.

## 9. Non-Goals for this specification

1. Stage 2 semantic passes.
2. Stage 2 backend/codegen.
3. New language features beyond Stage 1 parser behavior.

## 10. Current Status

Completed:

1. `compiler/stage2_l0/src/ast.l0` implemented with hybrid storage model.
2. `compiler/stage2_l0/src/parser.l0` implemented with Stage 1 style parsing behavior and diagnostics for covered paths.
3. `compiler/stage2_l0/tests/parser_test.l0` added and expanded.
4. Stage 2 test runner currently passing (`8/8`).
