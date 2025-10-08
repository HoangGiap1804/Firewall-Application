import sys
import subprocess
from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class Notification(QObject):
    @Slot(str, str)
    def send(self, title, message):
        subprocess.run(["notify-send", title, message])
