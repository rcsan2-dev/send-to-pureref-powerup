@echo off
title Send to PureRef Bridge R01
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py pure_ref_bridge.py & goto :eof)
where python >nul 2>nul
if %errorlevel%==0 (python pure_ref_bridge.py & goto :eof)
echo Python 3 was not found.
pause
