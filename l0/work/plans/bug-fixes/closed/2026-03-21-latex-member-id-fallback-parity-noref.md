# Bug Fix Plan

## LaTeX member-id fallback parity

- Date: 2026-03-21
- Status: Closed
- Title: Recover L0 PDF detail signatures when XML and LaTeX member ids diverge
- Kind: Bug Fix
- Severity: High (CI-built PDFs can still show C-style detail signatures for `.l0` members after earlier LaTeX fixes)
- Stage: Shared
- Subsystem: Documentation / Docgen
- Modules:
  - `compiler/docgen/l0_docgen_latex.py`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_docgen_latex.py`
- Repro: inspect `build/ci-refman.pdf` for `compiler/stage2_l0/src/symbols.l0` under "Function Documentation"

## Summary

The PDF detail-signature rewrite currently prefers locating the LaTeX `\footnotesize` signature block by converting the
member id from Doxygen XML into the matching LaTeX `\label{...}`. That works only if the XML and LaTeX runs emit the
same member id. In practice the docs pipeline generates XML and LaTeX via separate Doxygen invocations, so a CI-built
PDF can still retain raw C-style detail signatures even when summary signatures are already normalized to L0 syntax.

## Scope Of This Fix

1. Keep the existing id-based detail-signature rewrite as the primary fast path.
2. Add a fallback that locates the detailed member block from the `\doxysubsubsection{...}` heading when the XML id does
   not match the LaTeX label.
3. Preserve the existing LaTeX header and label while replacing only the signature body.
4. Add a regression fixture where XML and LaTeX intentionally use different member ids for the same documented function.

## Resolution

Implemented in this repo:

1. Added a brace-balanced helper for replacing the detailed `\footnotesize` signature block once its start is located.
2. Added a heading-based fallback that finds the detail block by member name when the XML-derived label lookup misses.
3. Kept the replacement narrow so only the signature body is rewritten; the surrounding label and section structure are
   preserved.
4. Added a LaTeX regression that reproduces a mismatched XML-vs-LaTeX member-id case for `symbol_create`.

## Verification

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_latex.py -q
./scripts/gen-docs.sh --pdf-fast --strict --latex-only
pdftotext -layout build/docs/pdf/refman.pdf - | rg -n "func symbol_create|func symbol_free"
```
