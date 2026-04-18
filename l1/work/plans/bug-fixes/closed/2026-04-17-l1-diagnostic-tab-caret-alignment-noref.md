# Bug Fix Plan

## Align L1 diagnostic spans and printed carets on tab-bearing lines

- Date: 2026-04-17
- Status: Done
- Title: Align L1 diagnostic spans and printed carets on tab-bearing lines
- Kind: Bug Fix
- Severity: Medium
- Stage: 1
- Subsystem: Diagnostics / lexer columns / parser spans / snippet rendering
- Modules:
  - `compiler/stage1_l0/src/lexer.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/src/ast.l0`
  - `compiler/stage1_l0/src/util/diag.l0`
  - `compiler/stage1_l0/src/diag_print.l0`
  - `compiler/stage1_l0/tests/diag_print_test.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `docs/reference/architecture.md`
- Test modules:
  - `compiler/stage1_l0/tests/diag_print_test.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
- Related:
  - `l1/docs/roadmap.md`
- Repro: `make test-stage1 TESTS="diag_print_test lexer_test parser_test"`

## Summary

L1 diagnostic printing currently risks a visual mismatch on source lines that contain ASCII tabs (`\t`). The compiler
may be storing a span that is internally consistent while the printed caret line is shifted on the terminal, or the
reverse: caret placement may appear correct only because the stored columns and the printed snippet are following
different width rules.

The current implementation has three likely contributors:

1. `lexer.l0` advances `LexerState.column` by `1` for every non-newline byte, including tabs.
2. `parser/shared.l0` extends spans by token text width in bytes.
3. `diag_print.l0` prints the original source line verbatim but constructs the caret prefix from repeated spaces and the
   stored diagnostic columns.

That combination is sufficient to misalign the printed underline whenever tab expansion in the visible snippet does not
match the width model used by stored columns and span endpoints.

## Current State

1. L1 stores diagnostic positions as one-based line and column pairs in `Span` and `Diagnostic`.
2. The lexer treats tabs as ordinary non-newline bytes for column advancement.
3. Parser span extension currently derives end columns from token-text byte width rather than from a terminal-facing
   rendered-width model.
4. Diagnostic snippet rendering prints the source line with raw tabs intact, then pads the caret line with spaces based
   on stored start and end columns.
5. `diag_print_test.l0` exercises basic located snippet printing, but there is no current regression coverage for
   tab-bearing lines.

## Hypotheses To Resolve

The implementation should start by proving which mismatch actually exists:

1. stored columns count tabs as width `1`, while printed output leaves tabs to terminal expansion
2. some upstream span computation already approximates tab stops, while the caret printer still assumes raw columns
3. tab handling is only part of the bug, and an existing end-column exclusivity/inclusivity ambiguity is also visible
   once tabs appear

## Defaults Chosen

1. Scope this fix to ASCII horizontal tabs; Unicode display-width handling is separate work.
2. Use one explicit width contract across stored columns and printed snippets; reject split semantics.
3. Preserve existing behavior for non-tab source as much as possible.
4. Add regression coverage for both stored column metadata and visible caret alignment.
5. Document the final invariant once the implementation lands.

## Goal

1. Determine the current tab-width behavior of L1 diagnostic spans and snippet rendering.
2. Make stored span columns and printed carets agree on tab-bearing lines.
3. Define stable behavior for single-column and multi-column highlights when tabs occur before or inside the span.
4. Leave L1 with a documented, test-backed diagnostic column contract instead of terminal-dependent behavior.

## Implementation Phases

### Phase 1: Reproduce and characterize the mismatch

Add focused fixtures and tests that cover:

- tabs before the offending token
- tabs inside a multi-column highlighted range
- mixed tabs and spaces before the highlighted token
- a real parser or typing diagnostic emitted on a tab-bearing line

Use those fixtures to record the current stored columns and the current printed snippet shape so the fix is driven by
observed behavior rather than guesswork.

### Phase 2: Choose one diagnostic-column contract

After reproducing the bug, choose and document one contract for tab-bearing diagnostics. The two viable families are:

1. **Logical-source columns.** Tabs count as one source column, and snippet rendering normalizes the displayed line and
   caret padding to the same logical model.
2. **Visual-display columns.** Tabs advance to a fixed tab stop, and lexer columns, parser spans, and caret rendering
   all follow that same display-width model.

The fix should reject any hybrid contract where stored columns mean one thing while snippet rendering assumes another.

### Phase 3: Align storage and rendering with the chosen contract

Update the affected layers together:

- lexer column advancement, if the chosen contract changes tab width upstream
- parser span extension, if end-column computation must track visual width instead of token byte width
- any diagnostic constructors that rely on the existing raw-column assumption
- snippet rendering in `diag_print.l0`, including the printed line, caret prefix, and caret width logic

This phase should also settle the span-end convention that rendering relies on, especially for multi-column highlights
on tab-bearing lines.

### Phase 4: Lock the behavior with regression coverage and docs

Add tests that verify:

1. the stored diagnostic columns for tab-bearing fixtures
2. the rendered snippet text and caret line for those fixtures
3. at least one end-to-end compiler diagnostic on a tab-bearing source line
4. unchanged behavior for representative non-tab diagnostics

Once the implementation is complete, update the relevant L1 reference docs so the diagnostic column contract is
explicit.

## Non-Goals

- Unicode grapheme or East Asian display-width handling
- fix-it hints or richer multi-line diagnostic rendering
- unrelated diagnostic-message wording improvements
- broad source pretty-printing beyond what is needed to make tab-bearing snippets deterministic

## Verification Criteria

1. `diag_print_test.l0` gains tab-bearing coverage that fails if the visible caret line drifts from the rendered
   snippet.
2. Lexer and/or parser tests assert the documented column contract for tab-bearing inputs.
3. At least one real parse or typing diagnostic fixture with tabs reproduces the old bug before the fix and stays
   covered afterward.
4. `make -C l1 test-stage1 TESTS="diag_print_test lexer_test parser_test"` passes.
5. `make -C l1 test-stage1` passes.

## Resolution

Chosen contract: **logical-source columns**. Each non-newline source byte, including ASCII horizontal tabs, advances the
stored column by exactly one. Snippet rendering normalizes the displayed source line to match (each tab becomes a single
space), so stored columns, caret offsets, and visible output all use the same width model.

Changes landed together:

- `compiler/stage1_l0/src/diag_print.l0` — added `dp_normalize_line_for_display` and a pure `dp_format_snippet` used by
  `dp_render_snippet`; snippet rendering now emits a tab-normalized source line.
- `compiler/stage1_l0/tests/diag_print_test.l0` — tab-before-token, tab-inside-span, mixed tabs/spaces, and non-tab
  regressions assert the exact formatted snippet.
- `compiler/stage1_l0/tests/lexer_test.l0` — `test_tab_advances_one_column` locks the lexer side of the contract.
- `docs/reference/architecture.md` — invariants section documents the logical-source column contract.

Lexer column advancement and parser span extension were already consistent with this contract and did not need to
change.

## Open Design Constraints

1. The final behavior must be deterministic and should not depend on whichever implicit tab-stop behavior a terminal
   uses.
2. The displayed source line and caret underline must be derived from the same width model.
3. The chosen contract should remain simple enough to reuse in future diagnostic UX work.
4. The fix should minimize churn in code paths unrelated to diagnostic locations and snippet rendering.
