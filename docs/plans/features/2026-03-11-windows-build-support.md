# Feature Plan

## Windows Build Support

- Date: 2026-03-11
- Status: Draft
- Title: Windows Build Support (MinGW-w64 Tier 1, MSVC Tier 2)
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / driver / CI
- Modules:
    - `pyproject.toml`
    - `compiler/stage1_py/l0c.py`
    - `compiler/stage1_py/tests/conftest.py`
    - `compiler/stage2_l0/src/build_driver.l0`
    - `compiler/stage2_l0/test_runner_common.py`
    - `scripts/build-stage2-l0c.sh`
    - `.github/workflows/ci.yml`
    - `docs/reference/project-status.md`
    - `CLAUDE.md`
- Test modules:
    - `compiler/stage1_py/tests/` (all — via Windows CI runner)
    - `compiler/stage2_l0/tests/` (all — via Windows CI runner)

## Summary

L0 currently builds and runs exclusively on POSIX systems (macOS, Linux). While the Python code is largely
cross-platform (`pathlib`, `shutil.which`, `subprocess` without `shell=True`), several shell scripts and hardcoded
assumptions block Windows support. The C runtime (`l0_runtime.h`) already has `_WIN32` guards and MSVC flag handling
exists in the driver.

This plan adds Windows build support using **MinGW-w64 as Tier 1** (GCC flags, GNU Make, MSYS2 bash all work
unchanged) and **MSVC as Tier 2** (partial flag support exists, full support deferred). Linux CI validation now lands
first via `.github/workflows/ci.yml`; Windows runner validation remains a follow-up extension of that workflow.

## Goals

1. `l0c --build` and `l0c --run` produce correct executables on Windows with MinGW-w64 GCC.
2. Stage 2 `build-stage2-l0c.sh` succeeds on Windows via MSYS2 bash.
3. Stage 1 and Stage 2 test suites pass on a Windows CI runner.
4. `.sh` test scripts degrade gracefully when bash is unavailable.
5. Makefile targets (from the bootstrap plan) work on Windows once they land.

## Non-Goals

- Full MSVC Tier 1 support (link model, `/Fe:`, MSVC lib syntax) — deferred.
- Porting `gen-docs.sh` — docs build stays Linux/macOS-only.
- Porting `l0-env.sh` — env setup on Windows via Makefile targets or manual config.
- Rewriting `.sh` test scripts in Python — they run via bash when available, skip otherwise.

## Prerequisites

- The bootstrap/Makefile plan (`closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md`) should be at least
  through
  Phase 2 (Makefile exists) before Phase 6 CI validation of Makefile targets.

## Current Cross-Platform Foundation

The following already work or have Windows code paths:

- `_compiler_flag_family()` handles `cl.exe` / MSVC in both Stage 1 and Stage 2.
- `_get_optimize_flag()` returns MSVC flags (`/O1`, `/Od`).
- MSVC standard flags (`/std:c11 /W4`) in `cmd_build()`.
- `l0_runtime.h` has `#if defined(_WIN32)` for `sys/wait.h` and exit status.
- Stage 2 `bd_temp_root()` checks `TEMP`/`TMP` env vars (Windows convention).
- Stage 2 `bd_compiler_flag_family()` handles `cl.exe`.
- `pyproject.toml` has no platform-specific deps.
- Python code uses `pathlib.Path` and `shutil.which()` throughout.

## Blockers

| Blocker                          | Location               | Fix                                                       |
|----------------------------------|------------------------|-----------------------------------------------------------|
| `l0c` is a bash script           | `./l0c`                | Python `console_scripts` entry point + `l0c.cmd` fallback |
| `l0-env.sh` is bash/zsh only     | `./l0-env.sh`          | Out of scope — env setup via Makefile or manual           |
| `build-stage2-l0c.sh` is bash    | `scripts/`             | Runs via MSYS2 bash from MinGW-w64; no rewrite needed     |
| `gen-docs.sh` is bash            | `scripts/`             | Out of scope — docs build stays Linux/macOS-only          |
| `l0c-stage2` is a POSIX launcher | `build/dea/bin/`       | Generate `.cmd` launcher alongside on Windows             |
| Default output `a.out`           | `l0c.py`               | Use `a.exe` on Windows                                    |
| Temp exe has no `.exe` suffix    | `l0c.py`               | Add `.exe` suffix on Windows                              |
| `-o` flag for MSVC               | `l0c.py`               | Use `/Fe:` for MSVC (Tier 2, prep only)                   |
| `-L`/`-l` for runtime lib        | `l0c.py`               | Use MSVC link syntax (Tier 2, prep only)                  |
| Test fixture hardcodes GCC flags | `conftest.py`          | Make flag selection family-aware                          |
| Shell test scripts (`.sh`)       | `stage2_l0/tests/*.sh` | Skip when bash not available                              |
| Stage 2 POSIX shell quoting      | `build_driver.l0`      | Add Windows quoting path                                  |
| `command -v` probe in Stage 2    | `build_driver.l0`      | Use `where.exe` on Windows                                |
| `Makefile` targets use shell     | `Makefile` (upcoming)  | GNU Make from MinGW-w64 + MSYS2 bash                      |
| CI is Linux-only today           | `.github/workflows/`   | Extend `ci.yml` with a Windows job or matrix              |

## Implementation Phases

### Phase 1: Python Entry Point

Replace the bash `l0c` wrapper with a cross-platform Python entry point.

**Changes:**

1. `pyproject.toml` — add `[project.scripts]` entry:
   ```toml
   [project.scripts]
   l0c = "compiler.stage1_py.l0c:main"
   ```
2. `compiler/stage1_py/l0c.py` — ensure `main()` is callable as an entry point (verify `sys.argv` handling, add
   `if __name__ == "__main__"` guard if missing).
3. Create `l0c.cmd` at the repo root as a minimal Windows batch fallback:
   ```cmd
   @python -m compiler.stage1_py.l0c %*
   ```

**Validation:** `python -m compiler.stage1_py.l0c -P examples --check hello` works on both platforms.

### Phase 2: Platform-Aware Executable Naming

Fix hardcoded POSIX assumptions in Stage 1 build/run commands.

**Changes in `compiler/stage1_py/l0c.py`:**

1. `cmd_build()` — default output name: `a.exe` when `sys.platform == "win32"`, otherwise `a.out`.
2. `cmd_run()` — temp executable suffix: `.exe` on Windows.
3. MSVC prep (Tier 2 only): document where `/Fe:` replaces `-o` and `/I` replaces `-I` for future expansion.

**Changes in `compiler/stage1_py/tests/conftest.py`:**

1. Make `_compile_and_run()` compiler-family-aware for flag selection.
2. Output `output.exe` on Windows.

**Validation:** `l0c --build -P examples hello` produces `a.exe` on Windows; `l0c --run -P examples hello` runs it.

### Phase 3: Stage 2 Build Driver Portability

The L0-in-L0 build driver needs a Windows code path.

**Changes in `compiler/stage2_l0/src/build_driver.l0`:**

1. Add `bd_is_windows()` helper (check `L0_PLATFORM` env var or a compile-time define).
2. Add `bd_shell_quote_windows()` — Windows command-line quoting (double-quote wrapping, `"` escaping).
3. Dispatch quoting: use `bd_shell_quote_windows()` on Windows, existing POSIX quoting otherwise.
4. Replace `command -v` compiler probe with `where.exe` on Windows.
5. Executable output suffix: append `.exe` on Windows.

**Validation:** Stage 2 `--build` and `--run` produce correct executables on Windows.

### Phase 4: Stage 2 Launcher Generation

When `build-stage2-l0c.sh` runs on Windows (via MSYS2 bash), generate a `.cmd` companion launcher.

**Changes in `scripts/build-stage2-l0c.sh`:**

1. After generating the POSIX launcher `l0c-stage2`, detect Windows via `OSTYPE` or `uname -s`.
2. On Windows, also generate `l0c-stage2.cmd` alongside:
   ```cmd
   @"%~dp0l0c-stage2-bin.exe" %*
   ```
   (Adjust the inner binary name to match what the build produces.)

**Validation:** `build/dea/bin/l0c-stage2.cmd` exists and invokes the Stage 2 binary on Windows.

### Phase 5: Bash Test Graceful Degradation

Make test runners detect bash availability and conditionally run `.sh` tests.

**Changes in `compiler/stage2_l0/test_runner_common.py`:**

1. At discovery time, check `shutil.which("bash")`.
2. If bash is available: run `.sh` tests via `["bash", script_path]`.
3. If bash is not available: skip `.sh` test cases with a logged warning.

This way MSYS2/Git Bash users get full coverage; native Windows users degrade gracefully.

**Validation:** `run_tests.py` completes on Windows without bash (skips `.sh` tests); completes with bash (runs all).

### Phase 6: GitHub Actions CI

Extend the Linux-first CI workflow to cover Windows as a follow-up.

**New file: `.github/workflows/ci.yml`:**

The repository now has a Linux-only `CI` workflow that runs `make test-all` on `ubuntu-latest` for `pull_request` and
`workflow_dispatch`, with a commented-out `push` trigger block reserved for later.

**Follow-up changes to `.github/workflows/ci.yml`:**

1. Keep the existing Linux job as the baseline path.
2. Add a Windows job or `os` matrix entry using `windows-latest`.
3. Install MinGW-w64 and any shell tooling required by the Windows bootstrap path.
4. Reuse the same top-level validation entrypoint where feasible (`make test-all` if the Windows shell environment is
   ready; otherwise an equivalent explicit command sequence).
5. Preserve the manual and PR triggers unless there is a deliberate CI policy change.

Windows-specific CI considerations:

- `mingw32-make` or ensure `make` is on PATH for Makefile targets.
- MSYS2 provides bash — `.sh` tests will run.
- Test the Makefile targets (`make test-all`) once the Windows shell environment is ready.

**Validation:** CI stays green on Ubuntu after the current rollout, then goes green on both Ubuntu and Windows once the
follow-up lands.

### Phase 7: Documentation

1. This plan document (you are reading it).
2. `docs/reference/project-status.md` — update platform support section to list Windows (MinGW-w64) as supported.
3. `CLAUDE.md` — add Windows setup instructions (MinGW-w64 via MSYS2, env vars, `l0c.cmd`).

## Verification Criteria

1. Linux CI stays green in the current `ci.yml` workflow.
2. Windows CI goes green in the follow-up extension of `ci.yml`.
3. `pytest -n auto` passes on Windows runner (MinGW-w64 GCC).
4. `build-stage2-l0c.sh` succeeds on Windows via MSYS2 bash.
5. Stage 2 `run_tests.py` and `run_trace_tests.py` pass on Windows.
6. `l0c --build -P examples hello` produces `a.exe` on Windows and runs correctly.
7. `.sh` test scripts run when bash is available, skip gracefully otherwise.
8. Makefile targets work on Windows once the shell/toolchain setup is validated.

## Risk Assessment

- **Low risk:** Phases 1–2 are Python-only changes with clear platform guards (`sys.platform`).
- **Medium risk:** Phase 3 (Stage 2 build driver) requires L0 code changes and a platform detection mechanism.
- **Medium risk:** Phase 6 (Windows CI follow-up) depends on MinGW-w64 and Python 3.14 availability in GitHub Actions
  runners.
- **Mitigation:** MinGW-w64 is well-supported via `choco install mingw`; Python 3.14 is available via
  `actions/setup-python@v5`.

## Related Documents

- [Bootstrap plan](closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md) — Makefile and install layout
- [Architecture](../../reference/architecture.md) — compiler pipeline and file layout
- [Project status](../../reference/project-status.md) — platform support and roadmap
