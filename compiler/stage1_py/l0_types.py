#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from typing import Tuple, Dict, Optional

# ========================================
# The current semantic type system for L0.
# ========================================

L0_PRIMITIVE_TYPES = ("bool", "byte", "int", "string", "void")

class Type:
    """
    Base class for all semantic types.
    Used only as a common marker; concrete types are dataclasses below.
    """
    pass


@dataclass(frozen=True)
class BuiltinType(Type):
    name: str  # "int", etc.


@dataclass(frozen=True)
class StructType(Type):
    module: str
    name: str


@dataclass(frozen=True)
class EnumType(Type):
    module: str
    name: str


@dataclass(frozen=True)
class PointerType(Type):
    inner: Type


@dataclass(frozen=True)
class NullableType(Type):
    inner: Type


@dataclass(frozen=True)
class FuncType(Type):
    params: Tuple[Type, ...]
    result: Type


@dataclass(frozen=True)
class NullType(Type):
    pass


# --- helpers for builtins ---

_BUILTIN_CACHE: Dict[str, BuiltinType] = {}
_NULL_TYPE = NullType()


def get_builtin_type(name: str) -> BuiltinType:
    """
    Get (or create) a canonical BuiltinType for a given name.
    """
    if name not in _BUILTIN_CACHE:
        _BUILTIN_CACHE[name] = BuiltinType(name)
    return _BUILTIN_CACHE[name]


def get_null_type() -> NullType:
    return _NULL_TYPE

# --- type stringification for debugging ---

def format_type(t: Optional[Type]) -> str:
    if t is None:
        return "<none>"
    elif isinstance(t, BuiltinType):
        return t.name
    elif isinstance(t, StructType):
        return f"{t.module}::{t.name}"
    elif isinstance(t, EnumType):
        return f"{t.module}::{t.name}"
    elif isinstance(t, PointerType):
        return f"{format_type(t.inner)}*"
    elif isinstance(t, NullableType):
        return f"{format_type(t.inner)}?"
    elif isinstance(t, FuncType):
        params_str = ", ".join(format_type(p) for p in t.params)
        return f"func({params_str}) -> {format_type(t.result)}"
    elif isinstance(t, NullType):
        return "null"
    else:
        # Fallback (should not happen)
        return repr(t)