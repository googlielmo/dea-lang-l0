# Bug Fix Plan

## Shared nested symbol-path wording parity

- Date: 2026-04-12
- Status: Closed
- Title: Restore shared nested symbol-path diagnostic wording parity across Python and self-hosted compilers
- Kind: Bug Fix
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - L0 Stage 1
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 1, using the shared wording decision as the oracle for downstream native ports
- Porting rule: Settle the wording and reject-point behavior in L0 Stage 1 first, then port the equivalent native paths
  mechanically into L0 Stage 2 and L1 Stage 1 while the expression/type-resolution code remains aligned
- Target status:
  - L0 Stage 1: Implemented
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Diagnostics / Type resolution / Expression typing / Shared docs
- Modules: `l0/compiler/stage1_py/{l0_expr_types,l0_signatures}.py`,
  `l0/compiler/stage1_py/tests/name_resolver/test_qualified_names.py`,
  `l0/compiler/stage2_l0/src/{expr_types,type_resolve}.l0`,
  `l0/compiler/stage2_l0/tests/diagnostic_message_parity_test.py`,
  `l1/compiler/stage1_l0/src/{expr_types,type_resolve}.l0`,
  `l1/compiler/stage1_l0/tests/diagnostic_message_parity_test.py`, `scripts/diagnostic_message_parity.py`,
  `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules: `l0/compiler/stage1_py/tests/name_resolver/test_qualified_names.py`,
  `l0/compiler/stage2_l0/tests/diagnostic_message_parity_test.py`,
  `l1/compiler/stage1_l0/tests/diagnostic_message_parity_test.py`
- Repro: direct `--check` smoke tests on nested symbol paths such as `color::Color::Red` in type and expression position

## Summary

The shared diagnostic-code parity fix closed on 2026-04-11 restored the right `SIG-0018` and `TYP-0158` codes, but it
left two follow-up gaps:

- the user-facing wording for nested symbol paths still differed across implementations,
- the native expression checker could still let `color::Color::Red` fall through to a later type mismatch instead of
  rejecting it immediately with `TYP-0158`.

This follow-up closes both gaps and updates the shared diagnostic catalog wording accordingly.

## Scope of This Fix

1. Change `SIG-0018` wording to the shared nested symbol-path sentence in L0 Stage 1, L0 Stage 2, and L1 Stage 1.
2. Change `TYP-0158` wording to the same shared nested symbol-path sentence in L0 Stage 1, L0 Stage 2, and L1 Stage 1.
3. Align the native expression reject path with Python Stage 1 so nested symbol paths are rejected as soon as a
   qualifier is present.
4. Update `docs/specs/compiler/diagnostic-code-catalog.md` so both codes read “Nested symbol paths are not supported”.
5. Add focused native wording checks that pin the shared message text.

## Non-Goals

- Do not change the diagnostic codes themselves.
- Do not change unrelated type-resolution or value-resolution wording.
- Do not broaden the native wording parity harness beyond the focused nested-path and existing type-resolution message
  cases added here.

## Approach

- Update the Python Stage 1 `SIG-0018` and `TYP-0158` emitters to the new shared wording.
- Mirror that wording into the homologous self-hosted L0 Stage 2 and L1 Stage 1 emitters.
- Reuse native helper formatting so expression diagnostics can print the full nested path plus the suggested
  `module::symbol` form.
- Tighten the native `TYP-0158` guard from “invalid multi-segment qualifier” to “any nested qualifier present” so the
  reject point matches Python Stage 1.
- Add a small shared native message-parity harness and per-stage test entrypoints.

## Tests

Minimum coverage to keep in sync:

1. Python Stage 1 qualified-name tests assert the new `SIG-0018` and `TYP-0158` wording.
2. L0 Stage 2 native wording tests assert the new `SIG-0018` and `TYP-0158` text directly.
3. L1 Stage 1 native wording tests assert the same text directly.

## Verification

```bash
cd l0
../.venv/bin/python -m pytest compiler/stage1_py/tests/name_resolver/test_qualified_names.py
make install-dev-stage2
make test-stage2 TESTS=diagnostic_message_parity_test.py

cd ../l1
make build-stage1
make test-stage1 TESTS=diagnostic_message_parity_test.py
```

## Outcome

- Standardized `SIG-0018` and `TYP-0158` wording across L0 Stage 1, L0 Stage 2, and L1 Stage 1.
- Aligned the native expression reject path with Python Stage 1 so nested symbol paths now emit `TYP-0158` instead of
  falling through to later type mismatches.
- Added shared native wording parity coverage plus stage-local test entrypoints.
- Updated `docs/specs/compiler/diagnostic-code-catalog.md` so both code entries describe nested symbol-path rejection in
  shared wording.

## Related Work

- `work/plans/bug-fixes/closed/2026-04-11-shared-diagnostic-code-parity-noref.md`
- `work/plans/bug-fixes/closed/2026-04-10-shared-match-qualified-pattern-parity-noref.md`

## Assumptions

- The new nested symbol-path wording is now the intended shared user-facing contract for both type-position and
  expression-position variants of this diagnostic family.
