# Compiler Diagnostic Code Catalog

Version: 2026-04-03

Shared inventory of Dea compiler diagnostic codes.

## Related Docs

- [l0/docs/specs/compiler/diagnostic-code-policy.md](../../../l0/docs/specs/compiler/diagnostic-code-policy.md):
  normative parity and reuse policy.
- [l0/docs/specs/compiler/diagnostic-format.md](../../../l0/docs/specs/compiler/diagnostic-format.md): output rendering
  format.
- [l0/compiler/stage1_py/l0_diagnostics.py](../../../l0/compiler/stage1_py/l0_diagnostics.py): current registered
  family/code source of truth.
- [l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py](../../../l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py):
  trigger matrix for registered code meanings.

## Scope

This catalog snapshots the compiler diagnostic codes currently registered in the repository-wide oracle inventory.

It is intended to be shared across Dea compiler implementations rather than tied to a specific level or stage.

This document is an inventory reference. The normative rule for parity and reuse remains
`l0/docs/specs/compiler/diagnostic-code-policy.md`.

## Notes

- Codes are grouped by family following `DIAGNOSTIC_CODE_FAMILIES`; additional Dea-wide codes not yet present in the
  current L0 Stage 1 registry appear in numeric order within their family tables.
- Each family is presented as a table so the catalog can be extended incrementally as new compiler rules and diagnostic
  families are implemented.
- For L0 compiler codes, Python Stage 1 is the current oracle inventory and meaning source.
- `Meaning` records the current canonical issue represented by the code.
- `Meaning` may include an implementation-scope suffix such as `(L1+)` when a code is intentionally Dea-wide but not
  part of the current L0 Stage 1 oracle inventory.
- `ICE-xxxx` codes are currently not part of that central register and are therefore not included in this catalog.
- Any change to the registered compiler inventory should update this document in the same change, including `Meaning`.

## `LEX`

| Code       | Meaning                                                |
| ---------- | ------------------------------------------------------ |
| `LEX-0010` | Unterminated string literal                            |
| `LEX-0020` | Unterminated char literal                              |
| `LEX-0021` | Invalid char literal, expected closing single quote    |
| `LEX-0030` | Character literal must represent a single byte         |
| `LEX-0031` | Character literal hex escape out of range (0-255)      |
| `LEX-0040` | Unexpected character in source text                    |
| `LEX-0050` | Invalid hex escape sequence                            |
| `LEX-0051` | Invalid unicode escape sequence (\\u)                  |
| `LEX-0052` | Invalid unicode escape sequence (\\U)                  |
| `LEX-0053` | Octal escape sequence out of range (0-255)             |
| `LEX-0054` | Unicode code point out of range (must be \<= 0x10FFFF) |
| `LEX-0059` | Unknown escape sequence                                |
| `LEX-0060` | Integer literal exceeds 32-bit signed range            |
| `LEX-0061` | Invalid character after integer literal                |
| `LEX-0062` | Invalid hexadecimal integer literal (L1+)              |
| `LEX-0063` | Invalid binary integer literal (L1+)                   |
| `LEX-0064` | Invalid octal integer literal (L1+)                    |
| `LEX-0070` | Unterminated block comment                             |

## `PAR`

| Code       | Meaning                                                                    |
| ---------- | -------------------------------------------------------------------------- |
| `PAR-0000` | Fallback parser error when no specific parse/lex diagnostic is available   |
| `PAR-0010` | Invalid variable name: reserved keyword                                    |
| `PAR-0011` | Invalid variable name: reserved identifier                                 |
| `PAR-0020` | Unexpected top-level declaration                                           |
| `PAR-0030` | Expected 'extern'                                                          |
| `PAR-0040` | Expected 'func'                                                            |
| `PAR-0041` | Expected function name                                                     |
| `PAR-0042` | Expected '('                                                               |
| `PAR-0043` | Expected parameter name                                                    |
| `PAR-0044` | Expected ':' after parameter name                                          |
| `PAR-0045` | Expected ')' after parameters                                              |
| `PAR-0046` | Expected ';' after extern function decl                                    |
| `PAR-0050` | Expected 'struct'                                                          |
| `PAR-0051` | Expected struct name                                                       |
| `PAR-0052` | Expected '{' after struct name                                             |
| `PAR-0053` | Expected field name                                                        |
| `PAR-0054` | Expected ':' after field name                                              |
| `PAR-0055` | Expected ';' after field declaration                                       |
| `PAR-0056` | Expected '}' after struct body                                             |
| `PAR-0060` | Expected 'enum'                                                            |
| `PAR-0061` | Expected enum name                                                         |
| `PAR-0062` | Expected '{' after enum name                                               |
| `PAR-0063` | Expected variant name                                                      |
| `PAR-0064` | Expected variant field name                                                |
| `PAR-0065` | Expected ':'                                                               |
| `PAR-0066` | Expected ')' after variant payload                                         |
| `PAR-0067` | Expected ';' after variant                                                 |
| `PAR-0068` | Expected '}' after enum body                                               |
| `PAR-0070` | Expected type name                                                         |
| `PAR-0071` | Expected type alias name                                                   |
| `PAR-0072` | Expected '=' in type alias                                                 |
| `PAR-0073` | Expected ';' after type alias                                              |
| `PAR-0080` | Expected 'let'                                                             |
| `PAR-0081` | Expected variable name                                                     |
| `PAR-0082` | Expected '=' in let binding                                                |
| `PAR-0083` | Expected ';' after let declaration                                         |
| `PAR-0090` | Expected '{' to start block                                                |
| `PAR-0091` | Expected '}' after block                                                   |
| `PAR-0100` | Expected ';' after statement                                               |
| `PAR-0110` | Expected 'let'                                                             |
| `PAR-0111` | Expected variable name                                                     |
| `PAR-0112` | Expected '=' in let binding                                                |
| `PAR-0120` | Expected 'if'                                                              |
| `PAR-0121` | Expected '(' after 'if'                                                    |
| `PAR-0122` | Expected ')' after condition                                               |
| `PAR-0130` | Expected 'while'                                                           |
| `PAR-0131` | Expected '('                                                               |
| `PAR-0132` | Expected ')'                                                               |
| `PAR-0140` | Expected 'for'                                                             |
| `PAR-0141` | Expected '(' after 'for'                                                   |
| `PAR-0142` | Expected ';' after for loop initialization                                 |
| `PAR-0143` | Expected ';' after for loop condition                                      |
| `PAR-0144` | Expected ')' after for loop clauses                                        |
| `PAR-0150` | Expected 'return'                                                          |
| `PAR-0160` | Expected 'drop'                                                            |
| `PAR-0161` | Expected variable name after 'drop'                                        |
| `PAR-0170` | Expected 'match'                                                           |
| `PAR-0171` | Expected '('                                                               |
| `PAR-0172` | Expected ')'                                                               |
| `PAR-0173` | Expected '{' after match expression                                        |
| `PAR-0174` | Expected '=>' in match arm                                                 |
| `PAR-0175` | Expected '}' after match                                                   |
| `PAR-0176` | Duplicate variant patterns in match statement                              |
| `PAR-0177` | Match statement must have at least one arm                                 |
| `PAR-0180` | Expected pattern variable name                                             |
| `PAR-0181` | Expected ')' in pattern                                                    |
| `PAR-0182` | Unexpected pattern syntax                                                  |
| `PAR-0190` | Expected 'break'                                                           |
| `PAR-0200` | Expected 'continue'                                                        |
| `PAR-0210` | Expected ')' after arguments                                               |
| `PAR-0211` | Expected '\]' after index                                                  |
| `PAR-0212` | Expected field name after '.'                                              |
| `PAR-0223` | Expected ')' after arguments to 'new'                                      |
| `PAR-0224` | Expected ')' after expression                                              |
| `PAR-0225` | Expected expression                                                        |
| `PAR-0226` | Operator is not yet supported                                              |
| `PAR-0230` | Expected 'case'                                                            |
| `PAR-0231` | Expected '('                                                               |
| `PAR-0232` | Expected ')'                                                               |
| `PAR-0233` | Expected '{' after 'case' expression                                       |
| `PAR-0234` | Value arm cannot appear after 'else' in 'case' statement                   |
| `PAR-0235` | Expected '=>' in 'case' arm                                                |
| `PAR-0236` | Duplicate 'else' arm in 'case' statement                                   |
| `PAR-0237` | '=>' not allowed in 'else' arm                                             |
| `PAR-0238` | Expected value literal or `else` in `case` arm                             |
| `PAR-0239` | Expected '}' after 'case' statement                                        |
| `PAR-0240` | 'case' statement must have at least one arm                                |
| `PAR-0241` | Expected literal in 'case' arm                                             |
| `PAR-0300` | Expected identifier after '.' in module name                               |
| `PAR-0310` | Expected 'module'                                                          |
| `PAR-0311` | Expected module name                                                       |
| `PAR-0312` | Expected ';' after module name                                             |
| `PAR-0320` | Expected imported module name                                              |
| `PAR-0321` | Expected ';' after import                                                  |
| `PAR-0400` | Expected type name                                                         |
| `PAR-0401` | Expected identifier after '::' in qualified name                           |
| `PAR-9401` | Array types not yet supported: use pointers and [] indexing in expressions |
| `PAR-0500` | Expected 'with'                                                            |
| `PAR-0501` | Expected '(' after 'with'                                                  |
| `PAR-0502` | Expected ')' after with items                                              |
| `PAR-0503` | 'with': all items must use '=>' or none                                    |
| `PAR-0504` | 'with': cannot have both '=>' and cleanup block                            |
| `PAR-0505` | 'with': cleanup block required when '=>' is not used                       |

## `DRV`

| Code       | Meaning                                                                               |
| ---------- | ------------------------------------------------------------------------------------- |
| `DRV-0010` | File-related driver error, e.g. module source file not found                          |
| `DRV-0011` | Cannot read source file for a resolved module                                         |
| `DRV-0020` | Input validation error, e.g. declared module name does not match the requested module |
| `DRV-0030` | Import-related driver error, e.g. cyclic module imports                               |
| `DRV-0040` | Source decoding error, e.g. input file is not valid UTF-8                             |

## `L0C`

| Code       | Meaning                                                                                               |
| ---------- | ----------------------------------------------------------------------------------------------------- |
| `L0C-0009` | No C compiler found: use '--c-compiler' to specify one or set the L0_CC environment variable          |
| `L0C-0010` | C compilation failed                                                                                  |
| `L0C-0011` | Invalid entry module name: module components must be valid identifiers                                |
| `L0C-0012` | Entry module not found in analysis result                                                             |
| `L0C-0013` | Entry `main` returns a non-preferred type; the generated C entry wrapper ignores the return value     |
| `L0C-0014` | Runtime library path does not exist or is not a directory                                             |
| `L0C-0015` | Runtime library directory does not contain any supported `l0runtime` library                          |
| `L0C-0016` | Missing type information for the entry `main` function                                                |
| `L0C-0017` | '--output' is ignored in '--run' mode unless '--keep-c' is set; the executable path remains temporary |
| `L0C-0020` | Analysis or AST command failed with an exception                                                      |
| `L0C-0030` | Entry module not found in compilation unit                                                            |
| `L0C-0040` | Cannot read an input source file during token dump                                                    |
| `L0C-0041` | Source file encoding error during token dump                                                          |
| `L0C-0050` | Compilation-unit discovery failed during all-modules token dump                                       |
| `L0C-0060` | Discovered module path could not be resolved during all-modules token dump                            |
| `L0C-0070` | Entry module path could not be resolved for token dump                                                |

## `RES`

| Code       | Meaning                                                                              |
| ---------- | ------------------------------------------------------------------------------------ |
| `RES-0010` | Duplicate top-level definition in the same module                                    |
| `RES-0020` | Imported extern function is shadowed by a compatible local extern declaration        |
| `RES-0021` | Imported symbol is shadowed by a local definition                                    |
| `RES-0022` | Ambiguous unqualified import: the same symbol name is imported from multiple modules |
| `RES-0029` | Import refers to an unknown module                                                   |

## `SIG`

| Code       | Meaning                                                                           |
| ---------- | --------------------------------------------------------------------------------- |
| `SIG-0010` | Symbol is not a type                                                              |
| `SIG-0011` | Type 'void' cannot be nullable                                                    |
| `SIG-0018` | Overqualified type path is not supported                                          |
| `SIG-0019` | Unknown or ambiguous type reference                                               |
| `SIG-0020` | Cyclic type alias definition                                                      |
| `SIG-0021` | Internal error: compiler-inserted type alias has no backing declaration           |
| `SIG-0030` | Cannot infer type for let - type annotation required for non-literal initializers |
| `SIG-0040` | Value-type cycle creates an infinitely sized type                                 |
| `SIG-9029` | Internal error: a type-alias symbol does not reference a type-alias declaration   |

## `TYP`

| Code       | Meaning                                                                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TYP-0001` | No compilation unit available for expression type checking                                                                                       |
| `TYP-0002` | Internal error: missing resolved function type during expression checking                                                                        |
| `TYP-0010` | Not all control paths return the required value type                                                                                             |
| `TYP-0020` | Local variable already declared in this scope                                                                                                    |
| `TYP-0021` | Local variable shadows variable from outer scope                                                                                                 |
| `TYP-0022` | Local variable shadows an enum variant in the same module                                                                                        |
| `TYP-0023` | Local variable shadows an imported enum variant                                                                                                  |
| `TYP-0024` | Local variable shadows an ambiguously imported symbol                                                                                            |
| `TYP-0025` | Local variable shadows a top-level symbol                                                                                                        |
| `TYP-0030` | Unreachable code                                                                                                                                 |
| `TYP-0031` | Unreachable code after 'return'                                                                                                                  |
| `TYP-0040` | Cannot resolve type annotation for variable                                                                                                      |
| `TYP-0050` | Variable cannot have type 'void'                                                                                                                 |
| `TYP-0051` | Initializer for type mismatch                                                                                                                    |
| `TYP-0052` | Cannot infer type from 'null'; explicit type required                                                                                            |
| `TYP-0053` | Initializer is 'void', cannot assign to variable                                                                                                 |
| `TYP-0060` | Unknown variable                                                                                                                                 |
| `TYP-0061` | Cannot drop non-pointer type                                                                                                                     |
| `TYP-0062` | Use of dropped variable                                                                                                                          |
| `TYP-0070` | If condition must have type 'bool'                                                                                                               |
| `TYP-0080` | While condition must have type 'bool'                                                                                                            |
| `TYP-0090` | For loop condition must have type 'bool'                                                                                                         |
| `TYP-0100` | Match expression must have enum type                                                                                                             |
| `TYP-0101` | Pattern variable count mismatch: variant has fields but pattern has variables                                                                    |
| `TYP-0102` | Unknown variant for enum                                                                                                                         |
| `TYP-0103` | No type information for enum                                                                                                                     |
| `TYP-0104` | Non-exhaustive match                                                                                                                             |
| `TYP-0105` | Unreachable wildcard pattern in match: all variants of enum are already covered                                                                  |
| `TYP-0106` | `case` scrutinee must have type `int`, `byte`, `bool`, or `string`                                                                               |
| `TYP-0107` | 'case' arm literal must be int, byte, bool, or string                                                                                            |
| `TYP-0108` | Duplicate literal value in 'case' statement                                                                                                      |
| `TYP-0109` | Invalid escape in 'case' literal                                                                                                                 |
| `TYP-0110` | 'break' statement not within a loop                                                                                                              |
| `TYP-0120` | 'continue' statement not within a loop                                                                                                           |
| `TYP-0139` | Unknown statement type                                                                                                                           |
| `TYP-0149` | Internal error: cannot infer the type of an empty expression placeholder                                                                         |
| `TYP-0150` | Use of dropped variable                                                                                                                          |
| `TYP-0151` | Symbol is not a value                                                                                                                            |
| `TYP-0152` | Variant requires arguments; use '(...)' constructor syntax                                                                                       |
| `TYP-0153` | Unknown identifier from an unknown module                                                                                                        |
| `TYP-0154` | Identifier refers to a non-imported module                                                                                                       |
| `TYP-0155` | Ambiguous identifier                                                                                                                             |
| `TYP-0156` | 'cleanup' block references 'with' header variable that may be uninitialized on '?' header-failure path; use nullable type or inline '=>' cleanup |
| `TYP-0158` | Overqualified symbol path is not supported                                                                                                       |
| `TYP-0159` | Unknown identifier                                                                                                                               |
| `TYP-0160` | Unary `-` requires an integer operand                                                                                                            |
| `TYP-0161` | Unary `!` requires a `bool` operand                                                                                                              |
| `TYP-0162` | Cannot dereference a non-pointer expression                                                                                                      |
| `TYP-0170` | Operator requires integer operands                                                                                                               |
| `TYP-0171` | Operator requires boolean operands                                                                                                               |
| `TYP-0172` | Equality operator requires compatible operand types                                                                                              |
| `TYP-0173` | Equality not supported for this type in this stage                                                                                               |
| `TYP-0180` | Callee must be a function name                                                                                                                   |
| `TYP-0181` | Symbol is not callable                                                                                                                           |
| `TYP-0182` | Callee is not a function                                                                                                                         |
| `TYP-0183` | Function call argument count mismatch                                                                                                            |
| `TYP-0189` | Unknown or ambiguous callee identifier                                                                                                           |
| `TYP-0190` | No type information for struct                                                                                                                   |
| `TYP-0191` | Struct constructor argument count mismatch                                                                                                       |
| `TYP-0200` | Variant has no type information                                                                                                                  |
| `TYP-0201` | Variant constructor argument count mismatch                                                                                                      |
| `TYP-0210` | Index expression must have type `int`                                                                                                            |
| `TYP-0211` | Cannot index into a nullable array                                                                                                               |
| `TYP-0212` | Cannot index into a non-array expression                                                                                                         |
| `TYP-0220` | Cannot access a field on a nullable struct                                                                                                       |
| `TYP-0221` | Struct has no field                                                                                                                              |
| `TYP-0222` | Cannot access field on non-struct type                                                                                                           |
| `TYP-0230` | Invalid explicit cast                                                                                                                            |
| `TYP-0240` | Cannot take sizeof(void)                                                                                                                         |
| `TYP-0241` | Sizeof expects exactly 1 argument                                                                                                                |
| `TYP-0242` | Ord expects exactly 1 argument                                                                                                                   |
| `TYP-0243` | `ord` expects an enum value                                                                                                                      |
| `TYP-0244` | Intrinsic reference may only be used in call position (L1+)                                                                                      |
| `TYP-0250` | Cannot apply '?' to non-nullable type                                                                                                            |
| `TYP-0251` | Cannot use '?' in a function that does not return a nullable type (T?)                                                                           |
| `TYP-0260` | Return statement outside of function                                                                                                             |
| `TYP-0270` | Type alias does not have a resolved type                                                                                                         |
| `TYP-0271` | Symbol is not a type                                                                                                                             |
| `TYP-0278` | Type 'void' cannot be nullable                                                                                                                   |
| `TYP-0279` | Unknown or ambiguous type                                                                                                                        |
| `TYP-0280` | Unknown type in 'new' expression                                                                                                                 |
| `TYP-0281` | Cannot allocate enum type without a variant                                                                                                      |
| `TYP-0282` | Missing struct layout information                                                                                                                |
| `TYP-0283` | Heap-allocated struct argument count mismatch                                                                                                    |
| `TYP-0285` | `new` scalar initializer arity mismatch                                                                                                          |
| `TYP-0286` | Invalid scalar initializer for `new`                                                                                                             |
| `TYP-0290` | Type expression is only valid as argument to type-accepting intrinsics such as 'sizeof'                                                          |
| `TYP-0300` | Unknown type from an unknown module                                                                                                              |
| `TYP-0301` | Type refers to a non-imported module                                                                                                             |
| `TYP-0303` | Ambiguous identifier                                                                                                                             |
| `TYP-0310` | Expression type mismatch                                                                                                                         |
| `TYP-0311` | Assignment type mismatch                                                                                                                         |
| `TYP-0312` | Function call argument type mismatch                                                                                                             |
| `TYP-0313` | Struct constructor field type mismatch                                                                                                           |
| `TYP-0314` | Enum variant constructor field type mismatch                                                                                                     |
| `TYP-0315` | Return expression type mismatch                                                                                                                  |
| `TYP-0316` | Heap allocation initializer type mismatch                                                                                                        |
| `TYP-0319` | Internal default code for widening-context type mismatches                                                                                       |
| `TYP-0700` | Explicit `int` to `byte` cast overflows the byte range                                                                                           |
| `TYP-0701` | Explicit nullable-pointer-to-pointer cast is provably null at compile time                                                                       |
| `TYP-9209` | Internal error: variant does not produce enum type                                                                                               |
| `TYP-9288` | Internal error: 'new' outside function context                                                                                                   |
| `TYP-9289` | Internal error: missing module environment for the current function                                                                              |
