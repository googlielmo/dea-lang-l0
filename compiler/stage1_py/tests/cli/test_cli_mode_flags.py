#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest

import l0c


def _patch_handlers(monkeypatch):
    calls = []

    def _mk_handler(name):
        def _handler(args):
            calls.append((name, args))
            return 0

        return _handler

    monkeypatch.setattr(l0c, "cmd_run", _mk_handler("run"))
    monkeypatch.setattr(l0c, "cmd_build", _mk_handler("build"))
    monkeypatch.setattr(l0c, "cmd_codegen", _mk_handler("gen"))
    monkeypatch.setattr(l0c, "cmd_check", _mk_handler("check"))
    monkeypatch.setattr(l0c, "cmd_tok", _mk_handler("tok"))
    monkeypatch.setattr(l0c, "cmd_ast", _mk_handler("ast"))
    monkeypatch.setattr(l0c, "cmd_sym", _mk_handler("sym"))
    monkeypatch.setattr(l0c, "cmd_type", _mk_handler("type"))
    return calls


def _run_main(argv):
    with pytest.raises(SystemExit) as exc:
        l0c.main(argv)
    return exc.value.code


def test_default_mode_is_build(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["app.main"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "build"
    assert args.entry == "app.main"


def test_explicit_run_uses_double_dash_for_program_args(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--run", "app.main", "--", "alpha", "--beta"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "run"
    assert args.entry == "app.main"
    assert args.args == ["alpha", "--beta"]


def test_short_run_alias_uses_double_dash_for_program_args(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["-r", "app.main", "--", "alpha", "--beta"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "run"
    assert args.entry == "app.main"
    assert args.args == ["alpha", "--beta"]


def test_explicit_run_rejects_implicit_program_args(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--run", "app.main", "alpha"])

    assert rc == 2
    assert calls == []
    assert "use '--' before runtime program arguments" in capsys.readouterr().err


def test_legacy_run_command_preserves_old_program_arg_style(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["run", "app.main", "alpha", "--beta"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "run"
    assert args.entry == "app.main"
    assert args.args == ["alpha", "--beta"]


def test_legacy_codegen_alias_maps_to_gen_mode(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["codegen", "app.main"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "gen"
    assert args.entry == "app.main"


def test_short_gen_alias_maps_to_gen_mode(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["-g", "app.main"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "gen"
    assert args.entry == "app.main"


def test_multiple_targets_rejected_for_non_run_modes(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--check", "a", "b"])

    assert rc == 2
    assert calls == []
    assert "multiple targets are not supported yet" in capsys.readouterr().err


def test_program_args_separator_only_allowed_for_run(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--check", "app.main", "--", "x"])

    assert rc == 2
    assert calls == []
    assert "arguments after '--' are valid only with '--run'" in capsys.readouterr().err


def test_include_eof_is_valid_in_tok(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--tok", "--include-eof", "app.main"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "tok"
    assert args.include_eof is True


def test_runtime_include_is_rejected_outside_build_run(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--tok", "-I", "/tmp/runtime", "app.main"])

    assert rc == 2
    assert calls == []
    assert "option '--runtime-include' is valid only with modes: --build, --run" in capsys.readouterr().err


def test_keep_c_is_rejected_outside_build_run(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--check", "--keep-c", "app.main"])

    assert rc == 2
    assert calls == []
    assert "option '--keep-c' is valid only with modes: --build, --run" in capsys.readouterr().err


def test_include_eof_is_rejected_outside_tok(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--run", "--include-eof", "app.main"])

    assert rc == 2
    assert calls == []
    assert "option '--include-eof' is valid only with modes: --tok" in capsys.readouterr().err


def test_all_modules_is_rejected_outside_dump_modes(monkeypatch, capsys):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--gen", "--all-modules", "app.main"])

    assert rc == 2
    assert calls == []
    assert "option '--all-modules' is valid only with modes: --ast, --sym, --tok, --type" in capsys.readouterr().err


def test_output_is_allowed_in_run_mode(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--run", "--output", "x", "app.main"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "run"
    assert args.entry == "app.main"
    assert args.output == "x"


def test_explicit_mode_flags_disable_legacy_rewrite(monkeypatch):
    calls = _patch_handlers(monkeypatch)

    rc = _run_main(["--build", "run"])

    assert rc == 0
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "build"
    assert args.entry == "run"
