# Contributing to Dea/L0

Thanks for contributing.

## Scope and status

L0 is experimental. The language, compiler CLI, and runtime APIs may change without notice.

## Development setup

Prerequisites:

- Python 3.14+
- A C99 compiler (GCC or Clang) for codegen tests and running compiled programs
- `make` for the recommended developer workflow
- [`uv`](https://github.com/astral-sh/uv) is recommended, but not required

For normal development, prefer the repo-local switchable `l0c` alias:

```bash
make venv
make install-dev-stages
make use-dev-stage1      # or `make use-dev-stage2`
source dist/bin/l0-env.sh
```

The source-tree `./scripts/l0c` entrypoint is Stage 1 only and is mainly useful for bootstrap mechanics, internal
tooling, and Stage 1-focused testing.

### Running tests

From the repository root:

```bash
make venv
make test-stage1
./.venv/bin/python -m pytest compiler/stage1_py/tests/lexer/test_lexer.py
./.venv/bin/python -m pytest -k "test_name" compiler/stage1_py/tests
```

For Stage 2 (`compiler/stage2_l0`) changes, run:

```bash
make test-stage2
make test-stage2-trace
```

`run_trace_tests.py` is an important finalization gate for Stage 2 changes because it checks runtime trace health
(including leak triage) across the full Stage 2 test suite.

### Smoke test

Verify the compiler works end-to-end:

```bash
l0c -P examples --run hello    # build and run hello.l0
l0c -P examples --check hello  # parse and type-check only
```

### Debugging

Use verbose flags to see compilation stages:

```bash
l0c -v -P examples --check hello     # info-level logging
l0c -vvv -P examples --check hello   # debug-level logging
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

### Documentation and styling standards

- **Python:** Use Google Style docstrings (include `Args`, `Returns`, `Raises` sections).
- **C (.h/.c) & L0 (.l0):**
    - **Doxygen:** Use Javadoc format (`/** ... */` with `@param`, `@return` tags). Omit the `@brief` tag; rely on the
      first sentence for the brief description.
    - **License Headers:** Keep `SPDX-License-Identifier` and copyright headers in standard C block comments
      (`/* ... */`) at the top of the file, distinct from Doxygen blocks.
    - **Section Separators:**
        - **C/C++:** Banners must fit within a **79-character maximum line width**. For standard block comment
          separators, use exactly 73 equals signs (`=`):
          ```c
          /* =========================================================================
           * Section name
           * ========================================================================= */
          ```
        - **L0:** Use a shorter format to fit within a 40-character line width, with exactly 33 equals (`=`) or
          hyphen ( `-`) signs. The title should stay within 33 characters (introduce a newline if longer).
          ```
          /* =================================
             Section Name
             ================================= */
          ```
          Notice the closing line has exactly 3 leading spaces and 33 signs before the `*/`.

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
