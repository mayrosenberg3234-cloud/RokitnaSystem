@echo off
REM ===========================================================
REM  Rokitna Project Management System - Windows launcher
REM  Double-click this file to start the application.
REM ===========================================================
chcp 65001 >nul
cd /d "%~dp0"
title Rokitna Project Management

echo ============================================
echo    Rokitna Project Management System
echo ============================================
echo.

REM --- Locate Python (try "python", then the "py" launcher) ---
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON ( where py >nul 2>&1 && set "PYTHON=py" )

if not defined PYTHON (
  echo [ERROR] Python was not found on this computer.
  echo Please install Python 3.12 from: https://www.python.org/downloads/
  echo During installation, check the box "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo Using Python: %PYTHON%
echo.

REM --- Install Streamlit only on the first run ---
%PYTHON% -c "import streamlit" >nul 2>&1
if errorlevel 1 (
  echo Installing required packages ^(first run only, please wait^)...
  %PYTHON% -m pip install -r requirements.txt
  echo.
)

echo Starting the application... your browser will open automatically.
echo To stop the application: close this window.
echo.
%PYTHON% -m streamlit run app.py

echo.
echo The application has stopped.
pause
