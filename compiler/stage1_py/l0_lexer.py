#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


# ==========================
# Tokens and lexer
# ==========================

class TokenKind(Enum):
    # Special
    EOF = auto()

    IDENT = auto()  # identifier, e.g. i, name, etc.
    UNDERSCORE = auto()  # "_"
    INT = auto()  # integer literal, e.g. 42, -7, etc.
    BYTE = auto()  # octet literal, e.g. 'a', '\n', etc.
    STRING = auto()  # string literal, e.g. "hello world", etc.

    # Keywords
    MODULE = auto()
    IMPORT = auto()
    FUNC = auto()
    STRUCT = auto()
    ENUM = auto()
    TYPE = auto()
    EXTERN = auto()
    LET = auto()
    RETURN = auto()
    MATCH = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    AS = auto()

    NEW = auto()
    DROP = auto()
    WITH = auto()
    CLEANUP = auto()

    # Punctuation / operators
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COMMA = auto()  # ,
    SEMI = auto()  # ;
    COLON = auto()  # :
    DOUBLE_COLON = auto()  # ::
    ARROW_FUNC = auto()  # ->
    ARROW_MATCH = auto()  # =>
    EQ = auto()  # =
    PLUS = auto()
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    MODULO = auto()  # %
    LT = auto()  # <
    GT = auto()  # >
    LE = auto()  # <
    GE = auto()  # <=
    EQEQ = auto()  # ==
    NE = auto()  # !=
    ANDAND = auto()  # &&
    OROR = auto()  # ||
    BANG = auto()  # !
    QUESTION = auto()  # ?
    DOT = auto()  # .

    # Reserved operators (not yet supported, lexed for diagnostics)
    AMP = auto()  # &
    PIPE = auto()  # |
    CARET = auto()  # ^
    TILDE = auto()  # ~
    LSHIFT = auto()  # <<
    RSHIFT = auto()  # >>

    FUTURE_EXTENSION = auto()  # placeholder for future tokens


KEYWORDS = {
    "module": TokenKind.MODULE,
    "import": TokenKind.IMPORT,
    "func": TokenKind.FUNC,
    "struct": TokenKind.STRUCT,
    "enum": TokenKind.ENUM,
    "type": TokenKind.TYPE,
    "extern": TokenKind.EXTERN,
    "let": TokenKind.LET,
    "return": TokenKind.RETURN,
    "match": TokenKind.MATCH,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "null": TokenKind.NULL,
    "as": TokenKind.AS,
    "new": TokenKind.NEW,
    "drop": TokenKind.DROP,
    "with": TokenKind.WITH,
    "cleanup": TokenKind.CLEANUP,
    "void": TokenKind.IDENT,
    "bool": TokenKind.IDENT,
    "string": TokenKind.IDENT,
    "int": TokenKind.IDENT,
    "byte": TokenKind.IDENT,
    "tiny": TokenKind.FUTURE_EXTENSION,
    "short": TokenKind.FUTURE_EXTENSION,
    "long": TokenKind.FUTURE_EXTENSION,
    "ushort": TokenKind.FUTURE_EXTENSION,
    "uint": TokenKind.FUTURE_EXTENSION,
    "ulong": TokenKind.FUTURE_EXTENSION,
    "float": TokenKind.FUTURE_EXTENSION,
    "double": TokenKind.FUTURE_EXTENSION,
    "in": TokenKind.FUTURE_EXTENSION,
    "const": TokenKind.FUTURE_EXTENSION,
}


@dataclass
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"{self.text!r}" if self.kind != TokenKind.EOF else "end-of-file"


@dataclass
class LexerError(Exception):
    message: str
    filename: str
    line: int
    column: int


def is_reserved_keyword(word: str) -> bool:
    return word in KEYWORDS


# Constants for escape sequence validation
OCT_CHARS = "01234567"
HEX_CHARS = "0123456789abcdefABCDEF"


class Lexer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.filename = filename
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1

    @classmethod
    def from_source(cls, source: str) -> "Lexer":
        return cls(source)

    # --- low-level char utilities ---

    def _at_end(self) -> bool:
        return self.index >= self.length

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.source[self.index]

    def _peek_next(self) -> str:
        if self.index + 1 >= self.length:
            return "\0"
        return self.source[self.index + 1]

    def _advance(self) -> str:
        c = self._peek()
        if not self._at_end():
            self.index += 1
            if c == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return c

    # --- main API ---

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.kind is TokenKind.EOF:
                break
        return tokens

    def _next_token(self) -> Token:
        self._skip_ws_and_comments()
        start_line, start_col = self.line, self.column

        if self._at_end():
            return Token(TokenKind.EOF, "", start_line, start_col)

        c = self._advance()

        # identifiers / keywords and underscore wildcard
        if c.isalpha() or c == "_":
            ident = [c]
            while self._peek().isalnum() or self._peek() == "_":
                ident.append(self._advance())
            text = "".join(ident)
            if text == "_":
                kind = TokenKind.UNDERSCORE
            else:
                kind = KEYWORDS.get(text, TokenKind.IDENT)
            return Token(kind, text, start_line, start_col)

        # numbers (only integers for now)
        if c.isdigit():
            text = self._read_number(c, start_col, start_line)
            return Token(TokenKind.INT, text, start_line, start_col)

        # strings
        if c == '"':
            text = self._read_string_literal()
            return Token(TokenKind.STRING, text, start_line, start_col)

        # byte / char literals
        if c == "'":
            text = self._read_byte_literal(start_col, start_line)
            return Token(TokenKind.BYTE, text, start_line, start_col)

        # punctuation / operators with lookahead

        if c == "-":
            if self._peek() == ">":
                self._advance()
                return Token(TokenKind.ARROW_FUNC, "->", start_line, start_col)
            elif self._peek().isdigit():
                text = self._read_number(self._advance(), start_col, start_line, is_negative=True)
                return Token(TokenKind.INT, text, start_line, start_col)
            return Token(TokenKind.MINUS, c, start_line, start_col)

        if c == "(":
            return Token(TokenKind.LPAREN, c, start_line, start_col)
        if c == ")":
            return Token(TokenKind.RPAREN, c, start_line, start_col)
        if c == "{":
            return Token(TokenKind.LBRACE, c, start_line, start_col)
        if c == "}":
            return Token(TokenKind.RBRACE, c, start_line, start_col)
        if c == "[":
            return Token(TokenKind.LBRACKET, c, start_line, start_col)
        if c == "]":
            return Token(TokenKind.RBRACKET, c, start_line, start_col)
        if c == ",":
            return Token(TokenKind.COMMA, c, start_line, start_col)
        if c == ";":
            return Token(TokenKind.SEMI, c, start_line, start_col)
        if c == ":":
            if self._peek() == ":":
                self._advance()
                return Token(TokenKind.DOUBLE_COLON, "::", start_line, start_col)
            return Token(TokenKind.COLON, c, start_line, start_col)
        if c == ".":
            return Token(TokenKind.DOT, c, start_line, start_col)
        if c == "?":
            return Token(TokenKind.QUESTION, c, start_line, start_col)

        if c == "=":
            nxt = self._peek()
            if nxt == ">":
                self._advance()
                return Token(TokenKind.ARROW_MATCH, "=>", start_line, start_col)
            if nxt == "=":
                self._advance()
                return Token(TokenKind.EQEQ, "==", start_line, start_col)
            return Token(TokenKind.EQ, c, start_line, start_col)

        if c == "!":
            if self._peek() == "=":
                self._advance()
                return Token(TokenKind.NE, "!=", start_line, start_col)
            return Token(TokenKind.BANG, c, start_line, start_col)

        if c == "<":
            if self._peek() == "=":
                self._advance()
                return Token(TokenKind.LE, "<=", start_line, start_col)
            if self._peek() == "<":
                self._advance()
                return Token(TokenKind.LSHIFT, "<<", start_line, start_col)
            return Token(TokenKind.LT, c, start_line, start_col)

        if c == ">":
            if self._peek() == "=":
                self._advance()
                return Token(TokenKind.GE, ">=", start_line, start_col)
            if self._peek() == ">":
                self._advance()
                return Token(TokenKind.RSHIFT, ">>", start_line, start_col)
            return Token(TokenKind.GT, c, start_line, start_col)

        if c == "&":
            if self._peek() == "&":
                self._advance()
                return Token(TokenKind.ANDAND, "&&", start_line, start_col)
            return Token(TokenKind.AMP, c, start_line, start_col)

        if c == "|":
            if self._peek() == "|":
                self._advance()
                return Token(TokenKind.OROR, "||", start_line, start_col)
            return Token(TokenKind.PIPE, c, start_line, start_col)

        if c == "^":
            return Token(TokenKind.CARET, c, start_line, start_col)
        if c == "~":
            return Token(TokenKind.TILDE, c, start_line, start_col)

        if c == "+":
            return Token(TokenKind.PLUS, c, start_line, start_col)
        if c == "*":
            return Token(TokenKind.STAR, c, start_line, start_col)
        if c == "/":
            return Token(TokenKind.SLASH, c, start_line, start_col)
        if c == "%":
            return Token(TokenKind.MODULO, c, start_line, start_col)

        raise LexerError(f"[LEX-0040] unexpected character {c!r} at {start_line}:{start_col}", self.filename, start_line,
                         start_col)

    def _read_byte_literal(self, start_col: int, start_line: int) -> str:
        chars: List[str] = []
        ch = self._peek()

        if ch == "\0" or ch == "\n":
            raise LexerError("[LEX-0020] unterminated char literal", self.filename, self.line, self.column)

        if ch == "\\":
            chars.append(self._read_valid_char_escape())
        else:
            chars.append(self._advance())

        if self._peek() != "'":
            raise LexerError("[LEX-0021] invalid char literal, expected closing single quote", self.filename, self.line, self.column)

        self._advance()  # consume closing '

        text = "".join(chars)

        # validate that the char literal **represents a single byte**
        if text.startswith("\\x"):
            # Hex escape: \xH+ (variable length, C rules)
            hex_digits = text[2:]
            value = int(hex_digits, 16)

            if value > 255:
                raise LexerError(
                    f"[LEX-0031] character literal hex escape out of range (0-255): '\\x{hex_digits}' = {value}",
                    self.filename, start_line, start_col
                )
        elif text.startswith("\\") and len(text) > 1 and text[1] in OCT_CHARS:
            # octal escape (range was checked during escape parsing)
            pass
        else:
            utf8string = text.encode("utf-8").decode("unicode_escape").encode("utf-8")
            if len(utf8string) != 1:
                raise LexerError("[LEX-0030] character literal must represent a single byte", self.filename, start_line,
                                 start_col)

            # if text is a \u or \U escape, convert it to the \xXX form to be C99-compatible
            if text.startswith("\\u") or text.startswith("\\U"):
                byte_value = utf8string[0]
                text = f"\\x{byte_value:02x}"
        return text

    def _read_string_literal(self) -> str:
        chars: List[str] = []
        while True:
            ch = self._peek()

            if ch == "\0" or ch == "\n":
                raise LexerError("[LEX-0010] unterminated string literal", self.filename, self.line, self.column)
            if ch == "\\":
                chars.append(self._read_valid_char_escape())
                continue
            if ch == '"':
                self._advance()
                break

            chars.append(self._advance())

        text = "".join(chars)
        return text

    def _read_valid_char_escape(self) -> str:
        chars: List[str] = [self._advance()]
        esc = self._peek()
        if esc in ("\\", "'", '"', "?", "a", "b", "f", "n", "r", "t", "v"):
            chars.append(self._advance())  # valid escapes

        elif esc == "x":  # hex escape of the form \xX+ (where X+ is one or more hex digits)
            chars.append(self._advance())  # append 'x'
            next_ch = self._peek()  # expect at least one hex digit
            if next_ch in HEX_CHARS:
                chars.append(self._advance())
            else:
                raise LexerError(f"[LEX-0050] invalid hex escape sequence", self.filename, self.line, self.column)
            while True:  # consume additional hex digits
                next_ch = self._peek()
                if next_ch in HEX_CHARS:
                    chars.append(self._advance())
                else:
                    break

        elif esc == "u":  # unicode escape of the form \uXXXX
            chars.append(self._advance())  # append 'u'
            for _ in range(4):  # expect exactly four hex digits
                next_ch = self._peek()
                if next_ch in HEX_CHARS:
                    chars.append(self._advance())
                else:
                    raise LexerError(f"[LEX-0051] invalid unicode escape sequence (\\u)", self.filename, self.line, self.column)

        elif esc == "U":  # unicode escape of the form \UXXXXXXXX
            chars.append(self._advance())  # append 'U'
            for _ in range(8):  # expect exactly eight hex digits
                next_ch = self._peek()
                if next_ch in HEX_CHARS:
                    chars.append(self._advance())
                else:
                    raise LexerError(f"[LEX-0052] invalid unicode escape sequence (\\U)", self.filename, self.line, self.column)

        elif esc in OCT_CHARS:  # octal escape
            chars.append(self._advance())  # append the first octal digit
            for _ in range(2):  # expect one to three octal digits total
                next_ch = self._peek()
                if next_ch in OCT_CHARS:
                    chars.append(self._advance())
                else:
                    break
            # check that the octal value is in range 0-255
            oct_value = int("".join(chars[1:]), 8)
            if oct_value > 255:
                raise LexerError(f"[LEX-0053] octal escape sequence out of range 0..255", self.filename, self.line, self.column)
        else:
            raise LexerError(f"[LEX-0059] unknown escape sequence \\{esc}", self.filename, self.line, self.column)

        return "".join(chars)

    def _read_number(self, c: str, start_col: int, start_line: int, is_negative: bool = False) -> str:
        digits = [c]
        while self._peek().isdigit():
            digits.append(self._advance())
        text = "".join(digits)
        if is_negative:
            text = "-" + text
        if self._peek().isalpha() or self._peek() == "_":
            raise LexerError(f"[LEX-0061] invalid character '{self._peek()}' after integer literal",
                             self.filename, self.line, self.column)
        value = int(text)
        if value > 2 ** 31 - 1 or value < -2 ** 31:
            raise LexerError(f"[LEX-0060] integer literal '{value}' exceeds 32-bit signed range",
                             self.filename, start_line, start_col)
        return text

    def _skip_ws_and_comments(self) -> None:
        while True:
            c = self._peek()
            if c in (" ", "\t", "\r", "\n"):
                self._advance()
                continue
            if c == "/" and self._peek_next() == "/":
                # line comment
                self._advance()  # '/'
                self._advance()  # second '/'
                while self._peek() not in ("\n", "\0"):
                    self._advance()
                continue
            if c == "/" and self._peek_next() == "*":
                # block comment
                self._advance()  # '/'
                self._advance()  # '*'
                while True:
                    if self._at_end():
                        raise LexerError("[LEX-0070] unterminated block comment", self.filename, self.line, self.column)
                    if self._peek() == "*" and self._peek_next() == "/":
                        self._advance()  # '*'
                        self._advance()  # '/'
                        break
                    self._advance()
                continue
            break
