# L0 Runtime, Integer Model, and C Backend Design

## 1. Scope and Goals

This document records the design decisions made for:

* The **L0 runtime and kernel** (C + L0 split).
* The **I/O model** for the compiler and early tooling.
* The **integer and size model** of L0 and its mapping to C.
* The **pointer model** (notably: no `&` in Stage 1/2).
* The **C backend** and how L0 abstracts away from specific C compilers.

Primary constraints:

* L0 is a **small, UB-free, C-like language** that compiles to C.
* It should be practical to write a **Stage 2 compiler in L0** itself.
* The generated C should be **portable across many C compilers**, including TinyCC.

## 2. High-Level Architecture

We distinguish three layers:

1. **L0 Language and Compiler**

    * Frontend (lexer, parser, resolver, typechecker).
    * Backend targeting C.
    * Entirely written in L0 from Stage 2 onward.

2. **L0 Runtime (R0)**

    * Data structures and utilities written in L0:

        * Specialized vectors (e.g. `TokenVec`).
        * String builders and pretty printers.
        * Higher-level helpers (e.g. diagnostic formatting).

    * Compiled to C by the L0 compiler.

3. **C Kernel (K0)**

    * Small, trusted C code providing:

        * Allocation and deallocation.
        * Whole-file I/O.
        * Basic printing and panicking.
        * Optional utilities like string interning.

    * This is the only place that talks directly to the C/OS environment,
      uses `malloc`, `fopen`, `size_t`, etc.

Design principle:

> All **UB and platform quirks** are quarantined inside the C kernel.
> L0 and the L0 runtime are specified and implemented as **UB-free**.

## 3. Pointer and `&` Design

### 3.1. Current Pointer Model

Stage 1/2 L0 has:

* Types like `T*` (pointers).
* Dereference `*expr`.
* Field access `obj.field`, `ptr.field` via sugar or IR lowering.

Pointers are obtained from:

* Runtime/kernel functions (e.g. `rt_alloc`).
* Other L0 functions that already hold them.
* Fields inside heap-allocated structs.

L0 code treats pointers as **opaque handles to heap-allocated storage**.
No pointer arithmetic is exposed in Stage 1; dereference is the only operation.

### 3.2. No `&` Operator (Address-of)

We **do not** introduce `&` in Stage 1/2.

Consequences:

* No taking addresses of locals/stack variables (no `&x`).
* No taking addresses of stack-allocated values or fields.
* All pointer values ultimately originate from the kernel or from L0 data structures that themselves store heap
  pointers.

This has two important effects:

1. It keeps the lifetime model simple:

    * Pointers are always assumed to refer to heap allocations managed via `rt_alloc`/`rt_free` (or equivalents).
    * There is no language-level concept of a pointer to a dead stack variable.

2. It keeps all lifetime/UB concerns inside the kernel:

    * If the kernel mismanages memory, that’s a kernel bug, not L0 UB.
    * L0 semantics remain well-defined.

This model is sufficient to implement:

* The compiler’s internal data structures.
* Containers that store elements in heap arrays.
* Pretty-printers and other utilities.

If we later add `&`, it will be under a more constrained, non-UB semantics; for now we stay without it.

### 3.3. No Indexing into Pointers

We **do not** allow pointer arithmetic or indexing into raw pointers (e.g. `ptr[i]`).

Indexing will be allowed only on buffers or slices **to be defined in later stages** (e.g. `arr[i]` where `arr` is a
fixed-size array or a heap-allocated buffer type).

Safe indexing types (e.g. `buffer<T>`, `slice<T>`) will encapsulate length and bounds checks.

## 4. Null Handling, Casting, and Introspection

To support robust compiler writing and optional value handling, L0 incorporates the following features:

### 4.1. `sizeof` operator

Syntax: `sizeof(T)`

* **Compile-time** operator that returns the size in bytes (as an `int`) of type `T`.
* Essential for interfacing with `rt_alloc` and implementing container growth.
* Since L0 has fixed-width `int` (32-bit), `sizeof` returns a 32-bit integer.

### Optional or Nullable Types

An optional type can hold either a valid value or indicate absence (`null`).
It's used for optional values, e.g., AST nodes that may be missing.

**Rules**:

* An optional type `T?` represents either a value of type `T` or `null`
* It is internally represented as structures or pointers, depending on `T`.
* A nullable non-pointer type `T?` is implemented as a struct containing a validity flag and the value.
* A nullable pointer type `T*?` maps directly to a C pointer, with `NULL` representing absence.
* Dereferencing a `T*?` requires checking for `null` first and panics if dereferenced when `null`.
* Wrapping and unwrapping between `T` and `T?` is done via checked casts with `as` and the try operator `?`.

### 4.2. Checked Casts (`as`)

The `as` operator is extended to handle nullable types explicitly:

* **Unwrap (Checked)**: `T? as T`

    * If the value is not null, it returns the inner value of type `T`.
    * If the value is null, the program **panics** (defined runtime abort).
    * This replaces the need for "unsafe" dereferences; L0 dereferences are always safe or panic.

* **Wrap (Promotion)**: `T as T?`

    * Implicit promotion is often allowed, but `as` can be used to explicitly cast a non-nullable value to a nullable
      container (e.g., `Some(v)`).

### 4.3. Try Operator (`?`)

Syntax: `expr?` (postfix)

* **Behavior**: Short-circuiting null propagation (Optional Chaining).
* If `expr` evaluates to `null`, the evaluation of the current chain stops, and the result is `null`.
* If `expr` is not null, the value is unwrapped/accessed.
* **Return type**: The result of an expression involving `?` is always a nullable type.

Example:

```
let x: MyStruct? = ...;
let y: int? = x?.field; // If x is null, y is null.
```

This avoids verbose `if` or `match` statements for simple property access on potentially missing values.

## 5. I/O Model for Early Stages

### 5.1. Requirements

For the Stage 2 compiler and basic tooling, L0 only needs:

1. To **read** source files:

    * Main module and imported modules.

2. To **write** generated C files:

    * One per module or a single output file.

3. To **print diagnostics**:

    * Human-readable messages to stderr (and sometimes stdout).

Streaming, seeking, and partial reads can be deferred.

### 5.2. Kernel I/O API

The kernel provides **whole-file** operations and simple printing:

```l0
extern func rt_read_file_all(path: string) -> string?;
// Returns entire file contents, or null on error.

extern func rt_write_file_all(path: string, data: string) -> bool;
// Returns true on success, false on error.

extern func rt_print_stdout(s: string) -> void;
extern func rt_print_stderr(s: string) -> void;
```

Notes:

* This is sufficient for a compiler that processes normal-sized source files and outputs one or a handful of C files.
* No `open/close`, no explicit file descriptors at the L0 level.
* If future stages need streaming or very large files, we can add a separate file-handle API later without changing
  existing compiler logic.

## 6. Containers and Pretty Printer in L0

### 6.1. Specialized Containers (No Generics Yet)

Given Stage 1 has **no generics**, we adopt specialized containers with a common pattern. Example:

```l0
struct TokenVec {
    data: Token*;  // pointer to contiguous array
    len: int;
    cap: int;
}
```

Typical API:

```l0
func token_vec_init(v: TokenVec*) -> void;
func token_vec_push(v: TokenVec*, value: Token) -> void;
func token_vec_reserve(v: TokenVec*, new_cap: int) -> void;
```

Analogous types:

* `IntVec`, `NodeVec`, `StringVec`, etc.

Implementation:

* Managed via `rt_alloc` / `rt_realloc` inside the kernel.
* Element size is known by convention or small helper functions.
* All container resizing and lifetime rules are explicit and simple.

### 6.2. Maps and Symbol Tables

For symbol tables and similar:

* Prefer a **string interner** in the kernel (or early runtime), mapping `string → int id`.
* Maps then become `int → value` (e.g. `id → symbol index`), which can be implemented as:

    * Thin wrappers around a C hash table in the kernel, or
    * Later, as open-addressing maps in L0 using `IntVec`.

This keeps hashing and resizing complexity out of the early L0 runtime.

### 6.3. String Builder and Printer

For C codegen and diagnostics, we use a simple **StringBuilder** and **Printer** in L0.

Example:

```l0
struct StringBuilder {
    data: byte*;
    len: int;
    cap: int;
}

func sb_init(sb: StringBuilder*) -> void;
func sb_push_char(sb: StringBuilder*, ch: int) -> void;
func sb_push_str(sb: StringBuilder*, s: string) -> void;
func sb_to_string(sb: StringBuilder*) -> string;
```

On top of that:

```l0
struct Printer {
    sb: StringBuilder*;
    indent: int;
    at_line_start: bool;
}

func printer_init(p: Printer*, sb: StringBuilder*) -> void;
func printer_indent(p: Printer*) -> void;
func printer_dedent(p: Printer*) -> void;
func printer_newline(p: Printer*) -> void;
func printer_write(p: Printer*, s: string) -> void;
```

C codegen and diagnostic printing use `Printer` to manage indentation and layout.

This keeps generated C and diagnostics readable and consistent.

## 7. Integer Model and Mapping to C

### 7.1. L0 Integer Semantics

L0 **does not** simply inherit whatever integer sizes C happens to use.

Instead, L0 specifies its own model:

* Stage 1:

    * `int` = **exactly 32-bit** signed, two’s complement.
    * `byte` = 8-bit unsigned (0..255).
    * `bool` = logical type with values `true` / `false`, represented as 0/1.

* Later extensions:

    * `uint`, `long`, `usize`, etc., each with defined bit-widths. (Names tentative.)

This makes L0 programs’ behavior independent of:

* Whether the C implementation uses LP64, LLP64, ILP32, etc.

### 7.2. C Backend Mapping

Generated C always uses an internal, fixed-width layer, e.g.:

```c
#include <stdint.h>
#include <stddef.h>

typedef int32_t  l0_int;
typedef uint8_t  l0_byte;
typedef uint8_t  l0_bool;
/* Later: typedef uint32_t  l0_uint; etc. */
```

Mapping:

* L0 `int` → `l0_int` (`int32_t`).
* L0 `byte` → `l0_byte` (`uint8_t`).
* L0 `bool` → `l0_bool` (`uint8_t` or `_Bool`).

The backend never emits plain `int`/`long` with semantic significance; it uses these typedefs instead.

### 7.3. `size_t` and Large Sizes

`size_t` is treated as a **kernel implementation detail only**:

* It appears **only inside the C kernel**, not in L0.

* At the L0 boundary we use:

  ```l0
  extern func rt_alloc(bytes: int) -> void*?;
  ```

* Kernel implementation:

  ```c
  void *rt_alloc(l0_int bytes) {
      if (bytes < 0) rt_panic("negative allocation size");
      size_t sz = (size_t)bytes;
      /* optionally check against SIZE_MAX, etc. */
      void *p = malloc(sz);
      ...
  }
  ```

If sizes exceed what fits into `l0_int` (e.g. > 2^31−1), the kernel may:

* Reject them (panic), or
* Return an error (`null`) if defined that way.

This is acceptable for a bootstrap compiler, and it keeps `size_t` from leaking into the L0 type system.

Later, when `usize` is introduced in L0, we can map:

* `usize` ↔ `size_t` or `uintptr_t` in a controlled way, still without exposing raw C types to L0 user code.

## 8. C Backend Portability and Toolchain Abstraction

### 8.1. Target C Subset

L0’s backend targets a **conservative, strictly-conforming C subset**:

* Baseline: **C99** (with a view to being compatible with TinyCC and other compilers).

* No reliance on:

    * GCC-only extensions (`__attribute__`, statement expressions, nested functions).
    * MSVC-only extensions (`__declspec`, nonstandard keywords).
    * Non-portable assumptions about `int` / `long` sizes.

The generated C should be “boring”:

* Use only `struct`, `enum`, `if`, `while`, `for`, `switch`, basic expressions.
* Use fixed-width typedefs (`l0_int`, etc.) from `<stdint.h>`.

### 8.2. Toolchain Configuration

The L0 compiler treats the C compiler as an **external toolchain object**, configured by:

* C compiler executable (`gcc`, `clang`, `tcc`, `cl`, ...).
* Standard version (`-std=c99`, etc.).
* Base flags (`-Wall -Wextra`, platform-specific flags).
* Include paths for the kernel headers.
* Linker options for the kernel/library.

All calls to the C compiler go through this minimal abstraction.

Porting to a new C compiler is then primarily a matter of:

* Adding a new toolchain configuration.
* Possibly adjusting the kernel’s C code for platform-specific quirks.

### 8.3. Kernel as the Only Non-portable C

Any platform- or compiler-specific C code is strictly confined to the kernel:

* Conditional compilation (`#ifdef _WIN32`, etc.).
* Use of nonstandard attributes or pragmas, if needed.
* Interaction with OS-specific APIs.

The generated C from the L0 compiler remains free of such details, and only includes:

* `"l0_runtime.h"` (kernel API).
* C standard headers (`<stdint.h>`, `<stddef.h>`, `<stdbool.h>`).

## 9. Future Evolution

Planned directions:

1. **Runtime in L0 grows**:

    * More containers, more utilities, eventually most of the “runtime” logic.

2. **Kernel shrinks**:

    * Ideally down to a tiny layer that just wraps allocator, minimal I/O, and platform-specific syscalls.

3. **Language grows carefully**:

    * Add fixed-width signed and unsigned integer types (`short`, `uint`, `long`, `usize`, etc.) with defined semantics.
    * Possibly add a constrained `&` later, with non-UB semantics, if needed.

4. **Backend remains conservative**:

    * Keep the strict C subset as the stable, portable target.
    * Optionally add a second, more aggressive backend later (e.g. with attributes), but keep the strict one canonical.

# Addendum: Planned additions for Stage 2 (L0-in-L0)

## 1. Bitwise operators for `int`

### 1.1. Operators and scope

We add the following **bitwise operators**, defined only for L0 `int` (32-bit signed) for now:

* Unary:

    * `~x` (bitwise NOT)

* Binary:

    * `x & y` (bitwise AND)

    * `x | y` (bitwise OR)

    * `x ^ y` (bitwise XOR)

    * `x << y` (left shift)

    * `x >> y` (right shift, arithmetic)

These are value-level operators; they do not interact with booleans or pointers.

There is no implicit “truthiness” for them; && and || remain the only logical operators.

### 1.2. Grammar / precedence

We extend the expression precedence ladder as follows (lowest → highest):

1. `||`

2. `&&`

3. `|` (bitwise OR)

4. `^` (bitwise XOR)

5. `&` (bitwise AND)

6. `==`, `!=`

7. `<`, `<=`, `>`, `>=`

8. `+`, `-`

9. `*`, `/`

10. unary: `-x`, `!x`, `*x`, `~x`, `sizeof`

11. postfix: calls, indexing, field access, try `?`

The lexer must distinguish:

* `&&` vs single `&`

* `||` vs single `|`

* `<<` / `>>` vs `<` / `>` / `<=` / `>=`

Bitwise operators are left-associative, like in C.

### 1.3. Semantics (no UB)

Given `int` is defined as **32-bit two’s complement**:

* `~`, `&`, `|`, `^` operate on the full 32-bit representation.

* Results are always defined 32-bit `int` values.

For shifts:

* Let `x << n` or `x >> n`:

    * `n` must be in the range `0 .. 31` (inclusive).

    * If `n` is outside this range at runtime, the operation **panics** (defined abort), not UB.

* `x << n`:

    * Left shift of the 32-bit pattern; no special casing beyond panic on invalid `n`.

* `x >> n`:

    * Arithmetic right shift (sign bit replicated).

This gives fully defined semantics independent of the C implementation.

The C backend implements these using 32-bit operations and explicit checks where needed.

## 2. Top-level `const` and `let`

We extend the set of **top-level declarations** with:

* `const` declarations (compile-time constants).

* `let` declarations (global variables).

### 2.1. Syntax

At top level, allowed forms now include:

```l0
// constant
const NAME: Type = expr;

// mutable global
let NAME: Type = expr;
```

in addition to existing `func`, `extern func`, `struct`, `enum`, `type` declarations.

Examples:

```l0
module compiler.config;

const MAX_PARSE_ERRORS: int = 50;
const TAB_WIDTH: int = 4;

let global_stats_enabled: bool = false;
```

### 2.2. Semantics of `const`

* A top-level `const` is:

    * **Immutable**: it cannot be assigned to anywhere.
    * **Compile-time evaluated**: its initializer must be a constant expression.

**Constant expressions** (Stage 1) are restricted to:

* Literal `int`, `bool`, `string`.
* References to other `const` values (with acyclic dependencies).
* Unary and binary operators on `int`/`bool`/`string` that are themselves pure:

    * Arithmetic: `+ - * /` (with defined behavior; e.g. division by constant zero must be rejected at compile-time).
    * Comparisons, logical, and bitwise ops on `int`/`bool`.

* No function calls.
* No heap allocation, no pointers, no I/O.

If evaluation of a `const` initializer would:

* Divide by zero,
* Shift by an invalid amount,
* Overflow in a way the language does not allow,

then it is a **compile-time error**, not UB.

Implementation:

* Stage 1 can start with a minimal constant folder/evaluator.
* More operators and types can be admitted over time.

`const` values are conceptually inlined; codegen is free to embed them as literals or as static data, as appropriate.

### 2.3. Semantics of top-level `let`

* A top-level `let` defines a **mutable global variable**, initialized before `main` runs.
* The initializer is evaluated at program start, in a well-defined order (e.g. module order, or as defined later).
* The initializer may be:

    * Any expression valid at runtime (restricted to constant expressions in Stage 1).
    * It may call functions, allocate memory, etc., if desired (later stages).

Example:

```l0
let diagnostics_enabled: bool = true;

let token_cache_capacity: int = 4096;
```

For Stage 2 compiler use, we can recommend:

* Prefer `const` where possible (for configuration constants, sizes, flags).
* Use global `let` sparingly, mainly for simple flags or counters.

### 2.4. UB-free guarantees

* Modifying a `const` is a **compile-time error** (not UB).
* Reading/writing a top-level `let` is always well-defined in single-threaded semantics:

    * There are no data races because the language has no threads yet.

* Initialization:

    * Either:

        * Fully defined initialization order (e.g. “module order + top-to-bottom”), or
        * Require initializers of `let` that depend on other module-level values to only depend on `const`, not `let`.

  This can be tightened as the module system / initialization model is specified.
