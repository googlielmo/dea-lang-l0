#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

# l0_internal_error.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from l0_ast import Span


@dataclass(frozen=True)
class ICELocation:
    filename: Optional[str]
    span: Optional[Span]


class InternalCompilerError(RuntimeError):
    """
    ICE = compiler bug / violated pipeline invariant.
    Not for user mistakes (those are Diagnostics).
    """

    def __init__(self, message: str, loc: ICELocation | None = None):
        super().__init__(message)
        self.message = message
        self.loc = loc

    def format(self) -> str:
        message = self.message
        if not "[ICE-" in message:
            message = f"[ICE-9999] {message}"
        if self.loc and self.loc.filename:
            if self.loc.span is not None:
                return f"{self.loc.filename}:{self.loc.span.start_line}:{self.loc.span.start_column}: internal compiler error: {message}"
            return f"{self.loc.filename}: internal compiler error: {message}"
        return f"internal compiler error: {message}"
