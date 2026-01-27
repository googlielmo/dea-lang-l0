#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from typing import Optional, List


# ==========================
# AST definitions
# ==========================


@dataclass
class Span:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass
class Node:
    span: Optional[Span] = field(default=None, repr=False, compare=False, kw_only=True)


# --- types ---

@dataclass
class TypeRef(Node):
    name: str  # e.g. "int", "MyStruct", etc.
    pointer_depth: int = 0  # number of *
    is_nullable: bool = False  # trailing ?


# --- declarations ---

@dataclass
class Import(Node):
    name: str


class TopLevelDecl(Node):
    pass


@dataclass
class Param(Node):
    name: str
    type: TypeRef


@dataclass
class FuncDecl(TopLevelDecl):
    name: str
    params: List[Param]
    return_type: TypeRef
    body: "Block"
    is_extern: bool = False


@dataclass
class FieldDecl(Node):
    name: str
    type: TypeRef


@dataclass
class StructDecl(TopLevelDecl):
    name: str
    fields: List[FieldDecl]


@dataclass
class EnumVariant(Node):
    name: str
    fields: List[FieldDecl]


@dataclass
class EnumDecl(TopLevelDecl):
    name: str
    variants: List[EnumVariant]


@dataclass
class TypeAliasDecl(TopLevelDecl):
    name: str
    target: TypeRef


@dataclass
class LetDecl(TopLevelDecl):
    name: str
    type: Optional[TypeRef]
    value: "Expr"


@dataclass
class Module(Node):
    name: str
    imports: List[Import]
    decls: List[TopLevelDecl]
    filename: Optional[str] = field(default=None, repr=False, compare=False, kw_only=True)


# --- statements ---

@dataclass
class Stmt(Node):
    pass


@dataclass
class Block(Stmt):
    stmts: List[Stmt]


@dataclass
class LetStmt(Stmt):
    name: str
    type: Optional[TypeRef]
    value: "Expr"


@dataclass
class AssignStmt(Stmt):
    target: "Expr"  # must be an l-value; checked later
    value: "Expr"


@dataclass
class ExprStmt(Stmt):
    expr: "Expr"


@dataclass
class IfStmt(Stmt):
    cond: "Expr"
    then_stmt: Stmt
    else_stmt: Optional[Stmt]


@dataclass
class WhileStmt(Stmt):
    cond: "Expr"
    body: Block


@dataclass
class ForStmt(Stmt):
    init: Optional[Stmt]
    cond: Optional["Expr"]
    update: Optional[Stmt]
    body: Block


@dataclass
class ReturnStmt(Stmt):
    value: Optional["Expr"]


@dataclass
class DropStmt(Stmt):
    name: str


@dataclass
class MatchArm(Node):
    pattern: "Pattern"
    body: Block


@dataclass
class MatchStmt(Stmt):
    expr: "Expr"
    arms: List[MatchArm]


@dataclass
class BreakStmt(Stmt):
    pass


@dataclass
class ContinueStmt(Stmt):
    pass


# --- patterns (minimal: variant or wildcard) ---

class Pattern(Node):
    pass


@dataclass
class WildcardPattern(Pattern):
    pass


@dataclass
class VariantPattern(Pattern):
    name: str
    vars: List[str]


# --- expressions ---

class Expr(Node):
    pass


@dataclass
class IntLiteral(Expr):
    value: int


@dataclass
class ByteLiteral(Expr):
    value: str


@dataclass
class StringLiteral(Expr):
    value: str


@dataclass
class BoolLiteral(Expr):
    value: bool


@dataclass
class NullLiteral(Expr):
    pass


@dataclass
class VarRef(Expr):
    name: str


@dataclass
class NewExpr(Expr):
    type_ref: TypeRef
    args: List[Expr]


@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr


@dataclass
class BinaryOp(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]


@dataclass
class IndexExpr(Expr):
    array: Expr
    index: Expr


@dataclass
class FieldAccessExpr(Expr):
    obj: Expr
    field: str


@dataclass
class ParenExpr(Expr):
    inner: Expr


@dataclass
class CastExpr(Expr):
    expr: Expr
    target_type: TypeRef


@dataclass
class TryExpr(Expr):
    expr: Expr


@dataclass
class TypeExpr(Expr):
    """A type used in expression position."""
    type_ref: TypeRef
