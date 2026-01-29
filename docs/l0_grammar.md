# L<sub>0</sub> Grammar (Stage 1)

The following is the formal grammar for the L<sub>0</sub> programming language in EBNF-style. This describes the
concrete syntax that the Python lexer/parser should accept.

## 1. Lexical structure

### 1.1 Identifiers

```ebnf
Ident           ::=     Letter (Letter | Digit | "_")*

Letter          ::=     "A".."Z" | "a".."z" | "_"
Digit           ::=     "0".."9"
OctDigit        ::=     "0".."7"
HexDigit        ::=     "0".."9" | "A".."F" | "a".."f"
```

### 1.2 Literals

```ebnf
IntLiteral          ::=     Digit+

BoolLiteral         ::=     "true" | "false"

ByteLiteral         ::=     "'" SingleByteChar "'"
SingleByteChar      ::=     '\' EscapedChar
                      |     any character except '\', "'" or newline (* must fit in one byte *)

StringLiteral       ::=     '"' StringChar* '"'
StringChar          ::=     '\' EscapedChar
                      |     any character except '\', '"' or newline (* multi-byte UTF-8 allowed *)

Oct1to3             ::=     OctDigit ( OctDigit ( OctDigit )? )?
Hex4                ::=     HexDigit HexDigit HexDigit HexDigit
Hex8                ::=     Hex4 Hex4
EscapedChar         ::=     '"' | '\' | 'n' | 't' | 'r' | "'" | Oct1to3
                      |     'u' Hex4 | 'U' Hex8 | 'x' HexDigit HexDigit*
```

### 1.3 Keywords

Reserved keywords (not valid as identifiers):

```text
module import func struct enum type extern let const
return match if else while for break continue in
true false sizeof null as new drop void bool string
byte short int long ubyte ushort uint ulong float double
```

Note: not all keywords are used in L<sub>0</sub>; some are reserved for future stages.

### 1.4 Symbols / operators

```text
{ } ( ) [ ] ; , : .
-> => 
= == != < <= > >=
+ - * /
&& || !
& | ^ ~ << >> (* to be implemented in stage 2 *)
?   (* used in types and as postfix try operator *)
```

### 1.5 Special identifier `_`

The single identifier `_` is tokenized as a dedicated `UNDERSCORE` token and used only as the wildcard pattern. It is
not a normal Ident in patterns.

Line comments: `// ...` until end of line. Whitespace: spaces, tabs, newlines, carriage returns are skipped.

## 2. Top-level structure

One file corresponds to one module, path names are dot-separated.

```ebnf
CompilationUnit     ::=     ModuleDecl ImportDecl* TopLevelDecl*

ModuleDecl          ::=     "module" ModulePath ";"

ImportDecl          ::=     "import" ModulePath ";"

ModulePath          ::=     Ident ("." Ident)*
```

`Ident` here is the module name (no hierarchical packages in L<sub>0</sub>).

## 3. Top-level declarations

```ebnf
TopLevelDecl        ::=     FunctionDecl
                      |     StructDecl
                      |     EnumDecl
                      |     TypeAliasDecl
                      |     ExternFuncDecl
```

### 3.1 Functions

```ebnf
FunctionDecl        ::=     "func" Ident "(" ParamList? ")" "->" Type Block

ParamList           ::=     Param ("," Param)*
Param               ::=     Ident ":" Type
```

### 3.2 Extern functions

```ebnf
ExternFuncDecl      ::=     "extern" "func" Ident "(" ParamList? ")" "->" Type ";"
```

Extern functions have no body; they declare functions implemented in the runtime.

### 3.3 Structs

```ebnf
StructDecl      ::=     "struct" Ident "{" FieldDecl* "}"

FieldDecl       ::=     Ident ":" Type ";"
```

### 3.4 Enums (sum types)

```ebnf
EnumDecl                ::=     "enum" Ident "{" EnumVariantDecl* "}"

EnumVariantDecl         ::=     Ident VariantFields? ";"

VariantFields           ::=     "(" VariantFieldList? ")"
VariantFieldList        ::=     VariantField ("," VariantField)*

VariantField            ::=     Ident ":" Type
```

Each variant may have zero or more named payload fields.

### 3.5 Type aliases

```ebnf
TypeAliasDecl ::= "type" Ident "=" Type ";"
```

Used for things like `type RawPtr = void*;`.

## 4. Types

L<sub>0</sub> has simple named types, pointer suffixes, and an optional nullable suffix.

```ebnf
Type                ::=     SimpleType PointerSuffix* NullableSuffix?

SimpleType          ::=     Ident
PointerSuffix       ::=     "*"
NullableSuffix      ::=     "?"     (* applies to the preceding type syntactically *)
```

Examples (all syntactically valid types in L<sub>0</sub>):

* `string`
* `Expr*`
* `Expr**`
* `int?`
* `Expr*?`

Exact semantic rules (e.g. when `?` is allowed) are enforced in the type checker, not in the grammar.

## 5. Blocks and statements

```ebnf
Block           ::=     "{" Stmt* "}"

Stmt            ::=     Block
                  |     IfStmt
                  |     MatchStmt
                  |     WhileStmt
                  |     ForStmt
                  |     SimpleStmt ";"

SimpleStmt      ::=     LetStmt
                  |     AssignStmt
                  |     BreakStmt
                  |     ContinueStmt
                  |     ReturnStmt
                  |     Expr
```

### 5.1 Variable declarations

```ebnf
LetStmt     ::=     "let" Ident ( ":" Type )? "=" Expr
```

### 5.2 Assignments

Assignments are *statements only* in L<sub>0</sub>; `=` does not appear as an expression operator.

```ebnf
AssignStmt      ::=     LValue "=" Expr 

LValue          ::=     PrimaryExpr ( PostfixOp )*
                        (* Must resolve to an assignable location; checked semantically. *)
```

### 5.3 Conditionals and loops

```ebnf
IfStmt          ::=     "if" "(" Expr ")" Stmt ( "else" Stmt )?

WhileStmt       ::=     "while" "(" Expr ")" Block

ForStmt         ::=     "for" "(" ( SimpleStmt )? ";" ( Expr )? ";" ( SimpleStmt )? ")" Block

BreakStmt       ::=     "break" 

ContinueStmt    ::=     "continue" 
```

### 5.4 Return

```ebnf
ReturnStmt      ::=     "return" ( Expr )? 
```

### 5.5 Match (statement-only in L<sub>0</sub>)

```ebnf
MatchStmt       ::=     "match" "(" Expr ")" "{" ( MatchArm )+ "}"

MatchArm        ::=     Pattern "=>" Block
```

Patterns (L<sub>0</sub> subset):

```ebnf
Pattern             ::=     VariantPattern | WildcardPattern

VariantPattern      ::=     Ident "(" ( PatternVarList )? ")"
PatternVarList      ::=     Ident ( "," Ident )*

WildcardPattern     ::=     "_"
```

No literal patterns, nested patterns, or or-patterns in L<sub>0</sub>.

## 6. Expressions

L<sub>0</sub> expressions are side-effectful, but assignment is not an expression.

Precedence (from lowest to highest):

1. `||`
2. `&&`
3. `|`   (bitwise OR)
4. `^`   (bitwise XOR)
5. `&`   (bitwise AND)
6. `==`, `!=`
7. `<`, `<=`, `>`, `>=`
8. `+`, `-`
9. `*`, `/`
10. unary `-`, `!`, `*`, `~`
11. postfix call/index/field/try

There is **no** ternary `?:` operator in L<sub>0</sub>.

```ebnf
Expr                ::=     OrExpr

OrExpr              ::=     AndExpr ( "||" AndExpr )*

AndExpr             ::=     BitOrExpr ( "&&" BitOrExpr )*

BitOrExpr           ::=     BitXorExpr ( "|" BitXorExpr )*
BitXorExpr          ::=     BitAndExpr ( "^" BitAndExpr )*
BitAndExpr          ::=     EqualityExpr ( "&" EqualityExpr )*

EqualityExpr        ::=     RelExpr ( ( "==" | "!=" ) RelExpr )*

RelExpr             ::=     ShiftExpr ( ( "<" | "<=" | ">" | ">=" ) ShiftExpr )*

ShiftExpr           ::=     AddExpr ( ( "<<" | ">>" ) AddExpr )*

AddExpr             ::=     MulExpr ( ( "+" | "-" ) MulExpr )*

MulExpr             ::=     UnaryExpr ( ( "*" | "/" ) UnaryExpr )*

UnaryExpr           ::=     ( "-" | "!" | "~" ) UnaryExpr
                      |     CastExpr

CastExpr            ::=     PostfixExpr ( "as" Type )?

PostfixExpr         ::=     PrimaryExpr ( PostfixOp )*

PostfixOp           ::=     "(" ( ArgList )? ")"    (* function call *)
                      |     "[" Expr "]"            (* indexing *)
                      |     "." Ident               (* field access *)
                      |     "?"                     (* try / optional chaining *)

ArgList             ::=     Arg ( "," Arg )*

Arg                 ::=     TypeExpr
                      |     Expr

TypeExpr            ::=     BuiltinTypeName ( "*" )* ( "?" )?
                      |     Ident ( "*" )+ ( "?" )?

BuiltinTypeName     ::=     "int" | "byte" | "bool" | "string" | "void"

PrimaryExpr         ::=     IntLiteral
                      |     ByteLiteral
                      |     StringLiteral
                      |     BoolLiteral
                      |     Ident
                      |     "new" Type ( "(" ArgList? ")" )?
                      |     "(" Expr ")"
```

Notes:

* `Ident` as a primary expression is a simple variable reference.
  When the identifier resolves to a zero-argument enum variant, it acts as a constructor
  (e.g. `Red` is equivalent to `Red()`).
* `as` casts support `T?` <-> `T` conversion.
* The `?` type suffix denotes nullable types in the `Type` grammar.
* `?` as a postfix operator is the **null propagation operator** (also known as the **try operator**).
* `TypeExpr` allows types in argument position for intrinsics like `sizeof(int*)`.
* A `TypeExpr` is syntactically unambiguous: either a builtin type name, or an identifier
  followed by `*` or `?` suffixes that end at an argument boundary (`,` or `)`).
* Plain identifiers like `sizeof(Point)` parse as `Expr`; the type checker resolves
  whether `Point` refers to a type or variable.
* `sizeof` is not a keyword; it's a compiler-recognized intrinsic function.

This grammar is intended to be just expressive enough to:

* Write the compiler and standard library in L<sub>0</sub>.
* Avoid undefined behavior at the language level.
* Keep the Python lexer/parser implementation straightforward for Stage 1.
