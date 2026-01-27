# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language with a compile-to-C backend. The goal is to build a self-hosting compiler (Stage 2 in L0 itself). Stage 1 is implemented in Python for fast iteration.

Key design principles:
- **No undefined behavior** - operations are well-defined, rejected with diagnostics, or trigger defined runtime failures
- **C-like syntax** with algebraic enums, pattern matching, and optional types (`T?`)
- **Compile to C99** - portable output works with GCC, Clang, TinyCC

## Commands

All commands run from the repository root:

```bash
# Build and run a module
./l0c -P examples run hello

# Build an executable
./l0c -P examples build hello

# Generate C code only
./l0c -P examples gen hello

# Parse and type-check (no codegen)
./l0c -P examples check hello

# Debug commands
./l0c -P examples tok hello    # dump tokens
./l0c -P examples ast hello    # pretty-print AST
./l0c -P examples sym hello    # dump symbols
./l0c -P examples type hello   # dump resolved types
```

### Debugging and Logging

```bash
# Enable info-level logging (compilation stages, module loading)
./l0c -v -P examples check hello

# Enable debug-level logging (detailed diagnostics, includes info)
./l0c -vvv -P examples check hello

# Alternative syntax (equivalent to -vvv)
./l0c -v -v -v -P examples check hello
```

### Testing

```bash
cd compiler/stage1_py
pytest                           # run all tests
pytest tests/test_l0_lexer.py   # run specific test file
pytest -k "test_name"           # run tests matching pattern
```

Tests require pytest >= 9.0.2 and a C compiler (GCC/Clang) for codegen tests.

## Architecture

```
Source (.l0) → Lexer → Parser → NameResolver → SignatureResolver
             → LocalScopeResolver → ExpressionTypeChecker → CBackend → C99 → gcc/clang
```

### Key Files (compiler/stage1_py/)

| File | Purpose |
|------|---------|
| `l0c.py` | CLI driver, argument parsing, orchestrates compilation |
| `l0_lexer.py` | Tokenization (keywords, operators, literals) |
| `l0_parser.py` | Recursive-descent parser producing AST |
| `l0_ast.py` | AST node dataclasses |
| `l0_driver.py` | Module loading, import resolution, caching |
| `l0_codegen.py` | C99 code generation with string ARC |
| `l0_expr_types.py` | Expression type inference and checking |
| `l0_signatures.py` | Function/struct type resolution |
| `l0_name_resolver.py` | Module-level symbol binding |
| `l0_locals.py` | Local variable scoping |
| `l0_types.py` | Type representations |
| `runtime/l0_runtime.h` | C kernel runtime (allocation, I/O, strings) |

### Stage 2 Compiler (compiler/stage2_l0/)

The self-hosted compiler in L0, under active development:
- `src/tokens.l0` - Token type definitions
- `src/lexer.l0` - Lexer implementation
- `src/util/` - Utility libraries (vector, map, string, array)
- `tests/` - Unit tests

### Standard Library

Located in `compiler/stage1_py/l0/stdlib/`:
- `std/io.l0` - print, println, input
- `std/string.l0` - string utilities
- `std/rand.l0` - random numbers
- `std/system.l0` - system calls, command line args
- `std/assert.l0` - assertions
- `sys/unsafe.l0` - unsafe operations

## Language Quick Reference

```l0
module demo;
import std.io;

// Structs
struct Point { x: int; y: int; }

// Enums with payloads
enum Expr {
    Int(value: int);
    Add(left: Expr*, right: Expr*);
}

// Functions
func eval(e: Expr*) -> int {
    match (*e) {
        Int(value) => { return value; }
        Add(left, right) => { return eval(left) + eval(right); }
    }
}

// Optional types and try operator
func safe_div(a: int, b: int) -> int? {
    if (b == 0) { return null; }
    return (a / b) as int?;
}
```

Types: `int`, `uint`, `byte`, `ubyte`, `bool`, `string`, `void`, `T*` (pointer), `T?` (optional)

## Important Constraints

- No `&` (address-of) operator - pointers come from runtime/heap allocation
- Assignment is a statement, not an expression
- `match` is statement-only (no expression match)
- No generics, traits, or macros in Stage 1
- Auto-dereference: `ptr.field` works without explicit `(*ptr).field`

## Git Conventions

- Commit messages: Use multiline format with summary line and detailed body for non-trivial changes.
- Summary line: Sentence case with period at end (e.g., "Add `byte` type support.").
- Body: Factual description of changes only. List items end with periods.
- Use backticks for L0 code snippets and type names in commit messages.
- Do not include Co-Authored-By lines in commits.

## Documentation

Detailed design documents in `docs/`:
- `architecture.md` - compiler pipeline and data flow
- `l0_grammar.md` - formal EBNF grammar
- `design_decisions.md` - rationale for key decisions
- `project_status.md` - implementation status and roadmap

Community files:
- `CONTRIBUTING.md` - development setup and contribution guidelines
- `SECURITY.md` - vulnerability reporting