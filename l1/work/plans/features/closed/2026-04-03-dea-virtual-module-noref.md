# Feature Plan

## Introduce the `dea` virtual prelude module

- Date: 2026-04-03
- Status: Implemented
- Title: Introduce the `dea` virtual prelude module for Stage 1 intrinsic resolution
- Kind: Feature
- Severity: High
- Stage: L1
- Subsystem: Name resolution / type checking / backend / CLI symbols
- Modules:
  - `l1/compiler/stage1_l0/src/dea_prelude.l0`
  - `l1/compiler/stage1_l0/src/name_resolver.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/driver.l0`
  - `l1/compiler/stage1_l0/src/symbols.l0`
  - `l1/compiler/stage1_l0/src/l1c_lib.l0`
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/reference/grammar.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/name_resolver_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/type_resolve_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`

## Summary

Stage 1 originally recognized intrinsics by bare callee name in the type checker and backend. That made `sizeof(...)`
and `ord(...)` non-symbolic compiler magic and allowed user-defined functions with those names to be hijacked.

This work introduced a compiler-synthesized `dea` module that is implicitly available in every compilation unit with the
lowest precedence. `sizeof` and `ord` now resolve through the normal module system, bare calls can still work through
the implicit prelude import, and `dea::sizeof(...)` / `dea::ord(...)` are always available as the explicit qualified
escape hatch.

## Implemented Design

### 1. Virtual module synthesis

A new `dea_prelude` module synthesizes the virtual `dea` module and its exports in-memory.

- `dea` is not backed by an on-disk `.l0` source file.
- the synthesized module currently exports `dea::sizeof` and `dea::ord`
- the helper layer is structured so future compiler-owned type aliases can be added without introducing a parsed source
  file

### 2. Name-resolution integration

`dea` is injected directly into name resolution rather than being represented as a parsed `DriverUnit`.

- `nr_resolve` creates the `dea` environment before import opening
- every non-`dea` module implicitly opens `dea` first
- explicit imports and locals shadow prelude-provided names normally
- `dea` is tracked in `imported_modules` so qualified `dea::...` lookup always works

### 3. Prelude-shadow behavior

The import-opening logic was extended so explicit imports replace prelude-provided bindings instead of becoming
ambiguous.

- local shadowing still reports `RES-0021`
- explicit imported `sizeof` / `ord` also shadow the prelude with `RES-0021`
- explicit-vs-explicit clashes still use the normal ambiguity path
- explicit `import dea;` is treated as redundant and does not double-open the module

### 4. Intrinsic dispatch by resolved symbol origin

Type checking and backend lowering now dispatch intrinsics by resolved symbol identity rather than string-matching the
source text.

- only symbols originating from module `dea` trigger intrinsic handling
- user-defined `sizeof` / `ord` are treated as normal functions
- qualified `dea::sizeof(...)` and `dea::ord(...)` work through the same resolved-symbol path
- bare non-call references to `dea` intrinsics are rejected during type checking

### 5. Virtual-symbol representation

Synthesized module-level symbols now use nullable declaration pointers.

- `Symbol.decl_ptr` was changed from `void*` to `void*?`
- synthesized `dea` symbols store `null`
- no fake AST declaration nodes are created just to satisfy the symbol shape
- code paths that may observe synthesized symbols now guard `decl_ptr` before dereferencing

This was an explicit architectural choice: virtual symbols are modeled as declaration-less compiler-owned symbols rather
than pretending to be parsed declarations.

## Key Decisions

1. Inject `dea` in name resolution, not as a filesystem-loaded module. This keeps the feature aligned with semantic
   analysis rather than driver-unit bookkeeping.
2. Open `dea` before explicit imports but track prelude-provided names separately so later explicit imports can shadow
   them cleanly.
3. Dispatch intrinsics from resolved symbols in both the checker and backend. Fixing only the checker would still allow
   backend-time hijacking of user functions named `sizeof` or `ord`.
4. Use nullable `decl_ptr` for synthesized symbols. A fake declaration pointer would have introduced unnecessary fake
   AST ownership and hidden the fact that these symbols are compiler-synthesized.

## Verification

The feature was validated with new resolution, typing, backend, and CLI symbol-dump coverage, including:

- bare intrinsic resolution
- qualified `dea::sizeof(...)`
- local and imported shadowing over the prelude
- backend lowering only for resolved `dea` intrinsics
- `--sym --all-modules` showing the synthesized `dea` module

Verification commands:

```bash
make -C l1 test-stage1
```

Result:

- Passed: 30
- Failed: 0
