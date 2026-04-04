# Feature Plan

## Add core empty/split/join/replace text helpers (`std.string` + `std.text`)

- Date: 2026-02-27
- Status: Implemented (2026-02-27)
- Title: Add `is_empty_s`/`find_last_s`, standard split/line/join/replace helpers, and document `trim_s`
- Kind: Feature
- Severity: Medium (stdlib completeness and shared helper consistency)
- Stage: Shared stdlib (affects Stage 1 and Stage 2 users)
- Subsystem: Standard Library (`std.string`, `std.text`)
- Modules:
  - `compiler/shared/l0/stdlib/std/string.l0`
  - `compiler/shared/l0/stdlib/std/text.l0`
  - `compiler/stage2_l0/tests/util_text_test.l0`
  - `compiler/stage1_py/tests/backend/test_string_runtime.py`
  - `docs/reference/standard-library.md`

## Summary

This change adds missing basic text-manipulation helpers while keeping module ownership clear:

1. Add `is_empty_s` and `find_last_s` to `std.string`.
2. Keep `trim_s` in `std.string` and document it in the public reference.
3. Add high-level collection/text helpers to `std.text`:
   - `split_s`
   - `lines_s`
   - `join_s`
   - `replace_s`
4. Add Stage 2 and Stage 1 runtime coverage for all new helpers.
5. Add runtime panic tests for invalid empty-pattern inputs.

## Public API Changes

### Added to `std.string`

1. `is_empty_s(s: string) -> bool`
2. `find_last_s(haystack: string, needle: string) -> int`

### Existing in `std.string` now documented

1. `trim_s(s: string) -> string`

### Added to `std.text`

1. `split_s(s: string, sep: string) -> VectorString*`
2. `lines_s(s: string) -> VectorString*`
3. `join_s(parts: VectorString*, sep: string) -> string`
4. `replace_s(s: string, old: string, replacement: string) -> string`

## Behavior and Design Decisions

1. `split_s` uses string separators and keeps empty tokens.
2. `split_s` rejects `sep == ""` with assertion message: `split_s: separator must be non-empty`.
3. `lines_s` matches existing Stage 2 utility semantics:
   - split on `\n`
   - strip trailing `\r` from each line
   - `lines_s("")` returns an empty vector
   - trailing final `\n` does not add a final empty line
4. `join_s` uses `VectorString*` and returns a single string.
5. `replace_s` performs non-overlapping left-to-right replacement.
6. `replace_s` rejects `old == ""` with assertion message: `replace_s: old pattern must be non-empty`.

## Implementation Scope

### `std.string`

1. Add `is_empty_s`.
2. Add `find_last_s`.
3. Keep existing `trim_s` implementation unchanged.

### `std.text`

1. Add `split_s` with keep-empty semantics.
2. Add `lines_s` with CRLF normalization.
3. Add `join_s` for `VectorString*`.
4. Add `replace_s` for global non-overlapping replacement.

### Tests

1. Extend Stage 2 `util_text_test` with:
   - `test_is_empty_s`
   - `test_find_last_s`
   - `test_split_s`
   - `test_lines_s`
   - `test_join_s`
   - `test_replace_s`
2. Extend Stage 1 runtime tests with:
   - success-path integration coverage for all new helpers
   - panic coverage for invalid empty separator/pattern assertions

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/tests --check util_text_test
./l0c -P compiler/stage2_l0/tests --run util_text_test
./.venv/bin/pytest compiler/stage1_py/tests/backend/test_string_runtime.py
```

Observed:

1. Stage 2 util text checks/run pass with new helper tests.
2. Stage 1 string runtime tests pass, including panic assertions.

## Documentation Updates

`docs/reference/standard-library.md` updated to:

1. add `is_empty_s` and `trim_s` in `std.string`.
2. add `find_last_s` in `std.string`.
3. add `split_s`, `lines_s`, `join_s`, and `replace_s` in `std.text`.

## Assumptions and Defaults

1. String utilities operate on byte strings (ASCII-oriented helpers).
2. Empty-token-preserving split behavior is the default public behavior.
3. Assertion failures are surfaced through runtime `Software Failure` messages.
4. No migration of Stage 2 internal `util.strings` helpers is performed in this change.
