import sys
import os
import subprocess
import threading
import json
import uuid
import asyncio
import requests
import websockets
import traceback
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QFileDialog,
    QLineEdit, QTabWidget, QHBoxLayout
)
from PySide6.QtCore import Qt

CONFIG_PATH = os.path.expanduser("~/.render_client_config.json")

class RenderClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Render Client")
        self.resize(800, 600)
        self.client_id = str(uuid.uuid4())
        self.assigned_jobs = {}
        self.progress_map = {}

        self.tabs = QTabWidget()
        self.status_label = QLabel("🔴 Нет подключения")

        self.init_main_tab()
        self.init_settings_tab()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        self.load_config()
        self.update_aerender_status()

    def init_main_tab(self):
        self.main_tab = QWidget()
        layout = QVBoxLayout()

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Задача", "Статус", "Прогресс"])
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.progress = QProgressBar()

        self.start_btn = QPushButton("▶️ Старт рендера (локально)")
        self.register_btn = QPushButton("🔌 Зарегистрироваться и подключиться")

        layout.addWidget(self.tree)
        layout.addWidget(self.start_btn)
        layout.addWidget(QLabel("Прогресс:"))
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Логи:"))
        layout.addWidget(self.logs)
        layout.addWidget(self.register_btn)

        self.main_tab.setLayout(layout)
        self.tabs.addTab(self.main_tab, "Очередь")

        self.start_btn.clicked.connect(self.run_selected_job)
        self.register_btn.clicked.connect(self.register_and_connect)

    def init_settings_tab(self):
        self.settings_tab = QWidget()
        layout = QVBoxLayout()

        self.server_url_input = QLineEdit()
        self.aerender_path_input = QLineEdit()
        self.browse_btn = QPushButton("🔍 Обзор aerender.exe")
        self.save_btn = QPushButton("💾 Сохранить")
        self.status_indicator = QLabel("❌ aerender не найден")

        layout.addWidget(QLabel("Адрес сервера:"))
        layout.addWidget(self.server_url_input)
        layout.addWidget(QLabel("Путь до aerender.exe:"))
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.aerender_path_input)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.save_btn)

        self.settings_tab.setLayout(layout)
        self.tabs.addTab(self.settings_tab, "Настройки")

        self.browse_btn.clicked.connect(self.choose_aerender)
        self.save_btn.clicked.connect(self.save_config)

    def choose_aerender(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите aerender.exe", filter="*.exe")
        if path:
            self.aerender_path_input.setText(path)
            self.update_aerender_status()

    def update_aerender_status(self):
        path = self.aerender_path_input.text().strip()
        if os.path.exists(path) and path.endswith(".exe"):
            self.status_indicator.setText("✅ aerender найден")
        else:
            self.status_indicator.setText("❌ aerender не найден")

    def save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump({
                "server_url": self.server_url_input.text().strip(),
                "aerender_path": self.aerender_path_input.text().strip()
            }, f)
        self.update_aerender_status()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                self.server_url_input.setText(data.get("server_url", "http://localhost:8000"))
                self.aerender_path_input.setText(data.get("aerender_path", ""))
        else:
            self.server_url_input.setText("http://localhost:8000")
            self.aerender_path_input.setText("")

    def register_and_connect(self):
        try:
            hostname = os.getenv("COMPUTERNAME") or os.uname().nodename
            payload = {
                "client_id": self.client_id,
                "hostname": hostname,
                "os": sys.platform
            }
            url = self.server_url_input.text().strip() + "/register"
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                self.logs.append("✅ Клиент зарегистрирован")
                threading.Thread(target=self.start_websocket_listener, daemon=True).start()
            else:
                self.logs.append(f"⚠️ Ошибка регистрации: {r.status_code}")
        except Exception as e:
            self.logs.append(f"[Ошибка регистрации] {e}")

    def start_websocket_listener(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.listen_ws())
        except Exception as e:
            self.logs.append(f"[WS Error] {e}")
            self.status_label.setText("🔴 Нет подключения")

    async def listen_ws(self):
        uri = self.server_url_input.text().strip().replace("http", "ws") + f"/ws/{self.client_id}"
        try:
            async with websockets.connect(uri) as ws:
                self.status_label.setText("🟢 Подключено")
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    if data.get("action") == "start":
                        job_id = data.get("job_id")
                        self.logs.append(f"[WS] Получена задача {job_id}")
                        self.assigned_jobs[job_id] = "pending"
                        self.progress_map[job_id] = 0
                        self.refresh_tree()
        except:
            self.status_label.setText("🔴 Нет подключения")

    def refresh_tree(self):
        self.tree.clear()
        for job_id, status in self.assigned_jobs.items():
            prog = f"{self.progress_map.get(job_id, 0)}%"
            self.tree.addTopLevelItem(QTreeWidgetItem([job_id, status, prog]))

    def run_selected_job(self):
        item = self.tree.currentItem()
        if not item:
            return
        job_id = item.text(0)
        if job_id not in self.assigned_jobs:
            return
        try:
            url = self.server_url_input.text().strip() + "/jobs"
            r = requests.get(url)
            jobs = r.json()
            job = next((j for j in jobs if j["id"] == job_id), None)
            if not job:
                self.logs.append("[Ошибка] Задача не найдена")
                return
            project = job["project_path"]
            jsx = job["jsx_path"]
            cmd = [self.aerender_path_input.text().strip(), "-project", project, "-r", jsx]
            self.logs.append(f"[CMD] {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            last_sent = 0
            for line in proc.stdout:
                self.logs.append(line.strip())
                match = re.search(r"(\\d{1,3})%", line)
                if match:
                    progress = int(match.group(1))
                    self.progress_map[job_id] = progress
                    self.progress.setValue(progress)
                    self.refresh_tree()
                    if progress - last_sent >= 10:
                        self.report_progress(job_id, progress)
                        last_sent = progress
                QApplication.processEvents()
            self.assigned_jobs[job_id] = "done"
            self.refresh_tree()
        except Exception as e:
            self.logs.append(f"[Ошибка выполнения] {e}")

    def report_progress(self, job_id, percent):
        try:
            url = self.server_url_input.text().strip() + f"/jobs/{job_id}/progress"
            requests.patch(url, json={
                "client_id": self.client_id,
                "progress": percent
            })
        except:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RenderClient()
    win.show()
    sys.exit(app.exec())
