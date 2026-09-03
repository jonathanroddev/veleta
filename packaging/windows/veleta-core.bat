@echo off
rem Start the veleta core, listening for sensors over WiFi.
rem
rem Packed into the bundle as veleta-sensor-wifi.bat.
rem
rem ajustes-wifi.txt is named explicitly rather than left to the search
rem order. The search order looks for a file called config.env, and the
rem package does not ship one under that name: relying on it would have
rem quietly dropped this launcher onto the built-in defaults.
rem
rem The runtime beside this file is a private copy of Python: nothing is
rem installed on the machine and nothing on PATH is used or changed.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core --config ajustes-wifi.txt %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  pause
)
endlocal
