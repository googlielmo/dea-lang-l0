# The Dea Programming Language.

> _C-family syntax, UB-free semantics, ARC strings, sum types and pattern matching._

Welcome to the **Dea** programming language!

## Dea/L<sub>0</sub> on Windows

The validated Windows workflow for Dea/L0 `1.0.0` requires a supported backend C toolchain:

- **MSYS2** `MINGW64`: install MSYS2 from https://www.msys2.org/.
- **MinGW-w64 GCC** (or **Clang**): install `mingw-w64-x86_64-gcc` or `mingw-w64-x86_64-clang` from the MSYS2 package
  manager.
- **GNU Make**: install the `make` package from the MSYS2 package manager.
- **System PATH**: `l0-env.cmd` auto-detects the MSYS2 install and puts `mingw64/bin/` on `PATH`. Set `MSYS2_ROOT` if
  MSYS2 is not in the default location.

Install the toolchain packages with:

```bash
pacman -S mingw-w64-x86_64-gcc make
# or use Clang instead: pacman -S mingw-w64-x86_64-clang make
```

Native `cmd.exe` launchers are supported. MSYS2 `MINGW64` is required as the Dea compiler's `--build` and `--run`
workflows depend on a supported Windows C toolchain.

## Using the shipped archive

After extracting the archive, the Windows launchers live under `bin/`.

### From `cmd.exe`

```cmd
call bin\l0-env.cmd
l0c --version
```

`l0-env.cmd` automatically puts MSYS2 `mingw64\bin` on `PATH` so that the C compiler (GCC or Clang) and its support DLLs
are visible. It probes `%MSYS2_ROOT%`, the Windows registry, and the default `C:\msys64` path. Set `MSYS2_ROOT` if MSYS2
is installed in a non-default location. These native launchers work without opening the MSYS2 shell first.

## Trying the bundled examples

```cmd
call bin\l0-env.cmd
l0c -P examples --run hello
```

The shipped examples live under `examples/`, and the bundled reference docs live under `docs/reference/`.
