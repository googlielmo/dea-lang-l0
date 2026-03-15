# Feature Plan

## Final Stage 2 public CLI parity and milestone closeout

- Date: 2026-03-14
- Status: Implemented
- Title: Implement the remaining Stage 2 public CLI parity gap (`--ast`) and close the Stage 2 parity milestone
- Kind: Feature
- Severity: Medium
- Stage: 2
- Subsystem: CLI / AST inspection / milestone closeout
- Modules:
  - `compiler/stage2_l0/src/l0c_lib.l0`
  - `compiler/stage2_l0/src/ast.l0`
  - `compiler/stage2_l0/src/driver.l0`
  - `docs/reference/project-status.md`
  - `docs/reference/architecture.md`
  - `README.md`
- Test modules:
  - `compiler/stage2_l0/tests/cli_args_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh`
  - `compiler/stage2_l0/tests/l0c_ast_test.sh`
- Repro: `./build/dea/bin/l0c-stage2 --ast -P examples hello`

## Summary

Stage 2 is already self-hosted, installable, and validated by the strict triple-bootstrap regression. The remaining
public CLI parity gap with Stage 1 is `l0c --ast`: the flag is parsed and documented in Stage 2, but the command still
dispatches to the generic NYI path (`L0C-9510`) instead of producing Stage 1-style AST output.

This plan closes that final public CLI gap. The implementation adds a Stage 2 AST pretty-printer, wires `CM_AST` to a
real command handler, adds end-to-end parity tests for single-module and `--all-modules` behavior, and updates the
current-state docs so the project can explicitly describe Stage 2 public CLI parity as complete.

This plan is intentionally narrow. It does not replace the separate shared CLI contract work in
`docs/plans/features/2026-03-12-shared-cli-contract-spec.md`; it only removes the last user-visible Stage 2 CLI mode
mismatch so that plan can proceed from a parity-complete implementation baseline.

## Public behavior and parity target

1. Stage 2 `l0c --ast <target>` must succeed and print a human-readable AST for the entry module instead of emitting
   `L0C-9510`.
2. Stage 2 `l0c --ast --all-modules <target>` must print every module in the compilation unit in a stable, sorted order,
   matching Stage 1’s module traversal contract.
3. Stage 2 help/usage text keeps advertising `--ast`, but after this change the flag must be truthful: it is no longer
   NYI.
4. Stage 2 must stop using `L0C-9510` for `CM_AST`. Keep `L0C-9510` reserved for any genuinely unimplemented future
   mode, but after this feature there should be no reachable public CLI mode that still uses it.

## Implementation

### 1. Add a Stage 2 AST formatting layer

Implement a dedicated AST pretty-printer in Stage 2 instead of trying to reuse backend or semantic debug output.

Required shape:

1. Add a formatter module under `compiler/stage2_l0/src/` dedicated to AST rendering, or place the logic in `ast.l0`
   only if that keeps ownership and dependencies simple.
2. The formatter must render the parsed Stage 2 AST, not typed semantic tables.
3. The output contract should match Stage 1 at the behavior level:
   - node kind on the header line,
   - simple scalar fields inline,
   - child nodes nested under labeled sections,
   - source-span annotations preserved where Stage 2 AST stores them,
   - deterministic field and child ordering.
4. Prefer Stage 1’s `l0_ast_printer.py` structure as the oracle for layout and traversal, but translate it into normal
   Stage 2 L0 code using explicit per-node formatting instead of Python reflection.
5. Keep the initial formatter scope limited to node kinds that can appear in the current Stage 2 parser surface; no
   speculative support is needed for future syntax.

### 2. Wire `CM_AST` to a real command path

1. Add `l0c_cmd_ast(opts: CliOptions*, cfg: LogConfig*) -> int` in `l0c_lib.l0`.
2. Follow Stage 1 command structure:
   - build search paths from CLI input,
   - build the compilation unit through the existing driver path,
   - print diagnostics and return `1` on build/parse/load failure,
   - print AST text and return `0` on success.
3. Use the same entry-module and `--all-modules` semantics as Stage 1:
   - without `--all-modules`, print only the entry module,
   - with `--all-modules`, sort module names and print all modules.
4. For `--all-modules`, preserve Stage 1-style per-module headers:
   - `=== Module <name> ===`
   - formatted AST
   - one trailing blank line between modules
5. Replace the `CM_AST -> l0c_cmd_nyi(...)` dispatch in `run_with_argv()` with the new handler.

### 3. Match Stage 1 failure behavior closely

1. Reuse the existing Stage 2 driver/build-compilation path rather than inventing a new parser-only loading path.
2. Preserve current Stage 2 diagnostic printing style for parser/driver failures by using the same collector/source
   printing helpers already used in `--check`, `--sym`, and `--type`.
3. Add explicit handling for “entry module not present in built compilation unit” and assign the Stage 1-equivalent
   diagnostic code if one already exists in the current Stage 2 families; do not introduce a new code if the Stage 1
   condition already has one.
4. Remove `CM_AST` from the practical NYI surface, but do not delete the generic NYI helper unless no other internal
   caller remains.

### 4. Tighten tests around the parity claim

1. Extend `compiler/stage2_l0/tests/cli_args_test.l0` with a positive parse/dispatch-shape test for `--ast` and
   `--all-modules` acceptance.
2. Add a new end-to-end regression, `compiler/stage2_l0/tests/l0c_ast_test.sh`, covering:
   - `--ast` success for a single-module fixture,
   - `--ast --all-modules` success for a multi-module fixture,
   - stable module header ordering for `--all-modules`,
   - absence of `L0C-9510` in successful `--ast` output,
   - at least one failure-path diagnostic for a bad target or missing module.
3. Update any existing Stage 2 help/verbose shell tests if they currently assume `--ast` is not implemented or if their
   expected help wording needs to change.
4. If the Stage 2 AST output can be made text-identical to Stage 1 for representative fixtures at reasonable cost,
   compare directly against Stage 1 output in the new shell regression. If exact text parity is not practical because of
   structural AST representation differences, lock the Stage 2 format explicitly in the test and document that the
   parity target is behavior and coverage, not byte-for-byte text identity.

### 5. Conclude the milestone in docs after the implementation lands

After code and tests are green, update current-state docs in the same change:

1. `README.md`
   - remove the “remaining public CLI gap is `--ast`” wording,
   - state that Stage 2 implements the full current public CLI surface.
2. `docs/reference/project-status.md`
   - remove `--ast` from the Stage 2 limitations list,
   - describe Stage 2 CLI parity with Stage 1 as complete for the current public modes.
3. `docs/reference/architecture.md`
   - remove the “`--ast` is still NYI” note and list `--ast` among the implemented Stage 2 CLI modes.
4. `compiler/stage2_l0/README.md`
   - remove the intro caveat that `--ast` is still missing.
5. `docs/plans/features/2026-03-12-shared-cli-contract-spec.md`
   - keep it open unless the shared spec also ships in the same work,
   - but remove or update any wording that still treats `--ast` as a remaining implementation mismatch.

## Verification

Execute:

```bash
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/cli_args_test.l0
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="cli_args_test l0c_ast_test"
make DEA_BUILD_DIR=build/dev-dea test-stage2
make DEA_BUILD_DIR=build/dev-dea test-stage2-trace
make DEA_BUILD_DIR=build/dev-dea triple-test
```

Expected:

1. `./build/dev-dea/bin/l0c-stage2 --ast -P examples hello` succeeds.
2. `./build/dev-dea/bin/l0c-stage2 --ast --all-modules -P compiler/stage2_l0/src l0c` succeeds.
3. No public Stage 2 CLI mode still emits `L0C-9510`.
4. The full Stage 2 test suite, trace suite, and triple-bootstrap regression remain green.
5. The updated docs consistently describe Stage 2 public CLI parity as complete.

## Assumptions and defaults

1. The remaining public Stage 2 CLI parity gap is only `--ast`; no other user-facing mode is intentionally NYI today.
2. Stage 1 remains the oracle for `--ast` traversal behavior, module ordering, and general output shape.
3. Exact byte-for-byte AST text parity is desirable but not mandatory if the Stage 2 AST representation makes a faithful
   structural match easier than a textual clone; this decision must be made explicit in tests.
4. This plan concludes the implementation milestone for public CLI parity, but it does not by itself close the separate
   shared CLI contract/spec plan.
