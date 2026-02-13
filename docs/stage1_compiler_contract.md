# L0 Stage 1 Compiler Contract

Version: 2026-02-13

This document is the compact Stage 1 contract and navigation index.

Canonical ownership:

- Architecture and pass flow: [architecture](architecture.md)
- C backend behavior and lowering details: [c_backend_design](c_backend_design.md)
- Language/runtime rationale and future evolution: [design_decisions](design_decisions.md)

## 1. Scope

Stage 1 is the Python compiler (`compiler/stage1_py`) that:

- parses and analyzes L0 modules,
- lowers analyzed programs to one C99 translation unit,
- optionally invokes a host C compiler.

The end-to-end flow is:

1. `Lexer.tokenize()`
2. `Parser.parse_module()`
3. `NameResolver.resolve()`
4. `SignatureResolver.resolve()`
5. `LocalScopeResolver.resolve()`
6. `ExpressionTypeChecker.check()`
7. `Backend.generate()`

## 2. Stable External Interfaces

### 2.1 CLI

Entry point: `compiler/stage1_py/l0c.py`

Primary commands:

- `run`
- `build`
- `gen` (alias: `codegen`)
- `check` (alias: `analyze`)
- `tok` (alias: `tokens`)
- `ast`
- `sym` (alias: `symbols`)
- `type` (alias: `types`)

Global options:

- `-v` / `--verbose` (counted)
- `-l` / `--log`
- `-P` / `--project-root`
- `-S` / `--sys-root`

Codegen/build options (where applicable):

- `-NLD` / `--no-line-directives`
- `-c` / `--c-compiler`
- `-C` / `--c-options`
- `-I` / `--runtime-include`
- `-L` / `--runtime-lib`
- `-o` / `--output`
- `--keep-c` (build)

Debug-dump options:

- `--all-modules` / `-a` for `tok|ast|sym|type`
- `--include-eof` / `-I` for `tok`

Exit behavior:

- analysis or C-compilation failures return non-zero from CLI commands,
- `run` returns the executed program's process exit code (`KeyboardInterrupt` -> `130`).

### 2.2 Source/module contract

- Source encoding: UTF-8; UTF-8 BOM is accepted and stripped by the driver.
- Module file extension: `.l0`.
- Module mapping: dotted name -> path segments (for example, `std.io` -> `std/io.l0`).
- Declared `module ...;` name must match the loaded module name.

### 2.3 Backend output contract

- Stage 1 emits a single C99 translation unit.
- Backend details are canonical in [c_backend_design](c_backend_design.md).

## 3. Current Core Data Shapes (Exact Names)

These names are externally relevant for contributors; details live in code.

### 3.1 Token model (`l0_lexer.py`)

`Token` fields:

- `kind`
- `text`
- `line`
- `column`

Token kind enum: `TokenKind`.
Important current names include:

- punctuation/operators: `SEMI`, `EQ`, `EQEQ`, `NE`, `MODULO`, `ARROW_FUNC`, `ARROW_MATCH`, `DOUBLE_COLON`
- logical operators: `ANDAND`, `OROR`, `BANG`
- reserved tokens: `AMP`, `PIPE`, `CARET`, `TILDE`, `LSHIFT`, `RSHIFT`, `FUTURE_EXTENSION`
- `CLEANUP` keyword token for `with ... cleanup`.

### 3.2 AST model (`l0_ast.py`)

AST nodes are Python `@dataclass` types (not frozen).

Important exact field names:

- `Module.decls`
- `Import.name`
- `Block.stmts`
- `IfStmt.cond`, `IfStmt.then_stmt`, `IfStmt.else_stmt`
- `ForStmt.init`, `ForStmt.cond`, `ForStmt.update`
- `WithStmt.cleanup_body`
- `CaseArm.literal`
- `VariantPattern.vars`
- `IndexExpr.array`
- `FieldAccessExpr.obj`
- `CastExpr.target_type`
- `TypeRef.module_path`, `TypeRef.name_qualifier`

## 4. Required Behavioral Guarantees

1. Driver import closure is explicit and cycle-checked (`ImportCycleError`).
2. User-facing failures are surfaced as diagnostics (lexer/parser exceptions are converted by driver).
3. Assignment remains statement-only in syntax.
4. Open import semantics remain default name-resolution behavior.
5. Nullability remains explicit in type syntax (`?`).
6. Backend emits deterministic single-unit C layout.

## 5. Known Stage 1 Constraints

1. No address-of (`&`) operator.
2. No generics/traits/macros.
3. Index syntax exists in AST/type-checking, but arrays/slices are not implemented, so index typing currently rejects
   non-supported targets.
4. Reserved operators/tokens are lexed for diagnostics and future expansion.

## 6. Documentation Routing

Use the narrowest canonical document for each question:

- Pass sequencing, module ownership, and frontend architecture:
  [architecture](architecture.md)
- Lowering policy, generated C layout, ARC/cleanup behavior, runtime calls:
  [c_backend_design](c_backend_design.md)
- Pointer/nullability model rationale, integer model rationale, stage-2 design direction:
  [design_decisions](design_decisions.md)
