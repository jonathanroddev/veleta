@echo off
rem List the serial ports Windows can see, so you can find which COM the
rem Bluetooth module was given. Pairing a classic Bluetooth module creates a
rem virtual COM port; its number is assigned by Windows and is not
rem predictable, so look here rather than guessing.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m serial.tools.list_ports -v
echo.
pause
endlocal
