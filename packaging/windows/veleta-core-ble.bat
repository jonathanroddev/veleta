@echo off
rem Start the veleta core listening to the BLE sensor (the battery kit).
rem
rem This is the one to run with an HM-10 based sensor. veleta-core.bat
rem listens for WiFi sensors over UDP instead, and with a BLE module it
rem would sit there forever receiving nothing.
rem
rem The runtime beside this file is a private copy of Python: nothing is
rem installed on the machine and nothing on PATH is used or changed.
rem
rem Windows will ask for Bluetooth permission the first time. If it reports
rem that Bluetooth is off while the adapter is clearly on, that is the
rem permission being denied, not the adapter.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core --config config.ble.env %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  echo.
  echo   - "no BLE peripheral advertising..."  the module is off, out of
  echo     range, or something else is already connected to it.
  echo   - every frame UNPARSED                wrong config file.
  echo   - around 21 Hz instead of 40          module still at 9600 baud,
  echo     send AT+BAUD2 with firmware/ble/hm10_config.
  pause
)
endlocal
