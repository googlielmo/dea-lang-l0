# Contributing to Dea/L0

Thanks for contributing.

## Scope and status

L0 is experimental. The language, compiler CLI, and runtime APIs may change without notice.

## Development setup

Prerequisites:

- Python 3.14+
- pytest >= 9.0.2 (install with `pip install pytest`)
- A C99 compiler (GCC or Clang) for codegen tests and running compiled programs

### Running tests

From the repository root:

```bash
cd compiler/stage1_py
pytest                           # run all tests
pytest tests/lexer/test_lexer.py # run a specific test file
pytest -k "test_name"           # run tests matching a pattern
```

### Smoke test

Verify the compiler works end-to-end:

```bash
./l0c -P examples run hello      # build and run hello.l0
./l0c -P examples check hello    # parse and type-check only
```

### Debugging

Use verbose flags to see compilation stages:

```bash
./l0c -v -P examples check hello     # info-level logging
./l0c -vvv -P examples check hello   # debug-level logging
```

## Making changes

1. Fork and create a topic branch.
2. Keep commits small and focused.
3. Add or update tests for behavior changes.
4. Update docs when changing user-visible behavior (syntax, diagnostics, CLI flags).

## Project structure

- `compiler/stage1_py/` — Stage 1 compiler (Python). This is the bootstrap implementation.
- `compiler/stage2_l0/` — Stage 2 compiler (L0). Self-hosted compiler in development.
- `examples/` — Example L0 programs.
- `docs/` — Design documents, grammar specification, architecture notes.

## Coding conventions

- Prefer explicit, simple implementations over cleverness.
- Preserve existing grammar/AST shapes unless the change is staged and justified.
- Error handling: return structured diagnostics (`Diagnostic` objects); avoid silent failures.
- See `docs/design_decisions.md` for rationale behind key language and compiler choices.

### Commit messages

- Use sentence case with a period at the end (e.g., "Add `byte` type support.").
- For non-trivial changes, include a detailed body describing what changed.
- Use backticks for L0 code snippets and type names.
- AI tools and agents should not add Co-Authored-By lines to commits.

## Pull requests

A PR should include:

- What changed and why (1–3 paragraphs)
- Any relevant issue link(s)
- Tests: added/updated, and how to run them locally
- Notes on backward-compatibility (breaking vs non-breaking)

By submitting a contribution, you agree that it may be distributed under the project's dual license (MIT OR Apache-2.0),
consistent with the repository LICENSE files.

## AI-Assisted Contributions Policy

The use of AI or other automated tools to assist in writing code, documentation, or other project materials is
**encouraged** in order to experiment, iterate rapidly, and explore solutions more efficiently.
Contributors remain fully responsible for the correctness, rights to contribute and license, licensing compatibility,
and security of their contributions, regardless of the tools used.

**All contributions must comply with the project’s licensing, contribution guidelines, and quality standards.**

## Code of Conduct

Assume good faith, be kind, and focus on technical substance.
Abusive or harassing content will be removed.

Report concerns to: googlielmo@gmail.com
