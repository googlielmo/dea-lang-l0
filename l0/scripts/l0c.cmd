@REM SPDX-License-Identifier: MIT OR Apache-2.0
@REM Copyright (c) 2026 gwz
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..") do set "MONOREPO_ROOT=%%~fI"
set "PYTHON_BIN=%PYTHON%"

if not defined PYTHON_BIN if exist "%MONOREPO_ROOT%\.venv\Scripts\python.exe" set "PYTHON_BIN=%MONOREPO_ROOT%\.venv\Scripts\python.exe"
if not defined PYTHON_BIN if exist "%MONOREPO_ROOT%\.venv\bin\python" set "PYTHON_BIN=%MONOREPO_ROOT%\.venv\bin\python"
if not defined PYTHON_BIN set "PYTHON_BIN=python"

if not defined L0_HOME set "L0_HOME=%REPO_ROOT%\compiler"

"%PYTHON_BIN%" "%L0_HOME%\stage1_py\l0c.py" %*
set "EXITCODE=%ERRORLEVEL%"
endlocal & exit /b %EXITCODE%
