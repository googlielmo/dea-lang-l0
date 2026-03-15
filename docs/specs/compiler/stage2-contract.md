# L0 Stage 2 Compiler Contract

Version: 2026-03-15

This document covers Stage 2-specific guarantees not part of the shared CLI contract.

Canonical ownership:

- Shared CLI contract (mode flags, options, targets, identity, exit codes): [cli-contract.md](cli-contract.md)
- Architecture and pass flow: [reference/architecture.md](../../reference/architecture.md)
- Diagnostic code assignment and cross-stage parity: [diagnostic-code-policy.md](diagnostic-code-policy.md)

## 1. Scope

Stage 2 is the self-hosted compiler (`compiler/stage2_l0`) that mirrors the Stage 1 pipeline through code generation and
driver execution. This document records the Stage 2-specific parts of the external interface.

## 2. `--version` Provenance Output

Repo-local (`make install-dev-stage2`) and install-prefix (`make install`) Stage 2 artifacts embed build provenance.
When provenance is present, `--version` prints the identity line followed by five fields:

```
Dea language / L0 compiler (Stage 2)
build: <build-id>
build time: <utc-timestamp>
commit: <git-hash>[+dirty]
host: <kernel> <release> <machine>
compiler: <cc-banner>
```

These fields are **informational**; their format is not guaranteed stable for machine parsing.

### 2.1 Field formats

**`build:`** — a token identifying the build context.

- Precedence: `DEA_BUILD_ID` environment variable (if set) → GitHub Actions composite id → `<short-hash>-<stamp>` →
  `local-<stamp>`, where `<stamp>` is `YYYYMMDDTHHMMSSz` (UTC).
- GitHub Actions form: `gha-<run_id>.<run_attempt>-<job>-<os>-<arch>`.
- Character set: alphanumeric, `.`, `_`, `-`.

**`build time:`** — UTC build timestamp, ISO 8601 with second precision and space separator. Example:
`2026-03-15 09:42:00+00:00`.

**`commit:`** — full 40-character git SHA-1 of `HEAD` at build time, suffixed with `+dirty` when the working tree had
uncommitted changes. `unknown` when git is unavailable.

**`host:`** — space-separated triplet `<kernel_name> <kernel_release> <machine>` from `uname -s`, `uname -r`, `uname -m`
on POSIX; from Python's `platform` module on Windows. Example: `Darwin 24.6.0 arm64`.

**`compiler:`** — first line of `<cc> --version` for the C compiler used to compile the Stage 2 binary. Example:
`Apple clang version 16.0.0 (clang-1600.0.26.3)`.

### 2.2 Fallback behavior

When any of `build`, `build time`, `host`, or `compiler` cannot be determined (value would be `unknown`), the entire
provenance block is suppressed. `--version` prints only the identity line. Raw compiler 2 / compiler 3 binaries produced
by the triple-bootstrap pipeline always use this fallback path.
