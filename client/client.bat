@echo off
echo [CLIENT GUI BUILD] Сборка клиента с PySide6 GUI...
cd /d %~dp0
pyinstaller --noconfirm --onefile --windowed client_main.py
echo Готово! dist\client_main.exe
pause
