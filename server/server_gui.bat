@echo off
echo [SERVER GUI BUILD] Сборка GUI-оболочки сервера...
cd /d %~dp0
pyinstaller --noconfirm --onefile --windowed run_server_gui.py
echo Готово! dist\run_server_gui.exe
pause
