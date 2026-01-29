#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from l0_compilation import CompilationUnit
from l0_context import CompilationContext
from l0_diagnostics import Diagnostic
from l0_locals import FunctionEnv
from l0_signatures import StructInfo, EnumInfo
from l0_symbols import ModuleEnv
from l0_types import Type, FuncType


class VarRefResolution(Enum):
    LOCAL = "local"
    MODULE = "module"


@dataclass
class AnalysisResult:
    """
    Full front-end analysis result for an entry module.

    Contains:
      - compilation unit
      - compilation context (cross-cutting compiler options)
      - module-level symbol envs
      - top-level type information (functions, structs, enums)
      - local scope information (functions + nested scopes)
      - expression types
      - diagnostics accumulated from all passes
    """
    cu: Optional[CompilationUnit] = None
    context: CompilationContext = field(default_factory=CompilationContext.default)

    module_envs: Dict[str, ModuleEnv] = field(default_factory=dict)

    # Keys are (module_name, decl_name)
    func_types: Dict[Tuple[str, str], FuncType] = field(default_factory=dict)
    struct_infos: Dict[Tuple[str, str], StructInfo] = field(default_factory=dict)
    enum_infos: Dict[Tuple[str, str], EnumInfo] = field(default_factory=dict)
    func_envs: Dict[Tuple[str, str], FunctionEnv] = field(default_factory=dict)
    let_types: Dict[Tuple[str, str], Type] = field(default_factory=dict)

    # Expression types keyed by id(expr_node)
    expr_types: Dict[int, Type] = field(default_factory=dict)

    # VarRef resolution keyed by id(expr_node): VarRefResolution.LOCAL or VarRefResolution.MODULE
    var_ref_resolution: Dict[int, VarRefResolution] = field(default_factory=dict)

    # Intrinsic function/type targets keyed by intrinsic id(expr_node)
    intrinsic_targets: Dict[int, Type] = field(default_factory=dict)

    diagnostics: List[Diagnostic] = field(default_factory=list)

    def has_errors(self) -> bool:
        return any(d.kind == "error" for d in self.diagnostics)
