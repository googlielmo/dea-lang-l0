# Refactor Plan

## Lift shared Stage 2 util data structures into `std.*` with cycle-safe string/text split

- Date: 2026-02-24
- Status: Closed (implemented)
- Title: Move reusable Stage 2 util modules into Stage 1 stdlib and hard-cut Stage 2 imports to `std.*`
- Kind: Refactor
- Severity: Medium (stdlib surface expansion and Stage 2 import migration)
- Stage: 1/2
- Subsystem: Standard Library + Stage 2 Frontend Infrastructure
- Modules: `compiler/stage1_py/l0/stdlib/std/array.l0`, `compiler/stage1_py/l0/stdlib/std/vector.l0`,
  `compiler/stage1_py/l0/stdlib/std/hashmap.l0`, `compiler/stage1_py/l0/stdlib/std/hashset.l0`,
  `compiler/stage1_py/l0/stdlib/std/linear_map.l0`, `compiler/stage1_py/l0/stdlib/std/text.l0`,
  `compiler/stage1_py/l0/stdlib/std/string.l0`,
  `compiler/stage2_l0/src/{lexer.l0,tokens.l0,ast.l0,parser/*.l0}`,
  `compiler/stage2_l0/tests/*.l0`,
  `docs/reference/standard-library.md`

## Summary

Lift common Stage 2 utility modules from `compiler/stage2_l0/src/util/` into the Stage 1 stdlib under flat `std.*` names.

Perform a hard cutover in Stage 2 sources/tests to import `std.*` directly for lifted modules.

Keep compiler-specific diagnostics (`util.diag`) in Stage 2 only.

Text helpers `concat3_s`, `concat4_s`, `to_upper_s`, `to_lower_s`, `repeat_s`, `reverse_s` remain in `std.text`
by decision, along with integer formatting helpers.

## Public API and Type Interface

1. Add new std modules:
   `std.array`, `std.vector`, `std.hashmap`, `std.hashset`, `std.linear_map`, `std.text`.

2. `std.text` required contents:
   `StringBuffer`, `CharBuffer`, `sb_*`, `cb_*`,
   `concat3_s`, `concat4_s`, `to_upper_s`, `to_lower_s`, `repeat_s`, `reverse_s`,
   `int_to_string_base`, `int_to_string`, `int_to_hex_string`, `int_to_bin_string`.

3. No `std.diag` addition in this refactor.

## Dependency Constraints

1. Final stdlib dependency graph must be acyclic.
2. Do not force `std.string <-> std.text` mutual imports.
3. Keep string helper placement acyclic; current implementation keeps helpers in `std.text`.
4. `util.diag` remains Stage-2-only and must not leak into `std.*`.

## Implementation Sequence

1. Port `util.array` -> `std.array`.
2. Port `util.vector` -> `std.vector` and update dependencies to `std.array`.
3. Port `util.hashmap` -> `std.hashmap` and update dependencies to `std.array`/`std.vector`.
4. Port `util.hashset` -> `std.hashset` and update dependencies to `std.array`/`std.vector`.
5. Port `util.linear_map` -> `std.linear_map` and update dependency to `std.vector`.
6. Port `util.text` core buffer/format APIs -> `std.text`.
7. Keep string helper functions in `std.text` (no move to `std.string` in this refactor).
8. Hard-cut Stage 2 imports from lifted `util.*` modules to `std.*` in `src/` and `tests/`.
9. Keep `import util.diag;` unchanged wherever used.
10. Remove lifted Stage 2 util modules:
    `util/array.l0`, `util/vector.l0`, `util/hashmap.l0`, `util/hashset.l0`, `util/linear_map.l0`, `util/text.l0`.
11. Update `docs/reference/standard-library.md` with final module/function locations.

## Acceptance Criteria

1. Stage 2 has no imports of removed util DS/text modules.
2. `util.diag` remains Stage-2-only.
3. Lifted std modules compile and behave equivalently to prior Stage 2 util behavior.
4. No circular dependency exists between `std.string` and `std.text` (or elsewhere in stdlib).
5. `docs/reference/standard-library.md` matches the final exported API locations.

## Test Cases and Scenarios

1. Stage 1 regression:
   `cd compiler/stage1_py && pytest -n auto`
2. Stage 2 runtime tests:
   `./compiler/stage2_l0/run_tests.sh`
3. Stage 2 trace/ownership gate:
   `./compiler/stage2_l0/run_trace_tests.sh`
4. Import audit:
   grep confirms no references to removed `util.array|vector|hashmap|hashset|linear_map|text`.
5. Helper-location audit:
   docs and imports reflect whether each candidate helper landed in `std.string` or remained in `std.text`.

## Assumptions and Defaults

1. Namespace layout is flat `std.*` (not `std.collections.*`).
2. Migration mode is hard cutover in one change set.
3. String helpers remain in `std.text` for this change.
4. This is a structural/library refactor; no language feature changes.

## Implementation Verification

Executed on 2026-02-24:

1. `./compiler/stage2_l0/run_tests.sh`
   Result: pass (`9/9` tests passed).
2. `./compiler/stage2_l0/run_trace_tests.sh`
   Result: pass (`9/9` trace checks passed; `leaked_object_ptrs=0`, `leaked_string_ptrs=0` for all tests).
3. `source .venv/bin/activate && cd compiler/stage1_py && pytest -n auto`
   Result: pass (`865 passed, 109 xfailed`).
