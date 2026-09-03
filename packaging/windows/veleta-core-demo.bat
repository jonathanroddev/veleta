@echo off
rem Replay the bundled recording instead of listening to hardware.
rem
rem Packed into the bundle as diagnostico\veleta-demo.bat - one level
rem down, which is why the runtime below is reached through ..
rem
rem This drives Blender exactly as a live sensor would: the recording holds
rem the sensor stream, so parsing, fusion and calibration all run for real.
rem Use it to check the whole chain on a machine with no sensor on it.
rem
rem ajustes-demo.txt is the recording's field layout, not your sensor's. It
rem is passed explicitly because this package may not carry any other
rem configuration the demo could fall back to.
setlocal
cd /d "%~dp0"
"%~dp0..\runtime\python.exe" -m veleta_core --config ajustes-demo.txt --play "samples\wt901_desk_wobble.jsonl" --loop %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo The core stopped with code %EXITCODE%.
  pause
)
endlocal
