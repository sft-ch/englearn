@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Englearn

set "PY="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

rem 0) --silent?????????????????
set "SILENT="
if /i "%~1"=="--silent" set "SILENT=1"
set "ARGS=%*"
if defined SILENT set "ARGS=%ARGS:--silent=%"

rem 1) user override
if defined ENGL_PY if exist "%ENGL_PY%" set "PY=%ENGL_PY%"

rem 2) python on PATH
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)

rem 3) py launcher
if not defined PY (
  where py >nul 2>nul
  if not errorlevel 1 set "PY=py"
)

rem 4) common install locations
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

if not defined PY goto nopython

echo   [Englearn] interpreter: %PY%
%PY% app.py %ARGS%
if errorlevel 1 if not defined SILENT pause
exit /b 0

:nopython
echo.
echo   [Englearn] Python 3 not found.
echo   Install Python 3.10+ or set ENGL_PY to the full path of python.exe
echo.
pause
exit /b 1
