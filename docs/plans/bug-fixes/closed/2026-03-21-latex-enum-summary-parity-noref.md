# Bug Fix Plan

## LaTeX enum summary parity

- Date: 2026-03-21
- Status: Closed
- Title: Remove broken Doxygen enum payload dumps from PDF summary lists
- Kind: Bug Fix
- Severity: Medium (PDF summary pages can misstate payload enum variants)
- Stage: Shared
- Subsystem: Documentation / Docgen
- Modules:
  - `compiler/docgen/l0_docgen_latex.py`
  - `compiler/stage1_py/tests/cli/test_docgen_latex.py`
- Repro: generate the PDF docs and inspect payload enums such as `TokenType` in `compiler/stage2_l0/src/tokens.l0`

## Summary

The native Doxygen LaTeX summary list for enums tries to inline enum variants directly in the file-reference
"Enumerations" section. For L0 payload enums, that summary is structurally wrong because Doxygen loses some payload
variants in XML and then misattaches payload text to later variants. The detailed enum section later in the PDF is
already corrected by the L0-aware variants injection, so the summary list becomes both redundant and misleading.

## Scope Of This Fix

1. Simplify enum entries in the LaTeX file-reference "Enumerations" summary to show only `enum Name`.
2. Keep the detailed enum section as the canonical place for the L0-aware variant list.
3. Add regression coverage using a payload enum fixture that reproduces the broken Doxygen summary shape.

## Verification

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_latex.py -q
./scripts/gen-docs.sh --strict
```
