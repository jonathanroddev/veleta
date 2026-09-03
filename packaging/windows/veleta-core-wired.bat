@echo off
rem Start the veleta core listening to a wired (USB cable) sensor.
rem
rem Packed into the bundle as veleta-sensor.bat - see docs/packaging.md for
rem the repository-name to package-name mapping.
rem
rem This is the one to run with the USB bench kit. veleta-sensor-wifi.bat
rem listens for WiFi sensors over UDP instead, and with a wired sensor it
rem would sit there forever receiving nothing.
rem
rem The port is found on its own when exactly one USB-serial device is
rem plugged in. With several, the core lists them and stops rather than
rem guess: set SERIAL_PORT in ajustes-sensor.txt, or pass --serial-port.
rem
rem The runtime beside this file is a private copy of Python: nothing is
rem installed on the machine and nothing on PATH is used or changed.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core --config ajustes-sensor.txt %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  echo.
  echo   - "more than one to choose from"  several serial devices are
  echo     plugged in, so the core will not pick one for you. It listed
  echo     them above: put the right one in ajustes-sensor.txt as
  echo     SERIAL_PORT=COM5, or run this with --serial-port COM5.
  echo   - "none could be found"      nothing is plugged in, or a classic
  echo     Bluetooth module has not been paired yet.
  echo   - "could not open port..."   the cable came out, or another
  echo     program - including a second copy of this core - already has
  echo     the port open.
  echo   - every frame UNPARSED       that port belongs to some other
  echo     device, or the sketch on it is not the wired one.
  pause
)
endlocal
