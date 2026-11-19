@echo off
title AI Answer Reliability Tracker — Advanced Edition
echo ========================================================
echo  AI Answer Reliability Tracker (Advanced Edition)
echo  Minimal Cream & Orange Theme | Figtree Typography
echo ========================================================
echo.

set PYTHON_CMD=

:: Check py launcher
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py -3.10
)

:: Check direct python
if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=python
    )
)

:: Check local appdata python 3.10
if "%PYTHON_CMD%"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.10 was not found on your system.
    echo Please install Python 3.10 or add it to PATH.
    pause
    exit /b 1
)

echo Starting web server on http://127.0.0.1:8000 ...
echo Default credentials: admin / admin123
echo.

:: Open default browser after a 1.5 second delay in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

:: Start the Python server
%PYTHON_CMD% app.py

pause
