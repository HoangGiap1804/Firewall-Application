from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer
import sys

from backend.ui import LogTab
from backend.rules.core import IptablesModel
from backend.monitoring import SystemMonitor, setup_charts
from backend.rules.handlers import RulesTableHandler, AddRuleHandler, AvailableRulesHandler
from frontend.ui_loader import load_all_tabs


class MainWindow(QtWidgets.QMainWindow):
    """Main window class - chỉ chịu trách nhiệm khởi tạo UI và kết nối signals"""
    
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")
        
        # Load các tab riêng biệt
        load_all_tabs(self.ui.tabWidget)
        
        # Tạo namespace để truy cập các widget trong tab
        self._setup_ui_namespace()

        # Khởi tạo các components
        self._init_log_tab()
        self._init_system_monitor()
        self._init_rules_table()
        self._init_add_rule()
        self._init_available_rules()

        # Show the main window
        self.ui.show()
    
    def _setup_ui_namespace(self):
        """Thiết lập namespace để truy cập các widget trong tab"""
        # Tìm tất cả các widget trong các tab và thêm vào self.ui
        for i in range(self.ui.tabWidget.count()):
            tab = self.ui.tabWidget.widget(i)
            # Tìm tất cả các widget con và thêm vào namespace
            for widget in tab.findChildren(QtWidgets.QWidget):
                widget_name = widget.objectName()
                if widget_name:
                    setattr(self.ui, widget_name, widget)
    
    def _init_log_tab(self):
        """Khởi tạo Log Tab"""
        # Truyền các widget cần thiết
        date_edit = getattr(self.ui, 'logDateEdit', None)
        load_button = getattr(self.ui, 'loadLogButton', None)
        realtime_button = getattr(self.ui, 'realtimeLogButton', None)
        self.log_tab = LogTab(
            self.ui.tabLogTable,
            date_edit=date_edit,
            load_button=load_button,
            realtime_button=realtime_button
        )
    
    def _init_system_monitor(self):
        """Khởi tạo System Monitor và Charts"""
        self.monitor = SystemMonitor(self.ui)
        self.sandbox_charts_manager, self.host_charts_manager = setup_charts(self.ui, self.monitor)
    
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
        # Kết nối button trong frameAddRule (tab Rules)
        if hasattr(self.ui, "buttonAddRuleInFrame"):
            self.ui.buttonAddRuleInFrame.clicked.connect(
                lambda: self.add_rule_handler.on_add_rule_in_frame_clicked(
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
