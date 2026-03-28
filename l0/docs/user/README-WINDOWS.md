# The Dea Programming Language.

> _C-family syntax, UB-free semantics, ARC strings, sum types and pattern matching._

Welcome to the **Dea** programming language!

## Dea/L<sub>0</sub> on Windows

The validated Windows workflow for Dea/L0 `1.0.0` requires a supported backend C toolchain:

- **MSYS2** `MINGW64`: install MSYS2 from https://www.msys2.org/.
- **MinGW-w64 GCC** (or **Clang**): install `mingw-w64-x86_64-gcc` or `mingw-w64-x86_64-clang` from the MSYS2 package
  manager.
- **GNU Make**: install the `make` package from the MSYS2 package manager.
- **System PATH**: ensure the MSYS2 `mingw64/bin/` and `usr/bin/` directories are on your `PATH`.

Install the toolchain packages with:

```bash
pacman -S mingw-w64-x86_64-gcc make
# or use Clang instead: pacman -S mingw-w64-x86_64-clang make
```

Native `cmd.exe` and PowerShell launchers are supported. MSYS2 `MINGW64` is required as the Dea compiler's `--build` and
`--run` workflows depend on a supported Windows C toolchain.

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

These native launchers work without opening the MSYS2 shell first.

## Trying the bundled examples

```cmd
call bin\l0-env.cmd
l0c -P examples --run hello
```

The shipped examples live under `examples/`, and the bundled reference docs live under `docs/reference/`.
