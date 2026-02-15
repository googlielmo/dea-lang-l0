#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from typing import List, Optional

from l0_ast import (
    Span, TypeRef, Import, TopLevelDecl, Param, FuncDecl, FieldDecl, StructDecl, EnumVariant, EnumDecl,
    TypeAliasDecl, LetDecl, Module, Stmt, Block, LetStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt, ReturnStmt, DropStmt,
    MatchArm, MatchStmt, CaseArm, CaseElse, CaseStmt, Pattern, WildcardPattern, VariantPattern, Expr, IntLiteral,
    ByteLiteral, StringLiteral, BoolLiteral, NullLiteral, VarRef, UnaryOp, BinaryOp, CallExpr, IndexExpr,
    FieldAccessExpr, ParenExpr, CastExpr, TryExpr, TypeExpr, NewExpr, BreakStmt, ContinueStmt, ForStmt,
    WithItem, WithStmt)
from l0_lexer import TokenKind, Token, Lexer, is_reserved_keyword


# ==========================
# Parser
# ==========================

@dataclass
class ParseError(Exception):
    message: str
    token: Optional[Token] = None
    filename: Optional[str] = None


class Parser:
    def __init__(self, tokens: List[Token], filename: Optional[str] = None) -> None:
        self.tokens = tokens
        self.index = 0
        self.filename = filename

    @classmethod
    def from_source(cls, source: str) -> "Parser":
        lexer = Lexer.from_source(source)
        tokens = lexer.tokenize()
        return cls(tokens)

    # --- token utilities ---

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _last(self) -> Token:
        return self.tokens[self.index - 1 if self.index > 0 else 0]

    def _at_end(self) -> bool:
        return self._peek().kind is TokenKind.EOF

    def _advance(self) -> Token:
        tok = self._peek()
        if not self._at_end():
            self.index += 1
        return tok

    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind is kind

    def _match(self, *kinds: TokenKind) -> bool:
        if self._peek().kind in kinds:
            self._advance()
            return True
        return False

    def _expect(self, kind: TokenKind, msg: str) -> Token:
        if not self._check(kind):
            raise ParseError(f"{msg}, got {self._peek()} instead", self._peek(), self.filename)
        return self._advance()

    def _expect_variable_name(self, msg: str) -> Token:
        tok = self._peek()
        if tok.kind == TokenKind.FUTURE_EXTENSION:
            raise ParseError(
                f"[PAR-0010] invalid variable name '{tok.text}': reserved keyword",
                tok,
                self.filename,
            )
        tok = self._expect(TokenKind.IDENT, msg)
        if is_reserved_keyword(tok.text):
            raise ParseError(
                f"[PAR-0011] invalid variable name '{tok.text}': reserved identifier",
                tok,
                self.filename,
            )
        return tok

    def _span_start(self) -> Span:
        here = self._peek()
        return Span(here.line, here.column, here.line, here.column)

    def _extend_span(self, start: Span) -> Span:
        here = self._last()
        return Span(
            start.start_line,
            start.start_column,
            here.line,
            here.column + len(here.text),
        )

    def _get_dotted_module_name(self, first: Token) -> list[str]:
        parts = [first.text]

        while self._match(TokenKind.DOT):
            ident = self._expect(TokenKind.IDENT, "[PAR-0300] expected identifier after '.' in module name", )
            parts.append(ident.text)
        return parts

    def _try_parse_qualified_name(self) -> Optional[tuple[list[str], Optional[list[str]], Token]]:
        if not self._check(TokenKind.IDENT):
            return None
        saved = self.index
        first = self._advance()
        parts = [first.text]
        while self._match(TokenKind.DOT):
            if not self._check(TokenKind.IDENT):
                self.index = saved
                return None
            parts.append(self._advance().text)
        if not self._match(TokenKind.DOUBLE_COLON):
            self.index = saved
            return None
        name_tok = self._expect(TokenKind.IDENT, "[PAR-0401] expected identifier after '::'")
        # Collect additional ::Ident segments (overqualified names like color::Color::Red)
        qualifier: list[str] = []
        while self._match(TokenKind.DOUBLE_COLON):
            qualifier.append(name_tok.text)
            name_tok = self._expect(TokenKind.IDENT, "[PAR-0401] expected identifier after '::'")
        return parts, qualifier if qualifier else None, name_tok

    # --- entry point ---

    def parse_module(self, filename: Optional[str] = None) -> Module:
        # module <Ident ( "." Ident )*> ;

        if filename is not None:
            self.filename = filename

        start = self._span_start()
        self._expect(TokenKind.MODULE, "[PAR-0310] expected 'module'")

        first_mod = self._expect(TokenKind.IDENT, "[PAR-0311] expected module name")
        mod_parts = self._get_dotted_module_name(first_mod)

        self._expect(TokenKind.SEMI, "[PAR-0312] expected ';' after module name")
        module_name = ".".join(mod_parts)

        imports: List[Import] = []
        # import <Ident ( "." Ident )*> ;
        while self._match(TokenKind.IMPORT):
            first = self._expect(TokenKind.IDENT, "[PAR-0320] expected imported module name")
            parts = self._get_dotted_module_name(first)

            self._expect(TokenKind.SEMI, "[PAR-0321] expected ';' after import")
            imports.append(Import(".".join(parts)))

        decls: List[TopLevelDecl] = []
        while not self._at_end():
            decls.append(self._parse_top_level_decl())

        return Module(module_name, imports, decls, span=self._extend_span(start), filename=filename)

    # --- top-level declarations ---

    def _parse_top_level_decl(self) -> TopLevelDecl:
        if self._check(TokenKind.EXTERN):
            return self._parse_extern_func()
        if self._check(TokenKind.FUNC):
            return self._parse_function(is_extern=False)
        if self._check(TokenKind.STRUCT):
            return self._parse_struct()
        if self._check(TokenKind.ENUM):
            return self._parse_enum()
        if self._check(TokenKind.TYPE):
            return self._parse_type_alias()
        if self._check(TokenKind.LET):
            return self._parse_top_level_let()
        raise ParseError(f"[PAR-0020] unexpected token in top level: {self._peek()}", self._peek(), self.filename)

    def _parse_extern_func(self) -> FuncDecl:
        self._expect(TokenKind.EXTERN, "[PAR-0030] expected 'extern'")
        return self._parse_function(is_extern=True)

    def _parse_function(self, is_extern: bool) -> FuncDecl:
        start = self._span_start()
        self._expect(TokenKind.FUNC, "[PAR-0040] expected 'func'")
        name_tok = self._expect(TokenKind.IDENT, "[PAR-0041] expected function name")
        self._expect(TokenKind.LPAREN, "[PAR-0042] expected '('")
        params: List[Param] = []
        if not self._check(TokenKind.RPAREN):
            while True:
                param_name = self._expect(TokenKind.IDENT, "[PAR-0043] expected parameter name")
                self._expect(TokenKind.COLON, "[PAR-0044] expected ':' after parameter name")
                param_type = self._parse_type()
                params.append(Param(param_name.text, param_type))
                if not self._match(TokenKind.COMMA):
                    break
        self._expect(TokenKind.RPAREN, "[PAR-0045] expected ')' after parameters")

        # no -> means void return type
        if not self._match(TokenKind.ARROW_FUNC):
            ret_type = TypeRef("void", 0, False, span=self._extend_span(start))

        else:
            ret_type = self._parse_type()

        if is_extern:
            self._expect(TokenKind.SEMI, "[PAR-0046] expected ';' after extern function decl")
            return FuncDecl(name_tok.text, params, ret_type, body=Block([]), is_extern=True,
                            span=self._extend_span(start))

        body = self._parse_block()
        return FuncDecl(name_tok.text, params, ret_type, body=body, is_extern=False, span=self._extend_span(start))

    def _parse_struct(self) -> StructDecl:
        start = self._span_start()
        self._expect(TokenKind.STRUCT, "[PAR-0050] expected 'struct'")
        name_tok = self._expect(TokenKind.IDENT, "[PAR-0051] expected struct name")
        self._expect(TokenKind.LBRACE, "[PAR-0052] expected '{' after struct name")
        fields: List[FieldDecl] = []
        while not self._check(TokenKind.RBRACE):
            field_name = self._expect(TokenKind.IDENT, "[PAR-0053] expected field name")
            self._expect(TokenKind.COLON, "[PAR-0054] expected ':' after field name")
            field_type = self._parse_type()
            self._expect(TokenKind.SEMI, "[PAR-0055] expected ';' after field declaration")
            fields.append(FieldDecl(field_name.text, field_type))
        self._expect(TokenKind.RBRACE, "[PAR-0056] expected '}' after struct body")
        return StructDecl(name_tok.text, fields, span=self._extend_span(start))

    def _parse_enum(self) -> EnumDecl:
        start = self._span_start()
        self._expect(TokenKind.ENUM, "[PAR-0060] expected 'enum'")
        name_tok = self._expect(TokenKind.IDENT, "[PAR-0061] expected enum name")
        self._expect(TokenKind.LBRACE, "[PAR-0062] expected '{' after enum name")
        variants: List[EnumVariant] = []
        while not self._check(TokenKind.RBRACE):
            var_name_tok = self._expect(TokenKind.IDENT, "[PAR-0063] expected variant name")
            fields: List[FieldDecl] = []
            if self._match(TokenKind.LPAREN):
                if not self._check(TokenKind.RPAREN):
                    while True:
                        fname = self._expect(TokenKind.IDENT, "[PAR-0064] expected variant field name")
                        self._expect(TokenKind.COLON, "[PAR-0065] expected ':'")
                        ftype = self._parse_type()
                        fields.append(FieldDecl(fname.text, ftype))
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN, "[PAR-0066] expected ')' after variant payload")
            self._expect(TokenKind.SEMI, "[PAR-0067] expected ';' after variant")
            variants.append(EnumVariant(var_name_tok.text, fields))
        self._expect(TokenKind.RBRACE, "[PAR-0068] expected '}' after enum body")
        return EnumDecl(name_tok.text, variants, span=self._extend_span(start))

    def _parse_type_alias(self) -> TypeAliasDecl:
        start = self._span_start()
        self._expect(TokenKind.TYPE, "[PAR-0070] expected type name")
        name_tok = self._expect(TokenKind.IDENT, "[PAR-0071] expected type alias name")
        self._expect(TokenKind.EQ, "[PAR-0072] expected '=' in type alias")
        target = self._parse_type()
        self._expect(TokenKind.SEMI, "[PAR-0073] expected ';' after type alias")
        return TypeAliasDecl(name_tok.text, target, span=self._extend_span(start))

    def _parse_top_level_let(self) -> LetDecl:
        start = self._span_start()
        self._expect(TokenKind.LET, "[PAR-0080] expected 'let'")
        name_tok = self._expect_variable_name("[PAR-0081] expected variable name")

        type_ref = None
        if self._match(TokenKind.COLON):
            type_ref = self._parse_type()

        self._expect(TokenKind.EQ, "[PAR-0082] expected '=' in let binding")
        value = self._parse_expr()
        self._expect(TokenKind.SEMI, "[PAR-0083] expected ';' after let declaration")
        return LetDecl(name_tok.text, type_ref, value, span=self._extend_span(start))

    # --- types ---

    def _parse_type(self) -> TypeRef:
        start = self._span_start()
        module_path = None
        name_qualifier = None
        name_tok = None
        qualified = self._try_parse_qualified_name()
        if qualified is not None:
            module_path, name_qualifier, name_tok = qualified
        else:
            name_tok = self._expect(TokenKind.IDENT, "[PAR-0400] expected type name")
        pointer_depth = 0
        while self._match(TokenKind.STAR):
            pointer_depth += 1
        is_nullable = False
        if self._match(TokenKind.QUESTION):
            is_nullable = True
        if self._peek().kind is TokenKind.LBRACKET:
            raise ParseError("[PAR-9401] array types not yet supported: use pointers and [] indexing in expressions",
                             self._peek(), self.filename)
        return TypeRef(name_tok.text, pointer_depth, is_nullable, module_path=module_path,
                       name_qualifier=name_qualifier, span=self._extend_span(start))

    # --- blocks and statements ---

    def _parse_block(self) -> Block:
        start = self._span_start()
        self._expect(TokenKind.LBRACE, "[PAR-0090] expected '{' to start block")
        stmts: List[Stmt] = []
        while not self._check(TokenKind.RBRACE):
            stmts.append(self._parse_stmt())
        self._expect(TokenKind.RBRACE, "[PAR-0091] expected '}' after block")
        return Block(stmts, span=self._extend_span(start))

    def _parse_stmt(self) -> Stmt:
        if self._check(TokenKind.LBRACE):
            return self._parse_block()  # nested block as statement
        elif self._check(TokenKind.IF):
            return self._parse_if_stmt()
        elif self._check(TokenKind.MATCH):
            return self._parse_match_stmt()
        elif self._check(TokenKind.CASE):
            return self._parse_case_stmt()
        elif self._check(TokenKind.WHILE):
            return self._parse_while_stmt()
        elif self._check(TokenKind.FOR):
            return self._parse_for_stmt()
        elif self._check(TokenKind.WITH):
            return self._parse_with_stmt()

        simple_stmt = self._parse_simple_stmt()

        self._expect(TokenKind.SEMI, "[PAR-0100] expected ';' after statement")

        return simple_stmt

    def _parse_simple_stmt(self) -> Stmt:
        start = self._span_start()

        if self._check(TokenKind.LET):
            simple_stmt = self._parse_let_stmt()
        elif self._check(TokenKind.BREAK):
            simple_stmt = self._parse_break_stmt()
        elif self._check(TokenKind.CONTINUE):
            simple_stmt = self._parse_continue_stmt()
        elif self._check(TokenKind.RETURN):
            simple_stmt = self._parse_return_stmt()
        elif self._check(TokenKind.DROP):
            simple_stmt = self._parse_drop_stmt()
        else:
            # otherwise: either assignment or expr-stmt
            expr = self._parse_expr()
            if self._match(TokenKind.EQ):
                value = self._parse_expr()
                simple_stmt = AssignStmt(expr, value, span=self._extend_span(start))
            else:
                simple_stmt = ExprStmt(expr, span=self._extend_span(start))

        return simple_stmt

    def _parse_let_stmt(self) -> LetStmt:
        start = self._span_start()
        self._expect(TokenKind.LET, "[PAR-0110] expected 'let'")
        name_tok = self._expect_variable_name("[PAR-0111] expected variable name")

        type_ref = None
        if self._match(TokenKind.COLON):
            type_ref = self._parse_type()

        self._expect(TokenKind.EQ, "[PAR-0112] expected '=' in let binding")
        value = self._parse_expr()
        return LetStmt(name_tok.text, type_ref, value, span=self._extend_span(start))

    def _parse_if_stmt(self) -> IfStmt:
        start = self._span_start()
        self._expect(TokenKind.IF, "[PAR-0120] expected 'if'")
        self._expect(TokenKind.LPAREN, "[PAR-0121] expected '(' after 'if'")
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN, "[PAR-0122] expected ')' after condition")
        then_stmt = self._parse_stmt()
        else_stmt: Optional[Stmt] = None
        if self._match(TokenKind.ELSE):
            else_stmt = self._parse_stmt()
        return IfStmt(cond, then_stmt, else_stmt, span=self._extend_span(start))

    def _parse_while_stmt(self) -> WhileStmt:
        start = self._span_start()
        self._expect(TokenKind.WHILE, "[PAR-0130] expected 'while'")
        self._expect(TokenKind.LPAREN, "[PAR-0131] expected '('")
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN, "[PAR-0132] expected ')'")

        body = self._parse_block()

        return WhileStmt(cond, body, span=self._extend_span(start))

    def _parse_for_stmt(self) -> Stmt:
        start = self._span_start()
        self._expect(TokenKind.FOR, "[PAR-0140] expected 'for'")
        self._expect(TokenKind.LPAREN, "[PAR-0141] expected '(' after 'for'")
        # Initialization
        if self._check(TokenKind.SEMI):
            self._advance()  # consume the ';'
            init = None
        else:
            init = self._parse_simple_stmt()
            self._expect(TokenKind.SEMI, "[PAR-0142] expected ';' after for loop initialization")
        # Condition
        if self._check(TokenKind.SEMI):
            self._advance()  # consume the ';'
            cond = None
        else:
            cond = self._parse_expr()
            self._expect(TokenKind.SEMI, "[PAR-0143] expected ';' after for loop condition")
        # Post-iteration
        if self._check(TokenKind.RPAREN):
            post = None
        else:
            post = self._parse_simple_stmt()

        self._expect(TokenKind.RPAREN, "[PAR-0144] expected ')' after for loop clauses")

        body = self._parse_block()

        return ForStmt(init, cond, post, body, span=self._extend_span(start))

    def _parse_return_stmt(self) -> ReturnStmt:
        start = self._span_start()
        self._expect(TokenKind.RETURN, "[PAR-0150] expected 'return'")
        if self._check(TokenKind.SEMI):
            return ReturnStmt(None, span=self._extend_span(start))
        value = self._parse_expr()
        return ReturnStmt(value, span=self._extend_span(start))

    def _parse_drop_stmt(self) -> DropStmt:
        start = self._span_start()
        self._expect(TokenKind.DROP, "[PAR-0160] expected 'drop'")
        name_tok = self._expect_variable_name("[PAR-0161] expected variable name after 'drop'")
        return DropStmt(name_tok.text, span=self._extend_span(start))

    def _parse_match_stmt(self) -> MatchStmt:
        start = self._span_start()
        self._expect(TokenKind.MATCH, "[PAR-0170] expected 'match'")
        self._expect(TokenKind.LPAREN, "[PAR-0171] expected '('")
        expr = self._parse_expr()
        self._expect(TokenKind.RPAREN, "[PAR-0172] expected ')'")
        self._expect(TokenKind.LBRACE, "[PAR-0173] expected '{' after match expression")
        arms: List[MatchArm] = []

        while not self._check(TokenKind.RBRACE):
            arm_start = self._span_start()
            pattern = self._parse_pattern()
            self._expect(TokenKind.ARROW_MATCH, "[PAR-0174] expected '=>' in match arm")
            body = self._parse_block()
            arms.append(MatchArm(pattern, body, span=self._extend_span(arm_start)))
        self._expect(TokenKind.RBRACE, "[PAR-0175] expected '}' after match")

        # Check for duplicate patterns/variant names or no arms
        if len(arms) != len(set(arm.pattern.name for arm in arms
                                if isinstance(arm.pattern, VariantPattern))
                                    .union("_" for arm in arms
                                           if isinstance(arm.pattern, WildcardPattern))):
            raise ParseError("[PAR-0176] duplicate variant patterns in match statement", self._peek(), self.filename)

        if len(arms) == 0:
            raise ParseError("[PAR-0177] match statement must have at least one arm", self._peek(), self.filename)

        return MatchStmt(expr, arms, span=self._extend_span(start))

    def _parse_with_item(self) -> WithItem:
        start = self._span_start()
        init = self._parse_simple_stmt()
        cleanup = None
        if self._match(TokenKind.ARROW_MATCH):
            cleanup = self._parse_simple_stmt()
        return WithItem(init, cleanup, span=self._extend_span(start))

    def _parse_with_stmt(self) -> WithStmt:
        start = self._span_start()
        self._expect(TokenKind.WITH, "[PAR-0500] expected 'with'")
        self._expect(TokenKind.LPAREN, "[PAR-0501] expected '(' after 'with'")
        items = []
        while True:
            items.append(self._parse_with_item())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN, "[PAR-0502] expected ')' after with items")
        body = self._parse_block()
        cleanup_body = None
        if self._match(TokenKind.CLEANUP):
            cleanup_body = self._parse_block()
        # Validate constraints
        has_arrows = any(it.cleanup is not None for it in items)
        has_bare = any(it.cleanup is None for it in items)
        if has_arrows and has_bare:
            raise ParseError("[PAR-0503] 'with': all items must use '=>' or none", self._peek(), self.filename)
        if has_arrows and cleanup_body is not None:
            raise ParseError("[PAR-0504] 'with': cannot have both '=>' and cleanup block", self._peek(), self.filename)
        if not has_arrows and cleanup_body is None:
            raise ParseError("[PAR-0505] 'with': cleanup block required when '=>' is not used", self._peek(),
                             self.filename)
        return WithStmt(items, body, cleanup_body, span=self._extend_span(start))

    def _parse_case_stmt(self) -> CaseStmt:
        start = self._span_start()
        self._expect(TokenKind.CASE, "[PAR-0230] expected 'case'")
        self._expect(TokenKind.LPAREN, "[PAR-0231] expected '('")
        expr = self._parse_expr()
        self._expect(TokenKind.RPAREN, "[PAR-0232] expected ')'")
        self._expect(TokenKind.LBRACE, "[PAR-0233] expected '{' after 'case' expression")
        arms: List[CaseArm] = []
        else_arm: Optional[CaseElse] = None
        seen_else = False

        while not self._check(TokenKind.RBRACE):
            if self._match(TokenKind.ELSE):
                if seen_else:
                    raise ParseError("[PAR-0236] duplicate 'else' arm in 'case' statement", self._peek(), self.filename)
                else_start = self._span_start()
                if self._match(TokenKind.ARROW_MATCH):
                    raise ParseError("[PAR-0237] '=>' not allowed in 'else' arm", self._peek(), self.filename)
                body = self._parse_stmt()
                else_arm = CaseElse(body, span=self._extend_span(else_start))
                seen_else = True
                continue
            else:
                if seen_else:
                    raise ParseError("[PAR-0234] value arm cannot appear after 'else' in 'case' statement",
                                     self._peek(), self.filename)
                arm_start = self._span_start()
                literal = self._parse_case_literal()
                self._expect(TokenKind.ARROW_MATCH, "[PAR-0235] expected '=>' in 'case' arm")
                body = self._parse_stmt()
                arms.append(CaseArm(literal, body, span=self._extend_span(arm_start)))
                continue

        self._expect(TokenKind.RBRACE, "[PAR-0239] expected '}' after 'case' statement")

        if len(arms) == 0 and else_arm is None:
            raise ParseError("[PAR-0240] 'case' statement must have at least one arm", self._peek(), self.filename)

        return CaseStmt(expr, arms, else_arm, span=self._extend_span(start))

    def _parse_case_literal(self) -> Expr:
        start = self._span_start()
        tok = self._peek()
        if self._match(TokenKind.INT):
            return IntLiteral(int(tok.text), span=self._extend_span(start))
        if self._match(TokenKind.BYTE):
            return ByteLiteral(tok.text, span=self._extend_span(start))
        if self._match(TokenKind.STRING):
            return StringLiteral(tok.text, span=self._extend_span(start))
        if self._match(TokenKind.TRUE):
            return BoolLiteral(True, span=self._extend_span(start))
        if self._match(TokenKind.FALSE):
            return BoolLiteral(False, span=self._extend_span(start))
        raise ParseError("[PAR-0241] expected literal in 'case' arm", tok, self.filename)

    def _parse_pattern(self) -> Pattern:
        start = self._span_start()
        # Wildcard '_'
        if self._match(TokenKind.UNDERSCORE):
            return WildcardPattern(span=self._extend_span(start))
        # Variant pattern: Name(...) or just Name
        if self._check(TokenKind.IDENT):
            module_path = None
            name_qualifier = None
            name_tok = None
            qualified = self._try_parse_qualified_name()
            if qualified is not None:
                module_path, name_qualifier, name_tok = qualified
            else:
                name_tok = self._advance()
            vars: List[str] = []
            if self._match(TokenKind.LPAREN):
                if not self._check(TokenKind.RPAREN):
                    while True:
                        var_tok = self._expect_variable_name("[PAR-0180] expected pattern variable name")
                        vars.append(var_tok.text)
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN, "[PAR-0181] expected ')' in pattern")
            return VariantPattern(name_tok.text, vars, module_path=module_path,
                                  name_qualifier=name_qualifier, span=self._extend_span(start))
        raise ParseError(f"[PAR-0182] unexpected token in pattern: {self._peek()}", self._peek(), self.filename)

    def _parse_break_stmt(self) -> Stmt:
        start = self._span_start()
        self._expect(TokenKind.BREAK, "[PAR-0190] expected 'break'")
        return BreakStmt(span=self._extend_span(start))

    def _parse_continue_stmt(self):
        start = self._span_start()
        self._expect(TokenKind.CONTINUE, "[PAR-0200] expected 'continue'")
        return ContinueStmt(span=self._extend_span(start))

    # --- expressions with precedence ---

    def _parse_expr(self) -> Expr:
        return self._parse_or_expr()

    _RESERVED_BINARY_OPS = {
        TokenKind.AMP: "'&' (bitwise AND)",
        TokenKind.PIPE: "'|' (bitwise OR)",
        TokenKind.CARET: "'^' (bitwise XOR)",
        TokenKind.LSHIFT: "'<<' (left shift)",
        TokenKind.RSHIFT: "'>>' (right shift)",
    }

    def _check_reserved_binary_op(self) -> None:
        """Raise a diagnostic if the next token is a reserved binary operator."""
        tok = self._peek()
        desc = self._RESERVED_BINARY_OPS.get(tok.kind)
        if desc is not None:
            raise ParseError(
                f"[PAR-0226] {desc} operator is not yet supported",
                tok,
                self.filename,
            )

    def _parse_or_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_and_expr()
        self._check_reserved_binary_op()
        while self._match(TokenKind.OROR):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_and_expr()
            self._check_reserved_binary_op()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_and_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_equality_expr()
        self._check_reserved_binary_op()
        while self._match(TokenKind.ANDAND):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_equality_expr()
            self._check_reserved_binary_op()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_equality_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_rel_expr()
        while self._match(TokenKind.EQEQ, TokenKind.NE):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_rel_expr()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_rel_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_add_expr()
        while self._match(TokenKind.LT, TokenKind.GT, TokenKind.LE, TokenKind.GE):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_add_expr()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_add_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_mul_expr()
        while self._match(TokenKind.PLUS, TokenKind.MINUS):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_mul_expr()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_mul_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_unary_expr()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.MODULO):
            op_tok = self.tokens[self.index - 1]
            right = self._parse_unary_expr()
            expr = BinaryOp(op_tok.text, expr, right, span=self._extend_span(start))
        return expr

    def _parse_unary_expr(self) -> Expr:
        start = self._span_start()
        # prefix unary operators: !, -, *
        if self._match(TokenKind.BANG, TokenKind.MINUS, TokenKind.STAR):
            op_tok = self.tokens[self.index - 1]
            operand = self._parse_unary_expr()
            return UnaryOp(op_tok.text, operand, span=self._extend_span(start))
        # reserved prefix operator: ~ (bitwise NOT)
        if self._check(TokenKind.TILDE):
            tok = self._peek()
            raise ParseError(
                "[PAR-0226] '~' (bitwise NOT) operator is not yet supported",
                tok,
                self.filename,
            )
        return self._parse_cast_expr()

    def _parse_cast_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_postfix_expr()
        if self._match(TokenKind.AS):
            target_type = self._parse_type()
            return CastExpr(expr, target_type, span=self._extend_span(start))
        return expr

    def _parse_postfix_expr(self) -> Expr:
        start = self._span_start()
        expr = self._parse_primary_expr()
        while True:
            if self._match(TokenKind.LPAREN):
                # call
                args: List[Expr] = []
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._parse_call_argument())  # account for type expressions in argument position
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN, "[PAR-0210] expected ')' after arguments")
                expr = CallExpr(expr, args, span=self._extend_span(start))
                continue
            if self._match(TokenKind.LBRACKET):
                index = self._parse_expr()
                self._expect(TokenKind.RBRACKET, "[PAR-0211] expected ']' after index")
                expr = IndexExpr(expr, index, span=self._extend_span(start))
                continue
            if self._match(TokenKind.DOT):
                field_tok = self._expect(TokenKind.IDENT, "[PAR-0212] expected field name after '.'")
                expr = FieldAccessExpr(expr, field_tok.text, span=self._extend_span(start))
                continue
            if self._match(TokenKind.QUESTION):
                expr = TryExpr(expr, span=self._extend_span(start))
                continue
            break
        return expr

    # NEW: Parse call argument - tries type first in unambiguous cases
    def _parse_call_argument(self) -> Expr:
        """
        Parse a function call argument.

        In argument position, we can have either expressions or type expressions.
        We parse as TypeExpr only when syntactically unambiguous:
          - Builtin type name: int, byte, bool, string, void
          - Any name followed by * or ?: Point*, int?, Foo*?
        """
        start = self._span_start()

        if self._is_unambiguous_type_start():
            type_ref = self._parse_type()
            return TypeExpr(type_ref=type_ref, span=self._extend_span(start))

        return self._parse_expr()

    def _is_builtin_type_name(self) -> bool:
        """Check if current token is a builtin type keyword."""
        if not self._check(TokenKind.IDENT):
            return False
        return self._peek().text in ("int", "byte", "bool", "string", "void")

    def _lookahead_is_type_suffix(self) -> bool:
        """Check if there's a * or ? immediately after current identifier (for type disambiguation)."""
        saved = self.index
        self._advance()  # skip the identifier
        result = self._check(TokenKind.STAR) or self._check(TokenKind.QUESTION)
        self.index = saved
        return result

    def _is_unambiguous_type_start(self) -> bool:
        """
        In call argument position, check if this is unambiguously a type.

        Unambiguous type cases:
          - Builtin type name (int, byte, bool, string, void)
          - Ident followed by * or ? suffixes, ending at argument boundary (, or ))

        Examples:
          sizeof(int*)     → int is builtin → type
          sizeof(Point*)   → Point* followed by ) → type
          sizeof(a * b)    → a* followed by b, not boundary → expression
          sizeof(Point)    → Point with no suffix → ambiguous, defaults to expr
        """
        # Builtin type names are always types in argument position
        if self._is_builtin_type_name():
            return True

        if not self._check(TokenKind.IDENT):
            return False

        # Look ahead: Ident, then any * or ?, then check for argument boundary
        saved = self.index
        self._advance()  # skip identifier

        has_suffix = False
        while self._check(TokenKind.STAR) or self._check(TokenKind.QUESTION):
            has_suffix = True
            self._advance()

        # At argument boundary?
        at_boundary = self._check(TokenKind.RPAREN) or self._check(TokenKind.COMMA)

        self.index = saved

        # Type only if: has suffix AND at argument boundary
        return has_suffix and at_boundary

    def _parse_primary_expr(self) -> Expr:
        start = self._span_start()
        tok = self._peek()

        # 'new' constructor
        if self._match(TokenKind.NEW):
            type_ref = self._parse_type()  # Full type, not just identifier
            args: List[Expr] = []
            if self._match(TokenKind.LPAREN):
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._parse_call_argument())
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN, "[PAR-0223] expected ')' after arguments to 'new'")
            return NewExpr(type_ref, args, span=self._extend_span(start))

        # Literals
        if self._match(TokenKind.INT):
            return IntLiteral(int(tok.text), span=self._extend_span(start))
        if self._match(TokenKind.BYTE):
            return ByteLiteral(tok.text, span=self._extend_span(start))
        if self._match(TokenKind.STRING):
            return StringLiteral(tok.text, span=self._extend_span(start))
        if self._match(TokenKind.TRUE):
            return BoolLiteral(True, span=self._extend_span(start))
        if self._match(TokenKind.FALSE):
            return BoolLiteral(False, span=self._extend_span(start))
        if self._match(TokenKind.NULL):
            return NullLiteral(span=self._extend_span(start))

        # Identifier (variable reference, or ambiguous type name resolved later)
        if self._check(TokenKind.IDENT):
            qualified = self._try_parse_qualified_name()
            if qualified is not None:
                module_path, name_qualifier, name_tok = qualified
                return VarRef(name_tok.text, module_path=module_path,
                              name_qualifier=name_qualifier, span=self._extend_span(start))
            name_tok = self._advance()
            return VarRef(name_tok.text, span=self._extend_span(start))

        # Parenthesized expression
        if self._match(TokenKind.LPAREN):
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN, "[PAR-0224] expected ')' after expression")
            return ParenExpr(inner, span=self._extend_span(start))

        raise ParseError(f"[PAR-0225] unexpected token in expression: {tok.kind}:'{tok.text}'", tok, self.filename)
