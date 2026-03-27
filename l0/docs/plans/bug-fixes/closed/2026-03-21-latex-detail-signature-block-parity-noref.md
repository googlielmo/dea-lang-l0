# Bug Fix Plan

## LaTeX detail signature block parity

- Date: 2026-03-21
- Status: Closed
- Title: Make PDF detail-signature normalization robust across Doxygen LaTeX variants
- Kind: Bug Fix
- Severity: High (CI-built PDFs can still fall back to raw Doxygen C-style signatures in detailed member sections)
- Stage: Shared
- Subsystem: Documentation / Docgen
- Modules:
  - `compiler/docgen/l0_docgen_latex.py`
  - `compiler/stage1_py/tests/cli/test_docgen_latex.py`
- Repro: compare locally generated PDF output with CI-built PDF for `.l0` pages such as `symbols.l0`, `parser.l0`, and
  `hashset.l0`

## Summary

The `.l0` detail-signature replacement in the LaTeX/PDF path currently depends on one exact
`{\footnotesize\ttfamily \label{...}}` wrapper shape. A CI-built PDF showed that summary-list normalization still worked
while detailed member blocks for functions and top-level `let` values fell back to raw Doxygen output, which indicates
the underlying LaTeX wrapper shape differs enough across environments to bypass the current regex.

## Scope Of This Fix

1. Replace the fragile exact-regex detail block match with logic that locates the labeled `\footnotesize` block and
   replaces its body using brace balancing.
2. Preserve the existing source-declaration recovery and only broaden the LaTeX wrapper match.
3. Add regression coverage for function and variable detail blocks using an alternate `\footnotesize \ttfamily` wrapper
   shape.

## Resolution

Implemented in this repo:

1. Replaced the exact-regex detail block match with a label-based, brace-balanced replacement that tolerates Doxygen
   wrapper variations around the detailed signature block.
2. Kept source-backed declaration recovery unchanged and limited the change to how the LaTeX block is located and
   rewritten.
3. Extended the LaTeX tests so both documented function details and top-level `let` details are covered with the
   alternate wrapper shape.

## Verification

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_latex.py -q
./scripts/gen-docs.sh --strict
./scripts/gen-docs.sh --pdf-fast --strict
pdftotext build/docs/pdf/refman.pdf - | rg -n "func symbol_free|func parse_diag_count|let HS_EMPTY: byte = 0"
```
