from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer
import sys

from backend.ui import LogTab
from backend.rules.core import IptablesModel
from backend.monitoring import SystemMonitor, setup_charts
from backend.rules.handlers import RulesTableHandler, AddRuleHandler, AvailableRulesHandler


class MainWindow(QtWidgets.QMainWindow):
    """Main window class - chỉ chịu trách nhiệm khởi tạo UI và kết nối signals"""
    
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")

        # Khởi tạo các components
        self._init_log_tab()
        self._init_system_monitor()
        self._init_rules_table()
        self._init_add_rule()
        self._init_available_rules()

        # Show the main window
        self.ui.show()
    
    def _init_log_tab(self):
        """Khởi tạo Log Tab"""
        self.log_tab = LogTab(self.ui.tabLogTable)
    
    def _init_system_monitor(self):
        """Khởi tạo System Monitor và Charts"""
        self.monitor = SystemMonitor(self.ui)
        self.charts_manager = setup_charts(self.ui, self.monitor)
    
    def _init_rules_table(self):
        """Khởi tạo Rules Table Handler"""
        self.iptables_model = IptablesModel()
        self.rules_table_handler = RulesTableHandler(self.ui, self.iptables_model)
        
        # Kết nối signals
        self.ui.buttonSearch.clicked.connect(self.rules_table_handler.on_search_clicked)
        self.ui.buttonDeleteMany.clicked.connect(self.rules_table_handler.on_delete_many_clicked)
        
        # Refresh rules table periodically
        self.iptables_model.timer.timeout.connect(self.rules_table_handler.refresh_rules_table)
        
        # Refresh lần đầu
        self.rules_table_handler.refresh_rules_table()
    
    def _init_add_rule(self):
        """Khởi tạo Add Rule Handler"""
        self.add_rule_handler = AddRuleHandler(self.ui)
        self.ui.buttonAddRule.clicked.connect(
            lambda: self.add_rule_handler.on_add_rule_clicked(
                self.rules_table_handler.refresh_rules_table
            )
        )
    
    def _init_available_rules(self):
        """Khởi tạo Available Rules Handler"""
        self.available_rules_handler = AvailableRulesHandler(self.ui)
        
        # Kết nối checkboxes
        self.available_rules_handler.connect_checkboxes(
            self.available_rules_handler.on_available_rule_toggled
        )
        
        # Restore checkbox states (delay để UI load xong)
        QTimer.singleShot(0, self.available_rules_handler.load_available_rules_status)
    
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())
