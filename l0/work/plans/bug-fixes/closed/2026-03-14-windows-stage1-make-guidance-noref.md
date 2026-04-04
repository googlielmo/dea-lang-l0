# Bug Fix Plan

## Windows `use-dev-stage1` guidance points native shells at the wrong entry point

- Date: 2026-03-14
- Status: Implemented
- Title: Correct the Windows `make use-dev-stage1` guidance to use `scripts\\l0c.cmd` in native shells
- Kind: Bug Fix
- Severity: Medium
- Stage: Shared
- Subsystem: Developer workflow / Makefile messaging
- Modules:
  - `Makefile`
- Test modules:
  - none
- Repro: `make use-dev-stage1` on Windows

## Summary

The Windows message printed by `make use-dev-stage1` told users to prepend `DEA_BUILD_DIR/bin` to `PATH` so bare `l0c`
would invoke the selected compiler. That is true for Stage 2, but not for repo-local Stage 1: there is no generated
`l0c.cmd` alias in `build/.../bin`, so native Windows shells should use `scripts\\l0c.cmd` instead.

## Fix

- keep the MSYS2 bash guidance unchanged
- replace the native-shell guidance with direct `scripts\\l0c.cmd` usage for `cmd.exe` and PowerShell
- state explicitly that the repo-local Stage 1 `l0c` alias is Bash-only on Windows today

## Verification

```bash
make OS=Windows_NT use-dev-stage1
```
