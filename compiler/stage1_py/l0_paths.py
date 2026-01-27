#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class SourceSearchPaths:
    """
    Search configuration for L0 modules.

    - system_roots: for standard library / toolchain modules
    - project_roots: for user / project modules

    Resolution rule: system_roots are searched first, then project_roots.
    """
    system_roots: List[Path] = field(default_factory=list)
    project_roots: List[Path] = field(default_factory=list)

    def add_system_root(self, root: str | Path) -> None:
        self.system_roots.append(Path(root))

    def add_project_root(self, root: str | Path) -> None:
        self.project_roots.append(Path(root))

    def module_relpath(self, module_name: str) -> Path:
        """
        Convert a dotted module name like 'std.io' to 'std/io.l0'.
        """
        return Path(*module_name.split(".")) .with_suffix(".l0")

    def resolve(self, module_name: str) -> Path:
        """
        Find the first existing file for module_name.

        Search order:
          1. system_roots
          2. project_roots

        Raises FileNotFoundError if not found.
        """
        rel = self.module_relpath(module_name)

        # 1. system roots
        for root in self.system_roots:
            candidate = root / rel
            if candidate.exists():
                return candidate

        # 2. project roots
        for root in self.project_roots:
            candidate = root / rel
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"Module '{module_name}' not found in system_roots or project_roots"
        )
