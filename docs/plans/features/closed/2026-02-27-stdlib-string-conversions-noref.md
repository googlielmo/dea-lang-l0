# Feature Plan

## Consolidate and expand stdlib string conversions (`std.string` + `std.text`)

- Date: 2026-02-27
- Status: Implemented (2026-02-27)
- Title: Unify base-digit helpers, move decimal int parsing to `std.text`, and add builtin bool/byte conversions
- Kind: Feature
- Severity: Medium (API completeness and stdlib consistency)
- Stage: Shared stdlib (affects Stage 1 and Stage 2 users)
- Subsystem: Standard Library (`std.string`, `std.text`)
- Modules:
    - `compiler/shared/l0/stdlib/std/string.l0`
    - `compiler/shared/l0/stdlib/std/text.l0`
    - `compiler/stage2_l0/tests/util_text_test.l0`
    - `docs/reference/standard-library.md`

## Summary

This work delivers one coherent conversion refactor/expansion across string utilities:

1. **Refactor ownership of digit primitives**:
   base-digit helpers are centralized in `std.string` (`is_digit_base`, `to_digit_base`) while keeping `is_digit` as a
   direct trivial check.
2. **Move decimal parse API**:
   `string_to_int` is removed from `std.string` and exposed in `std.text` as a wrapper over `string_to_int_base(s, 10)`.
3. **Add missing builtin conversions in `std.text`**:
   bool <-> string and numeric byte <-> string (including base-aware byte parse/format).
4. **Expand Stage 2 coverage**:
   add conversion tests for base helpers, base int parsing, bool parsing/formatting, and byte parsing/formatting.
5. **Update stdlib reference docs**:
   document the new API surface and clarified module responsibilities.

## Public API Changes

### Added to `std.string`

1. `is_digit_base(c: byte, base: int) -> bool`
2. `to_digit_base(c: byte, base: int) -> int?`

### Removed from `std.string`

1. `string_to_int(s: string) -> int?`

### Added to `std.text`

1. `string_to_int(s: string) -> int?` (decimal wrapper)
2. `bool_to_string(value: bool) -> string`
3. `string_to_bool(s: string) -> bool?`
4. `byte_to_string(value: byte) -> string`
5. `byte_to_string_base(value: byte, base: int) -> string`
6. `string_to_byte(s: string) -> byte?`
7. `string_to_byte_base(s: string, base: int) -> byte?`
8. `string_to_int_base(s: string, base: int) -> int?`

## Behavior and Design Decisions

1. Keep `is_digit(c)` as inline direct check in `std.string` (no wrapper call overhead).
2. Keep conversion/parsing APIs in `std.text`; keep low-level byte/string and char helpers in `std.string`.
3. `string_to_bool` is strict and case-sensitive:
    - accepts only `"true"` and `"false"`
    - returns `null` otherwise
4. `byte_to_s` in `std.string` remains character-byte conversion; numeric byte formatting/parsing is explicit in
   `std.text`.
5. `string_to_byte_base` reuses `string_to_int_base` and applies range validation (`0..255`), returning `null` for
   invalid/out-of-range values.

## Implementation Scope

### `std.string`

1. Add base-aware digit classification/conversion helpers.
2. Remove decimal `string_to_int` implementation now owned by `std.text`.

### `std.text`

1. Keep existing int formatting helpers (`int_to_string*`).
5. Add `string_to_int_base` as canonical signed-base parser for `2..16`.
2. Add decimal wrapper `string_to_int`.
3. Add bool conversion helpers (`bool_to_string`, `string_to_bool`).
4. Add numeric byte conversion helpers (`byte_to_string*`, `string_to_byte*`).

### Tests (`util_text_test`)

Add and wire in:

1. `test_is_digit_base`
2. `test_to_digit_base`
3. `test_string_to_int_base_valid`
4. `test_string_to_int_base_invalid`
5. `test_string_to_int_base_limits`
6. `test_bool_string_conversions`
7. `test_byte_string_conversions`

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/tests --check util_text_test
./l0c -P compiler/stage2_l0/tests --run util_text_test
./l0c -P compiler/stage2_l0/src --check l0c
```

Observed:

1. Stage 2 util text tests pass, including new bool/byte conversion cases.
2. Stage 2 source check for `l0c` passes.

## Documentation Updates

`docs/reference/standard-library.md` updated to:

1. list `std.string` char-level helpers (`is_digit_base`, `to_digit_base`) and clarify `byte_to_s` semantics.
2. list expanded `std.text` conversion APIs (`bool_to_string`, `string_to_bool`, `byte_to_string*`, `string_to_byte*`,
   `string_to_int*`).

## Assumptions and Defaults

1. Bool textual representation is canonical lowercase only (`true` / `false`).
2. Numeric byte parsing supports optional leading zeros and base `2..16` via shared int parser.
3. Out-of-range byte values are rejected with `null` (no saturation/wrap behavior).
4. No external tracker is attached yet (`noref`).
