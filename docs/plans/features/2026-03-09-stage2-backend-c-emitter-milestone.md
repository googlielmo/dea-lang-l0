# Feature Plan

## Stage 2 Backend and C Emitter Milestone

- Date: 2026-03-09
- Status: Draft
- Title: Stage 2 backend and C emitter milestone
- Kind: Feature
- Severity: High
- Stage: 2
- Subsystem: Backend / C code generation / CLI `--gen`
- Modules:
    - `compiler/stage2_l0/src/codegen_options.l0`
    - `compiler/stage2_l0/src/scope_context.l0`
    - `compiler/stage2_l0/src/string_escape.l0`
    - `compiler/stage2_l0/src/c_emitter.l0`
    - `compiler/stage2_l0/src/backend.l0`
    - `compiler/stage2_l0/src/sem_context.l0`
    - `compiler/stage2_l0/src/analysis.l0`
    - `compiler/stage2_l0/src/l0c.l0`
    - `scripts/refresh_stage2_backend_goldens.py`
- Test modules:
    - `compiler/stage2_l0/tests/backend_test.l0`
    - `compiler/stage2_l0/tests/c_emitter_test.l0`
    - `compiler/stage2_l0/tests/l0c_test.l0`
    - `compiler/stage2_l0/tests/l0c_codegen_test.sh`

## Summary

Implement the Stage 2 backend and C emitter with Stage 1 feature parity for emitted C, and make exact Stage 1 C output
plus exact Stage 1 diagnostic and ICE code reuse for equivalent failures the oracle for Stage 2 through committed
golden fixtures and parity tests.

This milestone is intentionally centered on `AnalysisResult -> C99 translation unit` and Stage 2 `--gen`. Exact-text
parity is measured with deterministic Stage 1 output generated via `./l0c --gen --no-line-directives`. Stage 2
`--build` and `--run` are explicitly deferred until `--gen` parity is stable.

All new L0 code in this milestone uses Doxygen Javadoc-style comments with autobrief, matching current Stage 2
conventions. Small helper modules and utility functions are allowed when they reduce backend duplication or encode
stable Stage 1 rules without changing emitted text.

## Goals

1. Port Stage 1 backend responsibilities into Stage 2 with the same output structure, naming, lowering rules, and
   cleanup semantics.
2. Port Stage 1 C emitter responsibilities into Stage 2 with the same textual layout for deterministic
   `--gen --no-line-directives` output.
3. Implement Stage 2 CLI `--gen` with Stage 1-aligned behavior for stdout/file output and codegen-affecting flags.
4. Add a curated, committed golden-C corpus generated from Stage 1 and diff Stage 2 output against it exactly.
5. Preserve Stage 1 diagnostic and `ICE-xxxx` code numbers for equivalent backend, emitter, and `--gen` failure paths.
6. Keep the work chunked so each chunk has a narrow parity target and a clear acceptance gate.

## Non-Goals

1. Stage 2 `--build` and `--run`.
2. Stage 2 self-hosted test execution or replacement of the current Stage 1-driven test runner.
3. New language features, backend optimizations, or IR layers not already present in Stage 1.
4. Full-file golden comparison with line directives enabled.
5. Shared runtime/process helper additions for host compiler execution.

## Public Interfaces and Type Changes

1. Add `CodegenOptions` as a Stage 2 codegen-only configuration type with `emit_line_directives`, `trace_arc`, and
   `trace_memory`.
2. Add `backend_generate(result: AnalysisResult*, opts: CodegenOptions*, cfg: LogConfig*) -> string` as the public
   Stage 2 backend entry point.
3. Add Stage 2 semantic helpers in `sem_context.l0` for backend use: `analysis_expr_key`, `analysis_get_expr_type`,
   `analysis_get_intrinsic_target`, `analysis_get_var_ref_resolution`, `analysis_is_arc_type`, and
   `analysis_has_arc_data`.
4. Add Stage 2 backend scope-tracking types in `scope_context.l0`, mirroring Stage 1 cleanup responsibilities for
   owned locals, declared locals, and `with` cleanup state.
5. Implement Stage 2 CLI `CM_GEN` in `l0c.l0`; keep `CM_BUILD` and `CM_RUN` on `L0C-9510` in this milestone.

## Implementation Chunks

### 1. Codegen substrate

Add `CodegenOptions`, extract shared semantic lookup helpers from `expr_types.l0` into `sem_context.l0`, add
`analysis_has_arc_data` and related queries, and add `scope_context.l0` plus a minimal backend ICE helper. Before
adding new backend/emitter ICEs, audit existing Stage 2 `ICE-*` usage and renumber any collisions so Stage 1 numbers
are reused only for equivalent invariants.

Acceptance for this chunk:

1. `expr_types` still passes unchanged.
2. Backend code can query typed analysis without duplicating `expr_types` internals.
3. Pure helper tests compile and pass.
4. No Stage 2 `ICE-*` code already used by Stage 1 is repurposed with a different meaning.

### 2. C emitter skeleton and exact-text rules

Implement `c_emitter.l0` with a builder, Stage 1 section comments, includes, trace defines, header layout, name
mangling, C keyword hygiene, type lowering, optional-wrapper naming, forward declarations, struct/enum emission,
top-level `let` declarations, function declarations, function-definition headers/footers, and main-wrapper emission.

Preserve Stage 1 ordering rules exactly: compilation-unit module order, source declaration order, dependency-ordered
value-type emission, and early/late optional-wrapper phases.

Acceptance for this chunk:

1. Focused emitter tests cover headers, typedef guards, mangled names, string escaping, and type-ordering snippets.
2. Stage 2 text for the covered sections matches Stage 1 exactly.
3. Emitter helper ICEs either reuse the Stage 1 number for the equivalent invariant or use a new Stage 2-only number.

### 3. Backend lowering phase 1

Implement `backend.l0` orchestration for type dependency analysis, top-level `let` constant initializers, pure
expression lowering, and basic statement lowering: literals, var refs, unary/binary ops, calls, field/index access,
casts, constructors, `sizeof`, `ord`, blocks, `let`, assignment, expression statements, `if`, `while`, `for`, and
`return`.

Acceptance for this chunk:

1. Stage 2 can generate deterministic C for non-ownership fixtures.
2. The first curated fixtures match committed Stage 1 goldens exactly.

### 4. Backend lowering phase 2

Port ownership-sensitive and control-flow-sensitive lowering exactly: ARC temp materialization, retain-on-copy,
direct-return move optimization, `new`, `drop`, `try`, `with`, struct/enum recursive cleanup, nullable cleanup rules,
`match`, `case`, pattern bindings, `break`, `continue`, and path-sensitive loop-exit cleanup.

Acceptance for this chunk:

1. Ownership/control-flow fixtures match Stage 1 goldens exactly.
2. Cleanup order, label naming, and runtime helper calls remain identical to Stage 1.

### 5. CLI `--gen` integration

Replace `CM_GEN` NYI in `l0c.l0` with analysis plus `backend_generate`, support stdout default and `--output`, and
thread `--no-line-directives`, `--trace-arc`, and `--trace-memory` into `CodegenOptions`.

Exit codes remain Stage 2 standard: `2` for CLI parse/validation failure, `1` for analysis/codegen failure, and `0`
for success.

Acceptance for this chunk:

1. Stage 2 `l0c` can be invoked externally through `./l0c -P compiler/stage2_l0/src --run l0c -- --gen ...`.
2. Output and failure behavior match Stage 1 for the implemented mode.
3. Equivalent codegen/CLI failure paths reuse the same Stage 1 diagnostic codes; Stage 2-only NYI paths remain on
   `L0C-9510`.

### 6. Golden C fixture system

Create `compiler/stage2_l0/tests/fixtures/backend_golden/` as the curated corpus. Each case stores source modules,
`<case>.golden.c`, and optional `<case>.expected.out`.

Initial cases are:

1. `basic_main`
2. `types_and_toplet`
3. `control_flow`
4. `constructors_and_intrinsics`
5. `ownership_and_with`
6. `match_case`
7. `cross_module_main`

All full-file goldens are generated with `--gen --no-line-directives`; trace-define deltas and line-directive behavior
are covered by focused unit tests instead of committed full-file goldens.

### 7. Golden refresh tooling

Add `scripts/refresh_stage2_backend_goldens.py` that discovers the curated corpus, invokes Stage 1 as oracle with
`./l0c --gen --no-line-directives -P <fixture_root> <module>`, normalizes line endings to LF, enforces one trailing
newline, supports case filters, and provides `--check` to fail on stale committed goldens.

Acceptance for this chunk:

1. Goldens are reproducible from current Stage 1 output.
2. Stage 2 tests depend only on committed fixtures.

### 8. End-to-end parity tests

Add `l0c_codegen_test.sh` that runs Stage 2 `l0c` as a program through Stage 1, diffs emitted C against
`<case>.golden.c`, and for any case with `<case>.expected.out` compiles the emitted C with the detected host compiler
and compares runtime output.

Extend `l0c_test.l0` to assert `--gen` success on a simple fixture while confirming `--build` and `--run` remain NYI
for now.

Acceptance for this chunk:

1. Exact-text parity is enforced end to end.
2. CLI coverage includes both stdout and `--output` file paths.

## Test Plan

1. `backend_test.l0` covers type dependency ordering, scope tracking, analysis ARC helpers, and backend-side lookup
   helpers.
2. `c_emitter_test.l0` covers type-to-C lowering, optional-wrapper naming, string-to-C escaping, null lowering, header
   layout, and trace-define emission.
3. `l0c_codegen_test.sh` diffs Stage 2 `--gen` output against committed Stage 1 goldens for the curated corpus.
4. `l0c_codegen_test.sh` compiles and runs any fixture that carries an `.expected.out` oracle.
5. `l0c_test.l0` verifies `--gen` success and preserves existing CLI parse/NYI behavior for `--build` and `--run`.
6. Focused unit tests, not full-file goldens, verify `#line` emission and trace-flag variants.
7. Focused unit tests and parity fixtures verify exact Stage 1 code reuse for equivalent emitter/backend/CLI failures.
8. Final verification commands for the milestone are:

```bash
python3 scripts/refresh_stage2_backend_goldens.py --check
./compiler/stage2_l0/run_tests.sh
./compiler/stage2_l0/run_trace_tests.sh
```

## Documentation Changes

1. Update `docs/reference/project-status.md` to mark Stage 2 backend/C emission plus `--gen` as implemented, and keep
   `--build`/`--run` listed as the immediate next step.
2. Update `docs/reference/architecture.md` so the Stage 2 pipeline includes backend generation for `--gen`.
3. Update `docs/reference/c-backend-design.md` so it becomes the shared canonical C-backend behavior document for both
   stages, while still naming Stage 1 as the reference implementation source.
4. Update `docs/specs/compiler/diagnostic-code-policy.md` and `CLAUDE.md` so exact Stage 1 code reuse, including
   `ICE-xxxx`, is a shared project rule.
5. Update `docs/reference/ownership.md` only if the Stage 2 backend port reveals wording that currently mentions
   Stage 1-only behavior where the rule is now shared.

## Assumptions and Defaults

1. Stage 1 is the sole oracle for backend behavior and exact text in this milestone.
2. Exact parity means full-file text equality for `--gen --no-line-directives` output after LF normalization in the
   refresh script; no additional normalization is allowed in tests.
3. The curated parity corpus is intentionally small and import-light so committed `.golden.c` files stay reviewable.
4. `--build` and `--run` stay out of scope until exact `--gen` parity is green across the curated corpus.
5. New helper modules are acceptable when they reduce duplication or encode stable Stage 1 output rules, but
   “equivalent” alternative formatting or lowering is not acceptable in this milestone.
6. Equivalent diagnostic parity means exact `XXX-NNNN` reuse, including `ICE-xxxx`; new codes are allowed only for
   genuinely Stage 2-only conditions with no Stage 1 counterpart.
