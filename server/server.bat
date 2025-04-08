@echo off
echo [SERVER BUILD] Упаковка сервера с зависимостями...
cd /d %~dp0
echo Создание run_server.py...
echo import uvicorn> run_server.py
echo import sys>> run_server.py
echo import os>> run_server.py
echo sys.path.append(os.path.dirname(__file__))>> run_server.py
echo import server_main>> run_server.py
echo if __name__ == "__main__":>> run_server.py
echo     uvicorn.run(server_main.app, host="0.0.0.0", port=8000)>> run_server.py
pyinstaller --noconfirm --onefile --add-data "%cd%\server_main.py;." run_server.py
del run_server.py
echo [SERVER BUILD] Готово! Файл: dist\run_server.exe
pause
