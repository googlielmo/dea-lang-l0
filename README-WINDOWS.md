# Dea/L0 on Windows

This document is the Windows-specific addendum to [README.md](README.md).

- If you want to build, install, and use `l0c` on Windows, read the next section.
- If you are developing Dea/L0 itself, read the developer section after that.
- The rest is a technical addendum about generated launchers, shell behavior, and current Windows-specific caveats.

## How to build and use `l0c`

The recommended Windows path today is:

- MSYS2 `MINGW64`
- MinGW-w64 GCC
- GNU Make on `PATH`

This is the validated Dea/L0 `1.0.0` Windows path. MSVC-family builds remain outside the validated release matrix.

To build and install the Stage 2 compiler from the repo:

```bash
make venv
make PREFIX=/c/l0-install install
```

Then use it like this:

### From MSYS2 bash

```bash
source /c/l0-install/bin/l0-env.sh
l0c --version
```

### From `cmd.exe`

```cmd
call C:\l0-install\bin\l0-env.cmd
l0c --version
```

### From PowerShell

```powershell
cmd /d /c "call C:\l0-install\bin\l0-env.cmd && l0c --version"
# or invoke the selected launcher directly:
& "C:\l0-install\bin\l0c.cmd" --version
```

Notes:

- The installed Windows entry point is `l0c.cmd`; native Windows shells resolve bare `l0c` to that launcher.
- `l0-env.cmd` is generated for native `cmd.exe` activation.
- `l0-env.sh` remains the MSYS2/bash activation helper.

## If you are developing Dea/L0 itself

For day-to-day development, MSYS2 bash is the recommended shell.

### Work on Stage 2

```bash
make use-dev-stage2
source build/dea/bin/l0-env.sh
l0c --version
```

### Work on Stage 1

```bash
make use-dev-stage1
source build/dea/bin/l0-env.sh
l0c --version
```

Native Windows shell summary:

- Repo-local Stage 1 and Stage 2 both work through `build\dea\bin\l0c.cmd` after `make use-dev-stage1` or
  `make use-dev-stage2`.
- Installed Stage 2 works through `<PREFIX>\bin\l0-env.cmd` followed by `l0c`, or through the direct launcher
  `<PREFIX>\bin\l0c.cmd`.

## Technical addendum

You can ignore the next sections unless you are working on Dea/L0 itself or need to understand the Windows launcher
layout in detail.

### Supported workflow

| Scenario                                        | Recommended entry point on Windows                                    |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| Source-tree Stage 1 from MSYS2 bash             | `./scripts/l0c`                                                       |
| Source-tree Stage 1 from `cmd.exe` / PowerShell | `scripts\\l0c.cmd`                                                    |
| Repo-local Stage 1 or Stage 2 from MSYS2 bash   | `source build/dea/bin/l0-env.sh` then `l0c`                           |
| Repo-local Stage 1 or Stage 2 from `cmd.exe`    | `call build\\dea\\bin\\l0-env.cmd` then `l0c`                         |
| Repo-local Stage 1 or Stage 2 from PowerShell   | `build\\dea\\bin\\l0c.cmd` directly, or a one-shot `cmd /d /c` bridge |
| Installed Stage 2 from MSYS2 bash               | `source <PREFIX>/bin/l0-env.sh` then `l0c`                            |
| Installed Stage 2 from `cmd.exe`                | `call <PREFIX>\\bin\\l0-env.cmd` then `l0c`                           |
| Installed Stage 2 from PowerShell               | `<PREFIX>\\bin\\l0c.cmd` directly, or a one-shot `cmd /d /c` bridge   |

## What the Windows targets generate

### `make install-dev-stage1`

This writes a repo-local Stage 1 launcher layout under `DEA_BUILD_DIR/bin/`:

- `l0c-stage1`
- `l0-env.sh`
- `l0c-stage1.cmd`
- `l0-env.cmd`

Important current behavior:

- `l0c-stage1` is a POSIX shell wrapper.
- `l0c-stage1.cmd` is the Windows batch wrapper.
- There is no selected `l0c` alias yet.

This target is directly usable from MSYS2 bash or through `build\\...\\bin\\l0c-stage1.cmd` in native Windows shells.

### `make install-dev-stage2`

This writes a repo-local Stage 2 launcher layout under `DEA_BUILD_DIR/bin/`:

- `l0c-stage2.native`
- `l0c-stage2`
- `l0c-stage2.cmd`
- `l0-env.sh`
- `l0-env.cmd`

Important current behavior:

- `l0c-stage2` is the POSIX shell wrapper.
- `l0c-stage2.cmd` is the Windows batch wrapper.
- There is still no selected `l0c` alias until you run `make use-dev-stage2`.

### `make install-dev-stages`

This runs both `install-dev-stage1` and `install-dev-stage2`.

After this target, you have both stage-specific launchers, but you still do not have a selected `l0c` command until you
run `make use-dev-stage1` or `make use-dev-stage2`.

### `make use-dev-stage1`

This selects Stage 1 as the repo-local `l0c` alias under `DEA_BUILD_DIR/bin/`.

Current Windows behavior:

- `l0c` is created for the POSIX/MSYS2 side.
- `l0c.cmd`

Practical result:

- In MSYS2 bash, `source build/dea/bin/l0-env.sh` then `l0c ...` works.
- In `cmd.exe`, `call build\\dea\\bin\\l0-env.cmd` then `l0c ...` works.
- In PowerShell, `build\\dea\\bin\\l0c.cmd` works directly.

### `make use-dev-stage2`

This selects Stage 2 as the repo-local `l0c` alias under `DEA_BUILD_DIR/bin/`.

Current Windows behavior:

- `l0c`
- `l0c.cmd`

Both are created by copying the selected Stage 2 wrapper pair:

- `l0c` for POSIX/MSYS2 bash use
- `l0c.cmd` for native Windows shell resolution

This is the repo-local developer workflow that works cleanly in both MSYS2 bash and native Windows shells.

### `make install PREFIX=...`

This installs the self-hosted Stage 2 compiler into `PREFIX`.

On Windows the installed `PREFIX/bin/` layout includes:

- `l0c-stage2.native`
- `l0c-stage2`
- `l0c-stage2.cmd`
- `l0c`
- `l0c.cmd`
- `l0-env.sh`
- `l0-env.cmd`

There is no Stage 1 install-prefix workflow. `make install` installs Stage 2 only.

## MSYS2 bash usage

`l0-env.sh` is generated on Windows and is intended to be sourced from MSYS2 bash.

Repo-local Stage 2:

```bash
make use-dev-stage2
source build/dea/bin/l0-env.sh
l0c --version
```

Repo-local Stage 1:

```bash
make use-dev-stage1
source build/dea/bin/l0-env.sh
l0c --version
```

Installed Stage 2 prefix:

```bash
make PREFIX=/c/l0-install install
source /c/l0-install/bin/l0-env.sh
l0c --version
```

What `l0-env.sh` does:

- sets `L0_HOME`
- prepends the corresponding `bin/` directory to `PATH`
- keeps the repo-local or installed layout self-contained

Important caveat:

- The repo-local `l0-env.sh` only auto-sources `.venv/bin/activate`.
- If your Windows virtual environment was created in `.venv/Scripts`, the script may not activate it automatically.
- That does not block `l0c-stage1`, because the Stage 1 wrappers also probe `.venv/Scripts/python.exe` directly.

## `cmd.exe` usage

`l0-env.sh` is not for `cmd.exe`. The supported native activation pattern is:

1. `call` the generated `l0-env.cmd`
2. run `l0c`

Direct `.cmd` launcher invocation also works when you do not want a shell-local activation step.

### Repo-local Stage 2 in `cmd.exe`

After you have already run `make install-dev-stage2` and `make use-dev-stage2` from MSYS2 bash or another shell with GNU
Make available:

```cmd
call build\dea\bin\l0-env.cmd
l0c --version
```

Direct stage-specific invocation also works:

```cmd
build\dea\bin\l0c-stage2.cmd --version
```

### Installed Stage 2 in `cmd.exe`

After the prefix has already been created with `make install`:

```cmd
call C:\l0-install\bin\l0-env.cmd
l0c --version
```

Direct invocation:

```cmd
C:\l0-install\bin\l0c.cmd --version
```

### Stage 1 in `cmd.exe`

After you have already run `make use-dev-stage1`:

```cmd
call build\dea\bin\l0-env.cmd
l0c --version
l0c --check -P examples hello
```

Direct stage-specific invocation also works:

```cmd
build\dea\bin\l0c-stage1.cmd --version
```

## PowerShell usage

There is no generated `l0-env.ps1` today. In PowerShell, either invoke the generated `.cmd` launcher directly or use a
one-shot `cmd.exe /d /c` bridge when you want `l0-env.cmd` semantics.

### Repo-local Stage 2 in PowerShell

After you have already run `make install-dev-stage2` and `make use-dev-stage2` from MSYS2 bash or another shell with GNU
Make available:

```powershell
cmd /d /c "call $PWD\build\dea\bin\l0-env.cmd && l0c --version"
```

Direct invocation:

```powershell
& "$PWD\build\dea\bin\l0c.cmd" --version
```

### Installed Stage 2 in PowerShell

After the prefix has already been created with `make install`:

```powershell
cmd /d /c "call C:\l0-install\bin\l0-env.cmd && l0c --version"
```

Direct invocation:

```powershell
& "C:\l0-install\bin\l0c.cmd" --version
```

### Stage 1 in PowerShell

After `make use-dev-stage1`, use the selected repo-local batch wrapper:

```powershell
& "$PWD\build\dea\bin\l0c.cmd" --version
```

## Why both `l0c-stage2.cmd` and `l0c.cmd` exist

They are not redundant by role.

- `l0c-stage2.cmd` is the stage-specific launcher.
- `l0c.cmd` is the selected/public alias.

When Stage 2 is selected, both may dispatch to the same native binary, but they represent different contracts:

- `l0c-stage2.cmd` stays stable as "the Stage 2 entry point"
- `l0c.cmd` is "whatever stage is currently selected as `l0c`"

This matches the Unix layout conceptually:

- `l0c-stage2`
- `l0c`

The Windows-specific difference is implementation, not intent:

- Unix uses the stage-specific wrapper plus a symlinked alias.
- Windows uses the stage-specific `.cmd` wrapper plus a copied `.cmd` alias, because the tool generator does not rely on
  Windows symlink behavior for the selected command.

## Native-shell command resolution

In `cmd.exe` and PowerShell, bare `l0c` works by resolving `l0c.cmd` via the normal Windows executable-extension lookup
rules (`PATHEXT`).

That is why there is no `l0c.exe` wrapper in the generated layout:

- `l0c` resolves to `l0c.cmd`
- `l0c.cmd` dispatches to the real launcher target

## Current limitations

- There is no generated `l0-env.ps1`; PowerShell relies on direct `.cmd` launchers or a `cmd.exe` bridge.
- `l0-env.sh` remains the MSYS2/bash activation story.
- The source-tree fallback `scripts\\l0c.cmd` still exists for direct Stage 1 use outside the repo-local selected-alias
  workflow.
