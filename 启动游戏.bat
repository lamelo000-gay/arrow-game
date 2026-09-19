@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem 1) Preferred: the verified Doubao runtime Python (pygame already installed).
set "PYTHON_EXE=%LOCALAPPDATA%\Doubao\User Data\sandbox_runtime\bases\c98c5042338ed152c6f10ecd8591889f\python\python.exe"

rem 2) Fallback: search only one level of bases\<hash>\python\python.exe
if not exist "%PYTHON_EXE%" (
    for /d %%b in ("%LOCALAPPDATA%\Doubao\User Data\sandbox_runtime\bases\*") do (
        if exist "%%b\python\python.exe" set "PYTHON_EXE=%%b\python\python.exe"
    )
)
if not exist "%PYTHON_EXE%" (
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
        echo [ERROR] Failed to install pygame. Check network and retry.
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
