#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from pathlib import Path
from typing import Dict, Set

from l0_analysis import AnalysisResult
from l0_ast import Module
from l0_compilation import CompilationUnit
from l0_context import CompilationContext
from l0_diagnostics import Diagnostic, diag_from_token
from l0_expr_types import ExpressionTypeChecker
from l0_lexer import LexerError, Lexer
from l0_locals import LocalScopeResolver
from l0_logger import log_info, log_debug, log_stage
from l0_name_resolver import NameResolver
from l0_parser import Parser, ParseError
from l0_paths import SourceSearchPaths
from l0_signatures import SignatureResolver


class ImportCycleError(Exception):
    """Raised when a cyclic import is detected."""
    pass


class L0Driver:
    """
    Stage-1 driver:
      - read file
      - tokenize
      - parse
      - resolve imports recursively using SourceSearchPaths

    Entry points:
      - load_single_file(path): ad hoc one-off parsing (no import resolution).
      - load_module(name): load by dotted module name, recursively loading imports.
      - build_compilation_unit(name): build a closed set of modules for an entry.
    """

    def __init__(
        self,
        search_paths: SourceSearchPaths | None = None,
        context: CompilationContext | None = None,
    ):
        self.search_paths = search_paths or SourceSearchPaths()
        self.context = context or CompilationContext.default()
        # Modules successfully loaded (by module name).
        self.module_cache: Dict[str, Module] = {}
        # Modules currently being loaded (for cycle detection).
        self._loading: Set[str] = set()

    # --- Public API ---

    def analyze(self, entry_module_name: str) -> AnalysisResult:
        """
        High-level front-end pipeline:

          1. Build CompilationUnit for entry_module_name.
          2. Run NameResolver (module-level symbols).
          3. Run SignatureResolver (top-level types).
          4. Run LocalScopeResolver (function/block scopes).

        Returns an AnalysisResult containing all products and diagnostics.
        On fatal load errors, cu will be None and diagnostics will contain an error.
        """
        log_info(self.context, f"Starting analysis for entry module '{entry_module_name}'")
        result = AnalysisResult(cu=None, context=self.context)

        # 1. Build compilation unit (driver-level; can raise)
        log_stage(self.context, "Building compilation unit", entry_module_name)
        try:
            cu = self.build_compilation_unit(entry_module_name)
        except FileNotFoundError as e:
            result.diagnostics.append(
                Diagnostic(kind="error", message=f"file: [DRV-0010] {str(e)}")
            )
            return result
        except ValueError as e:
            # module name mismatch or similar
            result.diagnostics.append(
                Diagnostic(kind="error", message=f"input: [DRV-0020] {str(e)}")
            )
            return result
        except ImportCycleError as e:
            result.diagnostics.append(
                Diagnostic(kind="error", message=f"import: [DRV-0030] {str(e)}")
            )
            return result
        except LexerError as e:
            # syntax error during lexing
            result.diagnostics.append(
                Diagnostic(
                    kind="error",
                    message=f"syntax: {e.message}",
                    filename=e.filename,
                    line=e.line,
                    column=e.column,
                )
            )
            return result
        except ParseError as e:
            # syntax error during parsing
            result.diagnostics.append(
                diag_from_token(
                    kind="error",
                    message=e.message,
                    token=e.token,
                    module_name=None, # TODO: fill in module name (may need to pass it through ParseError)
                    filename=e.filename
                )
            )
            return result

        result.cu = cu
        log_debug(self.context, f"Compilation unit contains {len(cu.modules)} module(s): {', '.join(sorted(cu.modules.keys()))}")

        # 2. Module-level name resolution
        log_stage(self.context, "Resolving module-level names")
        nr = NameResolver(cu)
        module_envs = nr.resolve()
        result.module_envs = module_envs
        result.diagnostics.extend(nr.diagnostics)
        log_debug(self.context, f"Name resolution produced {len(nr.diagnostics)} diagnostic(s)")

        # 3. Signature resolution (top-level type information)
        log_stage(self.context, "Resolving type signatures")
        sr = SignatureResolver(cu, module_envs)
        sr.resolve()
        result.diagnostics.extend(sr.diagnostics)
        result.func_types = sr.func_types
        result.struct_infos = sr.struct_infos
        result.enum_infos = sr.enum_infos
        result.let_types = sr.let_types
        log_debug(self.context, f"Signature resolution found {len(sr.func_types)} function(s), {len(sr.struct_infos)} struct(s), {len(sr.enum_infos)} enum(s), {len(sr.let_types)} let(s)")

        # 4. Local scopes (function/block scopes)
        log_stage(self.context, "Resolving local scopes")
        ls = LocalScopeResolver(cu.modules)
        func_envs = ls.resolve()
        result.func_envs = func_envs
        log_debug(self.context, f"Local scope resolution processed {len(func_envs)} function(s)")
        # LocalScopeResolver currently has no diagnostics; add later if needed.

        # 5. Expression types
        log_stage(self.context, "Type-checking expressions")
        etc = ExpressionTypeChecker(result)
        etc.check()
        log_debug(self.context, f"Expression type checking produced {len(etc.diagnostics)} diagnostic(s)")

        log_info(self.context, f"Analysis complete: {len(result.diagnostics)} total diagnostic(s), {len([d for d in result.diagnostics if d.kind == 'error'])} error(s)")
        return result

    def build_compilation_unit(self, entry_module_name: str) -> CompilationUnit:
        """
        Load entry_module_name (if not already loaded), walk its imports, and
        return a CompilationUnit containing exactly the transitive closure of
        modules reachable from the entry.

        Any unrelated modules already in module_cache are ignored.
        """
        entry = self.load_module(entry_module_name)

        visited: Set[str] = set()
        collected: Dict[str, Module] = {}

        def visit(mod: Module) -> None:
            if mod.name in visited:
                return
            visited.add(mod.name)
            collected[mod.name] = mod
            for imp in mod.imports:
                dep = self.load_module(imp.name)
                visit(dep)

        visit(entry)
        return CompilationUnit(entry_module=entry, modules=collected)

    def load_module(self, module_name: str) -> Module:
        """
        Load a module by its qualified name using search paths + cache, and
        recursively load all imported modules.

        Example:
            driver.load_module("app.main")
        """
        # IMPORTANT: check for cycles *before* checking the cache.
        if module_name in self._loading:
            raise ImportCycleError(f"Cyclic import detected involving '{module_name}'")

        # If already fully loaded, reuse it.
        if module_name in self.module_cache:
            log_debug(self.context, f"Module '{module_name}' already loaded (cache hit)")
            return self.module_cache[module_name]

        log_debug(self.context, f"Loading module '{module_name}'")
        self._loading.add(module_name)
        try:
            # Resolve module name to a file path.
            path = self.search_paths.resolve(module_name)
            log_debug(self.context, f"Resolved '{module_name}' to {path}")

            module = self._load_single_file(path)

            # Sanity: declared name must match what we are loading.
            if module.name != module_name:
                raise ValueError(
                    f"Module name mismatch: file {path} declares 'module {module.name};' "
                    f"but was loaded as '{module_name}'"
                )

            # Store in cache before resolving imports so that non-cyclic
            # mutual references can reuse it once loading finishes.
            self.module_cache[module_name] = module

            # Recursively load imports.
            for imp in module.imports:
                self.load_module(imp.name)

            return module
        finally:
            self._loading.remove(module_name)

    # --- Internal helpers ---

    def _load_single_file(self, path: str | Path) -> Module:
        """
        Load a single file as a parsed module, ignoring search paths and
        not recursively resolving imports. The module is cached by its declared name.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"L0 source file not found: {path}")

        text = path.read_text(encoding="utf-8")
        return self._parse_source(text, file_path=str(path))

    def _parse_source(self, text: str, file_path: str) -> Module:
        log_debug(self.context, f"Lexing {file_path}")
        lexer = Lexer(text, filename=file_path)
        tokens = lexer.tokenize()
        log_debug(self.context, f"Lexed {len(tokens)} token(s) from {file_path}")

        log_debug(self.context, f"Parsing {file_path}")
        parser = Parser(tokens)
        module = parser.parse_module(filename=file_path)
        log_debug(self.context, f"Parsed module '{module.name}' from {file_path}")

        # Ensure any parsed module (even via load_single_file) appears in cache.
        self.module_cache[module.name] = module
        return module
