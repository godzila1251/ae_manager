import sys
import os
import subprocess
import threading
import requests
import json
import uuid
import signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget,
    QTextEdit, QHBoxLayout, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QLineEdit, QDialog, QDialogButtonBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer

CONFIG_PATH = os.path.expanduser("~/.render_server_config.json")
TEMP_DIR = os.path.abspath("./temp")
os.makedirs(TEMP_DIR, exist_ok=True)

SERVER_URL = "http://localhost:8000"

class ClientSelectDialog(QDialog):
    def __init__(self, clients):
        super().__init__()
        self.setWindowTitle("Назначить задачу клиентам")
        self.layout = QVBoxLayout()
        self.checkboxes = []
        for cid, info in clients.items():
            cb = QCheckBox(f"{info.get('hostname', 'Client')} ({cid[:6]})")
            cb.client_id = cid
            self.checkboxes.append(cb)
            self.layout.addWidget(cb)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        self.setLayout(self.layout)

    def get_selected(self):
        return [cb.client_id for cb in self.checkboxes if cb.isChecked()]

class ServerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexRender Server GUI")
        self.resize(900, 650)
        self.proc = None
        self.server_running = False
        self.assigned_clients = []
        self.last_project_path = ""
        self.job_loading = False
        self.client_loading = False

        self.tabs = QTabWidget()
        self.init_queue_tab()
        self.init_client_tab()
        self.init_settings_tab()
        self.init_project_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.load_config()

    def init_queue_tab(self):
        self.queue_tab = QWidget()
        layout = QVBoxLayout()
        self.status_label = QLabel("🔌 Сервер не запущен")
        layout.addWidget(self.status_label)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderLabels(["ID задачи", "Статус", "Клиент", "Прогресс"])
        layout.addWidget(self.task_tree)

        btns = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Запустить сервер")
        self.stop_btn = QPushButton("⏹ Остановить сервер")
        self.refresh_btn = QPushButton("🔄 Обновить задачи")
        self.launch_btn = QPushButton("🚀 Старт задачи")
        self.cancel_btn = QPushButton("❌ Отменить задачу")
        for btn in [self.start_btn, self.stop_btn, self.refresh_btn, self.launch_btn, self.cancel_btn]:
            btns.addWidget(btn)
        layout.addLayout(btns)

        self.queue_tab.setLayout(layout)
        self.tabs.addTab(self.queue_tab, "Очередь")

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        self.refresh_btn.clicked.connect(self.load_jobs)
        self.launch_btn.clicked.connect(self.start_selected_job)
        self.cancel_btn.clicked.connect(self.cancel_selected_job)

    def init_client_tab(self):
        self.client_tab = QWidget()
        layout = QVBoxLayout()
        self.client_list = QListWidget()
        layout.addWidget(QLabel("Подключённые клиенты:"))
        layout.addWidget(self.client_list)
        self.refresh_clients = QPushButton("🔄 Обновить")
        layout.addWidget(self.refresh_clients)
        self.refresh_clients.clicked.connect(self.load_clients)
        self.client_tab.setLayout(layout)
        self.tabs.addTab(self.client_tab, "Клиенты")

    def load_jobs(self):
        if self.job_loading:
            return
        self.job_loading = True
        self.refresh_btn.setText("⏳ Обновление...")
        def task():
            try:
                r = requests.get(f"{SERVER_URL}/jobs")
                jobs = r.json()
                self.task_tree.clear()
                for job in jobs:
                    item = QTreeWidgetItem([job["id"], job["status"], "", ""])
                    for cid, progress in job.get("progress", {}).items():
                        child = QTreeWidgetItem(["", "", cid[:6], f"{progress}%"])
                        item.addChild(child)
                    self.task_tree.addTopLevelItem(item)
                    item.setExpanded(True)
            except Exception as e:
                self.output.append(f"[Ошибка загрузки задач] {e}")
            finally:
                self.job_loading = False
                self.refresh_btn.setText("🔄 Обновить задачи")
        threading.Thread(target=task, daemon=True).start()

    def load_clients(self):
        if self.client_loading:
            return
        self.client_loading = True
        self.refresh_clients.setText("⏳ Обновление...")
        def task():
            try:
                r = requests.get(f"{SERVER_URL}/clients")
                clients = r.json()
                self.client_list.clear()
                for cid, info in clients.items():
                    status = info.get("status", "unknown")
                    icon = "🟢" if status == "connected" else "🔴"
                    self.client_list.addItem(f"{icon} {info.get('hostname', 'Client')} ({cid[:6]})")
            except Exception as e:
                self.output.append(f"[Ошибка загрузки клиентов] {e}")
            finally:
                self.client_loading = False
                self.refresh_clients.setText("🔄 Обновить")
        threading.Thread(target=task, daemon=True).start()
```
    }
  ]
}
