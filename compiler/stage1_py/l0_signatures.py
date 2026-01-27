#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from l0_ast import Node, TypeRef, FuncDecl, FieldDecl, StructDecl, EnumVariant, EnumDecl, TypeAliasDecl, LetDecl, \
    IntLiteral, BoolLiteral, ByteLiteral, StringLiteral, NullLiteral, CallExpr, VarRef, Expr
from l0_compilation import CompilationUnit
from l0_diagnostics import Diagnostic, diag_from_node
from l0_symbols import ModuleEnv, SymbolKind, Symbol
from l0_types import (
    L0_PRIMITIVE_TYPES,
    Type,
    BuiltinType,
    StructType,
    EnumType,
    PointerType,
    NullableType,
    FuncType,
    get_builtin_type,
)


@dataclass
class StructFieldInfo:
    name: str
    type: Type


@dataclass
class StructInfo:
    struct_type: StructType
    fields: List[StructFieldInfo]


@dataclass
class EnumVariantInfo:
    name: str
    field_types: List[Type]


@dataclass
class EnumInfo:
    enum_type: EnumType
    variants: Dict[str, EnumVariantInfo]


class SignatureResolver:
    """
    Resolves top-level signatures:

      - Function parameter/return types -> FuncType
      - Struct field types
      - Enum variant payload types
      - Type alias targets

    Uses ModuleEnv.all for type name lookup and emits diagnostics on errors.
    """

    def __init__(self, cu: CompilationUnit, module_envs: Dict[str, ModuleEnv]):
        self.cu = cu
        self.module_envs = module_envs

        self.diagnostics: List[Diagnostic] = []

        # Side tables, keyed by (module_name, decl_name) to avoid using
        # unhashable AST nodes as keys.
        self.func_types: Dict[Tuple[str, str], FuncType] = {}
        self.struct_infos: Dict[Tuple[str, str], StructInfo] = {}
        self.enum_infos: Dict[Tuple[str, str], EnumInfo] = {}
        self.let_types: Dict[Tuple[str, str], Type] = {}

    def resolve(self) -> None:
        for module in self.cu.modules.values():
            env = self.module_envs[module.name]
            self._resolve_module_signatures(env)

        # After resolving all signatures, detect value-type cycles
        # (cycles would create infinite-size types)
        self._detect_value_type_cycles()

    # --- internal helpers ---

    def _resolve_module_signatures(self, env: ModuleEnv) -> None:
        for decl in env.module.decls:
            if isinstance(decl, StructDecl):
                self._resolve_struct(env, decl)
            elif isinstance(decl, EnumDecl):
                self._resolve_enum(env, decl)
            elif isinstance(decl, FuncDecl):
                self._resolve_func(env, decl)
            elif isinstance(decl, TypeAliasDecl):
                self._resolve_type_alias(env, decl)
            elif isinstance(decl, LetDecl):
                self._resolve_let(env, decl)
            else:
                continue

    def _emit(self, diag: Diagnostic) -> None:
        self.diagnostics.append(diag)

    # --- type resolution core ---

    def _resolve_type_ref(
            self,
            env: ModuleEnv,
            tref: TypeRef,
            alias_stack: Optional[Set[Tuple[str, str]]] = None,
    ) -> Optional[Type]:
        """
        Resolve a TypeRef in the context of a module env.

        Returns a Type or None on error (and emits diagnostics).
        """
        base_name = tref.name

        # Builtins first (reserved names)
        if base_name in L0_PRIMITIVE_TYPES:
            base: Type = get_builtin_type(base_name)
        else:
            sym = env.all.get(base_name)
            if sym is None:
                self._emit(
                    diag_from_node(
                        kind="error",
                        message=f"[SIG-0019] unknown type '{base_name}' in module '{env.name}'",
                        module_name=env.name,
                        filename=env.module.filename,
                        node=tref
                    )
                )
                return None

            if sym.kind == SymbolKind.STRUCT:
                base = StructType(sym.module.name, sym.name)
            elif sym.kind == SymbolKind.ENUM:
                base = EnumType(sym.module.name, sym.name)
            elif sym.kind == SymbolKind.TYPE_ALIAS:
                base = self._resolve_type_alias_symbol(env, sym, alias_stack)
                if base is None:
                    return None
            else:
                self._emit(
                    diag_from_node(
                        kind="error",
                        message=(
                            f"[SIG-0010] symbol '{base_name}' in module '{env.name}' "
                            f"is not a type (kind={sym.kind.name})"
                        ),
                        module_name=env.name,
                        filename=env.module.filename,
                        node=tref
                    )
                )
                return None

        # Apply pointer depth
        t: Type = base
        for _ in range(tref.pointer_depth):
            t = PointerType(t)

        # Apply nullable suffix
        if tref.is_nullable:
            if t == get_builtin_type("void"):
                self._emit(
                    diag_from_node(
                        kind="error",
                        message="[SIG-0011] type 'void' cannot be nullable",
                        module_name=env.name,
                        filename=env.module.filename,
                        node=tref
                    )
                )
                return None

            t = NullableType(t)

        return t

    def _resolve_type_alias_symbol(
            self,
            env: ModuleEnv,
            sym: Symbol,
            alias_stack: Optional[Set[Tuple[str, str]]] = None,
    ) -> Optional[Type]:
        """
        Resolve a TYPE_ALIAS symbol to its target Type, caching it in sym.type.

        alias_stack is used to detect alias cycles via (module_name, alias_name) keys.
        """
        if sym.type is not None:
            return sym.type

        key = (sym.module.name, sym.name)

        if alias_stack is None:
            alias_stack = set()

        if key in alias_stack:
            self._emit(
                diag_from_node(
                    kind="error",
                    message=(
                        f"[SIG-0020] cyclic type alias involving '{sym.name}' in module "
                        f"'{sym.module.name}'"
                    ),
                    module_name=env.name,
                    filename=sym.module.filename,
                    node=(sym.node if isinstance(sym.node, Node) else None)
                )
            )
            return None

        alias_stack.add(key)

        # sym.node should be a TypeAliasDecl
        decl = sym.node
        if not isinstance(decl, TypeAliasDecl):
            # Should not happen; be defensive
            self._emit(
                diag_from_node(
                    kind="error",
                    message=(
                        f"[SIG-9029] internal error: TYPE_ALIAS symbol '{sym.name}' does not "
                        f"reference a TypeAliasDecl"
                    ),
                    module_name=env.name,
                    filename=env.module.filename,
                    node=(decl if isinstance(decl, Node) else None),
                )
            )
            alias_stack.remove(key)
            return None

        target_tref = decl.target
        target_type = self._resolve_type_ref(env, target_tref, alias_stack)

        alias_stack.remove(key)

        if target_type is not None:
            sym.type = target_type
        return target_type

    # --- per decl kind ---

    def _resolve_struct(self, env: ModuleEnv, decl: StructDecl) -> None:
        struct_sym = env.locals.get(decl.name)
        if struct_sym is None:
            return

        struct_ty = StructType(env.name, decl.name)
        struct_sym.type = struct_ty

        fields_info: List[StructFieldInfo] = []

        for field in decl.fields:  # FieldDecl
            assert isinstance(field, FieldDecl)
            ftype = self._resolve_type_ref(env, field.type)
            if ftype is None:
                # error already emitted
                continue
            fields_info.append(StructFieldInfo(name=field.name, type=ftype))

        key = (env.name, decl.name)
        self.struct_infos[key] = StructInfo(struct_type=struct_ty, fields=fields_info)

    def _resolve_enum(self, env: ModuleEnv, decl: EnumDecl) -> None:
        enum_sym = env.locals.get(decl.name)
        if enum_sym is None:
            return

        enum_ty = EnumType(env.name, decl.name)
        enum_sym.type = enum_ty

        variant_infos: Dict[str, EnumVariantInfo] = {}

        for variant in decl.variants:
            assert isinstance(variant, EnumVariant)
            field_types: List[Type] = []
            for field in variant.fields:  # FieldDecl list
                assert isinstance(field, FieldDecl)
                ftype = self._resolve_type_ref(env, field.type)
                if ftype is None:
                    continue
                field_types.append(ftype)
            variant_infos[variant.name] = EnumVariantInfo(
                name=variant.name, field_types=field_types
            )

        key = (env.name, decl.name)
        self.enum_infos[key] = EnumInfo(enum_type=enum_ty, variants=variant_infos)

        # Also annotate enum-variant symbols with their (tuple) payload type if desired
        for variant in decl.variants:
            sym = env.locals.get(variant.name)
            if sym is not None and sym.kind == SymbolKind.ENUM_VARIANT:
                info = variant_infos[variant.name]
                # Represent variant as a function-like type: (payload...) -> EnumType
                sym.type = FuncType(tuple(info.field_types), enum_ty)

    def _resolve_func(self, env: ModuleEnv, decl: FuncDecl) -> None:
        func_sym = env.locals.get(decl.name)
        if func_sym is None:
            return

        param_types: List[Type] = []
        ok = True

        for param in decl.params:
            ptype = self._resolve_type_ref(env, param.type)
            if ptype is None:
                ok = False
                continue
            param_types.append(ptype)

        result_type = self._resolve_type_ref(env, decl.return_type)
        if result_type is None:
            ok = False

        if not ok:
            return

        ft = FuncType(tuple(param_types), result_type)
        func_sym.type = ft

        key = (env.name, decl.name)
        self.func_types[key] = ft

    def _resolve_type_alias(self, env: ModuleEnv, decl: TypeAliasDecl) -> None:
        alias_sym = env.locals.get(decl.name)
        if alias_sym is None:
            return

        # This will cache the result in alias_sym.type
        self._resolve_type_alias_symbol(env, alias_sym, alias_stack=None)

    def _resolve_let(self, env: ModuleEnv, decl: LetDecl) -> None:
        let_sym = env.locals.get(decl.name)
        if let_sym is None:
            return

        # Resolve type annotation if present
        if decl.type is not None:
            let_type = self._resolve_type_ref(env, decl.type)
            if let_type is None:
                return
        else:
            # Infer type from initializer for simple literals
            let_type = self._infer_literal_type(env, decl.value)
            if let_type is None:
                self._emit(
                    diag_from_node(
                        kind="error",
                        message=f"[SIG-0030] cannot infer type for let '{decl.name}' - type annotation required for non-literal initializers",
                        module_name=env.name,
                        filename=env.module.filename,
                        node=decl
                    )
                )
                return

        let_sym.type = let_type
        key = (env.name, decl.name)
        self.let_types[key] = let_type

    def _infer_literal_type(self, env: ModuleEnv, expr : Expr) -> Optional[Type]:
        """Infer type from simple literal expressions and struct/enum construction."""
        if isinstance(expr, IntLiteral):
            return get_builtin_type("int")
        elif isinstance(expr, BoolLiteral):
            return get_builtin_type("bool")
        elif isinstance(expr, ByteLiteral):
            return get_builtin_type("byte")
        elif isinstance(expr, StringLiteral):
            return get_builtin_type("string")
        elif isinstance(expr, NullLiteral):
            # Cannot infer type from null - need annotation
            return None
        elif isinstance(expr, CallExpr) and isinstance(expr.callee, VarRef):
            # Struct or enum variant construction: Point(1, 2) or Color.Red
            name = expr.callee.name
            sym = env.all.get(name)
            if sym is None:
                return None

            # Struct constructor
            if sym.kind == SymbolKind.STRUCT:
                return StructType(sym.module.name, sym.name)

            # Type alias to struct
            if sym.kind == SymbolKind.TYPE_ALIAS and isinstance(sym.type, StructType):
                return sym.type

            # Enum variant constructor
            if sym.kind == SymbolKind.ENUM_VARIANT:
                # Find which enum this variant belongs to by checking module declarations
                for other_sym_name, other_sym in env.all.items():
                    if other_sym.kind == SymbolKind.ENUM:
                        # Check if this enum has the variant
                        enum_decl = other_sym.node
                        if isinstance(enum_decl, EnumDecl):
                            for variant in enum_decl.variants:
                                if variant.name == name:
                                    return EnumType(other_sym.module.name, other_sym.name)
                return None

            return None
        else:
            # Non-literal expressions need type annotation
            return None

    def _extract_value_type_dependencies(self, typ: Type) -> Set[Tuple[str, str]]:
        """
        Extract type dependencies for VALUE fields only.

        Returns set of (module, name) tuples for types that must be defined first.

        Value-type fields create dependencies (types must be fully defined).
        Pointer-type fields do NOT create dependencies (forward declarations suffice).
        """
        if isinstance(typ, PointerType):
            # Pointers don't create dependencies
            return set()

        elif isinstance(typ, NullableType):
            # Nullable pointer (T*?) - no dependency
            if isinstance(typ.inner, PointerType):
                return set()
            # Value-optional of user type (T?) - depends on T
            return self._extract_value_type_dependencies(typ.inner)

        elif isinstance(typ, StructType):
            return {(typ.module, typ.name)}

        elif isinstance(typ, EnumType):
            return {(typ.module, typ.name)}

        elif isinstance(typ, BuiltinType):
            return set()

        elif isinstance(typ, FuncType):
            return set()

        else:
            # Unknown type - conservatively return no dependencies
            return set()

    def _detect_value_type_cycles(self) -> None:
        """
        Detect cycles in value-type dependencies.

        Value-type cycles create infinite-size types and must be rejected.
        Pointer-type fields break cycles (forward declarations work).

        Emits error diagnostic if cycle is detected.
        """
        # Build dependency graph (same logic as codegen)
        graph: Dict[Tuple[str, str], Set[Tuple[str, str]]] = {}

        # Process all structs
        for (mod_name, struct_name), struct_info in self.struct_infos.items():
            key = (mod_name, struct_name)
            deps = set()

            for field in struct_info.fields:
                field_deps = self._extract_value_type_dependencies(field.type)
                deps.update(field_deps)

            graph[key] = deps

        # Process all enums
        for (mod_name, enum_name), enum_info in self.enum_infos.items():
            key = (mod_name, enum_name)
            deps = set()

            for variant_info in enum_info.variants.values():
                for field_type in variant_info.field_types:
                    field_deps = self._extract_value_type_dependencies(field_type)
                    deps.update(field_deps)

            graph[key] = deps

        # Perform topological sort to detect cycles
        from collections import deque

        in_degree = {node: len(graph[node]) for node in graph}
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        processed = []

        while queue:
            node = queue.popleft()
            processed.append(node)

            # Reduce in-degree of dependents
            for dependent in graph:
                if node in graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check for cycles
        if len(processed) != len(graph):
            # Find nodes involved in cycle
            unresolved = [node for node in graph if node not in processed]

            # Format cycle details for error message
            cycle_parts = []
            for node in unresolved[:3]:  # Limit to first 3 for readability
                deps = [f"{m}::{n}" for m, n in graph.get(node, set()) if (m, n) in unresolved]
                node_str = f"{node[0]}::{node[1]}"
                if deps:
                    cycle_parts.append(f"{node_str} depends on {', '.join(deps)}")

            cycle_desc = "; ".join(cycle_parts)

            # Find a struct or enum decl in the cycle to attach the diagnostic to
            first_node = unresolved[0]
            module = self.cu.modules.get(first_node[0])
            target_decl = None

            if module:
                for decl in module.decls:
                    if isinstance(decl, (StructDecl, EnumDecl)) and decl.name == first_node[1]:
                        target_decl = decl
                        break

            self._emit(
                diag_from_node(
                    kind="error",
                    message=(
                        f"[SIG-0040] Value-type cycle detected: {cycle_desc}. "
                        f"This creates infinite-size types. "
                        f"Consider using pointers to break the cycle."
                    ),
                    module_name=first_node[0],
                    filename=module.filename if module else None,
                    node=target_decl
                )
            )
