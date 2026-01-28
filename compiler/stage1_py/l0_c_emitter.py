"""
C Code Emitter

Handles C-specific code emission. Knows how to emit C syntax, but not why or when.
All high-level orchestration logic and decisions live in the Backend.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import dataclass, field
from typing import Dict, List, NoReturn, Optional, Set, Tuple

from l0_analysis import AnalysisResult
from l0_ast import (
    EnumDecl, EnumVariant, FuncDecl, LetDecl, StructDecl,
)
from l0_internal_error import InternalCompilerError, ICELocation
from l0_types import Type, BuiltinType, StructType, EnumType, PointerType, NullableType, FuncType, format_type


@dataclass
class CCodeBuilder:
    """
    Helper for building C code with indentation tracking.
    """
    lines: List[str] = field(default_factory=list)
    indent_level: int = 0
    indent_str: str = "    "  # 4 spaces

    def indent(self) -> None:
        self.indent_level += 1

    def dedent(self) -> None:
        assert self.indent_level > 0, "dedent below zero"
        self.indent_level -= 1

    def emit(self, line: str = "") -> None:
        """Emit a line with current indentation."""
        if line:
            self.lines.append(self.indent_str * self.indent_level + line)
        else:
            self.lines.append("")

    def emit_raw(self, line: str) -> None:
        """Emit a line without indentation."""
        self.lines.append(line)

    def to_string(self) -> str:
        return "\n".join(self.lines)


@dataclass
class CEmitter:
    """
    C-specific code emitter.

    Responsibilities:
    - Emit C syntax (knows C keywords, syntax, conventions)
    - Name mangling for C
    - Type emission (L0 types -> C types)
    - Statement/expression emission to C
    - Cleanup code emission (HOW to clean, not when/why)

    Does NOT:
    - Make decisions about what to emit
    - Perform semantic analysis
    - Manage scopes or lifetimes (queries backend for this)
    """

    # C keywords that need to be mangled to avoid compilation errors
    C_KEYWORDS: Set[str] = field(default_factory=lambda: {
        # C89/C99 keywords
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'inline', 'int', 'long', 'register', 'restrict', 'return', 'short',
        'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
        'unsigned', 'void', 'volatile', 'while',
        # C23 additions
        'alignas', 'alignof', 'atomic', 'bool', 'complex', 'imaginary',
        # Other identifiers to avoid
        'NULL', 'null', 'bool', 'true', 'false', 'asm', 'offsetof', 'typeof',
    })

    # Analysis data (set by Backend after construction)
    analysis: Optional[AnalysisResult] = None
    current_module: Optional[str] = None

    def set_analysis(self, analysis: AnalysisResult) -> None:
        self.analysis = analysis

    # Output builder
    out: CCodeBuilder = field(default_factory=CCodeBuilder)

    # Temporary variable counter for unique naming
    _tmp_counter: int = 0

    # Optional wrapper tracking (C-specific representation of T?)
    _opt_wrappers: Dict[str, Type] = field(default_factory=dict)
    _opt_emitted: Set[str] = field(default_factory=set)

    def get_output(self) -> str:
        """Returns the complete generated C code."""
        return self.out.to_string()

    # ============================================================================
    # Type Queries
    # ============================================================================

    def is_arc_type(self, ty: Type) -> bool:
        """Check if type needs ARC (reference counting). Currently only string."""
        return isinstance(ty, BuiltinType) and ty.name == "string"

    def has_owned_fields(self, ty: Type) -> bool:
        """Check if a type has fields that need cleanup."""
        if self.is_arc_type(ty):
            return True
        if isinstance(ty, StructType):
            info = self.analysis.struct_infos.get((ty.module, ty.name))
            if info:
                return any(self.has_owned_fields(f.type) for f in info.fields)
        if isinstance(ty, EnumType):
            enum_info = self.analysis.enum_infos.get((ty.module, ty.name))
            if enum_info:
                for vi in enum_info.variants.values():
                    if any(self.has_owned_fields(ft) for ft in vi.field_types):
                        return True
        return False

    def find_variant_decl(
            self, module_name: str, enum_name: str, variant_name: str
    ) -> Optional[EnumVariant]:
        """Look up an enum variant's AST declaration."""
        if self.analysis.cu is None:
            return None
        module = self.analysis.cu.modules.get(module_name)
        if not module:
            return None
        for decl in module.decls:
            if isinstance(decl, EnumDecl) and decl.name == enum_name:
                for variant in decl.variants:
                    if variant.name == variant_name:
                        return variant
        return None

    def ice(self, message: str, node: Optional[object] = None) -> NoReturn:
        """Raise an internal compiler error with context."""
        filename = None
        if self.current_module and self.analysis.cu:
            mod = self.analysis.cu.modules.get(self.current_module)
            if mod:
                filename = mod.filename
        span = getattr(node, "span", None) if node else None
        raise InternalCompilerError(message, ICELocation(filename=filename, span=span))

    # ============================================================================
    # Name Mangling (C-specific)
    # ============================================================================

    def mangle_struct_name(self, module_name: str, struct_name: str) -> str:
        """Mangle a struct name to avoid C namespace collisions."""
        mangled_module = module_name.replace(".", "_")
        return f"l0_{mangled_module}_{struct_name}"

    def mangle_enum_name(self, module_name: str, enum_name: str) -> str:
        """Mangle an enum name."""
        mangled_module = module_name.replace(".", "_")
        return f"l0_{mangled_module}_{enum_name}"

    def mangle_function_name(self, module_name: str, func_name: str) -> str:
        """Mangle a function name."""
        mangled_module = module_name.replace(".", "_")
        return f"l0_{mangled_module}_{func_name}"

    def mangle_let_name(self, module_name: str, let_name: str) -> str:
        """Mangle a top-level let name to C identifier."""
        safe_module = module_name.replace(".", "_")
        safe_name = let_name
        if safe_name in self.C_KEYWORDS:
            safe_name = f"l0_kw_{safe_name}"
        return f"l0_{safe_module}_{safe_name}"

    def mangle_identifier(self, name: str) -> str:
        """
        Mangle an identifier if it conflicts with C keywords or common extensions.
        Used for local variables, parameters, and pattern variables.

        Appends '__v' suffix to avoid C keyword conflicts.
        Also mangles names ending with '__v' itself,
        or starting with '_' or 'l0_' (to avoid clashes with L0 runtime names).
        """
        if name in self.C_KEYWORDS or name.endswith("__v") or name.startswith("l0_") or name.startswith("_"):
            return f"{name}__v"
        return name

    def fresh_tmp(self, kind: str = "tmp") -> str:
        """
        Generate a unique temporary variable name.

        Args:
            kind: Category of temporary (e.g., "tmp", "ptr", "try")

        Returns:
            Unique C identifier like "l0_tmp_1", "l0_ptr_2", etc.
        """
        self._tmp_counter += 1
        return f"l0_{kind}_{self._tmp_counter}"

    # ============================================================================
    # Intrinsic Emission
    # ============================================================================

    def emit_sizeof_type(self, typ: Type) -> str:
        """
        Emit C code for sizeof a given L0 type.

        Returns a C expression like "((l0_int)sizeof(l0_int))" or "((l0_int)sizeof(struct l0_module_MyStruct))"
        """
        c_type = self.emit_type(typ)
        return f"((l0_int)sizeof({c_type}))"

    def emit_ord(self, c_enum_expr: str) -> str:
        """
        Emit C code for ord(enum_value) intrinsic.

        Returns a C expression that extracts the tag field and casts to l0_int.
        """
        return f"((l0_int)(({c_enum_expr}).tag))"

    # ============================================================================
    # Type Emission (L0 types -> C types)
    # ============================================================================

    def emit_type(self, typ: Type) -> str:
        """
        Convert an L0 Type to its C representation.

        Returns a C type string (e.g., "l0_int", "struct l0_main_Point*")
        """
        if isinstance(typ, BuiltinType):
            if typ.name == "int":
                return "l0_int"
            elif typ.name == "byte":
                return "l0_byte"
            elif typ.name == "bool":
                return "l0_bool"
            elif typ.name == "string":
                return "l0_string"
            elif typ.name == "void":
                return "void"
            else:
                self.ice(f"[ICE-1290] unknown builtin type '{format_type(typ)}'", None)

        elif isinstance(typ, StructType):
            c_name = self.mangle_struct_name(typ.module, typ.name)
            return f"struct {c_name}"

        elif isinstance(typ, EnumType):
            c_name = self.mangle_enum_name(typ.module, typ.name)
            return f"struct {c_name}"

        elif isinstance(typ, PointerType):
            inner_c_type = self.emit_type(typ.inner)
            return f"{inner_c_type}*"

        elif isinstance(typ, NullableType):
            # Niche-optimize only pointer-shaped optionals: T*? is just T* (nullable pointer).
            if isinstance(typ.inner, PointerType):
                return self.emit_type(typ.inner)

            # General case: value-optional wrapper.
            return self._opt_wrapper_name_for_inner(typ.inner)

        elif isinstance(typ, FuncType):
            # Function pointer type
            self.ice(f"[ICE-1291] function pointer type emission not implemented", None)

        else:
            self.ice(f"[ICE-9299] unknown type kind for type emission: {type(typ)}", None)

    def _is_niche_nullable(self, t: NullableType) -> bool:
        """Check if a nullable type uses niche optimization (pointer-shaped)."""
        return isinstance(t.inner, PointerType)

    def is_niche_nullable(self, t: NullableType) -> bool:
        """Public wrapper for nullable shape checks."""
        return self._is_niche_nullable(t)

    def _opt_key_for_type(self, t: Type) -> str:
        """Generate a unique key for an optional wrapper type."""
        if isinstance(t, BuiltinType):
            return t.name
        if isinstance(t, StructType):
            return f"s_{self.mangle_struct_name(t.module, t.name)}"
        if isinstance(t, EnumType):
            return f"e_{self.mangle_enum_name(t.module, t.name)}"
        if isinstance(t, PointerType):
            return f"p_{self._opt_key_for_type(t.inner)}"
        if isinstance(t, NullableType):
            # Nullable-as-a-value can appear as an inner type via aliases.
            return f"n_{self._opt_key_for_type(t.inner)}"
        if isinstance(t, FuncType):
            return "fn"
        return "unk"

    def _opt_wrapper_name_for_inner(self, inner: Type) -> str:
        """Generate C typedef name for optional wrapper of given inner type."""
        return f"l0_opt_{self._opt_key_for_type(inner)}"

    def emit_none_value_for_nullable(self, t: NullableType) -> str:
        """Emit C code for the 'none' value of a nullable type."""
        if isinstance(t.inner, PointerType):
            return "NULL"
        wrapper_name = self._opt_wrapper_name_for_inner(t.inner)
        return f"(({wrapper_name}){{.has_value = 0}})"

    def emit_some_value_for_nullable(self, t: NullableType, c_inner_expr: str) -> str:
        """Emit C code for wrapping a value in 'some' for a nullable type."""
        if isinstance(t.inner, PointerType):
            return c_inner_expr
        wrapper_name = self._opt_wrapper_name_for_inner(t.inner)
        return f"(({wrapper_name}){{.has_value = 1, .value = {c_inner_expr}}})"

    def emit_null_literal(self, expected_type: Optional[Type], *, for_initializer: bool = False) -> str:
        """Emit a null literal appropriate for the expected type."""
        if isinstance(expected_type, NullableType):
            if self._is_niche_nullable(expected_type):
                return "NULL"
            if for_initializer:
                return "{0}"
            return self.emit_none_value_for_nullable(expected_type)
        self.ice(f"[ICE-1292] invalid expected type for null literal: {format_type(expected_type)}", None)

    def emit_widen_int(self, c_expr: str, src_type: BuiltinType, dst_type: BuiltinType) -> str:
        """Emit C code for implicit integer widening."""
        if src_type.name == dst_type.name:
            return c_expr
        if src_type.name == "byte" and dst_type.name == "int":
            return self.emit_cast(self.emit_type(dst_type), c_expr)
        self.ice(f"[ICE-1293] unsupported widening cast {format_type(src_type)} -> {format_type(dst_type)}", None)

    def emit_pointer_type(self, base_type: Type) -> str:
        """Emit C pointer type for a base type."""
        return f"{self.emit_type(base_type)}*"

    def emit_enum_tag(self, enum_type: EnumType, variant_name: str) -> str:
        """Emit C tag enum value for an enum variant."""
        c_enum_name = self.mangle_enum_name(enum_type.module, enum_type.name)
        return f"{c_enum_name}_{variant_name}"

    # ============================================================================
    # Output Formatting Utilities
    # ============================================================================

    def emit_section_comment(self, text: str) -> None:
        """Emit a section comment."""
        self.out.emit(f"/* {text} */")

    def emit_module_comment(self, module_name: str) -> None:
        """Emit a module comment."""
        self.out.emit(f"/* Module: {module_name} */")

    def emit_module_separator(self, module_name: str) -> None:
        """Emit a module separator with decorative lines."""
        self.out.emit("/* -------------------------------- */")
        self.out.emit(f"/* Module: {module_name} */")
        self.out.emit("/* -------------------------------- */")

    def emit_unreachable_comment(self) -> None:
        """Emit an unreachable code comment for debugging."""
        self.out.emit("/* unreachable code here */")

    # ============================================================================
    # Top-Level Structure Emission
    # ============================================================================

    def emit_header(self) -> None:
        """Emit C header boilerplate and L0 type layer."""
        self.out.emit("/* Generated by L0 compiler */")
        self.out.emit()
        self.out.emit("#include <stdint.h>")
        self.out.emit("#include <stdbool.h>")
        self.out.emit("#include <stddef.h>")
        self.out.emit()
        self.out.emit("/* L0 runtime header */")
        self.out.emit('#include "l0_runtime.h"')
        self.out.emit()

    def emit_line_directive(self, node, current_module: str) -> None:
        """Emit #line directive if node has span info and context allows it."""
        if not self.analysis.context.emit_line_directives:
            return
        if node is None or node.span is None:
            return
        filename = None
        if current_module and self.analysis.cu:
            mod = self.analysis.cu.modules.get(current_module)
            if mod:
                filename = mod.filename or f"{current_module}.l0"
        if filename:
            self.out.emit(f'#line {node.span.start_line} "{filename}"')

    def emit_forward_decls(self) -> None:
        """Emit forward declarations for all structs and enums."""
        self.out.emit("/* Forward declarations */")

        for module in self.analysis.cu.modules.values():
            for decl in module.decls:
                if isinstance(decl, StructDecl):
                    c_name = self.mangle_struct_name(module.name, decl.name)
                    self.out.emit(f"struct {c_name};")
                elif isinstance(decl, EnumDecl):
                    c_name = self.mangle_enum_name(module.name, decl.name)
                    self.out.emit(f"struct {c_name};")

        self.out.emit()

    def emit_struct(self, module_name: str, decl: StructDecl, struct_info) -> None:
        """Emit a single struct definition."""
        c_name = self.mangle_struct_name(module_name, decl.name)
        self.out.emit(f"struct {c_name} {{")
        self.out.indent()

        # Emit fields
        for field_info in struct_info.fields:
            c_type = self.emit_type(field_info.type)
            self.out.emit(f"{c_type} {field_info.name};")

        if not struct_info.fields:
            # Empty struct - add dummy field, as empty structs are not allowed in standard C (C99)
            self.out.emit("char __dummy__;")

        self.out.dedent()
        self.out.emit("};")
        self.out.emit()

    def emit_enum(self, module_name: str, decl: EnumDecl, enum_info) -> None:
        """
        Emit an enum as a tagged union.

        Example for:
            enum Expr {
                Int(value: int);
                Add(left: Expr*, right: Expr*);
            }

        Generates:
            enum l0_module_Expr_tag {
                l0_module_Expr_Int,
                l0_module_Expr_Add
            };

            struct l0_module_Expr {
                enum l0_module_Expr_tag tag;
                union {
                    struct { l0_int value; } Int;
                    struct { struct l0_module_Expr* left; struct l0_module_Expr* right; } Add;
                } data;
            };
        """
        c_name = self.mangle_enum_name(module_name, decl.name)
        tag_enum_name = f"{c_name}_tag"

        # Emit tag enum
        self.out.emit(f"enum {tag_enum_name} {{")
        self.out.indent()

        for variant in decl.variants:
            tag_value = f"{c_name}_{variant.name}"
            self.out.emit(f"{tag_value},")

        self.out.dedent()
        self.out.emit("};")
        self.out.emit()

        # Emit tagged union struct
        self.out.emit(f"struct {c_name} {{")
        self.out.indent()
        self.out.emit(f"enum {tag_enum_name} tag;")

        # Emit union of variant payloads
        self.out.emit("union {")
        self.out.indent()

        for variant in decl.variants:
            variant_info = enum_info.variants.get(variant.name)
            if variant_info is None:
                self.ice(f"[ICE-1271] missing VariantInfo for {module_name}.{decl.name}.{variant.name}", variant)

            if not variant_info.field_types:
                # Empty variant - still need a struct for uniform access
                self.out.emit(f"struct {{ char __dummy__; }} {variant.name};")
            else:
                # Variant with fields
                field_decls = []
                for field_, ftype in zip(variant.fields, variant_info.field_types):
                    c_type = self.emit_type(ftype)
                    field_decls.append(f"{c_type} {field_.name}")

                fields_str = "; ".join(field_decls) + ";"
                self.out.emit(f"struct {{ {fields_str} }} {variant.name};")

        self.out.dedent()
        self.out.emit("} data;")

        self.out.dedent()
        self.out.emit("};")
        self.out.emit()

    def emit_let_declaration(self, module_name: str, decl: LetDecl, let_type: Type, let_initializer_callback) -> None:
        """
        Emit a single top-level let declaration as a static variable.

        Args:
            module_name: Module containing the let
            decl: Let declaration AST node
            let_type: Resolved type of the let
            let_initializer_callback: Callback to emit initializer expression
        """
        c_type = self.emit_type(let_type)
        c_name = self.mangle_let_name(module_name, decl.name)
        c_init = let_initializer_callback(decl.value, let_type)
        self.out.emit(f"static {c_type} {c_name} = {c_init};")

    def emit_function_declaration(self, module_name: str, decl: FuncDecl, func_type: FuncType) -> None:
        """Emit a single function declaration."""
        # CRITICAL: extern functions are NOT mangled - they're the FFI boundary
        if decl.is_extern:
            c_name = decl.name
        else:
            c_name = self.mangle_function_name(module_name, decl.name)

        c_return_type = self.emit_type(func_type.result)

        # Parameter list
        if not func_type.params:
            params_str = "void"
        else:
            param_strs = []
            for param, ptype in zip(decl.params, func_type.params):
                c_ptype = self.emit_type(ptype)
                c_param_name = self.mangle_identifier(param.name)
                param_strs.append(f"{c_ptype} {c_param_name}")
            params_str = ", ".join(param_strs)

        self.out.emit(f"{c_return_type} {c_name}({params_str});")

    def emit_function_definition_header(self, module_name: str, decl: FuncDecl, func_type: FuncType) -> None:
        """
        Emit function definition header (signature + opening brace).

        Body emission is handled by the backend's statement emitter.
        """
        c_name = self.mangle_function_name(module_name, decl.name)
        c_return_type = self.emit_type(func_type.result)

        # Parameter list
        if not func_type.params:
            params_str = "void"
        else:
            param_strs = []
            for param, ptype in zip(decl.params, func_type.params):
                c_ptype = self.emit_type(ptype)
                c_param_name = self.mangle_identifier(param.name)
                param_strs.append(f"{c_ptype} {c_param_name}")
            params_str = ", ".join(param_strs)

        # Function header
        self.out.emit(f"{c_return_type} {c_name}({params_str})")
        self.out.emit("{")
        self.out.indent()

    def emit_function_definition_footer(self) -> None:
        """Emit function definition footer (closing brace)."""
        self.out.dedent()
        self.out.emit("}")
        self.out.emit()

    def emit_main_wrapper(self, entry_module: str, func_type: FuncType) -> None:
        """
        Emit C main() wrapper that calls the L0 main function.

        This allows consistent mangling of all L0 functions while providing
        the expected C entry point.
        """
        self.out.emit("/* C entry point wrapper */")
        self.out.emit(f"int main(int argc, char **argv)")
        self.out.emit("{")
        self.out.indent()

        # Take care of argc/argv
        self.out.emit("_rt_init_args(argc, argv);")

        # Determine return type and call
        mangled_name = self.mangle_function_name(entry_module, "main")
        c_return_type = self.emit_type(func_type.result)

        if c_return_type == "l0_int":
            # Regular int return
            self.out.emit(f"return (int) {mangled_name}();")
        elif c_return_type == "bool":
            # Bool return: convert to int
            self.out.emit(f"bool result = {mangled_name}();")
            self.out.emit("return result ? 0 : 1;")
        else:
            # 'void' or other return type (ignore return value)
            self.out.emit(f"{mangled_name}();")
            self.out.emit("return 0;")

        self.out.dedent()
        self.out.emit("}")
        self.out.emit()

    # ============================================================================
    # Optional Wrapper Emission (C-specific T? representation)
    # ============================================================================

    def _collect_opt_wrappers_from_type(self, t: Type) -> None:
        """Recursively collect optional wrapper types needed for a given type."""
        if isinstance(t, NullableType):
            if not self._is_niche_nullable(t):
                name = self._opt_wrapper_name_for_inner(t.inner)
                self._opt_wrappers[name] = t.inner
                # Inner itself may be another nullable-by-value (nested aliases), so recurse.
                self._collect_opt_wrappers_from_type(t.inner)
            else:
                # Pointer? -> no wrapper, but still traverse the pointer's inner for completeness.
                self._collect_opt_wrappers_from_type(t.inner)
            return

        if isinstance(t, PointerType):
            self._collect_opt_wrappers_from_type(t.inner)
            return

        if isinstance(t, FuncType):
            for p in t.params:
                self._collect_opt_wrappers_from_type(p)
            self._collect_opt_wrappers_from_type(t.result)
            return

    def _is_early_inner(self, inner: Type) -> bool:
        """
        Check if an inner type can be emitted early (before user-defined types).

        Early wrappers are those we can define before user struct/enum definitions.
        Builtins (including string as l0_string) are fine.
        """
        if isinstance(inner, BuiltinType):
            return True
        # Nullable-by-value of a builtin is also early (depends on its own wrapper).
        if isinstance(inner, NullableType) and not self._is_niche_nullable(inner):
            return self._is_early_inner(inner.inner)
        return False

    def prepare_optional_wrappers(self) -> None:
        """
        Scan all types in the analysis result and collect optional wrappers needed.
        """
        self._opt_wrappers.clear()
        self._opt_emitted.clear()

        # Function signatures
        for ft in self.analysis.func_types.values():
            self._collect_opt_wrappers_from_type(ft)

        # Struct fields / enum payloads
        for info in self.analysis.struct_infos.values():
            for f in info.fields:
                self._collect_opt_wrappers_from_type(f.type)

        for einfo in self.analysis.enum_infos.values():
            for v in einfo.variants.values():
                for ft in v.field_types:
                    self._collect_opt_wrappers_from_type(ft)

        # Also scan inferred expr types (covers locals/temps that never appear in sigs)
        for t in self.analysis.expr_types.values():
            self._collect_opt_wrappers_from_type(t)

    def emit_optional_wrappers(self, *, early: bool) -> None:
        """
        Emit typedef declarations for optional wrapper types.

        Args:
            early: If True, emit wrappers for builtin types only.
                   If False, emit wrappers for user-defined types.
        """
        # Emit typedefs for all needed wrappers whose inner types are ready at this phase.
        items = sorted(self._opt_wrappers.items(), key=lambda kv: kv[0])
        for name, inner in items:
            if name in self._opt_emitted:
                continue
            if self._is_early_inner(inner) != early:
                continue

            c_inner = self.emit_type(inner)  # may itself be another l0_opt_...

            # Emit #ifndef guard (so builtins won't conflict, and user-type wrappers still work).
            self.out.emit(f"#ifndef {name.upper()}_DEFINED")
            self.out.emit(f"#define {name.upper()}_DEFINED")
            self.out.emit(f"typedef struct {{ l0_bool has_value; {c_inner} value; }} {name};")
            self.out.emit(f"#endif /* {name.upper()}_DEFINED */")
            self.out.emit()
            self._opt_emitted.add(name)

    # ============================================================================
    # Cleanup Emission (HOW to emit cleanup code)
    # ============================================================================

    def emit_value_cleanup(self, c_expr: str, ty: Type) -> None:
        """
        Emit cleanup code for a by-value variable.

        Args:
            c_expr: C expression for the value (e.g., "x__v", "obj.field")
            ty: The type of the value being cleaned up
        """
        if self.is_arc_type(ty):
            self.out.emit(f"rt_string_release({c_expr});")

        elif isinstance(ty, StructType):
            info = self.analysis.struct_infos.get((ty.module, ty.name))
            if info is None:
                return

            for field_ in info.fields:
                field_expr = f"({c_expr}).{field_.name}"
                self._emit_field_cleanup(field_expr, field_.type)

        elif isinstance(ty, EnumType):
            self._emit_enum_value_cleanup(c_expr, ty)

    def _emit_enum_value_cleanup(self, c_expr: str, enum_type: EnumType) -> None:
        """
        Emit cleanup code for an enum by-value variable.
        Switches on tag to clean up only the active variant's owned fields.
        """
        enum_info = self.analysis.enum_infos.get((enum_type.module, enum_type.name))
        if enum_info is None:
            return

        c_enum_name = self.mangle_enum_name(enum_type.module, enum_type.name)

        # Check if any variant has owned fields
        has_owned = any(
            any(self.has_owned_fields(ft) for ft in vi.field_types)
            for vi in enum_info.variants.values()
        )

        if not has_owned:
            return

        # Emit switch on tag
        self.out.emit(f"switch (({c_expr}).tag) {{")

        for variant_name, variant_info in enum_info.variants.items():
            tag_value = f"{c_enum_name}_{variant_name}"

            variant_has_owned = any(
                self.has_owned_fields(ft) for ft in variant_info.field_types
            )

            if not variant_has_owned:
                continue

            self.out.emit(f"case {tag_value}: {{")
            self.out.indent()

            # Find variant decl from context
            variant_decl = self.find_variant_decl(
                enum_type.module, enum_type.name, variant_name
            )

            if variant_decl and len(variant_decl.fields) == len(variant_info.field_types):
                for field_decl, field_type in zip(variant_decl.fields, variant_info.field_types):
                    field_expr = f"({c_expr}).data.{variant_name}.{field_decl.name}"
                    self._emit_field_cleanup(field_expr, field_type)

            self.out.emit("break;")
            self.out.dedent()
            self.out.emit("}")

        self.out.emit("default: break;")
        self.out.emit("}")

    def emit_struct_cleanup(self, c_ptr_expr: str, struct_type: StructType) -> None:
        """
        Emit cleanup code for all owned fields in a struct.
        Recursively handles nested structs (by-value fields).
        """
        info = self.analysis.struct_infos.get((struct_type.module, struct_type.name))
        if info is None:
            self.ice(f"[ICE-1270] missing StructInfo for {struct_type.module}.{struct_type.name}", None)

        self.out.emit(f"if ({c_ptr_expr} != NULL) {{")
        self.out.indent()

        for field_ in info.fields:
            field_expr = f"{c_ptr_expr}->{field_.name}"
            self._emit_field_cleanup(field_expr, field_.type)

        self.out.dedent()
        self.out.emit("}")

    def emit_enum_cleanup(self, c_ptr_expr: str, enum_type: EnumType) -> None:
        """
        Emit cleanup code for owned fields in an enum's active variant.
        Uses switch on tag to only clean up the fields that are actually present.
        """
        enum_info = self.analysis.enum_infos.get((enum_type.module, enum_type.name))
        if enum_info is None:
            self.ice(f"[ICE-1080] missing EnumInfo for {enum_type.module}.{enum_type.name}", None)

        c_enum_name = self.mangle_enum_name(enum_type.module, enum_type.name)

        # Check if any variant has owned fields
        has_owned = any(
            any(self.has_owned_fields(ft) for ft in vi.field_types)
            for vi in enum_info.variants.values()
        )

        if not has_owned:
            return

        # Emit switch on tag
        self.out.emit(f"if ({c_ptr_expr} != NULL) {{")
        self.out.indent()

        self.out.emit(f"switch ({c_ptr_expr}->tag) {{")

        for variant_name, variant_info in enum_info.variants.items():
            tag_value = f"{c_enum_name}_{variant_name}"

            variant_has_owned = any(
                self.has_owned_fields(ft) for ft in variant_info.field_types
            )

            if not variant_has_owned:
                continue

            self.out.emit(f"case {tag_value}: {{")
            self.out.indent()

            # Find variant decl from context
            variant_decl = self.find_variant_decl(
                enum_type.module, enum_type.name, variant_name
            )

            if variant_decl and len(variant_decl.fields) == len(variant_info.field_types):
                for field_decl, field_type in zip(variant_decl.fields, variant_info.field_types):
                    field_expr = f"{c_ptr_expr}->data.{variant_name}.{field_decl.name}"
                    self._emit_field_cleanup(field_expr, field_type)

            self.out.emit("break;")
            self.out.dedent()
            self.out.emit("}")

        self.out.emit("default: break;")
        self.out.emit("}")

        self.out.dedent()
        self.out.emit("}")

    def _emit_field_cleanup(self, field_expr: str, field_type: Type) -> None:
        """
        Emit cleanup code for a single field of a given type.

        - string: release
        - struct by value: recursively clean up its fields
        - enum by value: recursively clean up active variant
        - pointer: no auto-cleanup (user's responsibility)
        """
        if self.is_arc_type(field_type):
            # Release string fields
            self.out.emit(f"rt_string_release({field_expr});")

        elif isinstance(field_type, StructType):
            # Nested struct by value: recursively clean up
            info = self.analysis.struct_infos.get((field_type.module, field_type.name))
            if info is None:
                return

            for nested_field in info.fields:
                nested_expr = f"({field_expr}).{nested_field.name}"
                self._emit_field_cleanup(nested_expr, nested_field.type)

        elif isinstance(field_type, EnumType):
            # Nested enum by value: switch on tag and clean up active variant
            self._emit_enum_value_cleanup(field_expr, field_type)

        elif isinstance(field_type, PointerType):
            # Pointer fields: NOT auto-dropped in Stage 1
            pass

    # ============================================================================
    # Expression Emission (C syntax for expressions)
    # ============================================================================

    def emit_int_literal(self, value: int) -> str:
        """Emit C code for an integer literal."""
        return str(value)

    def emit_byte_literal(self, value: str) -> str:
        """Emit C code for a byte literal."""
        return f"((l0_byte)'{value}')"

    def emit_string_literal(self, value: str) -> str:
        """Emit C code for a string literal."""
        return f'_rt_l0_string_from_const_literal("{value}")'

    def emit_const_string_literal(self, value: str) -> str:
        """Emit C code for a static string literal initializer."""
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
        str_len = len(value)
        return (
            "{ .kind = L0_STRING_K_STATIC, .data = { .s_str = { "
            f".len = {str_len}, .bytes = \"{escaped}\" "
            "} } }"
        )

    def emit_bool_literal(self, value: bool) -> str:
        """Emit C code for a boolean literal."""
        return "1" if value else "0"

    def emit_const_bool_literal(self, value: bool) -> str:
        """Emit C code for a boolean literal in a static initializer."""
        return "true" if value else "false"

    def emit_var_ref(self, c_name: str) -> str:
        """Emit C code for a variable reference."""
        return c_name

    def emit_unary_op(self, op: str, c_operand: str) -> str:
        """Emit C code for a unary operation."""
        return f"({op}{c_operand})"

    def emit_binary_op(self, op: str, c_left: str, c_right: str) -> str:
        """Emit C code for a simple binary operation."""
        return f"({c_left} {op} {c_right})"

    def emit_checked_int_div(self, c_left: str, c_right: str) -> str:
        """Emit C code for checked integer division."""
        return f"(_rt_idiv({c_left}, {c_right}))"

    def emit_checked_int_mod(self, c_left: str, c_right: str) -> str:
        """Emit C code for checked integer modulo."""
        return f"(_rt_imod({c_left}, {c_right}))"

    def emit_checked_int_mul(self, c_left: str, c_right: str) -> str:
        """Emit C code for checked integer multiplication."""
        return f"(_rt_imul({c_left}, {c_right}))"

    def emit_checked_int_add(self, c_left: str, c_right: str) -> str:
        """Emit C code for checked integer addition."""
        return f"(_rt_iadd({c_left}, {c_right}))"

    def emit_checked_int_sub(self, c_left: str, c_right: str) -> str:
        """Emit C code for checked integer subtraction."""
        return f"(_rt_isub({c_left}, {c_right}))"

    def emit_function_call(self, c_func_name: str, c_args: str) -> str:
        """Emit C code for a function call."""
        return f"{c_func_name}({c_args})"

    def emit_field_access(self, c_obj: str, field_name: str, is_pointer: bool) -> str:
        """Emit C code for field access."""
        if is_pointer:
            return f"({c_obj})->{field_name}"
        else:
            return f"({c_obj}).{field_name}"

    def emit_paren_expr(self, c_inner: str) -> str:
        """Emit C code for a parenthesized expression."""
        return f"({c_inner})"

    def emit_cast(self, c_type: str, c_inner: str) -> str:
        """Emit C code for a cast."""
        return f"(({c_type})({c_inner}))"

    def emit_checked_narrow_cast(self, c_dst_type: str, c_inner: str) -> str:
        """Emit C code for a checked narrowing cast."""
        return f"(_rt_narrow_{c_dst_type}({c_inner}))"

    def emit_unwrap_ptr(self, c_dst_type: str, c_inner: str, type_str: str) -> str:
        """Emit C code for unwrapping a pointer-shaped optional."""
        return f"(({c_dst_type}) _unwrap_ptr({c_inner}, \"{type_str}\"))"

    def emit_unwrap_opt(self, c_src_type: str, c_inner: str, type_str: str) -> str:
        """Emit C code for unwrapping a value-optional."""
        return f"((({c_src_type}*) _unwrap_opt(&({c_inner}), \"{type_str}\"))->value)"

    def emit_null_check_eq(self, c_expr: str) -> str:
        """Emit C code for null equality check (opt == null)."""
        return f"(!(({c_expr}).has_value))"

    def emit_null_check_ne(self, c_expr: str) -> str:
        """Emit C code for null inequality check (opt != null)."""
        return f"(({c_expr}).has_value)"

    def emit_pointer_null_check(self, c_expr: str, op: str) -> str:
        """Emit C code for pointer null check."""
        return f"({c_expr} {op} NULL)"

    # ============================================================================
    # Lvalue Emission (C syntax for lvalues)
    # ============================================================================

    def emit_deref_lvalue(self, ptr_expr: str) -> str:
        """Emit C code for a dereference lvalue: (*ptr)"""
        return f"(*{ptr_expr})"

    def emit_field_lvalue(self, obj: str, field: str, is_pointer: bool) -> str:
        """Emit C code for a field access lvalue: obj->field or obj.field"""
        return f"{obj}->{field}" if is_pointer else f"{obj}.{field}"

    def emit_index_lvalue(self, base: str, index: str) -> str:
        """Emit C code for an index lvalue: base[idx]"""
        return f"{base}[{index}]"

    # ============================================================================
    # Constructor Emission (C syntax for struct/enum constructors)
    # ============================================================================

    def emit_struct_constructor(self, c_struct_name: str, field_inits: List[Tuple[str, str]]) -> str:
        """
        Emit C code for a struct constructor.

        Args:
            c_struct_name: Mangled C struct name
            field_inits: List of (field_name, c_value) tuples

        Returns:
            C compound literal: (struct name){ .f1 = v1, .f2 = v2 }
        """
        if not field_inits:
            return f"(struct {c_struct_name}){{ 0 }}"

        inits_str = ", ".join(f".{name} = {value}" for name, value in field_inits)
        return f"(struct {c_struct_name}){{ {inits_str} }}"

    def emit_struct_constructor_for_type(self, struct_type: StructType, field_inits: List[Tuple[str, str]]) -> str:
        """Emit a struct constructor for a given L0 struct type."""
        c_struct_name = self.mangle_struct_name(struct_type.module, struct_type.name)
        return self.emit_struct_constructor(c_struct_name, field_inits)

    def emit_variant_constructor(
            self,
            c_enum_name: str,
            variant_name: str,
            tag_value: str,
            payload_inits: List[Tuple[str, str]]
    ) -> str:
        """
        Emit C code for an enum variant constructor.

        Args:
            c_enum_name: Mangled C enum name
            variant_name: Name of the variant
            tag_value: C tag value (e.g., "l0_main_Expr_Int")
            payload_inits: List of (field_name, c_value) tuples

        Returns:
            C tagged union literal: (struct enum){ .tag = X, .data = { .Variant = { .f = v } } }
        """
        if not payload_inits:
            return f"(struct {c_enum_name}){{ .tag = {tag_value} }}"

        payload_str = ", ".join(f".{name} = {value}" for name, value in payload_inits)
        return f"(struct {c_enum_name}){{ .tag = {tag_value}, .data = {{ .{variant_name} = {{ {payload_str} }} }} }}"

    def emit_variant_constructor_for_type(
            self,
            enum_type: EnumType,
            variant_name: str,
            payload_inits: List[Tuple[str, str]]
    ) -> str:
        """Emit a tagged union constructor for a given L0 enum type."""
        c_enum_name = self.mangle_enum_name(enum_type.module, enum_type.name)
        tag_value = self.emit_enum_tag(enum_type, variant_name)
        return self.emit_variant_constructor(c_enum_name, variant_name, tag_value, payload_inits)

    def emit_pattern_binding_init(self, scrutinee: str, variant: str, field: str) -> str:
        """
        Emit C code for initializing a pattern binding variable.

        Args:
            scrutinee: Name of the scrutinee variable (e.g., "_scrutinee")
            variant: Name of the variant being matched
            field: Name of the field being extracted

        Returns:
            C field access expression: _scrutinee.data.Variant.field
        """
        return f"{scrutinee}.data.{variant}.{field}"

    # ============================================================================
    # Statement Emission (C syntax for statements)
    # ============================================================================

    def emit_expr_stmt(self, c_expr: str) -> None:
        """Emit an expression statement."""
        self.out.emit(f"{c_expr};")

    def emit_return_stmt(self, c_value: Optional[str]) -> None:
        """Emit a return statement."""
        if c_value is not None:
            self.out.emit(f"return {c_value};")
        else:
            self.out.emit("return;")

    def emit_break_stmt(self) -> None:
        """Emit a break statement."""
        self.out.emit("break;")

    def emit_continue_stmt(self) -> None:
        """Emit a continue statement."""
        self.out.emit("continue;")

    def emit_block_start(self) -> None:
        """Emit opening brace for a block."""
        self.out.emit("{")
        self.out.indent()

    def emit_block_end(self) -> None:
        """Emit closing brace for a block."""
        self.out.dedent()
        self.out.emit("}")

    def emit_while_header(self, c_cond: str) -> None:
        """Emit while loop header."""
        self.out.emit(f"while ({c_cond})")

    def emit_if_header(self, c_cond: str) -> None:
        """Emit if statement header."""
        self.out.emit(f"if ({c_cond})")

    def emit_else(self) -> None:
        """Emit else keyword."""
        self.out.emit("else")

    def emit_for_loop_start(self) -> None:
        """Emit for loop outer block start."""
        self.out.emit("// for loop")
        self.out.emit("{")
        self.out.indent()

    def emit_for_loop_end(self) -> None:
        """Emit for loop outer block end."""
        self.out.dedent()
        self.out.emit("}")

    def emit_let_decl(self, c_type: str, c_var_name: str, c_init: str) -> None:
        """Emit let variable declaration."""
        self.out.emit(f"{c_type} {c_var_name} = {c_init};")

    def emit_assignment(self, c_target: str, c_value: str) -> None:
        """Emit simple assignment."""
        self.out.emit(f"{c_target} = {c_value};")

    def emit_pointer_assignment(self, c_ptr_name: str, c_value: str) -> None:
        """Emit assignment through a pointer."""
        self.out.emit(f"*{c_ptr_name} = {c_value};")

    def emit_temp_decl(self, c_type: str, c_temp_name: str, c_value: str) -> None:
        """Emit temporary variable declaration."""
        self.out.emit(f"{c_type} {c_temp_name} = {c_value};")

    def emit_string_retain(self, c_expr: str) -> None:
        """Emit string retain call."""
        self.out.emit(f"rt_string_retain({c_expr});")

    def emit_string_release(self, c_expr: str) -> None:
        """Emit string release call."""
        self.out.emit(f"rt_string_release({c_expr});")

    def emit_comment(self, comment: str) -> None:
        """Emit a C comment."""
        self.out.emit(f"/* {comment} */")

    def emit_match_scrutinee_decl(self, c_type: str, c_expr: str) -> None:
        """Emit match scrutinee declaration."""
        self.out.emit(f"{c_type} _scrutinee = {c_expr};")

    def emit_switch_start(self, c_expr: str) -> None:
        """Emit switch statement start."""
        self.out.emit(f"switch ({c_expr}) {{")

    def emit_match_switch_start(self, scrutinee_name: str) -> None:
        """Emit a match switch over the enum tag."""
        self.emit_switch_start(f"{scrutinee_name}.tag")

    def emit_switch_end(self) -> None:
        """Emit switch statement end."""
        self.out.emit("}")

    def emit_case_label(self, c_tag_value: str) -> None:
        """Emit case label."""
        self.out.emit(f"case {c_tag_value}:")

    def emit_default_label(self) -> None:
        """Emit default case label."""
        self.out.emit("default:")

    def emit_drop_call(self, c_ptr_expr: str) -> None:
        """Emit drop runtime call."""
        self.out.emit(f"_rt_drop((void*){c_ptr_expr});")

    def emit_null_assignment(self, c_var: str) -> None:
        """Emit assignment to NULL."""
        self.out.emit(f"{c_var} = NULL;")

    def emit_alloc_obj(self, c_ptr_type: str, c_base_type: str, c_temp_name: str) -> None:
        """Emit heap allocation for new expression."""
        self.out.emit(f"{c_ptr_type} {c_temp_name} = ({c_ptr_type})_rt_alloc_obj((l0_int)sizeof({c_base_type}));")

    def emit_struct_init(self, c_temp_name: str, c_base_type: str, c_init_str: str) -> None:
        """Emit struct initialization for new expression."""
        self.out.emit(f"*{c_temp_name} = ({c_base_type}){{ {c_init_str} }};")

    def emit_struct_init_from_fields(
            self,
            c_temp_name: str,
            base_type: Type,
            field_inits: List[Tuple[str, str]]
    ) -> None:
        """Emit struct initialization using field initializers."""
        c_base_type = self.emit_type(base_type)
        init_str = ", ".join(f".{name} = {value}" for name, value in field_inits)
        self.emit_struct_init(c_temp_name, c_base_type, init_str)

    def emit_enum_variant_init(
            self,
            c_temp_name: str,
            enum_type: EnumType,
            variant_name: str,
            payload_inits: List[Tuple[str, str]]
    ) -> None:
        """Emit enum variant initialization for a heap-allocated enum."""
        c_base_type = self.emit_type(enum_type)
        tag_value = self.emit_enum_tag(enum_type, variant_name)
        if not payload_inits:
            init_str = f".tag = {tag_value}"
        else:
            payload_str = ", ".join(f".{name} = {value}" for name, value in payload_inits)
            init_str = f".tag = {tag_value}, .data = {{ .{variant_name} = {{ {payload_str} }} }}"
        self.emit_struct_init(c_temp_name, c_base_type, init_str)

    def emit_zero_init(self, c_temp_name: str, c_base_type: str) -> None:
        """Emit zero initialization."""
        self.out.emit(f"*{c_temp_name} = ({c_base_type}){{ 0 }};")

    def emit_try_check_niche(self, c_tmp: str, ret_none: str) -> None:
        """Emit try expression null check for niche-optimized optional."""
        self.out.emit(f"if ({c_tmp} == NULL) return {ret_none};")

    def emit_try_check_value(self, c_tmp: str, ret_none: str) -> None:
        """Emit try expression check for value-optional."""
        self.out.emit(f"if (!{c_tmp}.has_value) return {ret_none};")

    def emit_try_extract_value(self, c_tmp: str) -> str:
        """Emit extraction of value from value-optional."""
        return f"({c_tmp}.value)"
