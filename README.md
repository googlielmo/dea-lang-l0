# Dea/L<sub>0</sub>: A Small, Safe, C-Family Language

> _C-family syntax, with UB-free semantics and modern sum types + pattern matching._

**Dea/L<sub>0</sub>** or simply **L0** is a small systems language with a staged compiler.

It is the first step in growing a new, small and carefully designed systems programming language called **Dea**.

The current implementation **emits portable C (C99)** as a bootstrap backend; the backend is intended to evolve (e.g.,
with LLVM).

It is designed to eventually **compile its own compiler** (Stage 2: L0-in-L0).

This repository is primarily the **L0 language + toolchain**, and includes:

* The language definition and design documents (`docs/`).
* A **Stage 1 bootstrap compiler** (`l0c`) used to validate the language and generate C99.
* A small trusted **C kernel/runtime** used by generated programs.
* A Stage 2 L0-in-L0 compiler (in development).

Stage 1 is implemented in **Python** intentionally (fast iteration, simple reference implementation).

The Python Stage 1 compiler is located in the [`compiler/stage1_py`](compiler/stage1_py) directory.

Generated programs link a small trusted **C kernel/runtime** that encapsulates platform-specific behavior.
L0 aims to eliminate **undefined behavior**: operations are either well-defined, rejected with diagnostics,
or (where appropriate) trigger a defined runtime failure.

L0 is C-family in **surface syntax**:

* braces/semicolons, explicit types, pointers, and familiar operator precedence.

It is **not C** in key semantic ways:

* enums with payloads and statement-only **`match`**,
* explicit **optional types** (`T?`, with `null` as the empty value),
* a postfix **null propagation operator** (`expr?`) to propagate `null` from an expression of type `T?`,
* no undefined behavior at the language level.

The design goals and technical model are described in the project documents in the [docs](docs) folder.

## Example

```l0
module demo;

enum Expr {
    Int(value: int);
    Add(left: Expr*, right: Expr*);
    Comment(text: string);
}

func eval(e: Expr*) -> int {
    match (*e) {
        Int(value) => { return value; }
        Add(left, right) => { return eval(left) + eval(right); }
        _ => { return 0; } // wildcard pattern matches anything else
    }
}

func add_opt(a: int?, b: int?) -> int? {
    let x: int = a?;    // propagate `null` if `a` is null
    let y: int = b?;    // propagate `null` if `b` is null
    return (x + y) as int?;
}

func process_config(path: string) -> int {
    with (let f = open(path, "r") => close(f)) { // `with` ensures `f` is closed when the block exits
        case (f.read_config_line()) {
            "" => { printl_s("Empty file"); return -1; }
            "enable_feature" => {
                printl_s("Feature enabled");
                return 1;
            }
            else {
                printl_ss("Unknown config:", line);
                return 0;
            }
        }
    }
}
```

## Table of contents

1. [Getting Started](#getting-started)
2. [Motivation](#motivation)
3. [Language overview](#language-overview)
4. [Grammar](#grammar)
5. [Compiler implementation architecture](#compiler-implementation-architecture)
6. [CLI](#cli)
7. [Project status](#project-status)
8. [License](#license)
9. [Author](#author)

## Getting Started

### Prerequisites

- Python 3.14 or later
- A C99-compatible compiler (gcc or clang)
- Git (for cloning the repository)

### Assumptions and Constraints

- Module name components must be valid identifiers (`[A-Za-z_][A-Za-z0-9_]*`), so names like `app.main` are valid while
  `app.my-module` and `9main` are not.
- Filesystem module resolution follows host behavior (case-sensitive hosts require exact case matches).
- Source files are decoded as UTF-8; a UTF-8 BOM is accepted and ignored.
- `run` and `build` require the entry module to define `main`.
- Preferred `main` return types are `int`, `void`, or `bool` (`bool` maps to C exit code `0`/`1`).
- If `--runtime-lib` or `L0_RUNTIME_LIB` is set, an `l0runtime` library artifact must exist in that directory.

### Setup

#### 1. Clone the repository:

   ```shell
   git clone https://github.com/googlielmo/dea-lang-l0.git
   cd dea-lang-l0
   ```

#### 2. Set environment variables (optional):

The `l0c` wrapper script sets sensible defaults, but you can override them with these variables:

   ```shell
   export L0_HOME=/path/to/l0/compiler/stage1_py
   
   # Optional: override system and runtime include paths (defaults are relative to L0_HOME)
   export L0_SYSTEM=/path/to/l0/compiler/stage1_py/l0/stdlib
   export L0_RUNTIME_INCLUDE=/path/to/l0/compiler/stage1_py/runtime
   ```

If not set, defaults are relative to the repository root:

- `L0_HOME` → `compiler/stage1_py`
- `L0_SYSTEM` → `$L0_HOME/l0/stdlib`
- `L0_RUNTIME_INCLUDE` → `$L0_HOME/runtime`

#### 3. Verify installation:

   ```shell
   ./l0c --help
   ```

### First Steps

#### 1. Create a simple L0 program:

Create a file named `hello.l0` with the following content:

   ```l0
   module hello;

   import std.io;

   func main() -> int {
       println("Hello, L0!");
       return 0;
   }
   ```

#### 2. Run it:

   ```shell
   ./l0c run hello.l0
   ```

This compiles and executes the program in one step.

You can just use the module name (without `.l0`) and the compiler will use the corresponding file:

   ```shell
   ./l0c run hello
   ```

#### 3. Build an executable:

   ```shell
   ./l0c build hello.l0 -o hello
   ./hello
   ```

#### 4. Check for errors without building:

   ```shell
   ./l0c check hello.l0
   ```

### Project Structure

When working on L0 projects, use `--project-root` (or `-P`) to specify your source directories:

```shell
./l0c run -P ./src -P ./lib main
```

The compiler searches for modules in:

1. System roots (standard library, specified via `--sys-root`/`-S` or `L0_SYSTEM`)
2. Project roots (specified via `--project-root`/`-P` or working directory)

### Examples

Explore the `examples/` directory for sample L0 programs demonstrating various language features.

## Motivation

The project aims to build a **bootstrap-friendly**, **well-specified**, **simple**, and **safe** systems language.

In other words, it's "the minimum viable systems language for writing a self-hosted compiler".

Its first self-hosted compiler is being written in L0 itself (Stage 2).
To support this, Stage 1 provides:

* A complete, deterministic parser.
* A precise semantic model.
* A small C kernel, isolating all platform-dependent behavior.
* Predictable, explicit control over types, pointers, and runtime.

## Language overview

L0's surface syntax is C-like:

```l0
module demo;

import std.io;

struct Token { kind: int; value: string; }

func add(a: int, b: int) -> int {
    return a + b;
}
```

Key properties:

* **No UB**: operations are defined or errors.
* **Modules**: one file = one module (dotted names supported).
* **Qualified names**: disambiguate imported symbols with `module.path::Symbol` in types, expressions, and patterns.
* **Types**: builtins, structs, enums with payloads, type aliases.
* **Automatically reference counted string values**: `string` is a first-class type.
* **Pointers**: `T*`, nullable `T*?`; no address-of operator `&` in early stages.
* **Auto-dereference**: Field access `ptr.field` automatically dereferences pointers.
* **Pattern matching**: statement-only, simple variant patterns.
* **Expressions**: C-like precedence, no assignment-as-expression.
* **Statements**: `let`, assignment, if/else, while, return, match.
* **Extern functions** interface with the C kernel.
* **Introspection**: `sizeof(T)` available at compile time.
* **Null Safety**:
    * Postfix **try operator** `?` for short-circuiting null propagation (optional chaining).
    * Checked casts: `T? as T` (unwrap with panic if null) and `T as T?` (safe wrap).

## Grammar

The authoritative Stage-1 grammar is in [reference/grammar/l0.md](docs/reference/grammar/l0.md).

Pointer and nullable types look like this:

```
T
T*
T**
T?
T*?
```

Expressions include unary (`-`, `!`, `*`, `~`), binary arithmetic, logical, comparisons, bitwise, indexing,
calls, field access, `as` casts, and the **try operator** `?`.

## Compiler implementation architecture

See [reference/architecture.md](docs/reference/architecture.md) for an overview of the Python L0 stage-1 compiler
implementation architecture and data flow.

See also [reference/design-decisions.md](docs/reference/design-decisions.md) for additional context.

See [specs/compiler/stage1-contract.md](docs/specs/compiler/stage1-contract.md) for the compact Stage 1 contract/index.

## CLI

Provided by the `l0c` executable (Python):

```shell
./l0c --help
```

Output:

```
usage: l0c [-h] [--verbose] [--project-root PROJECT_ROOT] [--sys-root SYS_ROOT] {run,build,gen,codegen,check,analyze,tok,tokens,ast,sym,symbols,type,types} ...

L0 compiler (Stage 1)

positional arguments:
  {run,build,gen,codegen,check,analyze,tok,tokens,ast,sym,symbols,type,types}
                        Command to run
    run                 Build and run a module
    build               Build an executable
    gen (codegen)       Generate C code
    check (analyze)     Parse and analyze a module
    tok (tokens)        Dump lexer tokens
    ast                 Pretty-print the parsed AST
    sym (symbols)       Dump module-level symbols
    type (types)        Dump resolved types

options:
  -h, --help            show this help message and exit
  --verbose, -v
  --project-root, -P PROJECT_ROOT
                        Add a project source root (can be passed multiple times)
  --sys-root, -S SYS_ROOT
                        Add a system/stdlib source root (can be passed multiple times; default: $L0_SYSTEM as colon-separated paths)
```

Trace options for generated C/runtime debugging:

```shell
./l0c gen --trace-arc app.main
./l0c run --trace-memory app.main
./l0c run --trace-arc --trace-memory app.main
```

Trace logs are written to `stderr`. See [specs/runtime/trace.md](docs/specs/runtime/trace.md) for the full contract.

Example usage:

```shell
./l0c -P examples run hamurabi
```

Output:

```
                                HAMURABI
               CREATIVE COMPUTING  MORRISTOWN, NEW JERSEY
                      WITH THANKS TO  DAVID H. AHL



TRY YOUR HAND AT GOVERNING ANCIENT SUMERIA
FOR A TEN-YEAR TERM OF OFFICE.



Hamurabi: I beg to report to you, 
In year 0, 0 people starved, 5 came to the city.
Population is now 95
The city now owns 1000 acres.
You harvested 3 bushels per acre.
Rats ate 200 bushels.
You now have 2800 bushels in store.

Land is trading at 23 bushels per acre.
How many acres do you wish to buy?
```

Enjoy the game! Type your inputs as prompted and see how well you can govern ancient Sumeria.

## Project status

The authoritative status file is [reference/project-status.md](docs/reference/project-status.md).

## License

This project is dual-licensed under the following terms:

- MIT License (see [LICENSE-MIT](LICENSE-MIT))
- Apache License 2.0 (see [LICENSE-APACHE](LICENSE-APACHE))

You may use this software under either license at your option.

## Author

Created and maintained by `gwz` ([@googlielmo](https://github.com/googlielmo)).
