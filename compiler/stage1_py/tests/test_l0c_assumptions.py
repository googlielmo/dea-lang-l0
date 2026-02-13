#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import argparse
import textwrap

from l0c import cmd_build, cmd_check, cmd_run


def _write_module(root, module_name: str, source: str):
    path = root.joinpath(*module_name.split(".")).with_suffix(".l0")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def _build_args(tmp_path, entry: str, **overrides):
    base = dict(
        entry=entry,
        output=str(tmp_path / "a.out"),
        c_compiler="cc",
        c_options=None,
        runtime_include=None,
        runtime_lib=None,
        keep_c=False,
        verbosity=0,
        project_root=[str(tmp_path)],
        sys_root=[],
        no_line_directives=False,
        log=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


class _RunResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_build_fails_when_entry_main_missing(tmp_path, monkeypatch, capsys):
    _write_module(
        tmp_path,
        "app.main",
        """
        module app.main;
        func helper() -> int { return 0; }
        """,
    )
    monkeypatch.setattr("l0c.subprocess.run", lambda *args, **kwargs: _RunResult(returncode=0))

    rc = cmd_build(_build_args(tmp_path, "app.main"))

    assert rc == 1
    assert "[L0C-0012]" in capsys.readouterr().err


def test_build_warns_when_entry_main_return_type_is_not_preferred(tmp_path, monkeypatch, capsys):
    _write_module(
        tmp_path,
        "app.main",
        """
        module app.main;
        func main() -> string { return "ok"; }
        """,
    )
    monkeypatch.setattr("l0c.subprocess.run", lambda *args, **kwargs: _RunResult(returncode=0))

    rc = cmd_build(_build_args(tmp_path, "app.main"))

    assert rc == 0
    assert "[L0C-0013]" in capsys.readouterr().err


def test_check_rejects_invalid_entry_module_name(tmp_path, capsys):
    args = argparse.Namespace(
        entry="bad-name",
        verbosity=0,
        project_root=[str(tmp_path)],
        sys_root=[],
        no_line_directives=False,
        log=False,
    )

    rc = cmd_check(args)

    assert rc == 1
    assert "[L0C-0011]" in capsys.readouterr().err


def test_build_fails_when_configured_runtime_lib_is_missing(tmp_path, monkeypatch, capsys):
    _write_module(
        tmp_path,
        "main",
        """
        module main;
        func main() -> int { return 0; }
        """,
    )
    runtime_dir = tmp_path / "runtime_lib"
    runtime_dir.mkdir()
    monkeypatch.setattr("l0c.subprocess.run", lambda *args, **kwargs: _RunResult(returncode=0))

    rc = cmd_build(_build_args(tmp_path, "main", runtime_lib=str(runtime_dir)))

    assert rc == 1
    assert "[L0C-0015]" in capsys.readouterr().err


def test_run_forwards_c_options_to_build(tmp_path, monkeypatch):
    captured = {}

    def _fake_cmd_build(args):
        captured["c_options"] = args.c_options
        return 1

    monkeypatch.setattr("l0c.cmd_build", _fake_cmd_build)

    args = argparse.Namespace(
        entry="app.main",
        args=[],
        c_compiler="cc",
        c_options="-O2 -DDEBUG",
        runtime_include=None,
        runtime_lib=None,
        verbosity=0,
        project_root=[str(tmp_path)],
        sys_root=[],
        no_line_directives=False,
        log=False,
    )

    rc = cmd_run(args)

    assert rc == 1
    assert captured["c_options"] == "-O2 -DDEBUG"
