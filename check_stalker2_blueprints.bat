@echo off
chcp 65001 >nul
title STALKER 2 Blueprint Checker

where py >nul 2>nul
if not errorlevel 1 goto run_with_py

where python >nul 2>nul
if not errorlevel 1 goto run_with_python

echo Python не найден. Установите Python 3.10+ с https://www.python.org/downloads/
goto finish

:run_with_py
py -3 "%~dp0stalker2_blueprint_checker.py" --download-oodle
goto finish

:run_with_python
python "%~dp0stalker2_blueprint_checker.py" --download-oodle

:finish
echo.
pause
