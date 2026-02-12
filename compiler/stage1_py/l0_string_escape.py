#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

"""
String escape helpers shared by semantic checks and C codegen.

Lexer keeps string token text with escape sequences preserved (e.g. "\\n").
This module decodes that token text to raw bytes and encodes bytes back to a
C-safe string-literal body.
"""

from dataclasses import dataclass


_HEX_CHARS = "0123456789abcdefABCDEF"
_OCT_CHARS = "01234567"
_SIMPLE_ESCAPES = {
    "\\": ord("\\"),
    "'": ord("'"),
    '"': ord('"'),
    "?": ord("?"),
    "a": 0x07,
    "b": 0x08,
    "f": 0x0C,
    "n": 0x0A,
    "r": 0x0D,
    "t": 0x09,
    "v": 0x0B,
}


@dataclass(frozen=True)
class EscapeDecodeError(ValueError):
    code: str
    details: str = ""


def decode_l0_string_token(text: str) -> bytes:
    """
    Decode an L0 string token payload to bytes.

    Input is lexer-preserved token text (without surrounding quotes).
    """
    out = bytearray()
    i = 0

    while i < len(text):
        ch = text[i]
        if ch != "\\":
            out.extend(ch.encode("utf-8"))
            i += 1
            continue

        i += 1
        if i >= len(text):
            out.append(ord("\\"))
            break

        esc = text[i]

        if esc in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[esc])
            i += 1
            continue

        if esc == "x":
            i += 1
            start = i
            while i < len(text) and text[i] in _HEX_CHARS:
                i += 1
            hex_digits = text[start:i]
            if not hex_digits:
                # Lexer should reject this, but keep this robust for malformed ASTs.
                out.extend(b"x")
                continue
            out.append(int(hex_digits, 16) & 0xFF)
            continue

        if esc == "u":
            digits = text[i + 1:i + 5]
            if len(digits) != 4 or any(c not in _HEX_CHARS for c in digits):
                raise EscapeDecodeError("invalid_unicode_escape", "\\u")
            value = int(digits, 16)
            if value > 0x10FFFF:
                raise EscapeDecodeError("unicode_out_of_range", "\\u")
            out.extend(chr(value).encode("utf-8"))
            i += 5
            continue

        if esc == "U":
            digits = text[i + 1:i + 9]
            if len(digits) != 8 or any(c not in _HEX_CHARS for c in digits):
                raise EscapeDecodeError("invalid_unicode_escape", "\\U")
            value = int(digits, 16)
            if value > 0x10FFFF:
                raise EscapeDecodeError("unicode_out_of_range", "\\U")
            out.extend(chr(value).encode("utf-8"))
            i += 9
            continue

        if esc in _OCT_CHARS:
            start = i
            i += 1
            while i < len(text) and text[i] in _OCT_CHARS and i - start < 3:
                i += 1
            oct_digits = text[start:i]
            out.append(int(oct_digits, 8) & 0xFF)
            continue

        # Unknown escapes should be rejected by lexer. Preserve best-effort behavior.
        out.extend(esc.encode("utf-8"))
        i += 1

    return bytes(out)


def encode_c_string_bytes(data: bytes) -> str:
    """
    Encode raw bytes into a C-safe string-literal body (without quotes).
    """
    parts: list[str] = []
    for b in data:
        if b == 0x5C:  # backslash
            parts.append("\\\\")
        elif b == 0x22:  # quote
            parts.append('\\"')
        elif b == 0x0A:
            parts.append("\\n")
        elif b == 0x09:
            parts.append("\\t")
        elif b == 0x0D:
            parts.append("\\r")
        elif b == 0x08:
            parts.append("\\b")
        elif b == 0x0C:
            parts.append("\\f")
        elif b == 0x0B:
            parts.append("\\v")
        elif 0x20 <= b <= 0x7E:
            parts.append(chr(b))
        else:
            # Use fixed-width octal escape to avoid \x run-on in C string literals.
            parts.append(f"\\{b:03o}")
    return "".join(parts)
