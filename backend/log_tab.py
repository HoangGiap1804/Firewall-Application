from PyQt6 import QtWidgets
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import re

Roles = [
    "in", "out", "mac", "src", "dst", "len", "tos", "prec",
    "ttl", "id", "proto", "spt", "dpt", "len2"
]


def parse_message(msg: str):
    """Phân tích dòng log."""
    result = {k: "" for k in Roles}
    for key, val in re.findall(r"(\b[A-Z]+)=([^\s]+)", msg):
        k = key.lower()
        if k in result:
            result[k] = val
    return result


class LogTab(QtWidgets.QWidget):
    def __init__(self, tableWidget):
        super().__init__()
        self.tableWidget = tableWidget

        self.tableWidget.setColumnCount(len(Roles))
        self.tableWidget.setHorizontalHeaderLabels([r.upper() for r in Roles])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        self.process = QProcess()
        self.process.setProgram("tail")
        self.process.setArguments(["-f", "/var/log/kern.log"])
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.start()

    def read_log(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.strip().splitlines():
            fields = parse_message(line)
            if all(v == "" for v in fields.values()):
                continue
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)
            bg = QColor("#f0f0f0") if row % 2 == 0 else QColor("white")
            for c, k in enumerate(Roles):
                item = QTableWidgetItem(fields[k])
                item.setBackground(bg)
                self.tableWidget.setItem(row, c, item)
            self.tableWidget.scrollToBottom()
