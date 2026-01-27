#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from typing import Dict

from l0_ast import Module


@dataclass
class CompilationUnit:
    """
    A closed set of modules starting from an entry module.

    - entry_module: the root module (e.g. 'app.main')
    - modules: mapping module_name -> Module for all transitively imported modules,
      including entry_module.
    """
    entry_module: Module
    modules: Dict[str, Module]

    @property
    def entry_name(self) -> str:
        return self.entry_module.name

    def __contains__(self, module_name: str) -> bool:
        return module_name in self.modules
