# CLAUDE.md

Guidance for Claude Code and AI agents working in this repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language compiling to C99. Stage 1 compiler is in Python; Stage 2 is
self-hosting in L0.

Core principle: **no undefined behavior** in the language itself.

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
| `docs/specs/runtime/trace.md`            | Trace flags, generated defines, runtime trace contract        |

Documentation policy:

- `docs/README.md` for docs placement, naming, and attic rules.
- `docs/attic/README.md` for archived/obsolete document policy details.
- When changing stdlib modules or exported `extern func` signatures, update `docs/reference/standard-library.md` in the
  same change.

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

When adding or moving tests, follow `compiler/stage1_py/tests/README.md` for placement and naming rules.

Requires pytest >= 9.0.2, pytest-xdist >= 3.5, and a C compiler.
Compiler auto-detection matches the command section above (`$L0_CC`, then `tcc|gcc|clang|cc` from PATH, then `$CC`).
Override with `./l0c --build -c <compiler>`.

## Important Constraints

- No `&` (address-of) operator.
- Assignment is a statement, not an expression.
- `match` is statement-only.
- `case` is statement-only (scalar/string dispatch).
- `with` provides deterministic resource cleanup (inline `=>` or `cleanup` block).
- No generics, traits, or macros in Stage 1.
- Auto-dereference: `ptr.field` works without `(*ptr).field`.
- Qualified names: single `module::Name` form only.

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
