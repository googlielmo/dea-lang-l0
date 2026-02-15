#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

def test_codegen_enum_tagging_and_match_switch(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        enum Option { None; Some(value: int); }

        func main() -> int {
            let opt: Option = Some(42);
            match (opt) {
                None => { return 0; }
                Some(v) => { return v; }
            }
        }
        """,
    )

    if c_code is None:
        return

    assert "enum l0_main_Option_tag" in c_code
    assert "l0_main_Option_None" in c_code
    assert "l0_main_Option_Some" in c_code
    assert "switch (_scrutinee.tag)" in c_code


def test_codegen_struct_field_access_and_nullability(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        struct Point { x: int; }

        func get_x(p: Point) -> int { return p.x; }
        func get_x_ptr(p: Point*) -> int { return p.x; }

        func main() -> int {
            let n: int? = null;
            let p: int*? = null;
            return get_x(new Point(1));
        }
        """,
    )

    if c_code is None:
        return

    assert "(p).x" in c_code
    assert "(p)->x" in c_code
    assert "l0_opt_int" in c_code
    assert "l0_int* p = NULL;" in c_code


def test_codegen_string_refcounts_and_cleanup_order(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func main() -> int {
            let a: string = "a";
            let b: string = a;
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "rt_string_retain(l0_copy_" in c_code

    b_release = c_code.find("rt_string_release(b);")
    a_release = c_code.find("rt_string_release(a);")
    assert b_release != -1 and a_release != -1
    assert b_release < a_release


def test_codegen_struct_cleanup_order_for_owned_fields(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        struct Pair {
            first: string;
            second: string;
        }

        func main() -> int {
            let p: Pair* = new Pair("a", "b");
            drop p;
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    first_release = c_code.find("rt_string_release(p->first);")
    second_release = c_code.find("rt_string_release(p->second);")
    assert first_release != -1 and second_release != -1
    assert first_release < second_release


def test_codegen_optional_string_cleanup_guards_and_order(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.string;
        extern func log(x: int) -> void;

        struct OptBox { value: string?; }

        enum OptEnum {
            None;
            Some(value: string?);
        }

        func fallthrough() -> void {
            let s: string = concat_s("raw", "-value");
            let wrapped: string? = s;
            let v: string? = concat_s("fall", "through") as string?;
            let box: OptBox = OptBox(v);
            let en: OptEnum = Some(v);
            let box2: OptBox = OptBox(wrapped);
        }

        func early_return(flag: bool) -> string? {
            let v: string? = concat_s("re", "turn") as string?;
            if (flag) {
                return v;
            }
            return null;
        }

        func loop_exit() -> void {
            let i: int = 0;
            while (i < 3) {
                let v: string? = concat_s("lo", "op") as string?;
                let box: OptBox = OptBox(v);
                if (i == 1) { break; }
                if (i == 2) {
                    i = i + 1;
                    continue;
                }
                i = i + 1;
            }
        }

        func with_cleanup() -> void {
            with (let v: string? = concat_s("wi", "th") as string?) {
                log(1);
            } cleanup {
                log(2);
            }
        }

        func main() -> int {
            fallthrough();
            with_cleanup();
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    fallthrough_func = c_code.find("l0_main_fallthrough")
    assert fallthrough_func != -1

    wrapped_retain = c_code.find("rt_string_retain(", fallthrough_func)
    assert wrapped_retain != -1

    assert "if ((v).has_value) {" in c_code
    assert "rt_string_release((v).value);" in c_code
    assert "if (((box).value).has_value) {" in c_code
    assert "rt_string_release(((box).value).value);" in c_code

    box2_init = c_code.find("struct l0_main_OptBox box2", fallthrough_func)
    box2_retain = c_code.rfind("rt_string_retain((l0_copy_", fallthrough_func, box2_init)
    assert box2_init != -1 and box2_retain != -1

    enum_init = c_code.find("struct l0_main_OptEnum en", fallthrough_func)
    enum_retain = c_code.rfind("rt_string_retain((l0_copy_", fallthrough_func, enum_init)
    assert enum_init != -1 and enum_retain != -1

    early_return_guard = c_code.find("if ((v).has_value) {", c_code.find("l0_main_early_return"))
    early_return_release = c_code.find("rt_string_release((v).value);", c_code.find("l0_main_early_return"))
    assert early_return_guard != -1 and early_return_release != -1
    assert early_return_guard < early_return_release

    with_cleanup_func = c_code.find("l0_main_with_cleanup")
    assert with_cleanup_func != -1

    cleanup_log = c_code.find("log(2);", with_cleanup_func)
    release_call = c_code.find("rt_string_release((v).value);", cleanup_log)
    assert cleanup_log != -1 and release_call != -1
    assert cleanup_log < release_call


def test_codegen_enum_cleanup_emits_switch_for_value_and_pointer_paths(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        enum E {
            A(value: string);
            B;
        }

        func cleanup_value() -> void {
            let e: E = A("x");
        }

        func cleanup_pointer() -> void {
            let p: E* = new E::A("y");
            drop p;
        }

        func main() -> int {
            cleanup_value();
            cleanup_pointer();
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "switch ((e).tag)" in c_code
    assert "rt_string_release((e).data.A.value);" in c_code
    assert "if (p != NULL) {" in c_code
    assert "switch (p->tag)" in c_code
    assert "rt_string_release(p->data.A.value);" in c_code


def test_codegen_nested_struct_and_enum_cleanup_recurses_from_single_path(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        struct Inner {
            value: string;
        }

        enum E {
            Has(inner: Inner);
            Empty;
        }

        struct Outer {
            e: E;
        }

        func main() -> int {
            let o: Outer = Outer(Has(Inner("z")));
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "switch (((o).e).tag)" in c_code
    assert "rt_string_release((((o).e).data.Has.inner).value);" in c_code


def test_codegen_enum_cleanup_emits_all_variant_field_cleanups(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        enum E {
            Pair(left: string, right: string);
            Empty;
        }

        func main() -> int {
            let e: E = Pair("l", "r");
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "rt_string_release((e).data.Pair.left);" in c_code
    assert "rt_string_release((e).data.Pair.right);" in c_code


def test_codegen_enum_copy_from_place_retain_uses_data_field(codegen_single):
    c_code, _ = codegen_single(
        "main",
        '''
        module main;

        enum E {
            One(value: string);
            Two;
        }

        func main() -> int {
            let a: E = One("hello");
            let b: E = a;
            return 0;
        }
        ''',
    )

    if c_code is None:
        return

    assert ".data.One.value" in c_code
    assert ".payload.One.value" not in c_code


def test_codegen_enum_copy_from_place_with_owned_payload_compiles(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        '''
        module main;

        enum E {
            One(value: string);
            Two;
        }

        func main() -> int {
            let a: E = One("hello");
            let b: E = a;
            match (b) {
                One(value) => { return 0; }
                Two => { return 1; }
            }
        }
        ''',
    )

    if c_code is None:
        return

    ok, _stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr


def test_codegen_return_from_field_place_expr_retains(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        struct Box { s: string; }

        func get_s(b: Box*) -> string {
            return b.s;
        }

        func main() -> int {
            let b: Box* = new Box(concat_s("ab", "cd"));
            {
                let x: string = get_s(b);
            }
            printl_s(b.s);
            drop b;
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    get_s_start = c_code.rfind("l0_string l0_main_get_s(")
    main_start = c_code.find("l0_int l0_main_main(", get_s_start)
    assert get_s_start != -1 and main_start != -1
    assert "rt_string_retain(" in c_code[get_s_start:main_start]

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "abcd"


def test_codegen_line_directives_and_mangling(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        let static: int = 1;

        func f(inline: int) -> int {
            let l0_val: int = inline;
            let _tmp: int = l0_val;
            return _tmp;
        }

        func main() -> int { return f(1); }
        """,
    )

    if c_code is None:
        return

    assert "#line" in c_code
    assert ".l0\"" in c_code
    assert "l0_main_l0_kw_static" in c_code
    assert "inline__v" in c_code
    assert "l0_val__v" in c_code
    assert "_tmp__v" in c_code


# ---------------------------------------------------------------------------
# Runtime-backed tests
# ---------------------------------------------------------------------------


def test_codegen_runtime_match_output(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        extern func rt_print_int(x: int) -> void;
        extern func rt_println() -> void;

        enum Option { None; Some(value: int); }

        func main() -> int {
            let opt: Option = Some(42);
            match (opt) {
                None => { rt_print_int(0); rt_println(); }
                Some(v) => { rt_print_int(v); rt_println(); }
            }
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "42"


def test_codegen_runtime_short_circuiting(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        extern func rt_print_int(x: int) -> void;

        func side() -> bool {
            rt_print_int(1);
            return true;
        }

        func main() -> int {
            let x: bool = false && side();
            if (x) { rt_print_int(2); }
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == ""


def test_codegen_runtime_integer_overflow_panics(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func main() -> int {
            let x: int = 2147483647;
            let y: int = x + 1;
            return y;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert not ok
    assert "integer addition overflow" in stderr


# ---------------------------------------------------------------------------
# ARC leak-fix tests
# ---------------------------------------------------------------------------


def test_codegen_discarded_arc_call_released(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.string;

        func main() -> int {
            concat_s("a", "b");
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    main_start = c_code.find("l0_int l0_main_main(")
    assert main_start != -1
    main_body = c_code[main_start:]
    # The discarded concat_s result should be materialized and released
    assert "_arc_" in main_body
    assert "rt_string_release(" in main_body


def test_codegen_try_stmt_with_arc_payload_compiles(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func may_s(ok: bool) -> string? {
            if (ok) {
                return "ok" as string?;
            }
            return null;
        }

        func helper(ok: bool) -> int? {
            may_s(ok)?;
            return 7 as int?;
        }

        func main() -> int {
            let a: int? = helper(true);
            let b: int? = helper(false);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    helper_start = c_code.find("l0_opt_int l0_main_helper(")
    assert helper_start != -1
    helper_body = c_code[helper_start:]
    assert "= (void)((l0_try_" not in helper_body

    ok, _stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr


def test_codegen_nested_arc_call_temps_released(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        func main() -> int {
            let x: string = concat_s("hello", concat_s(", ", "world"));
            printl_s(x);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    main_start = c_code.find("l0_int l0_main_main(")
    assert main_start != -1
    main_body = c_code[main_start:]
    # Inner concat_s temp should be materialized
    assert "_arc_" in main_body

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "hello, world"


def test_codegen_return_borrowed_param_retains(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;

        func id_s(s: string) -> string {
            return s;
        }

        func main() -> int {
            let x: string = id_s("hello");
            printl_s(x);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    id_s_start = c_code.rfind("l0_string l0_main_id_s(")
    main_start = c_code.find("l0_int l0_main_main(", id_s_start)
    assert id_s_start != -1 and main_start != -1
    id_s_body = c_code[id_s_start:main_start]
    assert "rt_string_retain(" in id_s_body

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "hello"


def test_codegen_return_borrowed_param_with_cleanup(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        func id_with_local(s: string) -> string {
            let tmp: string = concat_s("x", "y");
            return s;
        }

        func main() -> int {
            let x: string = id_with_local("hello");
            printl_s(x);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    fn_start = c_code.rfind("l0_string l0_main_id_with_local(")
    main_start = c_code.find("l0_int l0_main_main(", fn_start)
    assert fn_start != -1 and main_start != -1
    fn_body = c_code[fn_start:main_start]
    # Should have retain (borrowed param return) and release (local tmp cleanup)
    assert "rt_string_retain(" in fn_body
    assert "rt_string_release(" in fn_body

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "hello"


def test_codegen_return_borrowed_param_no_move(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func id_s(s: string) -> string {
            return s;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    fn_start = c_code.rfind("l0_string l0_main_id_s(")
    main_start = c_code.find("l0_int l0_main_main(", fn_start)
    assert fn_start != -1 and main_start != -1
    fn_body = c_code[fn_start:main_start]
    # Should retain (not move) because param is borrowed, not owned
    assert "rt_string_retain(" in fn_body


def test_codegen_param_reassign_no_double_free(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        func f(s: string) -> void {
            s = concat_s("new", "val");
            printl_s(s);
        }

        func main() -> int {
            f("old");
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    fn_start = c_code.rfind("void l0_main_f(")
    main_start = c_code.find("l0_int l0_main_main(", fn_start)
    assert fn_start != -1 and main_start != -1
    fn_body = c_code[fn_start:main_start]
    # First reassignment of borrowed param should NOT release old value
    # but the new value should be released at scope exit
    assert "rt_string_release(" in fn_body

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "newval"


def test_codegen_param_reassign_in_nested_scope(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        func f(s: string) -> void {
            if (true) {
                s = concat_s("inner", "val");
            }
            printl_s(s);
        }

        func main() -> int {
            f("old");
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "innerval"


def test_codegen_param_reassign_twice(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        import std.io;
        import std.string;

        func f(s: string) -> void {
            s = concat_s("first", "");
            s = concat_s("second", "");
            printl_s(s);
        }

        func main() -> int {
            f("old");
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "second"
