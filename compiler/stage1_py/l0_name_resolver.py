#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from typing import Dict

from l0_ast import Node, StructDecl, EnumVariant, EnumDecl, TypeAliasDecl, LetDecl
from l0_compilation import CompilationUnit
from l0_diagnostics import Diagnostic, diag_from_node
from l0_parser import FuncDecl
from l0_symbols import SymbolKind, Symbol, ModuleEnv


class NameResolver:
    """
    Stage-1 name resolver (module-level only, open import semantics).

    - Builds ModuleEnv for each module in a CompilationUnit.
    - Collects top-level symbols (funcs, structs, enums, variants, type aliases).
    - Opens imports by injecting imported modules' local symbols into importers.
    - Detects:
        * duplicate local definitions
        * conflicts between local and imported definitions
        * conflicts between multiple imports exporting the same name
    """

    def __init__(self, cu: CompilationUnit):
        self.cu = cu
        self.module_envs: Dict[str, ModuleEnv] = {}
        self.diagnostics: list[Diagnostic] = []

    def resolve(self) -> Dict[str, ModuleEnv]:
        """
        Main entry point: build environments for all modules and return the mapping.
        """
        # 1. Create envs
        for module in self.cu.modules.values():
            env = ModuleEnv(module=module)
            self.module_envs[module.name] = env

        # 2. Collect local symbols for each module
        for env in self.module_envs.values():
            self._collect_locals(env)

        # 3. Open imports (Option B semantics)
        for env in self.module_envs.values():
            self._open_imports(env)

        # 4. Aggregate diagnostics
        for env in self.module_envs.values():
            self.diagnostics.extend(env.diagnostics)

        return self.module_envs

    # --- internal helpers ---

    def _collect_locals(self, env: ModuleEnv) -> None:
        """
        Populate env.locals and env.all from the module's own declarations.
        Detect duplicate top-level names inside the same module.
        """
        m = env.module

        for decl in m.decls:
            # FuncDecl (includes extern funcs via is_extern flag)
            if isinstance(decl, FuncDecl):
                self._define_local(
                    env,
                    decl.name,
                    Symbol(decl.name, SymbolKind.FUNC, m, decl),
                )
            # Structs
            elif isinstance(decl, StructDecl):
                self._define_local(
                    env,
                    decl.name,
                    Symbol(decl.name, SymbolKind.STRUCT, m, decl),
                )
            # Enums and their variants
            elif isinstance(decl, EnumDecl):
                # Enum type name
                self._define_local(
                    env,
                    decl.name,
                    Symbol(decl.name, SymbolKind.ENUM, m, decl),
                )
                # Variants
                for variant in decl.variants:
                    assert isinstance(variant, EnumVariant)
                    self._define_local(
                        env,
                        variant.name,
                        Symbol(variant.name, SymbolKind.ENUM_VARIANT, m, variant),
                    )
            # Type aliases
            elif isinstance(decl, TypeAliasDecl):
                self._define_local(
                    env,
                    decl.name,
                    Symbol(decl.name, SymbolKind.TYPE_ALIAS, m, decl),
                )
            # Top-level let bindings
            elif isinstance(decl, LetDecl):
                self._define_local(
                    env,
                    decl.name,
                    Symbol(decl.name, SymbolKind.LET, m, decl),
                )
            else:
                # In case of future new TopLevelDecl kinds
                continue

    def _define_local(self, env: ModuleEnv, name: str, sym: Symbol) -> None:
        """
        Define a local symbol in a module, reporting duplicates.

        If a local with the same name already exists, keep the first and emit an error.
        """
        if name in env.locals:
            env.diagnostics.append(
                diag_from_node(
                    kind="error",
                    message=f"[RES-0010] duplicate top-level definition of '{name}' in module '{env.name}'",
                    module_name=env.name,
                    filename=env.module.filename,
                    node=(sym.node if isinstance(sym.node, Node) else None),
                )
            )
            # Keep existing symbol; ignore new one.
            return

        env.locals[name] = sym
        env.all[name] = sym

    def _open_imports(self, env: ModuleEnv) -> None:
        """
        Apply the following import semantics:

        - For each imported module, add its locals into env.imported/env.all.
        - If a name collides with a local, keep the local and report an error.
        - If a name is imported from multiple modules, mark it ambiguous and
          remove it from env.all; later resolution will see no binding.
        """
        m = env.module

        for imp in m.imports:
            imported_mod_name = imp.name

            imported_env = self.module_envs.get(imported_mod_name)
            if imported_env is None:
                # In a well-formed CompilationUnit this shouldn't happen,
                # since the driver should have already loaded all imports.
                env.diagnostics.append(
                    diag_from_node(
                        kind="error",
                        message=f"[RES-0029] unknown imported module '{imported_mod_name}' in module '{env.name}'",
                        module_name=env.name,
                        filename=env.module.filename,
                        node=imp
                    )
                )
                continue

            for name, sym in imported_env.locals.items():
                # Local definition wins
                if name in env.locals:
                    local_sym = env.locals[name]

                    # Special-case: extern function prototypes
                    if self._extern_signatures_compatible(local_sym, sym):
                        env.diagnostics.append(
                            diag_from_node(
                                kind="warning",
                                message=(
                                    f"[RES-0020] imported extern function '{imported_mod_name}::{name}' "
                                    f"will be shadowed by a compatible local extern declaration in module '{env.name}'"
                                ),
                                module_name=env.name,
                                filename=env.module.filename,
                                node=(local_sym.node if isinstance(local_sym.node, Node) else None),
                            )
                        )
                        # Keep local; do not import this symbol
                        continue

                    # Fallback: report shadowing
                    env.diagnostics.append(
                        diag_from_node(
                            kind="warning",
                            message=(
                                f"[RES-0021] imported symbol '{imported_mod_name}::{name}' will be shadowed "
                                f"by a local definition in module '{env.name}'"
                            ),
                            module_name=env.name,
                            filename=env.module.filename,
                            node=(local_sym.node if isinstance(local_sym.node, Node) else None),
                        )
                    )
                    # Keep local; do not overwrite
                    continue

                # Name already imported from another module -> ambiguous, will need disambiguation later
                if name in env.imported and env.imported[name] is not sym:
                    prev_module = env.imported[name].module.name
                    env.diagnostics.append(
                        diag_from_node(
                            kind="warning",
                            message=(
                                f"[RES-0022] symbol '{name}' imported from multiple modules "
                                f"('{prev_module}', '{imported_mod_name}') into '{env.name}'; "
                                f"unqualified '{name}' will be ambiguous unless a local definition shadows it; "
                                f"otherwise qualify as '<module>::{name}'"
                            ),

                            module_name=env.name,
                            filename=env.module.filename,
                            node=imp,
                        )
                    )
                    # Remove from visible set; name becomes unusable
                    if name in env.all and env.all[name] is env.imported[name]:
                        del env.all[name]
                    # Track ambiguous names for better diagnostics later
                    if name not in env.ambiguous_imports:
                        env.ambiguous_imports[name] = [prev_module, imported_mod_name]
                    else:
                        env.ambiguous_imports[name].append(imported_mod_name)
                    # Keep the first imported symbol in env.imported as bookkeeping,
                    # but resolution will consult env.all only.
                    continue

                # Fresh imported name
                env.imported[name] = sym
                # Only add to env.all if not already present (locals already handled)
                if name not in env.all:
                    env.all[name] = sym

    def _extern_signatures_compatible(self, local: Symbol, imported: Symbol) -> bool:
        # Only functions
        if local.kind is not SymbolKind.FUNC or imported.kind is not SymbolKind.FUNC:
            return False

        if not isinstance(local.node, FuncDecl) or not isinstance(imported.node, FuncDecl):
            return False

        a = local.node
        b = imported.node

        # Both must be extern
        if not (a.is_extern and b.is_extern):
            return False

        # Same number of parameters
        if len(a.params) != len(b.params):
            return False

        # Same parameter types (syntactic TypeRef equality is fine at this stage)
        for pa, pb in zip(a.params, b.params):
            if pa.type != pb.type:
                return False

        # Same return type
        if a.return_type != b.return_type:
            return False

        return True
