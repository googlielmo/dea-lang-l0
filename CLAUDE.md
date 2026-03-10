# CLAUDE.md

Guidance for Claude Code and AI agents working in this repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language compiling to C99.

- **Core principle:** No undefined behavior in the language itself.
- **Stage 1:** Compiler pipeline in Python (lexer → parser → AST → semantic passes → C codegen).
- **Stage 2:** Self-hosting compiler (L0-in-L0) with frontend, backend, `--gen`, `--build`, and `--run`
  implemented.
- **Subsystems:** Grammar/semantics, backend/codegen, driver/build/module layout, and stdlib.

## Documentation — Read On Demand

Detailed information lives in `docs/`. **Before answering questions about grammar, architecture, backend design, or
implementation status, read the relevant doc file(s).**

| Doc file                                   | Covers                                                        |
|--------------------------------------------|---------------------------------------------------------------|
| `docs/reference/architecture.md`           | Compiler pipeline, passes, data flow, file layout             |
| `docs/specs/compiler/diagnostic-format.md` | Normative diagnostic output format (header, snippet, gutter)  |
| `docs/specs/compiler/stage1-contract.md`   | Stage 1 compact contract, interfaces, guarantees, doc routing |
| `docs/reference/c-backend-design.md`       | C backend architecture, emission strategy                     |
| `docs/reference/design-decisions.md`       | Runtime, pointer model, integer model, I/O, rationale         |
| `docs/reference/grammar/l0.md`             | Formal EBNF grammar                                           |
| `docs/reference/project-status.md`         | Implementation status, known limitations, roadmap             |
| `docs/reference/standard-library.md`       | stdlib module reference (`std.*`, `sys.*`)                    |
| `docs/reference/ownership.md`              | Ownership rules for `new`/`drop`, ARC strings, and containers |
| `docs/specs/runtime/trace.md`              | Trace flags, generated defines, runtime trace contract        |

Documentation policy:

- `docs/README.md` for docs placement, naming, metadata standards, and attic rules.
- **Metadata:** Reference/Specs must have `Version: YYYY-MM-DD`. Plans (Bug Fix/Feature/Refactor) must use the standard
  metadata block (Date, Status, Kind, etc.).
- `docs/attic/README.md` for archived/obsolete document policy details.
- **Maintenance:** If you change stdlib or ARC behavior, you MUST update the corresponding `.md` in `docs/` in the same
  PR.

Also see: `CONTRIBUTING.md`, `SECURITY.md`.

## Environment & Setup

- **Virtual Environment:** Always check for a local `.venv` and/or `uv` availability. Use the local virtual environment
  to execute `pytest` and `./l0c`.
- **Environment Variables:** Source `source ./l0-env.sh` when needed to set up `L0_HOME`, `PATH`, and `L0_CC`.
- **Auto-provisioning:** If no local virtual environment is available and sufficient permissions are granted, install
  one using `uv sync` (preferred, uses `pyproject.toml`) or
  `python3 -m venv .venv && source .venv/bin/activate && pip install -e .`.

## Commands

All commands run from the repository root. The `l0c` commands below describe the main Stage 1 wrapper/driver
interface exposed today:

```bash
./l0c -P examples --run hello     # build + run
./l0c -P examples --build hello   # build executable
./l0c -P examples --gen hello     # emit C only
./l0c -P examples --check hello   # parse + type-check
./l0c -P examples --tok hello     # dump tokens
./l0c -P examples --ast hello     # pretty-print AST
./l0c -P examples --sym hello     # dump symbols
./l0c -P examples --type hello    # dump resolved top-level types
./scripts/gen-docs.sh --strict    # generate docs; fail on warnings and synthetic __padN__ regressions
./scripts/gen-docs.sh --pdf       # also build/copy build/docs/pdf/refman.pdf
./scripts/gen-docs.sh --pdf-fast  # faster preview PDF build (single pdflatex pass)
```

Verbosity: `-v` (info), `-vvv` (debug).

C compiler selection: `-c <compiler>`. Auto-detection order (used by `l0c` and Stage 1 tests): `$L0_CC`, then
`tcc`, `gcc`, `clang`, `cc` from PATH, then `$CC`.

Trace toggles (codegen/build/run): `--trace-arc`, `--trace-memory`.

For current Stage 2 CLI work, use:

```bash
./l0c -P compiler/stage2_l0/src --run l0c -- --gen -P examples hello # build a throwaway stage 2 compiler and use it
./scripts/build-stage2-l0c.sh # build the stage 2 compiler and place it under build/stage2/bin/l0c-stage2
./build/stage2/bin/l0c-stage2 --check -P examples hello # run the stage 2 compiler directly
./build/stage2/bin/l0c-stage2 --build -P examples hello # build directly with the stage 2 compiler
./build/stage2/bin/l0c-stage2 --run -P examples hello # build and run directly with the stage 2 compiler
```

Stage 2 currently implements analysis/dump modes plus `--gen`, `--build`, and `--run`.

Generated API documentation is written under `build/docs/` and is not part of the hand-authored `docs/` tree.
Native Doxygen LaTeX output is generated under `build/docs/doxygen/latex/`; use `./scripts/gen-docs.sh --pdf`
to build `refman.pdf` and copy it into `build/docs/pdf/` if a local TeX toolchain is installed.
For faster local previews, `./scripts/gen-docs.sh --pdf-fast --latex-only` performs a single-pass PDF build.
After each successful docs run, generated artifacts are mirrored to a stable preview tree under `build/preview/`
(`html/`, `markdown/`, `pdf/`), which is overwritten by the next successful run.
Use `-v` / `--verbose` with `scripts/gen-docs.sh` to show m.css warnings and LaTeX build output directly.
Release/manual publishing is handled by `.github/workflows/docs-publish.yml`; PR validation is handled by
`.github/workflows/docs-validate.yml`.

### Testing

```bash
cd compiler/stage1_py
pytest -n auto                    # all tests (parallel, optimal)
pytest tests/lexer/test_lexer.py  # specific file
pytest -k "test_name"             # pattern match
```

For Stage 2 (`compiler/stage2_l0`) changes, finalization checks should include:

```bash
./compiler/stage2_l0/run_tests.py
./compiler/stage2_l0/run_trace_tests.py
```

`run_trace_tests.py` is an important finalization gate because it validates ARC/memory traces and leak triage across
all Stage 2 tests.

For Stage 1 ownership-sensitive changes (ARC lowering, `drop` behavior, container ownership paths), run targeted ARC
trace tests from `compiler/stage1_py/tests/backend/test_trace_arc.py` and prefer the full file when touching shared
ARC pathways.

When adding or moving tests, follow `compiler/stage1_py/tests/README.md` for placement and naming rules.

Requires pytest >= 9.0.2, pytest-xdist >= 3.5, and a C compiler.
Compiler auto-detection follows the logic defined in the Commands section.

## Critical Constraints

- Assignment is a statement, not an expression.
- `match` is statement-only.
- `case` is statement-only (scalar/string dispatch).
- `with` provides deterministic resource cleanup (inline `=>` or `cleanup` block).
- No generics, traits, or macros in Stage 1.
- Qualified names: single `module::Name` form only.

## Ownership Guardrails

- No `&` (address-of) operator.
- Auto-dereference: `ptr.field` works without `(*ptr).field`.
- Treat `docs/reference/ownership.md` as normative for ownership and memory-management behavior.
- Normal L0 assignment over ARC-managed strings is usually compiler-balanced; avoid manual retain/release in regular
  assignment paths.
- Raw-memory/container internals require explicit ownership discipline (release before zero/remove, and clear owner
  contracts for moved bytes).
- If observed behavior contradicts ownership docs, report with a minimal `.l0` reproducer, generated C excerpt, and
  trace output.

## Diagnostic Codes

Format: `[XXX-NNNN]` (e.g., `[TYP-0158]`). Before adding a new code, confirm it is unused:

```bash
rg -n 'XXX-NNNN' compiler/stage1_py compiler/stage2_l0 docs
```

- Equivalent Stage 2 conditions MUST reuse the exact Stage 1 code, not just the same family. This includes
  user-facing diagnostics and `ICE-xxxx`.
- Never reuse a Stage 1 code with a different meaning in Stage 2.
- New codes are allowed only for Stage 2-only conditions with no Stage 1 equivalent.
- When porting Stage 1 behavior, treat Stage 1 code meaning as the oracle and preserve the same numeric code for the
  equivalent condition.

## Git Conventions

- Multiline commits: sentence-case summary with period, then factual body as bullets with "- " prefix, no wrapping.
- For multiline commit messages, write the message to a temporary file and use `git commit -F <file>` to avoid shell
  escaping issues (especially with backticks).
- No tag-phrases ("for clarity", "for consistency"). State what changed.
- Use backticks for L0/Python/C code snippets and function/type names in messages.
- No Co-Authored-By lines.
- Before committing, verify this file's accuracy (file references current, new modules listed, deleted ones removed).

## Quality Standards

### Documentation Standards

- **Python:** Use Google Style docstrings (Args, Returns, Raises).
- **C (.h/.c) & L0 (.l0):** Use Doxygen Style (Javadoc format: `/** ... */` with `@param`, `@return`; omit `@brief`).

### Definition of Done

1. **No UB:** Emitted C99 must be memory-safe and UB-free.
2. **Trace Validated:** `run_trace_tests.py` must pass with zero leaks.
3. **English Only:** All code names and comments MUST be in English.
4. **Tests Updated:** All relevant tests must be added/updated in the same PR.
5. **Documentation Updated:** If behavior changes, corresponding `.md` in `docs/`
6. **Diagnostic Codes:** Equivalent Stage 2 conditions reuse Stage 1 codes exactly, including `ICE-xxxx`; new codes are
   globally unique and verified by search.
7. **Plans Documented:** For non-trivial changes or bug fixes a plan must be documented in `docs/plans/` with a clear
   execution path and expected outcomes. See `docs/README.md` for naming and placement rules.
