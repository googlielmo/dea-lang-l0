# Feature Plan

## Stage 2 Expression Type Checking Milestone

- Date: 2026-03-01
- Status: Implemented (2026-03-01)
- Title: Stage 2 expression type checking milestone
- Kind: Feature
- Severity: Medium
- Stage: 2
- Subsystem: Frontend Semantics
- Modules:
    - `compiler/stage2_l0/src/analysis.l0`
    - `compiler/stage2_l0/src/type_resolve.l0`
    - `compiler/stage2_l0/src/expr_types.l0`
    - `compiler/stage2_l0/src/l0c.l0`
- Test modules:
    - `compiler/stage2_l0/tests/type_resolve_test.l0`
    - `compiler/stage2_l0/tests/expr_types_test.l0`
    - `compiler/stage2_l0/tests/l0c_test.l0`

## Summary

Implement the Stage 2 expression type checking milestone to achieve feature parity with Stage 1`s `l0_expr_types.py
` and `l0_resolve.py
`. This is the final semantic pass before backend/codegen. It includes checking expressions (literals, variables, operators, calls, constructors, casts, sizeof), basic type compatibility, widening from inferred types to annotated types, statement checking (let, return, if, while, match, drop), type reference resolution helpers, and CLI `
--type`/`--sym` output formatting.

## Goals

1. Implement type resolution helpers to resolve type references into semantic types, parity with Stage 1
   `l0_resolve.py`.
2. Implement expression and statement type checking, parity with Stage 1 `l0_expr_types.py`.
3. Support type compatibility rules, pointer tracking, and nullability checks.
4. Integrate with `AnalysisResult` to store resolved types for expressions, intrinsic targets, and variable reference
   targets.
5. Enable and implement `--type` and `--sym` formatting for the CLI to match Stage 1 output exactly.
6. Validate the type checker with Stage 2 tests and ensure Stage 2 passes existing semantic test cases.

## Non-Goals

1. Backend/codegen, IR, or C emission.
2. Stage 2 `--build`, `--run`, or `--gen` support.
3. New language features, diagnostics, or type system rules not already present in Stage 1.

## Planned Modules

### 1. `type_resolve.l0`

Implement type reference resolution and symbol resolution parity with Stage 1:

1. Find and validate type aliases, structs, enums, builtins.
2. Handle pointer types, nullable types, and function types.
3. Preserve Stage 1 behavior and code families for type resolution errors (`RES-0001`, `RES-0004`, `RES-0012`,
   `RES-0023`, `RES-0024`, `RES-0025`, `RES-0030`, `RES-0040`).

### 2. `expr_types.l0`

Implement the core `ExpressionTypeChecker` logic:

1. Walk the AST to infer and verify types for all expressions and statements.
2. Check assignment compatibility (e.g., int assignment, boolean condition checks, pointers, string compatibility).
3. Validate function calls against resolved top-level signatures.
4. Validate struct and enum constructors, indexing, and field accessors.
5. Check return types against the enclosing function signature.
6. Check variables against `locals.l0` local scopes, enforcing initialization/liveness.
7. Preserve Stage 1 behavior and diagnostic families (e.g., `TYP-0001` through `TYP-0028`, `CHK-0001` through
   `CHK-0005`, etc.).

### 3. `analysis.l0`

Update `AnalysisResult` to store typing results:

1. Map from AST node ID to resolved semantic `Type` (`expr_types`).
2. Map from `VarRef` node ID to variable resolution targets (`var_ref_resolution`: LOCAL vs MODULE).
3. Map from intrinsic node ID to target `Type` (`intrinsic_targets`).

### 4. `l0c.l0` and CLI

Update the driver and CLI integration:

1. Wire the expression type checking pass into `--check` immediately after local scope construction.
2. Implement AST formatting to support `--type` output annotations.
3. Implement symbol table formatting to support `--sym` output.
4. Ensure the output formats identically to Stage 1 to pass the end-to-end trace tests.

## Tests

Add dedicated Stage 2 tests for:

1. Type resolver behavior (`type_resolve_test.l0`).
2. Expression type checker rules (`expr_types_test.l0`).
3. Formatter output for `--type` and `--sym` (`l0c_test.l0`).

Add semantic fixtures under `compiler/stage2_l0/tests/fixtures/typing`.

## Documentation

1. Update `docs/reference/project-status.md` after implementation to mark the type checker as complete.
2. State that Stage 2 now has full frontend semantic feature parity with Stage 1.
3. State that backend/codegen is the next major phase.

## Verification

Final verification for this milestone:

```bash
./compiler/stage2_l0/run_tests.sh
./compiler/stage2_l0/run_trace_tests.sh
```

## Assumptions

1. Stage 1 remains the behavior oracle for the covered passes.
2. `--type` and `--sym` output strings from Stage 1 can be exactly matched by Stage 2 to leverage existing trace tests.
