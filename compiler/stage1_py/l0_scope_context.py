"""
Scope Context

Tracks variables and their lifetimes for cleanup management.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from l0_types import Type


@dataclass
class ScopeContext:
    """Track variables that need cleanup in current scope."""
    owned_vars: List[Tuple[str, Type]] = field(default_factory=list)  # Variables needing cleanup
    declared_vars: List[Tuple[str, Type]] = field(default_factory=list)  # All variables (for type lookup)
    parent: Optional['ScopeContext'] = None

    def add_owned(self, var_name: str, var_type: Type) -> None:
        """Mark a variable as owned (needs cleanup) and declared."""
        if var_type is not None:
            self.owned_vars.append((var_name, var_type))
            self.declared_vars.append((var_name, var_type))

    def add_declared(self, var_name: str, var_type: Type) -> None:
        """Mark a variable as declared (for type lookup only, no cleanup)."""
        if var_type is not None:
            self.declared_vars.append((var_name, var_type))

    def remove_owned(self, var_name: str) -> None:
        """Remove from owned list (e.g., when returning the variable)."""
        self.owned_vars = [(name, ty) for name, ty in self.owned_vars if name != var_name]
