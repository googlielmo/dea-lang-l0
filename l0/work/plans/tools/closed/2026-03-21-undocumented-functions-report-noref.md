# Tool Plan

## Undocumented Functions Report For Docs Builds

- Date: 2026-03-21
- Status: Closed
- Title: Generate and surface undocumented-function reports during documentation builds
- Kind: Tooling
- Severity: Medium (Documentation / CI visibility)
- Stage: Shared
- Subsystem: Documentation / CI
- Modules:
  - `compiler/docgen/l0_docgen.py`
  - `scripts/gen-docs.sh`
  - `.github/workflows/docs-validate.yml`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_docgen_cli.py`

## Summary

The docs pipeline intentionally allows undocumented functions to remain visible in generated output, but there was no
stable artifact listing which functions were still undocumented. That made cleanup work ad hoc and meant CI logs only
showed the generated docs succeeded, not which gaps remained.

This tooling change adds a generated report for undocumented functions, keeps the behavior informational instead of
failing strict docs builds, and exposes the report in the `Validate Documentation` workflow logs.

## Implementation Notes

### Report generation

- `compiler/docgen/l0_docgen.py` scans generated Doxygen XML for `memberdef kind="function"` entries whose brief,
  detailed, and in-body documentation sections are all empty.
- The pipeline writes a stable artifact at `build/docs/undocumented-functions.txt` (or
  `<output-dir>/undocumented-functions.txt`).
- Report entries are grouped by source type:
  - `Dea` for `.l0`
  - `Python` for `.py`
  - `Other` for anything else, such as shared runtime headers

### Build behavior

- Undocumented functions remain allowed; this is not a new strict failure class.
- `scripts/gen-docs.sh` prints the report path on successful builds when undocumented functions are present.
- The existing `--strict` behavior remains tied to Doxygen warnings and synthetic `__padN__` regressions.

### CI exposure

- `.github/workflows/docs-validate.yml` now prints the full report into workflow logs immediately after the strict docs
  build step.
- The publish workflow continues to show the report path through `scripts/gen-docs.sh`, but only the validation workflow
  cats the full report.

## Verification

Run:

```bash
uv run pytest compiler/stage1_py/tests/cli/test_docgen_cli.py -q
./scripts/gen-docs.sh --strict --no-latex
cat build/docs/undocumented-functions.txt
```

Success criteria:

1. The docs build succeeds even when undocumented functions exist.
2. `build/docs/undocumented-functions.txt` is generated.
3. The report is grouped into `Dea`, `Python`, and `Other` sections.
4. The validate-docs workflow prints the report contents in Actions logs.
