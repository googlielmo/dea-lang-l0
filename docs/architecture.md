# L0 Compiler Architecture (Stage 1)

This document summarizes the current compiler frontend architecture for the L0 language. Stage 1 is implemented in
Python and focuses on a safe, C-like language surface that lowers to C in later stages. The goal is to keep the pipeline
explicit, transparent, and easy to bootstrap.

## High-level Pipeline

The compiler is organized as a sequence of pure, explicit passes operating on structured data rather than side-effectful
globals.

``` 
  Source (.l0)
      |
      v
  Lexer.tokenize() --> tokens -->  Parser.parse_module()  --> AST -->  NameResolver.resolve()  -->
      --> scoped envs -->  ExpressionTypeChecker.check()  --> typed envs -->  CBackend.generate()  -->
      --> C99 -->  system C compiler --> executable
```

* **Lexer (`l0_lexer.py`)**: Converts UTF-8 source text into a token stream via `Lexer.tokenize()`, handling keywords,
  operators, literals, and comments with precise line/column tracking.
* **Parser (`l0_parser.py`)**: Hand-written recursive-descent parser that builds the AST in `l0_ast.py` through
  `Parser.parse_module()`, honoring precedence and statement/decl forms (modules, structs, enums, functions, match
  statements, etc.).
* **AST (`l0_ast.py`)**: Dataclasses that model modules, declarations, statements, expressions, and types. The AST
  remains syntax-oriented; it does not perform name or type resolution itself.
* **Name Resolver (`l0_name_resolver.py`)**: Walks the AST with `NameResolver.resolve()` to bind identifiers to
  declarations, enforcing scoping rules and detecting undefined or shadowed names. It produces module environments that
  annotate symbol bindings.
* **Type Checker (`l0_expr_types.py`, `l0_types.py`)**: Uses `ExpressionTypeChecker.check()` to compute expression
  types, enforce pointer nullability, match exhaustiveness, and return types, attaching type info to symbol
  environments. Any violations are routed to the diagnostics layer.
* **Diagnostics (`l0_diagnostics.py`)**: Centralized, structured error reporting with source spans, used by lexer/parser
  and semantic passes.
* **Driver (`l0_driver.py`, `l0_compilation.py`)**: Orchestrates the pipeline for a module: reading files, invoking
  passes, and coordinating code generation.
* **C backend (`l0_codegen.py`)**: Emits a single portable C99 translation unit from the analyzed program (current Stage
  1 backend).

## Module and File Layout

The project keeps modules flat and explicit:

* `l0_lexer.py` — tokenization logic and token definitions.
* `l0_parser.py` — recursive-descent parser entry `parse_module()`.
* `l0_ast.py` — AST node dataclasses used across passes.
* `l0_ast_printer.py` — human-readable dumps for debugging.
* `l0_name_resolver.py` — scope and symbol resolution.
* `l0_types.py` — primitive type representations and helpers.
* `l0_expr_types.py` — expression/type checking and inference helpers.
* `l0_diagnostics.py` — diagnostic objects and formatting utilities.
* `l0_paths.py` — module path handling and filesystem conventions.
* `l0_driver.py` / `l0_compilation.py` — top-level coordination of the compilation flow.
* `tests/` — pytest suites covering lexer, parser, and semantic passes.

## Data Flow and Invariants

```
Tokens:      immutable list of Token {kind, text, line, column}
AST:         dataclasses; no side effects; children own lists of nested nodes
Scopes:      resolver assigns symbol bindings; no implicit globals
Types:       explicit `TypeRef` and pointer/nullability fields; no ad-hoc strings
Diagnostics: collected with spans; passes must not raise uncaught exceptions for user errors
```

Key invariants enforced throughout:

1. **No implicit mutation across passes**: each stage receives and returns explicit structures; global state is avoided
   to keep the pipeline deterministic.
2. **No undefined behavior**: questionable constructs are rejected or represented as typed errors; panics are explicit.
3. **Source stability**: line/column tracking persists from lexer through diagnostics for precise error reporting.
4. **Total parsing**: the parser consumes all tokens or emits diagnostics; partial parses are treated as failures.
5. **Explicit nullability**: pointer types carry an explicit nullable bit (`?`), and the type checker enforces safe
   usage.

## Frontend architecture

The compiler frontend consists of:

### Lexer

* Tokenizes keywords, identifiers, literals, operators.
* Implemented per spec in project documents.

### Parser

* Handwritten recursive descent matching the grammar.
* Builds Python `dataclasses` AST:
* Modules, imports, functions, structs, enums.
* Statements and expressions with precedence.
* Type references (`TypeRef`).

### AST

* Program represented as clean immutable dataclasses.
* No semantic information stored in the AST.

## Semantic model

The semantic passes follow the order specified in [design_decisions.md](design_decisions.md).

### Name resolution

* Each module builds a `ModuleEnv`:
    * local symbols
    * imported symbols
    * ambiguity checks

* Diagnostics for:
    * duplicate names
    * conflicting imports
    * unknown identifiers

### Type resolution (SignatureResolver)

* Resolves all top-level `TypeRef`s to semantic types:
    * Builtins
    * Structs
    * Enums
    * Pointer and nullable types
    * Aliases (cycle-checked)

* Determines:
    * `FuncType`
    * struct field types
    * enum payload types

### Local scope resolution

* Builds lexical scopes per function:
    * parameters
    * block scopes
    * match-arm scopes

* Pattern variables are introduced into scopes.

### Expression type checker

* Computes type for every expression.
* Enforces:
    * return type matching
    * condition must be bool
    * incompatible assignments
    * illegal dereference (nullable or non-pointer)
    * unresolved names
    * etc.

Diagnostics are accumulated in a unified structure.

## C backend model

The C backend is described in detail in [c_backend_design.md](c_backend_design.md).

## Control Flow Example

The L0Driver object is the main entry point that coordinates passes for modules and their imports.

```
driver = L0Driver(search_paths)                   # setup with module search paths: project dirs, stdlib, etc.

analysis = driver.analyze(module.name)            # runs full frontend analysis pipeline for module and imports:
                                                  # runs driver.build_compilation_unit to get full import closure
                                                  # then runs NameResolver.resolve,
                                                  # SignatureResolver.resolve,
                                                  # LocalScopeResolver.resolve,
                                                  # and ExpressionTypeChecker.check

cu = driver.build_compilation_unit(module.name)   # recursive import closure, uses driver.load_module

module = driver.load_module(module.name)          # gets from cache or loads/parses the file
                                                  # runs Lexer.tokenize and Parser.parse_module


if analysis.diagnostics contain errors:
    report and abort
else:
    c_source = codegen(analysis)  # future stage
    write_output(c_source)
```

Each step returns structured results (modules, environments) plus diagnostics; the driver aggregates them for consistent
reporting.

## Future Directions

* **Richer diagnostics** with fix-it hints and multi-span notes.
* **Incremental builds**: cache lexer/parser results per module to speed up large projects.
