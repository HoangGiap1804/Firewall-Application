from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import re
import sys

# Danh sách các cột log
Roles = [
    "in", "out", "mac", "src", "dst", "len", "tos", "prec",
    "ttl", "id", "proto", "spt", "dpt", "len2"
]


def parse_message(msg: str):
    """Phân tích chuỗi log thành dict theo Roles"""
    result = {key: "" for key in Roles}
    pattern = re.findall(r'(\b[A-Z]+)=([^\s]+)', msg)
    for key, value in pattern:
        k = key.lower()
        if k in result:
            result[k] = value
    return result


class LogTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/log_tab.ui")  # Đảm bảo file UI có tableWidget

        # Cấu hình table
        self.ui.tableWidget.setColumnCount(len(Roles))
        self.ui.tableWidget.setHorizontalHeaderLabels([r.upper() for r in Roles])
        self.ui.tableWidget.setAlternatingRowColors(True)
        self.ui.tableWidget.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)

        # Khởi tạo process
        self.process = QProcess()
        # ⚠️ Không nên dùng sudo vì sẽ yêu cầu password, chỉ test khi cần
        self.process.setProgram("tail")
        self.process.setArguments(["-f", "/var/log/kern.log"])
        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.start()

    def on_ready_read(self):
        """Khi có log mới"""
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.strip().splitlines():
            if not line.strip():
                continue

            fields = parse_message(line)

            # Thêm dòng mới
            row = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(row)

            # Đặt màu nền xen kẽ
            bg_color = QColor("#f0f0f0") if row % 2 == 0 else QColor("white")

            # Gán từng giá trị vào cột
            for col, key in enumerate(Roles):
                item = QTableWidgetItem(fields[key])
                item.setBackground(bg_color)
                self.ui.tableWidget.setItem(row, col, item)

            # Cuộn xuống cuối
            self.ui.tableWidget.scrollToBottom()

    def on_reload(self):
        print("Reloading logs...")
