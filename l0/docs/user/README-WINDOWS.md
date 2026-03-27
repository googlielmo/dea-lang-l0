# Dea/L<sub>0</sub> on Windows

This document explains how to use the shipped Dea/L0 binary distribution on Windows.

## Supported Windows path

The validated Windows path for `1.0.0` is:

- MSYS2 `MINGW64`
- MinGW-w64 GCC
- GNU Make on `PATH`

MSVC-family builds remain outside the validated release matrix.

## Using the shipped archive

After extracting the archive, the Windows launchers live under `bin/`.

### From `cmd.exe`

```cmd
call bin\l0-env.cmd
l0c --version
```

### From PowerShell

```powershell
cmd /d /c "call bin\l0-env.cmd && l0c --version"
# or invoke the selected launcher directly:
& ".\bin\l0c.cmd" --version
```

## Trying the bundled examples

```cmd
call bin\l0-env.cmd
l0c -P examples --run hello
```

The shipped examples live under `examples/`, and the bundled reference docs live under `docs/reference/`.
