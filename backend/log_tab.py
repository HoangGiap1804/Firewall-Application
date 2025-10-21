from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import re

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
    def __init__(self, tableWidget):
        super().__init__()

        # Giữ tham chiếu đến bảng được truyền từ MainWindow
        self.tableWidget = tableWidget

        # Cấu hình bảng log
        self.tableWidget.setColumnCount(len(Roles))
        self.tableWidget.setHorizontalHeaderLabels([r.upper() for r in Roles])
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        self.tableWidget.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
                font-family: monospace;
                font-size: 12px;
            }
        """)

        # Tạo process đọc log
        self.process = QProcess()
        self.process.setProgram("tail")
        self.process.setArguments(["-f", "/var/log/kern.log"])
        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.start()

    def on_ready_read(self):
        """Đọc dữ liệu log và hiển thị lên bảng"""
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.strip().splitlines():
            line = line.strip()
            if not line:
                continue  # Bỏ qua dòng rỗng

            fields = parse_message(line)

            # Bỏ qua dòng nếu tất cả các giá trị trong fields đều rỗng
            if all(v == "" for v in fields.values()):
                continue

            # Thêm dòng mới vào bảng
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)

            # Xen kẽ màu nền
            bg_color = QColor("#f0f0f0") if row % 2 == 0 else QColor("white")

            for col, key in enumerate(Roles):
                item = QTableWidgetItem(fields[key])
                item.setBackground(bg_color)
                self.tableWidget.setItem(row, col, item)

            # Cuộn xuống cuối bảng
            self.tableWidget.scrollToBottom()
