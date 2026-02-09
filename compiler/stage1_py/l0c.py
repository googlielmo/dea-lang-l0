#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

import argparse
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from l0_analysis import AnalysisResult
from l0_ast_printer import format_module
from l0_backend import Backend
from l0_context import CompilationContext
from l0_diagnostics import Diagnostic
from l0_driver import L0Driver
from l0_internal_error import InternalCompilerError
from l0_lexer import TokenKind, Lexer
from l0_logger import log_info, log_error
from l0_paths import SourceSearchPaths
from l0_symbols import SymbolKind
from l0_types import (
    format_type,
)


def _init_env_defaults() -> None:
    l0_home = os.getenv("L0_HOME")
    if not l0_home:
        return
    if not os.getenv("L0_SYSTEM"):
        os.environ["L0_SYSTEM"] = os.path.join(l0_home, "l0", "stdlib")
    if not os.getenv("L0_RUNTIME_INCLUDE"):
        os.environ["L0_RUNTIME_INCLUDE"] = os.path.join(l0_home, "runtime")


def _load_file_lines(path: str, cache: Dict[str, List[str]]) -> List[str]:
    if path not in cache:
        text = Path(path).read_text(encoding="utf-8")
        cache[path] = text.splitlines()
    return cache[path]


def print_diagnostics(result: AnalysisResult, context : CompilationContext) -> None:
    file_cache: Dict[str, List[str]] = {}

    for diag in result.diagnostics:
        print_diagnostic_with_snippet(diag, file_cache, context)


def print_diagnostic_with_snippet(diag: Diagnostic, file_cache: Dict[str, List[str]], context: CompilationContext = None) -> None:
    # First line: header
    log_error(context, diag.format())

    if not diag.filename or diag.line is None:
        return

    try:
        lines = _load_file_lines(diag.filename, file_cache)
    except OSError:
        # Can't read file; fall back to header only
        return

    line_idx = diag.line - 1
    if not (0 <= line_idx < len(lines)):
        return

    src_line = lines[line_idx]

    # Pretty "N | ..." formatting (calculate width so multi-digit line numbers align)
    width = max(5, len(str(diag.line)))
    gutter = f"{diag.line:>{width}} | "

    log_error(context, gutter + src_line)

    if diag.column is None:
        return

    # Determine caret span (simple case: same line)
    start_col = max(1, diag.column)
    if diag.end_line is None or diag.end_column is None:
        end_col = start_col
    else:
        if diag.end_line == diag.line:
            end_col = max(start_col, diag.end_column)
        else:
            end_col = len(src_line) + 1

    caret_width = max(1, end_col - start_col)
    # Spaces: same gutter, then (start_col-1) spaces before carets
    caret_prefix = " " * width + " | " + " " * (start_col - 1)
    carets = "^" * caret_width
    log_error(context, caret_prefix + carets)


def build_search_paths(context: CompilationContext, args: argparse.Namespace) -> SourceSearchPaths:
    # if args.entry is a path, split into dir and module name
    entry_path = Path(args.entry)
    if entry_path.suffix == ".l0" or entry_path.is_absolute() or entry_path.parent != Path('.'):
        if entry_path.suffix == ".l0":
            module_name = entry_path.stem
        else:
            module_name = entry_path.name
        if entry_path.parent != Path('.'):
            args.project_root.append(str(entry_path.parent))
        args.entry = module_name
    if not args.project_root:
        args.project_root = ["."]
    if not args.sys_root:
        # Default system root from environment variable L0_SYSTEM if set
        # Supports multiple paths separated by : (Unix) or ; (Windows)
        sys_env = os.getenv("L0_SYSTEM")
        if sys_env:
            separator = ';' if os.name == 'nt' else ':'
            args.sys_root = [p for p in sys_env.split(separator) if p]
        else:
            args.sys_root = []
    sp = SourceSearchPaths()
    for root in args.sys_root:
        sp.add_system_root(root)
    for root in args.project_root:
        sp.add_project_root(root)
    sys_list = ",".join(f"'{p}'" for p in sp.system_roots)
    proj_list = ",".join(f"'{p}'" for p in sp.project_roots)
    log_info(context, f"System root(s): {sys_list or '<none>'}")
    log_info(context, f"Project root(s): {proj_list or '<none>'}")
    return sp


def build_compilation_context(args: argparse.Namespace) -> CompilationContext:
    """Build a CompilationContext from command-line arguments."""
    from l0_context import LogLevel

    # Log format
    log_rich_format = getattr(args, 'log', False)

    # Convert verbosity count to LogLevel
    verbosity = getattr(args, 'verbosity', 0)
    if verbosity >= 3:
        log_level = LogLevel.DEBUG
    elif verbosity >= 1:
        log_level = LogLevel.INFO
    else:
        log_level = LogLevel.ERROR

    return CompilationContext(
        emit_line_directives=not getattr(args, 'no_line_directives', False),
        log_rich_format=log_rich_format,
        log_level=log_level,
    )


def _run_analysis(args):
    """Run the analysis pipeline, returning (result, context, exit_code)."""
    context = build_compilation_context(args)
    search_paths = build_search_paths(context, args)
    driver = L0Driver(search_paths=search_paths, context=context)
    result = driver.analyze(args.entry)
    print_diagnostics(result, context=context)
    exit_code = 1 if (result.cu is None or result.has_errors()) else 0
    return result, context, exit_code


def _get_module_names(args, cu) -> List[str]:
    """Get list of module names based on --all-modules flag."""
    if getattr(args, 'all_modules', False):
        return sorted(cu.modules.keys())
    return [args.entry]


def cmd_build(args: argparse.Namespace) -> int:
    """Build an executable from an L0 module."""
    context = build_compilation_context(args)
    search_paths = build_search_paths(context, args)
    driver = L0Driver(search_paths=search_paths, context=context)

    result = driver.analyze(args.entry)
    print_diagnostics(result, context=context)

    if result.cu is None or result.has_errors():
        return 1

    # Generate C code
    backend = Backend(result)
    try:
        c_code = backend.generate()
    except InternalCompilerError as e:
        log_error(context, e.format())
        return 1

    # Determine output executable path
    if args.output:
        exe_path = Path(args.output)
    else:
        exe_path = Path("a.out")

    # Write C code to temporary or specified file
    if args.keep_c:
        c_path = exe_path.with_suffix(".c")
    else:
        c_path = Path(tempfile.mktemp(suffix=".c"))

    try:
        c_path.write_text(c_code)
        log_info(context, f"Generated C code: {c_path}")

        # Determine C compiler
        compiler = args.c_compiler or os.getenv("CC") or "gcc"

        # Build compiler command
        cmd = [compiler, str(c_path), "-o", str(exe_path)]

        # Add standard flags
        cmd.extend(["-std=c99", "-Wall", "-Wextra", "-Wno-unused", "-Wno-parentheses", "-pedantic-errors"])

        # Add runtime include path
        if args.runtime_include:
            cmd.extend(["-I", args.runtime_include])
        elif os.getenv("L0_RUNTIME_INCLUDE"):
            cmd.extend(["-I", os.getenv("L0_RUNTIME_INCLUDE")])

        # Add runtime library
        if args.runtime_lib:
            cmd.extend(["-L", args.runtime_lib, "-ll0runtime"])
        elif os.getenv("L0_RUNTIME_LIB"):
            cmd.extend(["-L", os.getenv("L0_RUNTIME_LIB"), "-ll0runtime"])

        log_info(context, f"Compiling: {' '.join(cmd)}")

        # Run C compiler
        compile_result = subprocess.run(cmd, capture_output=True, text=True)

        if compile_result.returncode != 0:
            log_error(context, "error: [L0C-0010] C compilation failed:")
            if compile_result.stderr:
                log_error(context, compile_result.stderr)
            if compile_result.stdout:
                log_error(context, compile_result.stdout)
            return 1

        if compile_result.stderr:
            log_error(context, compile_result.stderr)


        log_info(context, f"Built executable: {exe_path}")

        return 0

    finally:
        # Clean up temporary C file if not keeping it
        if not args.keep_c and c_path.exists():
            c_path.unlink()


def cmd_run(args: argparse.Namespace) -> int:
    """Build and run an L0 module."""
    context = build_compilation_context(args)
    # Create temporary executable
    with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
        temp_exe = f.name

    try:
        # Build to temporary executable
        build_args = argparse.Namespace(
            entry=args.entry,
            output=temp_exe,
            c_compiler=args.c_compiler,
            runtime_include=args.runtime_include,
            runtime_lib=args.runtime_lib,
            keep_c=False,
            verbosity=getattr(args, 'verbosity', 0),
            project_root=args.project_root,
            sys_root=args.sys_root,
            no_line_directives=args.no_line_directives,
            log=args.log,
        )

        rc = cmd_build(build_args)
        if rc != 0:
            return rc

        # Run the executable with any provided arguments
        log_info(context, f"Running: {temp_exe} {' '.join(args.args)}")

        run_result = subprocess.run([temp_exe] + args.args)
        return run_result.returncode

    # Handle Ctrl-C gracefully
    except KeyboardInterrupt:
        return 130
    finally:
        # Clean up temporary executable
        if Path(temp_exe).exists():
            Path(temp_exe).unlink()


def cmd_codegen(args: argparse.Namespace) -> int:
    """Generate C code for a module."""
    result, context, exit_code = _run_analysis(args)
    if exit_code != 0:
        return exit_code

    backend = Backend(result)
    try:
        c_code = backend.generate()
    except InternalCompilerError as e:
        log_error(context, e.format())
        return 1

    # Write to output file or stdout
    if args.output:
        Path(args.output).write_text(c_code)
    else:
        print(c_code)

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    _, _, exit_code = _run_analysis(args)
    return exit_code


def cmd_ast(args: argparse.Namespace) -> int:
    """
    Pretty-print the parsed AST.

    By default, prints only the entry module.
    With --all-modules, prints every module in the compilation unit.
    """
    context = build_compilation_context(args)
    search_paths = build_search_paths(context, args)
    driver = L0Driver(search_paths=search_paths, context=context)

    try:
        cu = driver.build_compilation_unit(args.entry)
    except Exception as e:
        log_error(context, f"error: [L0C-0020] {e}")
        return 1

    if args.all_modules:
        for name in sorted(cu.modules.keys()):
            mod = cu.modules[name]
            print(f"=== Module {name} ===")
            print(format_module(mod))
            print()
    else:
        mod = cu.modules.get(args.entry)
        if mod is None:
            log_error(context, f"error: [L0C-0030] entry module '{args.entry}' not found in compilation unit")
            return 1
        print(format_module(mod))

    return 0


def _dump_tokens_for_file(path: Path, include_eof: bool, context = None) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log_error(context, f"error: [L0C-0040] cannot read {path}: {e}")
        return 1

    lexer = Lexer(text, filename=str(path))
    tokens = lexer.tokenize()

    for tok in tokens:
        if not include_eof and tok.kind is TokenKind.EOF:
            continue
        # Format: file:line:col: KIND  'text'
        print(
            f"{path}:{tok.line}:{tok.column}:\t"
            f"{tok.kind.name:<12} {tok.text!r}"
        )
    return 0


def cmd_tok(args: argparse.Namespace) -> int:
    """
    Dump lexer tokens.

    By default, dumps tokens for the entry module only.
    With --all-modules, dumps tokens for all modules in the compilation unit.
    """
    context = build_compilation_context(args)
    search_paths = build_search_paths(context, args)
    driver = L0Driver(search_paths=search_paths, context=context)

    if args.all_modules:
        # Use the driver to discover all modules, then lex each file separately.
        try:
            cu = driver.build_compilation_unit(args.entry)
        except Exception as e:
            log_error(context, f"error: [L0C-0050] {e}")
            return 1

        exit_code = 0
        for name in sorted(cu.modules.keys()):
            try:
                path = search_paths.resolve(name)
            except FileNotFoundError as e:
                log_error(context, f"error: [L0C-0060] {e}")
                exit_code = 1
                continue

            print(f"=== Tokens for module {name} ({path}) ===")
            rc = _dump_tokens_for_file(path, include_eof=args.include_eof)
            if rc != 0:
                exit_code = rc
            print()
        return exit_code
    else:
        # Only the entry module: resolve its path directly.
        try:
            path = search_paths.resolve(args.entry)
        except FileNotFoundError as e:
            log_error(context, f"error: [L0C-0070] {e}")
            return 1

        return _dump_tokens_for_file(path, include_eof=args.include_eof)


def cmd_sym(args: argparse.Namespace) -> int:
    """
    Dump module-level symbol tables.

    By default dumps symbols only for the entry module.
    With --all-modules, dumps symbols for all modules in the compilation unit.
    """
    result, _, _ = _run_analysis(args)
    if result.cu is None:
        return 1

    module_names = _get_module_names(args, result.cu)

    for mod_name in module_names:
        env = result.module_envs.get(mod_name)
        if env is None:
            print(f"=== module {mod_name} (no symbol env) ===")
            continue

        print(f"=== module {mod_name} ===")

        # locals
        print("  locals:")
        if env.locals:
            for name in sorted(env.locals.keys()):
                sym = env.locals[name]
                type_str = f": {format_type(sym.type)}" if sym.type is not None else ""
                print(f"    {sym.kind.name:<12} {sym.name}{type_str}")
        else:
            print("    <none>")

        # imported
        print("  imported:")
        if env.imported:
            for name in sorted(env.imported.keys()):
                sym = env.imported[name]
                type_str = f": {format_type(sym.type)}" if sym.type is not None else ""
                print(
                    f"    {sym.kind.name:<12} {sym.name}"
                    f" (from {sym.module.name}){type_str}"
                )
        else:
            print("    <none>")

        # all
        print("  all:")
        if env.all:
            for name in sorted(env.all.keys()):
                sym = env.all[name]
                origin = (
                    "local" if name in env.locals
                    else ("imported" if name in env.imported else "unknown")
                )
                type_str = f": {format_type(sym.type)}" if sym.type is not None else ""
                print(
                    f"    {sym.kind.name:<12} {sym.name}"
                    f" [{origin}]{type_str}"
                )
        else:
            print("    <none>")

        print()

    return 0


def cmd_type(args: argparse.Namespace) -> int:
    """
    Dump resolved type information:

      - function signatures
      - struct field types
      - enum variant payloads
      - type aliases
    """
    result, _, _ = _run_analysis(args)
    if result.cu is None:
        return 1

    module_names = _get_module_names(args, result.cu)

    for mod_name in module_names:
        print(f"=== module {mod_name} ===")

        # Functions
        print("  functions:")
        any_funcs = False
        for (m, fname), ftype in sorted(result.func_types.items()):
            if m != mod_name:
                continue
            any_funcs = True
            print(f"    {fname}: {format_type(ftype)}")
        if not any_funcs:
            print("    <none>")

        # Structs
        print("  structs:")
        any_structs = False
        for (m, sname), sinfo in sorted(result.struct_infos.items()):
            if m != mod_name:
                continue
            any_structs = True
            print(f"    {sname}:")
            for field in sinfo.fields:
                print(f"      {field.name}: {format_type(field.type)}")
        if not any_structs:
            print("    <none>")

        # Enums
        print("  enums:")
        any_enums = False
        for (m, ename), einfo in sorted(result.enum_infos.items()):
            if m != mod_name:
                continue
            any_enums = True
            print(f"    {ename}:")
            for vname, vinfo in sorted(einfo.variants.items()):
                if not vinfo.field_types:
                    print(f"      {vname}")
                else:
                    fields_str = ", ".join(
                        format_type(t) for t in vinfo.field_types
                    )
                    print(f"      {vname}({fields_str})")
        if not any_enums:
            print("    <none>")

        # Type aliases (from symbol table)
        env = result.module_envs.get(mod_name)
        print("  type aliases:")
        if env is not None:
            aliases = [
                sym
                for sym in env.locals.values()
                if sym.kind == SymbolKind.TYPE_ALIAS
            ]
            if aliases:
                for sym in sorted(aliases, key=lambda s: s.name):
                    if sym.type is not None:
                        print(f"    {sym.name} = {format_type(sym.type)}")
                    else:
                        print(f"    {sym.name} = <unresolved>")
            else:
                print("    <none>")
        else:
            print("    <no module env>")

        print()

    return 0


def _add_entry_arg(parser: argparse.ArgumentParser) -> None:
    """Add the entry module argument."""
    parser.add_argument("entry", help="Entry module name (e.g. 'app.main')")


def _add_all_modules_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --all-modules flag."""
    parser.add_argument(
        "--all-modules", "-a",
        action="store_true",
        help="Process all modules in the compilation unit",
    )


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    """Add runtime-related arguments (compiler, include, lib paths)."""
    parser.add_argument(
        "--c-compiler",
        help="C compiler to use (default: $CC or gcc)",
    )
    parser.add_argument(
        "--runtime-include", "-I",
        help="Path to L0 runtime headers (default: $L0_RUNTIME_INCLUDE)",
    )
    parser.add_argument(
        "--runtime-lib", "-L",
        help="Path to L0 runtime library (default: $L0_RUNTIME_LIB)",
    )


def _add_codegen_arg(parser: argparse.ArgumentParser) -> None:
    """Add codegen-related arguments."""
    parser.add_argument(
        "--no-line-directives",
        action="store_true",
        help="Disable #line directives in generated C code",
    )


def main(argv=None) -> None:
    _init_env_defaults()
    parser = argparse.ArgumentParser(prog="l0c", description="L0 compiler (Stage 1)")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")

    parser.add_argument("-v", "--verbose",
                        action='count',
                        default=0,
                        dest='verbosity',
                        help="Increase verbosity: -v=INFO, -vvv=DEBUG")
    parser.add_argument("-l", "--log",
                        action='store_true',
                        default=False,
                        help="Enable rich log formatting (timestamps, levels)")
    parser.add_argument(
        "-P", "--project-root",
        action="append",
        default=[],
        help="Add a project source root (can be passed multiple times)",
    )
    parser.add_argument(
         "-S", "--sys-root",
        action="append",
        default=[],
        help="Add a system/stdlib source root (can be passed multiple times; default: $L0_SYSTEM as colon-separated paths)",
    )

    ###########################
    # run command
    ###########################
    p_run = subparsers.add_parser("run", help="Build and run a module")
    _add_runtime_args(p_run)
    _add_codegen_arg(p_run)
    _add_entry_arg(p_run)
    p_run.add_argument("args", nargs="*", help="Arguments to pass to the program")
    p_run.set_defaults(func=cmd_run)

    ###########################
    # build command
    ###########################
    p_build = subparsers.add_parser("build", help="Build an executable")
    p_build.add_argument("--output", "-o", help="Output executable path (default: a.out)")
    _add_runtime_args(p_build)
    _add_codegen_arg(p_build)
    p_build.add_argument("--keep-c", action="store_true",
                         help="Keep generated C file (saves as <output>.c)")
    _add_entry_arg(p_build)
    p_build.set_defaults(func=cmd_build)

    ###########################
    # gen command
    ###########################
    p_gen = subparsers.add_parser("gen", help="Generate C code", aliases=["codegen"])
    p_gen.add_argument("--output", "-o", help="Output C file (default: stdout)")
    _add_codegen_arg(p_gen)
    _add_entry_arg(p_gen)
    p_gen.set_defaults(func=cmd_codegen)

    ###########################
    # check command
    ###########################
    p_check = subparsers.add_parser("check", help="Parse and analyze a module", aliases=["analyze"])
    _add_entry_arg(p_check)
    p_check.set_defaults(func=cmd_check)

    ###########################
    # tok command
    ###########################
    p_tok = subparsers.add_parser("tok", help="Dump lexer tokens", aliases=["tokens"])
    _add_all_modules_arg(p_tok)
    p_tok.add_argument("--include-eof", "-I", action="store_true",
                       help="Include the EOF token in the output")
    _add_entry_arg(p_tok)
    p_tok.set_defaults(func=cmd_tok)

    ###########################
    # ast command
    ###########################
    p_ast = subparsers.add_parser("ast", help="Pretty-print the parsed AST")
    _add_all_modules_arg(p_ast)
    _add_entry_arg(p_ast)
    p_ast.set_defaults(func=cmd_ast)

    ###########################
    # sym command
    ###########################
    p_sym = subparsers.add_parser("sym", help="Dump module-level symbols", aliases=["symbols"])
    _add_all_modules_arg(p_sym)
    _add_entry_arg(p_sym)
    p_sym.set_defaults(func=cmd_sym)

    ###########################
    # type command
    ###########################
    p_type = subparsers.add_parser("type", help="Dump resolved types", aliases=["types"])
    _add_all_modules_arg(p_type)
    _add_entry_arg(p_type)
    p_type.set_defaults(func=cmd_type)

    args = parser.parse_args(argv)

    rc = args.func(args)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
