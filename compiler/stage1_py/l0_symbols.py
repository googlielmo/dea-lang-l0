#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from l0_ast import Module
from l0_diagnostics import Diagnostic
from l0_types import Type


class SymbolKind(Enum):
    MODULE = auto()  # reserved for future (aliases/using)
    FUNC = auto()
    STRUCT = auto()
    ENUM = auto()
    ENUM_VARIANT = auto()
    TYPE_ALIAS = auto()
    LET = auto()


@dataclass
class Symbol:
    """
    A resolved symbol at module level.
    """
    name: str
    kind: SymbolKind
    module: Module  # module that defines this symbol
    node: object  # AST node that defined this symbol
    type: Optional[Type] = None  # optional semantic type (for funcs, aliases, etc.)


@dataclass
class ModuleEnv:
    """
    Per-module symbol environment.

    locals   : symbols defined in this module
    imported : symbols opened from imported modules (not re-exported)
    all      : effective view = locals U imported, but with ambiguous names removed
    """
    module: Module
    locals: Dict[str, Symbol] = field(default_factory=dict)
    imported: Dict[str, Symbol] = field(default_factory=dict)
    all: Dict[str, Symbol] = field(default_factory=dict)
    ambiguous_imports: Dict[str, List[str]] = field(default_factory=dict)
    diagnostics: List[Diagnostic] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.module.name
