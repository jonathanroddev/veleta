@echo off
rem Start the veleta core, listening for sensors over WiFi.
rem
rem The runtime beside this file is a private copy of Python: nothing is
rem installed on the machine and nothing on PATH is used or changed.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  pause
)
endlocal
