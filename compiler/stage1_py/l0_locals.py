#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, Tuple

from l0_ast import Node, TypeRef, FuncDecl, Module, Stmt, Block, LetStmt, IfStmt, WhileStmt, MatchArm, MatchStmt, \
    Pattern, WildcardPattern, VariantPattern


class LocalKind(Enum):
    PARAM = auto()
    LOCAL = auto()
    PATTERN_VAR = auto()


@dataclass
class LocalSymbol:
    """
    A single local binding: parameter, let-binding, or pattern variable.
    """
    name: str
    kind: LocalKind
    type_ref: Optional[TypeRef]
    decl: Node  # Param | LetStmt | Pattern


@dataclass
class Scope:
    """
    A lexical scope for locals inside a function.

    Scopes form a tree via the 'parent' link.
    """
    parent: Optional[Scope]
    symbols: Dict[str, LocalSymbol] = field(default_factory=dict)

    def lookup(self, name: str) -> Optional[LocalSymbol]:
        scope: Optional[Scope] = self
        while scope is not None:
            sym = scope.symbols.get(name)
            if sym is not None:
                return sym
            scope = scope.parent
        return None


@dataclass
class FunctionEnv:
    """
    Environment for a single function: the function AST and its root scope.
    """
    module_name: str
    func: FuncDecl
    root_scope: Scope


class LocalScopeResolver:
    """
    Builds lexical scopes for all non-extern functions in a set of modules.

    Public API:

        resolver = LocalScopeResolver(modules_by_name)
        func_envs = resolver.resolve()

        # helper to fetch scopes later:
        scope = resolver.get_block_scope(block_node)
        arm_scope = resolver.get_match_arm_scope(arm_node)

    Design choices:

    - Parameters live in the function's root scope.
    - Top-level lets inside the function body also live in the root scope.
    - Each nested Block inside 'if', 'else', 'while', and 'match' arms gets
      its own child scope.
    - Pattern variables in a 'match' arm live in the arm's scope (which is
      also the scope of the arm's Block body).
    """

    def __init__(self, modules: Dict[str, Module]) -> None:
        self.modules = modules

        # (module_name, func_name) -> FunctionEnv
        self.function_envs: Dict[Tuple[str, str], FunctionEnv] = {}

        # Node id -> Scope
        # We avoid using AST nodes as dict keys directly because dataclasses
        # are unhashable by default.
        self._block_scopes: Dict[int, Scope] = {}
        self._match_arm_scopes: Dict[int, Scope] = {}

    # --- public API ---

    def resolve(self) -> Dict[Tuple[str, str], FunctionEnv]:
        """
        Build scopes for all non-extern functions in all modules.
        """
        for module_name, module in self.modules.items():
            for decl in module.decls:
                if isinstance(decl, FuncDecl) and not decl.is_extern:
                    fe = self._build_function_env(module_name, decl)
                    self.function_envs[(module_name, decl.name)] = fe
        return self.function_envs

    def get_block_scope(self, block: Block) -> Optional[Scope]:
        return self._block_scopes.get(id(block))

    def get_match_arm_scope(self, arm: MatchArm) -> Optional[Scope]:
        return self._match_arm_scopes.get(id(arm))

    # --- internal helpers ---

    def _build_function_env(self, module_name: str, func: FuncDecl) -> FunctionEnv:
        root = Scope(parent=None)

        # Parameters live in the root scope.
        for param in func.params:
            self._declare(root, param.name, LocalKind.PARAM, param.type, param)

        # The function body uses the root scope directly.
        self._block_scopes[id(func.body)] = root
        self._visit_block(func.body, root)

        return FunctionEnv(module_name=module_name, func=func, root_scope=root)

    def _visit_block(self, block: Block, scope: Scope) -> None:
        for stmt in block.stmts:
            self._visit_stmt(stmt, scope)

    def _visit_stmt(self, stmt: Stmt, scope: Scope) -> None:
        if isinstance(stmt, LetStmt):
            self._declare(scope, stmt.name, LocalKind.LOCAL, stmt.type, stmt)
            return

        if isinstance(stmt, IfStmt):
            self._visit_stmt(stmt.then_stmt, scope)
            # 'else' branch (if any) also gets visited in the same scope.
            if stmt.else_stmt is not None:
                self._visit_stmt(stmt.else_stmt, scope)
            return

        if isinstance(stmt, WhileStmt):
            body_scope = Scope(parent=scope)
            self._block_scopes[id(stmt.body)] = body_scope
            self._visit_block(stmt.body, body_scope)
            return

        if isinstance(stmt, MatchStmt):
            for arm in stmt.arms:
                self._visit_match_arm(arm, scope)
            return

        if isinstance(stmt, Block):
            # Register a new scope for this block.
            block_scope = Scope(parent=scope)
            self._block_scopes[id(stmt)] = block_scope
            self._visit_block(stmt, block_scope)
            return

        # ReturnStmt, AssignStmt, ExprStmt and others do not introduce scopes
        # or new bindings; nothing to do here.

    def _visit_match_arm(self, arm: MatchArm, parent_scope: Scope) -> None:
        # Each arm has its own scope, child of the parent scope in which
        # the 'match' appears.
        arm_scope = Scope(parent=parent_scope)
        self._match_arm_scopes[id(arm)] = arm_scope
        self._block_scopes[id(arm.body)] = arm_scope

        # Bind pattern variables (if any).
        self._bind_pattern_vars(arm.pattern, arm_scope)

        # Visit the arm body in this scope.
        self._visit_block(arm.body, arm_scope)

    def _bind_pattern_vars(self, pattern: Pattern, scope: Scope) -> None:
        if isinstance(pattern, VariantPattern):
            for var_name in pattern.vars:
                # Pattern variables have no explicit type at this stage.
                self._declare(scope, var_name, LocalKind.PATTERN_VAR, None, pattern)
        elif isinstance(pattern, WildcardPattern):
            # '_' does not introduce a binding.
            return
        else:
            # Future pattern forms would go here.
            return

    def _declare(
            self,
            scope: Scope,
            name: str,
            kind: LocalKind,
            type_ref: Optional[TypeRef],
            decl: Node,
    ) -> LocalSymbol:
        # For now, first declaration in a scope wins; duplicates could be
        # diagnosed later via a Diagnostic mechanism.
        if name in scope.symbols:
            return scope.symbols[name]
        sym = LocalSymbol(name=name, kind=kind, type_ref=type_ref, decl=decl)
        scope.symbols[name] = sym
        return sym
