@echo off
rem Start the veleta core listening to a wired (USB cable) sensor.
rem
rem This is the one to run with the USB bench kit. veleta-core.bat listens
rem for WiFi sensors over UDP instead, and with a wired sensor it would sit
rem there forever receiving nothing.
rem
rem Before the first run: edit config.wired.env and set SERIAL_PORT to your
rem sensor's COM port. Run list-ports.bat first if you do not know it.
rem
rem The runtime beside this file is a private copy of Python: nothing is
rem installed on the machine and nothing on PATH is used or changed.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core --config config.wired.env %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  echo.
  echo   - "could not open port..."   wrong SERIAL_PORT in config.wired.env,
  echo     the cable is unplugged, or another program (including a second
  echo     copy of this core) already has the port open. Run list-ports.bat
  echo     to see the COM number Windows actually assigned.
  echo   - every frame UNPARSED       SERIAL_PORT points at the wrong
  echo     device, or the sketch on it is not the wired one.
  pause
)
endlocal
