@echo off
rem Replay the bundled recording instead of listening to hardware.
rem
rem This drives Blender exactly as a live sensor would: the recording holds
rem the sensor stream, so parsing, fusion and calibration all run for real.
rem Use it to check the whole chain on a machine with no sensor on it.
rem
rem config.demo.env is the recording's field layout. It is passed explicitly
rem because this package may not carry any other configuration the demo
rem could fall back to.
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m veleta_core --config config.demo.env --play "samples\wt901_desk_wobble.jsonl" --loop %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  pause
)
endlocal
