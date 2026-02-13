# CLAUDE.md

Guidance for Claude Code and AI agents working in this repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language compiling to C99. Stage 1 compiler is in Python; Stage 2 is
self-hosting in L0.

Core principle: **no undefined behavior** in the language itself.

## Documentation — Read On Demand

Detailed information lives in `docs/`. **Before answering questions about grammar, architecture, backend design, or
implementation status, read the relevant doc file(s).**

| Doc file                   | Covers                                                |
|----------------------------|-------------------------------------------------------|
| `docs/architecture.md`            | Compiler pipeline, passes, data flow, file layout                |
| `docs/stage1_compiler_contract.md` | Stage 1 compact contract, interfaces, guarantees, doc routing   |
| `docs/c_backend_design.md`          | C backend architecture, emission strategy                        |
| `docs/design_decisions.md`          | Runtime, pointer model, integer model, I/O, rationale           |
| `docs/l0_grammar.md`                | Formal EBNF grammar                                              |
| `docs/project_status.md`            | Implementation status, known limitations, roadmap                |
| `docs/standard_library.md`          | stdlib module reference (`std.*`, `sys.*`)                       |

Also see: `CONTRIBUTING.md`, `SECURITY.md`.

## Commands

All commands run from the repository root:

```bash
./l0c -P examples run hello       # build + run
./l0c -P examples build hello     # build executable
./l0c -P examples gen hello       # emit C only
./l0c -P examples check hello     # parse + type-check
./l0c -P examples tok hello       # dump tokens
./l0c -P examples ast hello       # pretty-print AST
./l0c -P examples sym hello       # dump symbols
./l0c -P examples type hello      # dump resolved top-level types
```

Verbosity: `-v` (info), `-vvv` (debug).

C compiler selection: `-c <compiler>`. Auto-detection order: tcc, gcc, clang, cc from PATH, then `$CC`.

### Testing

```bash
cd compiler/stage1_py
pytest -n 3                       # all tests (parallel, optimal)
pytest tests/test_l0_lexer.py     # specific file
pytest -k "test_name"             # pattern match
```

Requires pytest >= 9.0.2, pytest-xdist >= 3.5, and a C compiler.
TCC is used by default if present (fastest); Clang and GCC are also searched in the current $PATH if `tcc` is not
available. Override with `./l0c build -c <compiler>`.

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
- No tag-phrases ("for clarity", "for consistency"). State what changed.
- Use backticks for L0/Python/C code snippets and function/type names in messages.
- No Co-Authored-By lines.
- Before committing, verify this file's accuracy (file references current, new modules listed, deleted ones removed).