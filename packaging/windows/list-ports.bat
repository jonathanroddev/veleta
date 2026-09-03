@echo off
rem List the serial ports Windows can see.
rem
rem Packed into the bundle as diagnostico\ver-puertos.bat - one level
rem down, which is why the runtime below is reached through ..
rem
rem Mostly a diagnostic now: with one sensor plugged in the core finds the
rem port on its own. This is for the case it cannot - several devices
rem connected at once, so it will not guess - and for finding which COM a
rem paired classic Bluetooth module was given. Pairing often creates TWO
rem ports, one outgoing and one incoming; the outgoing one is the one that
rem works, and neither number is predictable.
setlocal
cd /d "%~dp0"
"%~dp0..\runtime\python.exe" -m serial.tools.list_ports -v
echo.
pause
endlocal
