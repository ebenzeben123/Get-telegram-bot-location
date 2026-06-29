@echo off
REM Launcher for get_bot_location.py on Windows.
REM Double-click this file or run it from a command prompt.

setlocal

REM Prefer the Python launcher, fall back to python on PATH.
where py >nul 2>nul
if %errorlevel%==0 (
    py get_bot_location.py %*
) else (
    python get_bot_location.py %*
)

echo.
pause
endlocal
