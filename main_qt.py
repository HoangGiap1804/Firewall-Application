from PyQt6 import QtWidgets, uic
from backend.log_tab import LogTab
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")

        self.log_tab = LogTab(self.ui.tableWidget)

        # self.ui.tableWidget.addTab(self.log_tab.ui, "Log")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())
