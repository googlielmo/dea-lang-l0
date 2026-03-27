# Bug Fix Plan

## LaTeX documented function signature parity

- Date: 2026-03-21
- Status: Closed
- Title: Restore L0 function signatures in PDF detail sections for documented members
- Kind: Bug Fix
- Severity: High (PDF API docs can still show C-style function prototypes for documented `.l0` members)
- Stage: Shared
- Subsystem: Documentation / Docgen
- Modules:
  - `compiler/docgen/l0_docgen_l0_helpers.py`
  - `compiler/docgen/l0_docgen_latex.py`
  - `compiler/stage1_py/tests/cli/test_docgen_latex.py`
- Repro: generate the PDF docs and inspect `compiler/stage2_l0/src/symbols.l0` in the "Function Documentation" section

## Summary

The PDF/LaTeX path still regresses to C-style function prototypes in detailed function sections when the `.l0` member is
preceded by a Doxygen doc comment. In those cases the XML source location can point at the comment terminator instead of
the declaration line, so the shared source-declaration recovery fails and the LaTeX normalizer leaves the raw Doxygen
prototype in place.

## Scope Of This Fix

1. Make source-backed declaration recovery scan forward from the reported source line until it finds the actual member
   declaration.
2. Keep the existing declaration matching strict enough that later unrelated lines are not misidentified as the target
   member.
3. Add a LaTeX regression that reproduces the documented-function case from `symbols.l0`.

## Resolution

Implemented in this repo:

1. Updated the shared source-declaration recovery helper to scan forward from the XML-reported source line until it
   finds the actual `.l0` member declaration.
2. Kept the existing member-name-and-kind match as the gate before accepting recovered source text.
3. Added a LaTeX regression fixture that reproduces the documented `symbol_free` case where Doxygen points at the
   closing `*/` line instead of the function declaration.

## Verification

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_latex.py -q
./scripts/gen-docs.sh --strict
```
