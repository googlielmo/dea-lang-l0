# Feature Plan

## Embed build-provenance metadata in installed and repo-local Stage 2 compiler binaries

- Date: 2026-03-12
- Status: Closed (implemented)
- Title: Embed build-provenance metadata in Stage 2 binaries for `install-dev-stage2` and `install` without perturbing
  triple-bootstrap stability
- Kind: Feature
- Severity: Medium
- Stage: 2
- Subsystem: CLI / build tooling / install-prefix artifacts
- Modules:
    - `compiler/stage2_l0/src/build_info.l0`
    - `compiler/stage2_l0/src/cli_args.l0`
    - `scripts/build_stage2_l0c.py`
    - `scripts/dist_tools_lib.py`
    - `scripts/gen_dist_tools.py`
    - `compiler/stage2_l0/README.md`
    - `docs/reference/project-status.md`
- Test modules:
    - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`
    - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
    - `tests/test_make_dea_build_workflow.py`
    - `tests/test_dist_tools_lib_fallback.py`

## Summary

The current Stage 2 `--version` path prints only the static identity string:
`Dea language / L0 compiler (Stage 2)`.
That is sufficient for source-tree parity, but it does not answer the operational questions an installed compiler
should answer: which build produced it, when it was built, which commit it came from, which host built it, and which
host compiler banner identifies the actual native toolchain.

The approved direction is to embed this metadata in the binary itself, but only in artifact-producing flows:

1. `make install-dev-stage2`
2. `make install`

Raw self-hosted Stage 2 builds, including compiler 2 / compiler 3 in the strict triple-bootstrap regression, must stay
on the plain source tree and must not receive embedded build metadata.

The preferred implementation is a generated Stage 2 source overlay. The build/install tooling should synthesize one
temporary `build_info.l0`, prepend its root ahead of `compiler/stage2_l0/src`, and compile the artifact with that
embedded metadata. This avoids wrapper-side metadata plumbing and avoids fragile post-link binary patching.

## Implementation

1. Add a dedicated Stage 2 module, `build_info.l0`, that owns the values used by `--version`.
   The checked-in source-tree copy should provide default or unknown values only, so normal source-tree and raw
   self-hosted builds remain on the static fallback path.
2. Keep `--help` and verbose startup identity unchanged. Only the `--version` path should consult `build_info.l0`.
   When the embedded fields are absent or unknown, `--version` should fall back to the current single-line Stage 2
   identity output.
3. Add one shared Python helper in the build/install tooling that collects a build-provenance snapshot:
    - full git commit hash
    - short git commit hash
    - repository cleanliness (`clean` / `dirty`)
    - build id
    - one captured UTC build timestamp reused for both the build ID suffix and rendered build time
    - host platform text
    - the first line of `<compiler> --version`
4. Host platform text should use `uname -s`, `uname -r`, and `uname -m` on Unix-like systems, joined as
   `<kernel-name> <kernel-release> <machine>`. On non-Unix systems it should use a portable fallback with the same
   three-field shape.
5. Repository cleanliness should come from git state at build time and should be expressed only in the `commit:` line:
    - clean tree: `<fullsha>`
    - dirty tree: `<fullsha>+dirty`
6. Resolve the host C compiler once in Python using the same precedence already used by the compiler drivers:
    - `L0_CC`
    - `tcc`, `gcc`, `clang`, `cc`
    - `CC`
      Then export that exact value back into the subprocess environment as `L0_CC` so the captured compiler banner and
      the
      actual build compiler agree.
7. For `install-dev-stage2`, `scripts/build_stage2_l0c.py` should:
    - generate a temporary overlay root containing a synthesized `build_info.l0`
    - invoke the Stage 1 builder with:
        - `-P <overlay_root>`
        - `-P compiler/stage2_l0/src`
    - embed the collected build metadata in compiler 1
8. For `install`, `scripts/gen_dist_tools.py install-prefix` should:
    - generate the same kind of temporary overlay root
    - use it both for the bootstrap Stage 2 artifact when needed and for the self-hosted installed compiler build
    - ensure the final installed Stage 2 native binary has embedded build metadata
9. Do not use the overlay in raw Stage 2 `--build -o ...` invocations. In particular, do not use it in the
   triple-bootstrap self-build steps that produce compiler 2 and compiler 3.
10. Reject post-link binary patching for this feature. Do not reserve placeholder bytes, do not mutate linked binaries
    in place, and do not rely on ELF / Mach-O / PE section surgery or trailing payloads.
11. The embedded `--version` report shape should be:
    - first line: `Dea language / L0 compiler (Stage 2)`
    - subsequent labeled lines:
        - `build:`
        - `build time:`
        - `commit:`
        - `host:`
        - `compiler:`
12. `build time:` should render the same captured UTC instant used by the build ID logic, formatted as
    `YYYY-MM-DD HH:MM:SS+00:00`.
13. `compiler:` should print only the first line of `<compiler> --version`; do not print a separate compiler command
    line or a separate compiler-version line.
14. Build ID precedence should be:
    - `DEA_BUILD_ID`, if set
    - GitHub Actions auto-derived ID when `GITHUB_ACTIONS=true`
    - local fallback
15. The GitHub Actions auto-derived build ID format should be:
    - `gha-<run_id>.<run_attempt>-<job>-<runner_os>-<runner_arch>`
      using:
    - `GITHUB_RUN_ID`
    - `GITHUB_RUN_ATTEMPT`
    - `GITHUB_JOB`
    - `RUNNER_OS`
    - `RUNNER_ARCH`
16. For other CI systems in v1, do not add a broad provider-detection table. If a non-GitHub CI pipeline wants a
    CI-native build identifier, it should set `DEA_BUILD_ID` explicitly. Otherwise the tooling should fall back to a
    local-style build id.
17. The local fallback build ID should be:
    - `<shortsha>-<utcstamp>` when a git short SHA is available
    - `local-<utcstamp>` otherwise
18. Update Stage 2 docs to state:
    - built and installed Stage 2 binaries embed provenance for `--version`
    - direct `.native --version` works because the data is in the binary
    - `--help` and verbose identity remain static
    - compiler 2 / compiler 3 in the triple test intentionally remain on the static/fallback path
    - the report uses `build`, `build time`, `commit`, `host`, and `compiler`
    - `commit` appends `+dirty` only for dirty trees
    - `host` is the compact uname triplet
    - `compiler` is the compiler banner only
19. When git metadata is unavailable, the embedded report should still be emitted if the non-git fields are available:
    - `build` should fall back to the local timestamp form
    - `commit` should render as `unknown`
    - missing `git` should not abort artifact-producing builds

## Verification

Execute:

```bash
./scripts/build-stage2-l0c.sh
env -i PATH="$PATH" ./build/dea/bin/l0c-stage2 --help
env -i PATH="$PATH" ./build/dea/bin/l0c-stage2 --version
env -i PATH="$PATH" ./build/dea/bin/l0c-stage2.native --version
python3 tests/test_make_dea_build_workflow.py
python3 tests/test_dist_tools_lib_fallback.py
bash compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh
bash compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh
python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
```

Expected:

1. Repo-local and install-prefix Stage 2 artifacts print the multiline embedded build-provenance report on
   both wrapper and `.native` `--version`.
2. Stage 2 `--help` and verbose startup output remain unchanged apart from any intentional documentation wording
   changes.
3. Archive or source-tree builds without usable git metadata still emit partial embedded provenance with
   `commit: unknown` instead of aborting.
4. Compiler 2 and compiler 3 in the strict triple-bootstrap regression remain on the static/fallback `--version` path.
5. The strict triple-bootstrap regression still compares byte-stable compiler 2 / compiler 3 `.c` and `.native`
   outputs, with no generated build metadata leaking into those artifacts.
