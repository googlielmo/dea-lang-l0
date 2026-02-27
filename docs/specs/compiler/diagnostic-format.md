# Diagnostic Output Format Spec

Version: 2026-02-27

Normative specification for compiler diagnostic output in both Stage 1 and Stage 2.

## Header Line

```
{path}:{line}:{column}({module}): {severity}: [{code}] {message}
```

### Fields

| Field      | Description                                                          |
|------------|----------------------------------------------------------------------|
| `path`     | Absolute path (preferred) or as-stored path to the source file.      |
| `line`     | 1-based line number.                                                 |
| `column`   | 1-based column number.                                               |
| `module`   | Module name, appended after column in parentheses when available.    |
| `severity` | Lowercase: `error`, `warning`, or `note`.                            |
| `code`     | Diagnostic code in `XXX-NNNN` format (e.g., `TYP-0315`, `PAR-0010`). |
| `message`  | Human-readable description of the issue.                             |

### Graceful Degradation

Components are omitted when unavailable. The location prefix is built left-to-right and stops at the first missing
component:

| Available              | Rendered prefix      |
|------------------------|----------------------|
| path, line, column     | `path:line:column: ` |
| path, line (no column) | `path:line: `        |
| path only              | `path: `             |
| nothing                | (no location prefix) |

The `({module})` suffix is appended after column only when a module name is available. When column is absent, the
module suffix is omitted.

The `[{code}]` bracket is present only when a diagnostic code is set. When absent, severity is followed directly by the
message.

### Examples

Full location with module:

```
/home/user/project/hello.l0:21:12(hello2): error: [TYP-0315] return value type mismatch: expected 'int', got 'bool'
```

Full location without module:

```
/home/user/project/hello.l0:21:12: error: [TYP-0315] return value type mismatch
```

No column:

```
/home/user/project/hello.l0:21: error: [PAR-0010] unexpected token
```

No file:

```
error: [PAR-0010] unexpected token
```

No code:

```
/home/user/project/hello.l0:21:12: error: unexpected token
```

## Snippet

```
{gutter}{line_no} | {source}
{gutter}          | {carets}
```

### Gutter

- `gutter_width = max(5, len(str(line_number)))` — ensures alignment for small line numbers.
- The line number is right-aligned within the gutter width.
- The caret line uses the same gutter width filled with spaces.

### Carets

- `caret_width = max(1, end_col - start_col)` — at least one `^`.
- When the span crosses lines, carets extend to end of the source line.
- When no column information is available, the source line is shown but the caret line is omitted.
- When no source text is available, the entire snippet is omitted.

### Example

```
   21 | return true;
      |        ^^^^
```

Here `gutter_width = 5`, line number `21` is right-aligned, and the caret line uses the same 5-space gutter.

## Output Destination

All diagnostic output is written to **stderr**.
