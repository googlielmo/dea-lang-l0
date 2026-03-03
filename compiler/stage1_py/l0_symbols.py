#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

"""Symbol table definitions for the L0 compiler.

This module provides classes for representing resolved symbols and module
environments during name resolution and type checking.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from l0_ast import Module
from l0_diagnostics import Diagnostic
from l0_types import Type


class SymbolKind(Enum):
    """Enumeration of all top-level symbol categories.

    Attributes:
        MODULE: A module; reserved for future use (aliases, etc.).
        FUNC: A function.
        STRUCT: A struct type.
        ENUM: An enum type.
        ENUM_VARIANT: An enum variant constructor.
        TYPE_ALIAS: A type alias.
        LET: A module-level constant or variable.
    """
    MODULE = auto()
    FUNC = auto()
    STRUCT = auto()
    ENUM = auto()
    ENUM_VARIANT = auto()
    TYPE_ALIAS = auto()
    LET = auto()


@dataclass
class Symbol:
    """A resolved module-level symbol.

    Attributes:
        name: The name of the symbol.
        kind: The category of the symbol.
        module: The module that defines this symbol.
        node: The AST node where the symbol was defined.
        type: Optional resolved semantic Type.
    """
    name: str
    kind: SymbolKind
    module: Module
    node: object
    type: Optional[Type] = None


@dataclass
class ModuleEnv:
    """Per-module symbol environment.

    Attributes:
        module: The Module AST node for this environment.
        locals: Mapping of symbols defined within this module.
        imported: Mapping of symbols imported from other modules.
        all: Effective view of all symbols visible in this module (locals +
            imported), with ambiguous names removed.
        ambiguous_imports: Mapping of ambiguous names to the list of modules
            they were imported from.
        diagnostics: List of diagnostics collected during name resolution.
    """
    module: Module
    locals: Dict[str, Symbol] = field(default_factory=dict)
    imported: Dict[str, Symbol] = field(default_factory=dict)
    all: Dict[str, Symbol] = field(default_factory=dict)
    ambiguous_imports: Dict[str, List[str]] = field(default_factory=dict)
    diagnostics: List[Diagnostic] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Get the name of the module associated with this environment."""
        return self.module.name
