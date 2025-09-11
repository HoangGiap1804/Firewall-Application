import sys
import subprocess
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QByteArray, QProcess
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from log_mode import LogModel
from rule_input import IptablesModel
from add_rule import IptablesHandler
from app_network_model import AppNetworkModel

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

log_model = LogModel()
engine.rootContext().setContextProperty("logModel", log_model)

iptable_model = IptablesModel()
engine.rootContext().setContextProperty("inputRuleModel", iptable_model)

handler = IptablesHandler()
engine.rootContext().setContextProperty("pyHandler", handler)

model = AppNetworkModel()
engine.rootContext().setContextProperty("appModel", model)

engine.load("main.qml")

if not engine.rootObjects():
    print("Failed to load QML")
    sys.exit(-1)

# QProcess chạy lệnh sudo tail
process = QProcess()
process.setProgram("sudo")
process.setArguments(["tail", "-f", "/var/log/kern.log"])

# Lọc log IPTables-INPUT
def on_ready_read():
    for line in process.readAllStandardOutput().data().decode().splitlines():
        if "IPTables-INPUT" in line:
            log_model.addLog(line)

process.readyReadStandardOutput.connect(on_ready_read)
process.start()

sys.exit(app.exec())