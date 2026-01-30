#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Callable

from l0_ast import TypeRef
from l0_symbols import ModuleEnv, Symbol, SymbolKind
from l0_types import (
    Type,
    BuiltinType,
    StructType,
    EnumType,
    PointerType,
    NullableType,
    get_builtin_type,
    L0_PRIMITIVE_TYPES,
)


class ResolveErrorKind(Enum):
    UNKNOWN_MODULE = auto()
    MODULE_NOT_IMPORTED = auto()
    UNKNOWN_SYMBOL = auto()


class TypeResolveErrorKind(Enum):
    UNKNOWN_TYPE = auto()
    NOT_A_TYPE = auto()
    UNRESOLVED_ALIAS = auto()
    VARIANT_AS_TYPE = auto()
    UNKNOWN_MODULE = auto()
    MODULE_NOT_IMPORTED = auto()
    INVALID_NULLABLE_VOID = auto()


@dataclass(frozen=True)
class SymbolResolution:
    symbol: Optional[Symbol]
    error: Optional[ResolveErrorKind]
    module_name: str
    name: str


@dataclass(frozen=True)
class TypeResolution:
    type: Optional[Type]
    error: Optional[TypeResolveErrorKind]
    module_name: str
    name: str
    symbol: Optional[Symbol] = None


def _is_imported(current_env: ModuleEnv, module_name: str) -> bool:
    return any(imp.name == module_name for imp in current_env.module.imports)


def resolve_symbol(
    module_envs: Dict[str, ModuleEnv],
    current_module: str,
    name: str,
    module_path: Optional[List[str]] = None,
    *,
    require_import: bool = True,
) -> SymbolResolution:
    module_name = ".".join(module_path) if module_path else current_module
    current_env = module_envs.get(current_module)

    if module_path and require_import:
        if current_env is None:
            return SymbolResolution(None, ResolveErrorKind.UNKNOWN_MODULE, module_name, name)
        if not _is_imported(current_env, module_name):
            return SymbolResolution(None, ResolveErrorKind.MODULE_NOT_IMPORTED, module_name, name)

    env = module_envs.get(module_name)
    if env is None:
        return SymbolResolution(None, ResolveErrorKind.UNKNOWN_MODULE, module_name, name)

    sym = env.locals.get(name) if module_path else env.all.get(name)
    if sym is None:
        return SymbolResolution(None, ResolveErrorKind.UNKNOWN_SYMBOL, module_name, name)

    return SymbolResolution(sym, None, module_name, name)


def resolve_type_ref(
    module_envs: Dict[str, ModuleEnv],
    current_module: str,
    tref: TypeRef,
    module_path: Optional[List[str]] = None,
    *,
    resolve_alias: Optional[Callable[[Symbol], Optional[Type]]] = None,
    require_import: bool = True,
) -> TypeResolution:
    base_name = tref.name

    if module_path is None and base_name in L0_PRIMITIVE_TYPES:
        base: Type = get_builtin_type(base_name)
        if tref.is_nullable and base_name == "void" and tref.pointer_depth == 0:
            return TypeResolution(None, TypeResolveErrorKind.INVALID_NULLABLE_VOID, current_module, base_name)
        t: Type = base
        for _ in range(tref.pointer_depth):
            t = PointerType(t)
        if tref.is_nullable:
            t = NullableType(t)
        return TypeResolution(t, None, current_module, base_name)

    sym_result = resolve_symbol(
        module_envs,
        current_module,
        base_name,
        module_path,
        require_import=require_import,
    )

    if sym_result.symbol is None:
        if sym_result.error is ResolveErrorKind.UNKNOWN_MODULE:
            err = TypeResolveErrorKind.UNKNOWN_MODULE
        elif sym_result.error is ResolveErrorKind.MODULE_NOT_IMPORTED:
            err = TypeResolveErrorKind.MODULE_NOT_IMPORTED
        else:
            err = TypeResolveErrorKind.UNKNOWN_TYPE
        return TypeResolution(None, err, sym_result.module_name, base_name)

    sym = sym_result.symbol
    if sym.kind is SymbolKind.STRUCT:
        base = StructType(sym.module.name, sym.name)
    elif sym.kind is SymbolKind.ENUM:
        base = EnumType(sym.module.name, sym.name)
    elif sym.kind is SymbolKind.TYPE_ALIAS:
        base = resolve_alias(sym) if resolve_alias is not None else sym.type
        if base is None:
            return TypeResolution(None, TypeResolveErrorKind.UNRESOLVED_ALIAS, sym_result.module_name, base_name, sym)
    elif sym.kind is SymbolKind.ENUM_VARIANT:
        return TypeResolution(None, TypeResolveErrorKind.VARIANT_AS_TYPE, sym_result.module_name, base_name, sym)
    else:
        return TypeResolution(None, TypeResolveErrorKind.NOT_A_TYPE, sym_result.module_name, base_name, sym)

    if tref.is_nullable and isinstance(base, BuiltinType) and base.name == "void" and tref.pointer_depth == 0:
        return TypeResolution(None, TypeResolveErrorKind.INVALID_NULLABLE_VOID, sym_result.module_name, base_name, sym)

    t = base
    for _ in range(tref.pointer_depth):
        t = PointerType(t)

    if tref.is_nullable:
        t = NullableType(t)

    return TypeResolution(t, None, sym_result.module_name, base_name, sym)
