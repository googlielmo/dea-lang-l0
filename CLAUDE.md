# CLAUDE.md

Guidance for Claude Code and AI agents working in this repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language compiling to C99.

- **Core principle:** No undefined behavior in the language itself.
- **Stage 1:** Compiler pipeline in Python (lexer → parser → AST → semantic passes → C codegen).
- **Stage 2:** Self-hosting compiler (L0-in-L0, under development).
- **Subsystems:** Grammar/semantics, driver/build/module layout, and stdlib.

## Documentation — Read On Demand

Detailed information lives in `docs/`. **Before answering questions about grammar, architecture, backend design, or
implementation status, read the relevant doc file(s).**

| Doc file                                 | Covers                                                        |
|------------------------------------------|---------------------------------------------------------------|
| `docs/reference/architecture.md`         | Compiler pipeline, passes, data flow, file layout             |
| `docs/specs/compiler/stage1-contract.md` | Stage 1 compact contract, interfaces, guarantees, doc routing |
| `docs/reference/c-backend-design.md`     | C backend architecture, emission strategy                     |
| `docs/reference/design-decisions.md`     | Runtime, pointer model, integer model, I/O, rationale         |
| `docs/reference/grammar/l0.md`           | Formal EBNF grammar                                           |
| `docs/reference/project-status.md`       | Implementation status, known limitations, roadmap             |
| `docs/reference/standard-library.md`     | stdlib module reference (`std.*`, `sys.*`)                    |
| `docs/reference/ownership.md`            | Ownership rules for `new`/`drop`, ARC strings, and containers |
| `docs/specs/runtime/trace.md`            | Trace flags, generated defines, runtime trace contract        |

Documentation policy:

- `docs/README.md` for docs placement, naming, and attic rules.
- `docs/attic/README.md` for archived/obsolete document policy details.
- **Maintenance:** If you change stdlib or ARC behavior, you MUST update the corresponding `.md` in `docs/` in the same
  PR.

Also see: `CONTRIBUTING.md`, `SECURITY.md`.

## Commands

All commands run from the repository root:

```bash
./l0c -P examples --run hello     # build + run
./l0c -P examples --build hello   # build executable
./l0c -P examples --gen hello     # emit C only
./l0c -P examples --check hello   # parse + type-check
./l0c -P examples --tok hello     # dump tokens
./l0c -P examples --ast hello     # pretty-print AST
./l0c -P examples --sym hello     # dump symbols
./l0c -P examples --type hello    # dump resolved top-level types
```

Verbosity: `-v` (info), `-vvv` (debug).

C compiler selection: `-c <compiler>`. Auto-detection order (used by `l0c` and Stage 1 tests): `$L0_CC`, then
`tcc`, `gcc`, `clang`, `cc` from PATH, then `$CC`.

Trace toggles (codegen/build/run): `--trace-arc`, `--trace-memory`.

### Testing

```bash
cd compiler/stage1_py
pytest -n auto                    # all tests (parallel, optimal)
pytest tests/lexer/test_lexer.py  # specific file
pytest -k "test_name"             # pattern match
```

For Stage 2 (`compiler/stage2_l0`) changes, finalization checks should include:

```bash
./compiler/stage2_l0/run_tests.sh
./compiler/stage2_l0/run_trace_tests.sh
```

`run_trace_tests.sh` is an important finalization gate because it validates ARC/memory traces and leak triage across
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
grep -r 'XXX-NNNN' --include='*.py' compiler/stage1_py/
```

## Git Conventions

- Multiline commits: sentence-case summary with period, then factual body as bullets with "- " prefix, no wrapping.
- For multiline commit messages, write the message to a temporary file and use `git commit -F <file>` to avoid shell
  escaping issues (especially with backticks).
- No tag-phrases ("for clarity", "for consistency"). State what changed.
- Use backticks for L0/Python/C code snippets and function/type names in messages.
- No Co-Authored-By lines.
- Before committing, verify this file's accuracy (file references current, new modules listed, deleted ones removed).

## Quality Standards

### Definition of Done

1. **No UB:** Emitted C99 must be memory-safe and UB-free.
2. **Trace Validated:** `run_trace_tests.sh` must pass with zero leaks.
3. **English Only:** All code names and comments MUST be in English.
4. **Tests Updated:** All relevant tests must be added/updated in the same PR.
5. **Documentation Updated:** If behavior changes, corresponding `.md` in `docs/`
6. **Diagnostic Codes:** New diagnostics must have unique codes, verified by search.
7. **Plans Documented:** For non-trivial changes or bug fixes a plan must be documented in `docs/plans/` with a clear
   execution path and expected outcomes. See `docs/README.md` for naming and placement rules.