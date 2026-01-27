# L0 Project Status

Here’s where the project stands and what’s immediately next.

## Current status

This is a summary of the current implementation of the L0 compiler, focusing on the key components and features that
have been completed so far.

## Frontend core

### Lexer

* Handles all keywords, punctuation, operators, `->` vs `=>`, `_` as dedicated token.
* Exposed as `Lexer(text, filename).tokenize()`.

### Parser + AST

* Hand-written recursive descent parser.
* Supports:
    * `module` + `import` (dotted names).
    * `struct`, `enum`, `type` alias.
    * `func` and `extern func` with `->`.
    * Statements: `let`, `if/else`, `while`, `return`, `match` (statement-only).
    * Patterns: `Variant(...)`, `_`.
    * Expressions with full precedence rules:
      unary ops, binary ops, calls, field access, `as` casts, postfix try `?`.
* Produces a clean Python AST via `dataclasses`, with `TypeRef` in all type positions.

> Note: top-level `const` / top-level `let` are part of the language plan (see `docs/design_decisions.md`), and should
> be considered **in-progress** unless explicitly listed as implemented below.

## Driver + module loading

### SourceSearchPaths

* Maintains:
    * System roots.
    * Project roots.
* System roots take priority.
* `resolve("a.b")` → `Path("a/b.l0")` with system-first search order.

### L0Driver

* `load_module(name)`:
    * Resolve module path.
    * Parse.
    * Recursively load imported modules.
    * Caches modules in `module_cache`.
* Import cycle detection using `_loading` set → `ImportCycleError`.
* Module name mismatch (`file declares X; loaded as Y`) → `ValueError`.

### CompilationUnit

* `build_compilation_unit(entry_module)`:
    * Collects the full transitive import graph.
    * Yields a closed set of modules.
    * Hides unrelated cached modules.

## Diagnostics

### Diagnostic dataclass

* Fields:
    * `kind`: `"error"` or `"warning"`.
    * `message`.
    * Optional `file`, `line`, `column`.
* Method:
    * `format()` for CLI output.
    * Incorporating file/line/column from AST spans.

## Semantic layer (names + types)

### Module-level symbol tables

* `SymbolKind`: `FUNC`, `STRUCT`, `ENUM`, `ENUM_VARIANT`, `TYPE_ALIAS`, `MODULE`.
* `Symbol`: name, kind, defining module, AST node, optional `type`.
* `ModuleEnv`:
    * `locals` — symbols defined in this module.
    * `imported` — symbols opened from imports.
    * `all` — merged view (locals ∪ imported minus ambiguous).
    * Diagnostics emitted for:
    * Duplicate top-level definitions.
        * Conflicting imports.
        * Ambiguous names exported from multiple modules.

### Import semantics

* `import foo;` makes all symbols defined in module `foo` visible unqualified.
* No aliases yet (`import foo as bar` not supported).
* If two imported modules export the same name, that name becomes ambiguous → error.

### Semantic types (`l0_types`)

* Builtins: `int`, `bool`, `string`, `void`.
* `StructType(module, name)`.
* `EnumType(module, name)`.
* `PointerType(inner)`.
* `NullableType(inner)`.
* `FuncType(params, result)`.
* Builtins accessed via `get_builtin_type(name)`.

### Signature resolution (`SignatureResolver`)

* Input:
    * `CompilationUnit`
    * `module_envs`
* Resolves all top-level `TypeRef`s:
    * Function params and return types → `FuncType`.
    * Struct field types.
    * Enum variant payload types.
    * Type alias chains (with cycle detection).
* Attaches:
    * `Symbol.type` for `FUNC`, `STRUCT`, `ENUM`, `TYPE_ALIAS`, `ENUM_VARIANT`.
* Side tables:
    * `func_types[(module, func)]`.
    * `struct_infos[(module, struct)]`.
    * `enum_infos[(module, enum)]`.
* Diagnostics for:
    * Unknown type names.
    * Non-type symbols used as types.
    * Alias cycles.

## Local scopes

### LocalScopeResolver

* Builds lexical scopes for all non-extern functions.
* Produces a `FunctionEnv`:
    * Module name.
    * `FuncDecl`.
    * Root lexical scope.
* Scope rules:
    * Function parameters live in the root scope.
    * `let` introduces a local in the current scope.
    * Blocks (`{…}` in if/else/while/match arms) introduce new scopes.
    * Patterns introduce `PATTERN_VAR`s.
    * `_` never binds.
    * **Duplicate variable declarations** in the same scope are detected and reported as errors.
* Provides:
    * `get_block_scope(block)`.
    * `get_match_arm_scope(arm)`.

## Expression type checking

### ExpressionTypeChecker

The newest semantic pass, integrated directly after `LocalScopeResolver`.

* Traverses all non-extern function bodies.
* Maintains lexical scopes for:
    * Parameters.
    * `let` variables.
* Populates:
    * `AnalysisResult.expr_types[id(expr)]` with semantic types.
* Emits diagnostics for:
    * Wrong argument counts.
    * Wrong operand types.
    * Illegal dereference.
    * Invalid conditions.
    * Mismatched return types.
    * Mismatched `let` initializers.

#### Implemented rules

**1. Literals & VarRef**

* `IntLiteral → int`
* `BoolLiteral → bool`
* `StringLiteral → string`
* Variable lookup across:
    * Local scopes.
    * Function-valued symbols from the module.

**2. Unary operators**

| Operator | Operand Type | Result Type |
|----------|--------------|-------------|
| `-`      | int          | int         |
| `!`      | bool         | bool        |
| `*`      | T*           | T           |

* Nullable pointers (`T*?`) cannot be dereferenced (diagnostic emitted).

**3. Binary operators**

* Arithmetic (+ - * /) on `int → int`.
* Comparisons (< <= > >=) on `int → bool`.
* Equality (== !=) on same-type builtins (`int`, `bool`, `string`) → `bool`.
    * Unsupported types (structs/enums) produce a diagnostic.
* Logical operators (&& ||) on `bool → bool`.

**4. Calls**

* Only functions can be called.
* Checks:
    * Arity.
    * Parameter-by-parameter type compatibility.
* Returns `FuncType.result`.

**5. Indexing & field access**

* `IndexExpr` is reserved for future safe array access; currently always emits a diagnostic.
* `FieldAccessExpr` resolves struct field types.
    * Supports **automatic pointer dereferencing**: `ptr.field` is treated as `(*ptr).field`.
    * Rejects nullable structs/pointers without explicit handling, missing fields, or invalid bases.

**6. Casts & parens**

* `(expr)` transparently propagates the inner type.
* `expr as T` resolves `T` with full alias/nullable/pointer handling; emits diagnostics for unknown or non-type targets.

**7. Statement rules**

* `return`: value type must match function result type.
* `if` / `while`: condition must be `bool`.
* `let name: T = expr;`
    * Both sides typed.
    * Types must match (full pointer/nullable/alias resolution).
    * Binds `name` in the current scope.
    * Simple type inference is implemented: if `T` is omitted (as in `let name = expr;`), infers from `expr` type.

**8. TypeRef resolution inside expressions**

Uses the exact same logic as `SignatureResolver`:

* Builtins.
* Struct / Enum names.
* Type aliases (via `sym.type`).
* Pointer depth.
* Nullable suffix.
* Diagnostics for:
    * Unknown type names.
    * Non-type symbols used as types.

**9. Nullable dereference semantics**

* Dereferencing `ptr: T*?` is an error (diagnostic emitted). The canonical way to use nullable pointers is via explicit null checks:
  ```l0
  let ptr: T*? = ...;
  if ptr != null {
      let value: T = *ptr as T;  // OK
  } else {
      // handle null case
  }
  ```
* TBD: allow `*ptr` when `ptr: T*?` under explicit null-check patterns. (Currently always an error.)
* TBD: allow safe field access `ptr.field` when `ptr: T*?` under explicit null-check patterns. (Currently always an
  error.)

**10. Match typing**

* Scrutinee must be enum type.
* Patterns must match enum variants.
* Pattern variable typing.
* Exhaustiveness checking and unreachable/overlapping arm detection.

## Analysis pipeline

### AnalysisResult (`l0_analysis`)

Contains:

* `cu`: CompilationUnit or `None`.
* `module_envs`.
* `func_types`, `struct_infos`, `enum_infos`.
* `func_envs`.
* `expr_types` — expression types from `ExpressionTypeChecker`.
* `diagnostics`.

`has_errors()` returns `True` if any error diagnostics exist.

### L0Driver.analyze(entry_module)

1. `build_compilation_unit`
2. `NameResolver`
3. `SignatureResolver`
4. `LocalScopeResolver`
5. `ExpressionTypeChecker`
6. Merge diagnostics → `AnalysisResult`

## C codegen backend

### Implemented (Stage 1)

The C backend is implemented and can emit a single, portable C99 translation unit for the full compilation unit.

* Emits:
    * Fixed-width typedef layer (`l0_int`, `l0_bool`, `l0_string`, etc.).
    * Mangled names for non-extern L0 symbols.
    * Structs and enums (tagged unions).
    * Forward declarations + definitions.
    * A C `main()` wrapper that calls the mangled L0 entrypoint and normalizes the return type (`void`/`int`).

* Lowers:
    * `match` → `switch` on tag with per-arm bindings.
    * Calls → mangled C function names (externs are not mangled).
    * String literals → C-escaped strings.
    * Nullable → currently represented with C pointers/null checks.

* Runtime:
    * **Automatic String Reference Counting**: Appropriate calls to `rt_string_retain` / `rt_string_release` are
      inserted in the generated code to manage string lifespan and prevent double-frees/leaks.

### Known limitations (backend)

* Multi-module C output (headers/objects) is not implemented: everything is emitted into one C file.
* Nullable non-pointer array representation is incomplete/under-specified.
* Rich debug info (`#line`) is not emitted yet.

## CLI (`l0c`)

Implements developer tooling:

### Commands

* `run`:
    * Full analysis + C codegen + compilation + execution.
    * Temporary executable file.

* `build`:
    * Full analysis + C codegen + compilation.
    * Emits executable file.

* `gen`:
    * Full analysis + C codegen.
    * Emits `.c` file.

* `check`:
    * Runs full analysis.
    * Prints diagnostics.

* `ast`:
    * Pretty-prints AST of entry module (or all modules with `--all-modules`).

* `tok`:
    * Dumps tokens.
    * Optional `--include-eof`.

* `sym`:
    * Dumps module-level symbols.

* `type`:
    * Dumps resolved types for functions, structs, enums.

### Common options

* `--project-root`, `--sys-root` (multiple allowed).
* `--verbose` for extra logging.
* Entry module path (positional).
* `--all-modules` for `tok`, `ast`, `sym`, `type` (useful for debugging).
* Proper exit codes.

## Recent updates

* **Licensing**: Project is dual-licensed under MIT and Apache 2.0. Source files include SPDX license
  identifiers.
* **Stage 2 Compiler** (L0-in-L0): Initial work merged. See [Stage 2 Compiler](#stage-2-compiler-l0-in-l0) below.
* **Standard Library**: Added `std.rand`, `std.string`, `std.system`; extended `std.io` (`read_line`, `read_char`);
  refactored printing (`print_s`, `printl_i`).
* **Memory Management**: Implemented reference counting for heap-allocated strings.
* **Semantics**:
    * Added automatic pointer dereferencing for field access (`ptr.field`).
    * Implemented duplicate variable declaration detection.
* **Grammar**: Relaxed `if` statements to allow any statement in branches (not just blocks).
* **Structs**: Added support for empty structs and enums (Unit types).
* **Backend**: Enhanced name mangling to handle names starting with `_`.

## Stage 2 Compiler (L0-in-L0)

The self-hosted Stage 2 compiler is under active development in `compiler/stage2_l0/`.

### Implemented

* **Token definitions** (`tokens.l0`):
    * `TokenType` enum covering all L0 tokens (keywords, operators, punctuation, literals).
    * `Token` struct with position tracking (index, line, column).
    * Keyword-to-token mapping.
    * `TokenVector` for collecting lexer output.

* **Lexer** (`lexer.l0`):
    * `LexerState` struct tracking source position.
    * Whitespace and comment (single-line `//`, multi-line `/* */`) skipping.
    * Identifier and keyword tokenization.
    * Error state handling with error codes and messages.

* **Utility libraries** (`util/`):
    * `vector.l0` — Generic dynamic array using `VectorBase`.
    * `array.l0` — Fixed-size array utilities.
    * `map.l0` — Hash map implementation.
    * `string.l0` — String manipulation helpers.

* **Test suite** (`tests/`):
    * Unit tests for vector, array, map, string utilities.
    * Lexer tests.

### In progress

* Complete lexer (number literals, string literals, operators, punctuation).
* Parser and AST definitions.
* Semantic passes (name resolution, type checking).

## Immediate next steps

* Nullable semantics:
    * Document the chosen representation for `T?` (non-pointer) vs `T*?`.
* Debug info:
    * Emit `#line` directives for better C-level errors and source mapping.

## Upcoming features

### Top-level `const` / `let`

* Parser + AST support (top-level decl forms).
* Constant evaluation for `const` initializers (restricted constant expressions).
* Codegen for globals with defined initialization constraints.
