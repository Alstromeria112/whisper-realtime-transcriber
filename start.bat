@echo off

chcp 65001 >nul

if not exist .venv (
    echo Creating a virtual environment and installing dependencies...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
    echo Successfully created a virtual environment and installed dependencies.
    echo.
)

echo Booting software...
echo.

echo Activating enviroment...
call .venv\Scripts\activate.bat

echo.
echo Starting WebSocket server...
echo WebSocket: ws://localhost:8766
echo Web Client: http://localhost:8080
echo.
echo 停止するには Ctrl+C を押してネ
echo.

python main.py
