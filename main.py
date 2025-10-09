import sys
import subprocess
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QByteArray, QProcess
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from backend.log_mode import LogModel
from backend.rule_input import IptablesModel
from backend.add_rule import IptablesHandler
from backend.app_network_model import AppNetworkModel
from backend.notification import Notification
from backend.log_matcher import LogWatcher
from backend.firewall_controller import FirewallController
from backend.available_rules import AvailableRules

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

notification = Notification()
engine.rootContext().setContextProperty("notification", notification)

watcher = LogWatcher()
engine.rootContext().setContextProperty("LogWatcher", watcher)

firewall = FirewallController()
engine.rootContext().setContextProperty("firewall", firewall)

available_rules = AvailableRules()
engine.rootContext().setContextProperty("availableRules", available_rules)

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
        log_model.addLog(line)
            

process.readyReadStandardOutput.connect(on_ready_read)
process.start()

sys.exit(app.exec())