from PyQt6 import QtWidgets, uic
from backend.log_tab import LogTab
# from frontend.setting_tab import SettingTab
# from frontend.about_tab import AboutTab
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")

        # self.log_tab = LogTab()
        # self.setting_tab = SettingTab()
        # self.about_tab = AboutTab()

        # self.ui.tabWidget.addTab(self.log_tab, "Logs")
        # self.ui.tabWidget.addTab(self.setting_tab, "Settings")
        # self.ui.tabWidget.addTab(self.about_tab, "About")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())
