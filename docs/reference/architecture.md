# L0 Compiler Architecture (Stage 1)

This is the canonical architecture document for the Stage 1 compiler.

Related canonical docs:

- Backend lowering and generated C details: [reference/c-backend-design.md](c-backend-design.md)
- Language/runtime rationale and future evolution: [reference/design-decisions.md](design-decisions.md)
- Compact contract/index: [specs/compiler/stage1-contract.md](../specs/compiler/stage1-contract.md)

## 1. High-Level Pipeline

```
Source (.l0)
  |
  v
Lexer.tokenize() -> Token stream
  |
  v
Parser.parse_module() -> AST
  |
  v
NameResolver.resolve() -> ModuleEnv per module
  |
  v
SignatureResolver.resolve() -> func/struct/enum/let type tables
  |
  v
LocalScopeResolver.resolve() -> FunctionEnv per function
  |
  v
ExpressionTypeChecker.check() -> expression types + semantic diagnostics
  |
  v
Backend.generate() -> single C99 translation unit
  |
  v
Host C compiler -> executable (run/build commands)
```

Pass coordination entry point: `L0Driver.analyze()` in `compiler/stage1_py/l0_driver.py`.

## 2. Pass Responsibilities

### 2.1 Lexer (`l0_lexer.py`)

- Converts UTF-8 source text to `Token` list.
- Tracks `line`/`column`.
- Handles keywords, literals, operators, punctuation, and comment skipping.
- Emits `LexerError` for lexical failures.

### 2.2 Parser (`l0_parser.py`)

- Recursive-descent parser producing `l0_ast.py` dataclass nodes.
- Parses module header, imports, declarations, statements, expressions, and type refs.
- Assignment is statement-only syntax (`AssignStmt`).
- Emits `ParseError` for parse failures.

### 2.3 Name Resolver (`l0_name_resolver.py`)

- Builds `ModuleEnv` maps for all modules in a `CompilationUnit`.
- Collects locals and opens imported symbols (open import semantics).
- Tracks ambiguous imports and emits resolver diagnostics.

### 2.4 Signature Resolver (`l0_signatures.py`)

- Resolves top-level type references.
- Populates:
    - `func_types`
    - `struct_infos`
    - `enum_infos`
    - `let_types`
- Detects alias cycles and value-type dependency cycles.

### 2.5 Local Scope Resolver (`l0_locals.py`)

- Builds lexical scope trees for non-extern functions.
- Produces `FunctionEnv` keyed by `(module_name, func_name)`.

### 2.6 Expression Type Checker (`l0_expr_types.py`)

- Infers/checks expression and statement types.
- Validates control-flow requirements (for example non-void return paths).
- Tracks expression types in `AnalysisResult.expr_types`.
- Records variable-resolution origin in `AnalysisResult.var_ref_resolution`.
- Appends semantic diagnostics.

### 2.7 Backend (`l0_backend.py`, `l0_c_emitter.py`)

- Consumes a typed `AnalysisResult` and emits C99.
- Canonical backend details are maintained only in [reference/c-backend-design.md](c-backend-design.md).

## 3. Core Data Flow

Primary aggregate: `AnalysisResult` (`l0_analysis.py`).

Important tables:

- `module_envs`
- `func_types`
- `struct_infos`
- `enum_infos`
- `func_envs`
- `let_types`
- `expr_types`
- `var_ref_resolution`
- `intrinsic_targets`
- `diagnostics`

Compilation closure container: `CompilationUnit` (`l0_compilation.py`), containing:

- `entry_module`
- `modules` (transitive import closure)

## 4. Invariants

1. Stages are explicit and ordered as in the pipeline above.
2. Import closure is explicit and cycle-checked in the driver.
3. Source locations are propagated for diagnostics.
4. Semantic errors accumulate as diagnostics; they do not crash the compiler.
5. Generated output target for Stage 1 is one C99 translation unit.

## 5. File/Module Layout

Main Stage 1 modules under `compiler/stage1_py/`:

- `l0_lexer.py`
- `l0_parser.py`
- `l0_ast.py`
- `l0_name_resolver.py`
- `l0_signatures.py`
- `l0_locals.py`
- `l0_expr_types.py`
- `l0_types.py`
- `l0_resolve.py`
- `l0_symbols.py`
- `l0_analysis.py`
- `l0_driver.py`
- `l0_backend.py`
- `l0_c_emitter.py`
- `l0_string_escape.py`
- `l0_diagnostics.py`
- `l0_context.py`
- `l0_paths.py`
- `l0_compilation.py`

## 6. Host/Toolchain Assumptions

- Source decoding is UTF-8 with optional BOM stripping.
- Module names use identifier segments separated by dots.
- `run` and `build` require an entry `main` function in the entry module.
- C target is C99 and host compiler is selected from CLI/env or PATH.
