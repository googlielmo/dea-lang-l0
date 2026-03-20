# Feature Plan

## Windows README addendum

- Date: 2026-03-14
- Status: Implemented
- Title: Add a root-level Windows addendum for shell usage, launcher layout, and install workflows
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Documentation / developer workflow
- Modules:
  - `README.md`
  - `README-WINDOWS.md`
- Test modules:
  - none
- Repro: Windows shell usage of `make install-dev-*`, `make use-dev-*`, and `make install`

## Summary

The repository already contains working Windows launchers and partial shell guidance, but the information is scattered
across the main README, Stage 2 README, CLAUDE instructions, and implementation details. Add one root-level
`README-WINDOWS.md` as the Windows-specific addendum and link to it from the main README.

## Fix

- document the supported MSYS2/MinGW-w64 workflow
- explain what `install-dev-stage1`, `install-dev-stage2`, `use-dev-stage1`, `use-dev-stage2`, and `install` generate
- document `l0-env.sh` generation and its Bash/MSYS2-only activation role
- document native-shell usage for `cmd.exe` and PowerShell via generated `.cmd` launchers
- explain that `l0c-stage2.cmd` and `l0c.cmd` are stage-specific vs selected-alias entry points, not redundant files
- call out the current repo-local Stage 1 native-shell limitation explicitly instead of implying parity that does not
  exist

## Verification

- read the launcher/env generation paths in `scripts/dist_tools_lib.py`, `scripts/gen_dist_tools.py`, and `Makefile`
- verify the main README links to `README-WINDOWS.md` from the install/setup path
- verify the addendum examples match the current generated launcher layout and shell support contract
