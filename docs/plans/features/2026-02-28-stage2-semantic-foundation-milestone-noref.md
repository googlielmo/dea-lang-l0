# Feature Plan

## Stage 2 Semantic Foundation Milestone

- Date: 2026-02-28
- Status: Planned
- Title: Stage 2 semantic foundation milestone
- Kind: Feature
- Severity: Medium
- Stage: 2
- Subsystem: Frontend Semantics
- Modules:
  - `compiler/stage2_l0/src/types.l0`
  - `compiler/stage2_l0/src/symbols.l0`
  - `compiler/stage2_l0/src/analysis.l0`
  - `compiler/stage2_l0/src/name_resolver.l0`
  - `compiler/stage2_l0/src/signatures.l0`
  - `compiler/stage2_l0/src/locals.l0`
  - `compiler/stage2_l0/src/l0c.l0`
- Test modules:
  - `compiler/stage2_l0/tests/name_resolver_test.l0`
  - `compiler/stage2_l0/tests/signatures_test.l0`
  - `compiler/stage2_l0/tests/locals_test.l0`
  - `compiler/stage2_l0/tests/analysis_test.l0`
  - `compiler/stage2_l0/tests/l0c_test.l0`

## Summary

Implement the first Stage 2 semantic milestone as the semantic substrate required before expression type checking:
module-level name resolution, top-level signature resolution, local scope construction, semantic result ownership, and
`--check` integration.

Use the existing stdlib container surface for semantic tables. Create this plan document as the first commit. Update
the project status doc with durable wording that avoids fixed test counts.

## Goals

1. Implement Stage 2 module-level name resolution with Stage 1 parity for covered behavior.
2. Implement Stage 2 top-level signature resolution with Stage 1 parity for covered behavior.
3. Implement Stage 2 local scope construction over the arena-backed AST.
4. Introduce an `AnalysisResult`-style semantic aggregate for Stage 2.
5. Wire Stage 2 `--check` through semantic analysis.
6. Keep the milestone narrow so expression type checking is the next milestone, not part of this one.

## Non-Goals

1. Expression type checking or statement typing.
2. `expr_types`, `var_ref_resolution`, or `intrinsic_targets`.
3. `--sym`, `--type`, or `--ast` output formatting.
4. Backend/codegen or Stage 2 `--build`/`--run`/`--gen`.
5. New stdlib container implementations or new generic specializations unless a concrete blocker appears.

## Container Strategy

1. Reuse existing stdlib containers:
   - `std.hashmap` for `StringPtrMap` and `StringIntMap`
   - `std.hashset` for `StringSet`
   - vectors for ordered tables and id-indexed structures
2. Hide raw `void*` map access behind typed helper APIs in Stage 2 semantic modules.
3. Use canonical string keys such as `module::name` and `module::enum::variant` instead of emulating Python tuple keys.
4. Store primary semantic objects in vectors when iteration order matters, and use string maps as lookup indices.

## Planned Modules

### 1. `types.l0`

Introduce the semantic type model:

1. `TypeKind = TY_BUILTIN | TY_STRUCT | TY_ENUM | TY_POINTER | TY_NULLABLE | TY_FUNC | TY_NULL`
2. Constructors and singleton accessors for builtins and `null`
3. Structural equality helpers
4. Debug formatting helpers
5. Recursive cleanup helpers

### 2. `symbols.l0`

Introduce semantic symbols:

1. `SymbolKind = SYM_FUNC | SYM_STRUCT | SYM_ENUM | SYM_ENUM_VARIANT | SYM_TYPE_ALIAS | SYM_LET`
2. `Symbol` stores:
   - symbol name
   - symbol kind
   - defining module name
   - optional owner name for enum variants
   - declaration pointer
   - declaration span
   - resolved semantic type when available
3. Enum variant symbols must remember the parent enum name to avoid later rescanning.

### 3. `analysis.l0`

Introduce `AnalysisResult` as the Stage 2 semantic aggregate:

1. Own the `DriverState`
2. Own the combined diagnostic collector
3. Own name-resolution environments
4. Own signature tables
5. Own local-scope environments
6. Provide typed lookup helpers and cleanup

### 4. `name_resolver.l0`

Implement module-level name resolution:

1. Create envs for every loaded module first
2. Collect locals second
3. Open imports third
4. Aggregate diagnostics last
5. Preserve Stage 1 behavior and code families for:
   - `RES-0010`
   - `RES-0029`
   - `RES-0020`
   - `RES-0021`
   - `RES-0022`

### 5. `signatures.l0`

Implement top-level signature resolution:

1. Resolve types for functions, structs, enums, aliases, and top-level lets
2. Preserve Stage 1 behavior and code families for:
   - `SIG-0018`
   - `SIG-0019`
   - `SIG-0011`
   - `SIG-0010`
   - `SIG-0020`
   - `SIG-0030`
   - `SIG-0040`
3. Keep top-level `let` inference intentionally narrow:
   - infer from `int`, `byte`, `bool`, `string` literals
   - infer from constructor-style calls resolving to structs or enum variants
   - require annotations for everything else

### 6. `locals.l0`

Implement local scope construction:

1. Parameters live in the root scope
2. Top-level lets in the function body also live in the root scope
3. Nested blocks create child scopes
4. `match`, `case`, `while`, `for`, and `with` follow Stage 1 scope boundaries
5. Pattern variables live in the match-arm scope
6. Wildcard patterns introduce no locals
7. This pass remains structural only and does not introduce a new user-facing diagnostic family

## CLI Integration

1. Update Stage 2 `--check` to run semantic analysis instead of only driver analysis.
2. Return `1` on any driver or semantic error.
3. Keep `--sym` and `--type` NYI even though the underlying data now exists.

## Tests

Add dedicated Stage 2 tests for:

1. Name resolver behavior
2. Signature resolver behavior
3. Local scope behavior
4. End-to-end semantic analysis
5. `l0c --check` semantic failure paths

Add semantic fixtures under `compiler/stage2_l0/tests/fixtures/semantics`.

## Documentation

1. Update `docs/reference/project-status.md` after implementation.
2. Replace count-based status wording with durable capability descriptions.
3. State that Stage 2 includes lexer, parser, driver/CLI syntax plumbing, and semantic foundation passes.
4. State that expression type checking and backend/codegen remain pending.

## Verification

Final verification for this milestone:

```bash
./compiler/stage2_l0/run_tests.sh
./compiler/stage2_l0/run_trace_tests.sh
```

## Assumptions

1. Existing stdlib hash containers are sufficient for this milestone.
2. `DriverState` remains the compilation-closure carrier for now.
3. Stage 1 remains the behavior oracle for the covered passes.
4. Expression type checking is deferred to the next milestone.
