# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other AI tools and agents when working with code in this
repository.

## Project Overview

Dea/L0 is a small, safe, C-family systems language with a compile-to-C backend. The goal is to build a self-hosting
compiler (Stage 2 in L0 itself). Stage 1 is implemented in Python for fast iteration.

Key design principles:

- **No undefined behavior** - operations are well-defined, rejected with diagnostics, or trigger defined runtime
  failures
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
             → LocalScopeResolver → ExpressionTypeChecker → Backend (`l0_backend.py`) → C99 → gcc/clang
```

### Key Files (compiler/stage1_py/)

| File                   | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| `l0c.py`               | CLI driver, argument parsing, orchestrates compilation         |
| `l0_lexer.py`          | Tokenization (keywords, operators, literals)                   |
| `l0_parser.py`         | Recursive-descent parser producing AST                         |
| `l0_ast.py`            | AST node dataclasses                                           |
| `l0_driver.py`         | Module loading, import resolution, caching                     |
| `l0_backend.py`        | Code generation orchestration (language-agnostic)              |
| `l0_c_emitter.py`      | C99 code emission                                              |
| `l0_compilation.py`    | Compilation unit (closed set of modules)                       |
| `l0_context.py`        | Cross-cutting compiler options                                 |
| `l0_diagnostics.py`    | Error/warning reporting                                        |
| `l0_analysis.py`       | Analysis pipeline orchestration, ARC management, type analysis |
| `l0_expr_types.py`     | Expression type inference and checking                         |
| `l0_signatures.py`     | Function/struct type resolution                                |
| `l0_name_resolver.py`  | Module-level symbol binding                                    |
| `l0_resolve.py`        | Name and type resolution utilities                             |
| `l0_locals.py`         | Local variable scoping                                         |
| `l0_scope_context.py`  | Scope context management                                       |
| `l0_symbols.py`        | Symbol table and symbol kinds                                  |
| `l0_types.py`          | Type representations                                           |
| `l0_ast_printer.py`    | AST pretty-printing                                            |
| `l0_logger.py`         | Logging infrastructure                                         |
| `l0_paths.py`          | Path handling utilities                                        |
| `l0_internal_error.py` | Internal compiler error handling                               |
| `runtime/l0_runtime.h` | C kernel runtime (allocation, I/O, strings)                    |
| `runtime/l0_siphash.h` | SipHash implementation for hash functions                      |

### Stage 2 Compiler (compiler/stage2_l0/)

The self-hosted compiler in L0, under active development:

- `src/main.l0` - Compiler entry point
- `src/tokens.l0` - Token type definitions
- `src/lexer.l0` - Lexer implementation
- `src/util/` - Utility libraries (`array.l0`, `linear_map.l0`, `text.l0`, `vector.l0`)
- `tests/` - Unit tests

### Standard Library

Located in `compiler/stage1_py/l0/stdlib/`:

- `std/io.l0` - line input, printing, whole file I/O
- `std/string.l0` - string utilities
- `std/hash.l0` - hash functions
- `std/math.l0` - math utilities
- `std/rand.l0` - random numbers
- `std/system.l0` - system calls, command line args
- `std/assert.l0` - assertions
- `std/optional.l0` - optional type utilities
- `std/unit.l0` - unit type
- `sys/unsafe.l0` - unsafe operations
- `sys/rt.l0` - runtime primitives

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

// Zero-arg variants: bare name or call syntax
enum Color { Red(); Green(); Blue(); }
let c: Color = Red;       // equivalent to Red()
let d: Color = Green();

// Functions
func eval(e: Expr*) -> int {
    match (*e) {
        Int(value) => { return value; }
        Add(left, right) => { return eval(left) + eval(right); }
    }
}

// Case statement (scalar/string dispatch)
func classify(value: int) -> int {
    case (value) {
        0 => { printl_s("zero!"); return 0; }
        1 => return 1;
        else return -1;
    }
}

// Qualified names for disambiguation
import shapes;
import colors;           // both export `Red`
let p: shapes::Point = shapes::Point(1, 2);
let c: colors::Color = colors::Red;

// Optional types and try operator
func safe_div(a: int, b: int) -> int? {
    if (b == 0) { return null; }
    return (a / b) as int?;
}

// With statement (deterministic cleanup)
with (let f = open("a") => close(f),
      let g = open("b") => close(g)) {
    work(f, g);
}
// Or with cleanup block (programmer controls order)
with (let f = open("file"),
      let buf = alloc(1024)) {
    write(f, buf);
} cleanup {
    flush(f);
    free(buf);
    close(f);
}
```

Types: `int`, `uint`, `byte`, `ubyte`, `bool`, `string`, `void`, `T*` (pointer), `T?` (optional)

## Important Constraints

- No `&` (address-of) operator - pointers come from runtime/heap allocation
- Assignment is a statement, not an expression
- `match` is statement-only (no expression match)
- `case` is statement-only (no expression case)
- No generics, traits, or macros in Stage 1
- Auto-dereference: `ptr.field` works without explicit `(*ptr).field`
- Qualified names use a single `module::Name` form only. Multi-segment paths like `color::Color::Red` are parsed but
  rejected during semantic analysis with a diagnostic suggesting the correct `module::Name` form.

## Diagnostic Codes

Every diagnostic message uses a unique code in the format `[XXX-NNNN]` (e.g., `[TYP-0158]`, `[SIG-0018]`, `[PAR-0401]`).
Before adding a new diagnostic code, grep `compiler/stage1_py/` to confirm it is unused:

```bash
grep -r 'XXX-NNNN' --include='*.py' compiler/stage1_py/
```

## Git Conventions

- Commit messages: Use multiline format with summary line and detailed body for non-trivial changes.
- Summary line: Sentence case with period at end (e.g., "Add `byte` type support.").
- Body: Factual description of changes only. List items end with periods.
- Do not end messages with tag-phrases like "for clarity", "for better performance", "for consistency", etc. State what
  changed, not why it's supposedly good (e.g., "Fix null pointer deref in X." not "Fix null pointer deref in X for
  safety.").
- Use backticks for L0 code snippets and type names in commit messages.
- Do not include Co-Authored-By lines in commits.
- Before committing, verify CLAUDE.md accuracy: check that file references are current, update with new modules/files
  added, and remove references to deleted files.

## Documentation

Detailed design documents in `docs/`:

- `architecture.md` - compiler pipeline and data flow
- `c_backend_design.md` - C backend architecture
- `design_decisions.md` - rationale for key decisions
- `l0_grammar.md` - formal EBNF grammar
- `project_status.md` - implementation status and roadmap
- `standard_library.md` - standard library reference

Community files:

- `CONTRIBUTING.md` - development setup and contribution guidelines
- `SECURITY.md` - vulnerability reporting
