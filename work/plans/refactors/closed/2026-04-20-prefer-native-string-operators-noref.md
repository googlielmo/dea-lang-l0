# Refactor Plan

## Prefer native `string` operators over `std.string::eq_s` / `cmp_s` call-sites

- Date: 2026-04-20
- Status: Closed
- Title: Migrate native-code call-sites from `std.string::eq_s` / `cmp_s` helpers to the native `==`, `!=`, `<`, `<=`,
  `>`, `>=` string operators
- Kind: Refactor
- Scope: Shared
- Severity: Low
- Stage: Shared (L0 Stage 2 self-hosted, L1 Stage 1 self-hosted, shared stdlibs, examples, user-facing docs)
- Targets:
  - `l0/compiler/stage2_l0/` — source + tests
  - `l0/compiler/shared/l0/stdlib/std/` — stdlib internals that currently route through `eq_s` / `cmp_s`
  - `l1/compiler/stage1_l0/` — source + tests
  - `l1/compiler/shared/l1/stdlib/std/` — mirrored stdlib internals
  - `examples/` under both `l0/` and `l1/`
  - User-facing docs under `l0/docs/` and `l1/docs/`
- Origin: `l0/work/plans/features/closed/2026-04-20-string-equality-and-relational-operators-noref.md` (and the two L1
  predecessors under `l1/work/plans/features/closed/2026-04-18-string-*-noref.md`) landed native `string` equality and
  relational operators in both levels. With both levels at parity, the stdlib wrappers become a legacy spelling rather
  than a required indirection.
- Porting rule: Mechanical per-site conversion. L0 Stage 2 and L1 Stage 1 call-sites convert the same way; land them in
  a single change to keep the two self-hosted trees in lockstep. Do **not** delete `eq_s` / `cmp_s` themselves — the
  public stdlib entry points stay to avoid breaking user code and to preserve the tri-valued comparator signature of
  `cmp_s`.
- Target status:
  - `l0/compiler/stage2_l0/`: Implemented
  - `l0/compiler/shared/l0/stdlib/std/`: Implemented
  - `l1/compiler/stage1_l0/`: Implemented
  - `l1/compiler/shared/l1/stdlib/std/`: Implemented
  - `examples/` (L0 + L1): No matching call-sites found
  - User-facing docs (L0 + L1): No illustrative call-sites changed
- Subsystem: Self-hosted compiler sources, shared stdlib implementations, examples, user-facing docs
- Modules: enumerated at implementation time via `rg -l '\beq_s\b|\bcmp_s\b'` across the target subtrees — current
  baseline is ~864 occurrences across 78 `.l0` files plus ~12 occurrences across 6 `.l1` files and the listed doc files.
- Test modules:
  - `l0/compiler/stage2_l0/tests/**/*.l0`
  - `l1/compiler/stage1_l0/tests/**/*.l0`
  - `l0/compiler/stage1_py/tests/` — only if Python-side golden/integration assertions reference the old spelling

## Summary

Both L0 and L1 now accept native `string` equality and relational operators that lower to the same shared runtime
helpers (`rt_string_equals`, `rt_string_compare`) that back `std.string::eq_s` / `cmp_s`. The stdlib wrappers therefore
no longer hide a capability gap — they just route a call through one extra layer.

This refactor converts call-sites in the native codebase to the native operator spelling wherever the conversion is
semantic-preserving. The wrappers themselves remain in the stdlib surface; only their call-sites inside the compiler,
stdlib internals, examples, and docs change.

## Motivation

1. Readability: `a == b` reads more directly than `eq_s(a, b)`; `a < b` beats `cmp_s(a, b) < 0`. Every self-hosted
   compiler pass that compares tokens or identifiers is affected.
2. Consistency with integer and bool comparison — no reason to treat strings as a special case for users reading the
   compiler sources or examples.
3. Removes a subtle didactic hazard: newcomers reading stdlib-heavy code could conclude that `==` on `string` is
   unsupported, even though it has been supported since this work unit.
4. Closes the loop on the equality/relational feature plan — the feature adds the operators; this refactor makes them
   the idiomatic choice in the codebase.

## Conversion Rules

1. `eq_s(a, b)` → `a == b`.
2. `!eq_s(a, b)` → `a != b`.
3. `cmp_s(a, b) == 0` → `a == b`; `cmp_s(a, b) != 0` → `a != b`.
4. `cmp_s(a, b) < 0` → `a < b`; `<= 0` → `a <= b`; `> 0` → `a > b`; `>= 0` → `a >= b`.
5. `cmp_s(a, b) op k` for `k != 0` stays as `cmp_s` — the tri-valued magnitude is being consumed.
6. Any call-site where `eq_s` / `cmp_s` is passed as a first-class function value (comparator slot, callback table,
   etc.) stays. Operators are not function values in L0.
7. Tests that specifically exercise `eq_s` / `cmp_s` as public stdlib entry points stay (the wrappers remain part of the
   public surface and must keep coverage).

## Non-Goals

1. Removing or deprecating `std.string::eq_s` / `cmp_s`. The public stdlib surface is unchanged; the wrappers keep
   wrapping `rt_string_equals` / `rt_string_compare` for users and for comparator-shaped call-sites.
2. Changing runtime helpers, ARC rules, or diagnostic codes.
3. Converting Stage 1 Python compiler sources — they are host-language Python, not Dea, and do not call `eq_s` /
   `cmp_s`.
4. Changing `case`-over-string lowering (already uses `rt_string_equals` directly).
5. Touching `.l1` fixtures whose point is to exercise the wrappers themselves.

**Implementation Note:** Active `cmp_s(...)` call-sites in compiler/stdlib code are expected to be rare or nonexistent;
the bulk of this refactor is `eq_s(...)` → `==`. If a conversion pass encounters many `cmp_s` rewrites in code (vs
docs/definitions), that is a signal to pause and audit for unintended scope (for example, accidentally rewriting stdlib
reference entries or wrapper definitions). Always preserve direct tests of `std.string::cmp_s` as a public callable
function to maintain coverage of the tri-valued comparator contract.

## Execution Plan

1. Confirm call-site inventory at start of implementation, split by scope:
   - **Code trees to convert:** `rg -l --glob '*.l0' --glob '*.l1' '\beq_s\b|\bcmp_s\b' l0/compiler/ l1/compiler/`
     across source and test files.
   - **Examples and doc files to convert:** `l0/examples/`, `l1/examples/`, user-facing reference docs.
   - **Intentional survivors:** stdlib reference entries in docs, wrapper definitions, wrapper-targeted tests, plan docs
     themselves.
2. Work by mirrored file pairs to keep L0 Stage 2 and L1 Stage 1 in lockstep (for example, both `backend.l0` files
   together, both `expr_types.l0` files together).
3. Apply the conversion rules from top to bottom across: a. L0 Stage 2 compiler sources under
   `l0/compiler/stage2_l0/src/` and tests under `tests/`. b. L1 Stage 1 compiler sources under
   `l1/compiler/stage1_l0/src/` and tests under `tests/`. c. Shared stdlib internals under
   `l0/compiler/shared/l0/stdlib/std/` and `l1/compiler/shared/l1/stdlib/std/`. d. Examples under `l0/examples/` and
   `l1/examples/` (if any are introduced before this plan lands; current baseline has none using these helpers). e.
   User-facing docs that show call-site examples (`l0/docs/reference/standard-library.md`,
   `l1/docs/reference/standard-library.md`, `l0/docs/reference/design-decisions.md`,
   `l1/docs/reference/design-decisions.md`, `l1/docs/roadmap.md`). The stdlib reference entries for `eq_s` / `cmp_s`
   themselves must stay (they document the public API); only illustrative usage in surrounding prose changes.
4. For each target subtree, land the change as one commit per target to keep diffs reviewable, or as a single atomic
   commit if pre-commit latency makes that preferable. Bundle Stage 2 and L1 Stage 1 together if the split would churn
   shared fixtures.
5. After each batch, run the stage-appropriate Make target (see Verification).

## Verification

1. `make -C l0 test-stage2` — Stage 2 self-hosted tests, including existing `eq_s` / `cmp_s` coverage and any rewritten
   call-sites.
2. `make -C l0 test-stage1` — ensures the Stage 1 Python frontend still accepts the converted sources as valid L0.
3. `make -C l1 test-all` — L1 Stage 1 self-hosted tests (or `test-stage1` and `check-examples` if testing individual
   stages).
4. `make -C l0 check-examples` and the L1 equivalent — example programs still type-check and run.
5. `make -C l0 triple-test` — strict triple-bootstrap regression must stay green because Stage 2 is rewriting many of
   its own sources.
6. `make -C l0 test-all` — full pre-commit parallel run.
7. Pre-commit from each affected level directory against the root config, per `CLAUDE.md`.
8. Final `rg -n '\beq_s\b|\bcmp_s\b' l0/ l1/` inventory: the remaining hits must be (a) the wrapper definitions, (b)
   wrapper-targeted tests, (c) comparator-shaped callers, or (d) user-facing stdlib reference entries. Any unexplained
   residual hit blocks closure.

## Open Questions

1. Should `std.string::cmp_s` grow a deprecation note pointing users at the native operators for the boolean-consumed
   case while keeping the comparator-shaped case supported? Default answer: no, defer — this plan only mechanically
   moves the compiler and stdlib off the wrappers, it does not reshape the public API.
2. Should any of the new-style comparisons prompt an example or snippet in `l0/examples/` or `l1/examples/`? Default
   answer: not in this plan — the feature plan already carries driver fixtures; add an example only if a reader-facing
   doc needs one for illustration.

## Work Completed

1. Replaced eligible `eq_s(...)` call-sites with native `==` / `!=` string operators across L0 Stage 2, L1 Stage 1,
   mirrored tests, L0 stdlib internals, and L1 stdlib internals.
2. Preserved `eq_s` / `cmp_s` wrapper definitions and wrapper-targeted tests so the public stdlib surface remains
   covered.
3. Fixed native string operator lowering in the Python Stage 1 backend, L0 Stage 2 backend, and L1 Stage 1 backend so
   non-place ARC operands are materialized into cleanup-owned temporaries before `rt_string_equals` /
   `rt_string_compare` calls.

## Completion Notes

The trace failures were not caused by a bad `eq_s` conversion. They exposed a real lowering gap: `eq_s(...)` call
arguments already used normal function-call ARC temporary materialization, while native string operators lowered
directly to runtime helper calls and skipped cleanup for returned string operands such as `basename(...) == "demo.l0"`.

## Final Verification

1. `../.venv/bin/python compiler/stage2_l0/scripts/run_test_trace.py fs_path_test` followed by
   `check_trace_log.py --triage` — `leaked_string_ptrs=0`.
2. `../.venv/bin/python compiler/stage2_l0/scripts/run_test_trace.py util_text_test` followed by
   `check_trace_log.py --triage` — `leaked_string_ptrs=0`.
3. `../.venv/bin/python compiler/stage1_l0/scripts/run_test_trace.py fs_path_test` followed by
   `check_trace_log.py --triage` — `leaked_string_ptrs=0`.
4. `make -C l0 test-stage2-trace` — 32 passed, 0 failed.
5. `make -C l1 test-stage1-trace` — 32 passed, 0 failed.
6. `rg -n --glob '*.l0' --glob '*.l1' '\beq_s\b|\bcmp_s\b' l0/compiler l1/compiler` — remaining hits are only the public
   `std.string` wrapper definitions in L0 and L1.
