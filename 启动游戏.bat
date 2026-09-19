@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHON_EXE="

rem 1) Prefer the Doubao runtime Python (pygame already installed).
for /r "%LOCALAPPDATA%\Doubao\User Data\sandbox_runtime\bases" %%i in (python.exe) do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
)
rem 2) Fallback: python on PATH.
if not defined PYTHON_EXE (
    where python >nul 2>nul && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)
echo Using Python: %PYTHON_EXE%

rem 3) Auto-install pygame if missing.
"%PYTHON_EXE%" -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo [INFO] pygame not found, installing dependencies...
    "%PYTHON_EXE%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] Failed to install pygame. Check your network and retry.
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Game exited abnormally. Send me the error message above.
    pause
)
