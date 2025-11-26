"""
Main GUI Application sử dụng Firewall Service API
"""

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
import sys

from backend.ui import LogTab
from backend.monitoring import setup_charts
from backend.rules.handlers.rules_table_handler_api import RulesTableHandlerAPI
from backend.rules.handlers.add_rule_handler_api import AddRuleHandlerAPI
from backend.rules.handlers import AvailableRulesHandler
from frontend.ui_loader import load_all_tabs
from service.api_client import get_client


class MainWindow(QtWidgets.QMainWindow):
    """Main window class - sử dụng API Service"""
    
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")
        
        # Kiểm tra kết nối service
        self.client = get_client()
        if not self._check_service_connection():
            return
        
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
        
        # Bắt đầu monitoring trên service
        try:
            self.client.start_monitoring()
        except Exception as e:
            print(f"Lưu ý: Không thể bắt đầu monitoring: {e}")

        # Show the main window
        self.ui.show()
    
    def _check_service_connection(self):
        """Kiểm tra kết nối đến service"""
        try:
            if not self.client.health_check():
                QMessageBox.critical(
                    None, 
                    "Lỗi kết nối", 
                    "Không thể kết nối đến Firewall Service.\n\n"
                    "Vui lòng đảm bảo service đang chạy:\n"
                    "  sudo systemctl start firewall-service\n\n"
                    "Hoặc chạy thủ công:\n"
                    "  python3 service/firewall_service.py"
                )
                return False
            return True
        except Exception as e:
            QMessageBox.critical(
                None,
                "Lỗi kết nối",
                f"Không thể kết nối đến Firewall Service:\n{str(e)}\n\n"
                "Vui lòng đảm bảo service đang chạy."
            )
            return False
    
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
        """Khởi tạo System Monitor và Charts sử dụng API"""
        from backend.monitoring.system_monitor_api import SystemMonitorAPI
        self.monitor = SystemMonitorAPI(self.ui)
        self.sandbox_charts_manager, self.host_charts_manager = setup_charts(self.ui, self.monitor)
    
    def _init_rules_table(self):
        """Khởi tạo Rules Table Handler sử dụng API"""
        # Truyền cả ui và self (MainWindow) để timer có parent đúng
        self.rules_table_handler = RulesTableHandlerAPI(self.ui, self)
        
        # Kết nối signals
        self.ui.buttonSearch.clicked.connect(self.rules_table_handler.on_search_clicked)
        self.ui.buttonDeleteMany.clicked.connect(self.rules_table_handler.on_delete_many_clicked)
        
        # Refresh lần đầu
        self.rules_table_handler.refresh_rules_table()
    
    def _init_add_rule(self):
        """Khởi tạo Add Rule Handler sử dụng API"""
        self.add_rule_handler = AddRuleHandlerAPI(self.ui)
        # Kết nối button trong frameAddRule (tab Rules)
        if hasattr(self.ui, "buttonAddRuleInFrame"):
            self.ui.buttonAddRuleInFrame.clicked.connect(
                lambda: self.add_rule_handler.on_add_rule_in_frame_clicked(
                    self.rules_table_handler.refresh_rules_table
                )
            )
    
    def _init_available_rules(self):
        """Khởi tạo Available Rules Handler"""
        # AvailableRulesHandler vẫn có thể dùng trực tiếp vì nó chỉ đọc file
        self.available_rules_handler = AvailableRulesHandler(self.ui)
        
        # Kết nối checkboxes
        self.available_rules_handler.connect_checkboxes(
            self.available_rules_handler.on_available_rule_toggled
        )
        
        # Restore checkbox states (delay để UI load xong)
        QTimer.singleShot(0, self.available_rules_handler.load_available_rules_status)
    
    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        # Có thể dừng monitoring nếu cần
        # self.client.stop_monitoring()
        event.accept()

        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())

