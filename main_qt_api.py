"""
Main GUI Application sử dụng Firewall Service API
"""

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMessageBox
import sys

from backend.ui import LogTab
from backend.monitoring import setup_charts
from backend.rules.handlers.rules_table_handler_api import RulesTableHandlerAPI
from backend.rules.handlers.add_rule_handler_api import AddRuleHandlerAPI
from backend.rules.handlers import AvailableRulesHandler
from backend.blacklist.blacklist_handler import BlacklistHandler
from backend.sandbox.sandbox_handler import SandboxHandler
from backend.settings.settings_handler import SettingsHandler
from backend.notifications.notification import send_notification
from frontend.ui_loader import load_all_tabs
from service.api_client import get_client


class MainWindow(QtWidgets.QMainWindow):
    """Main window class - sử dụng API Service"""
    
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("frontend/main.ui")
        # Enable Min/Max buttons for QDialog and force top-level window behavior
        self.ui.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        # Ensure the dialog is resizable
        self.ui.setSizeGripEnabled(True)
        
        # Wrap tabWidget in QScrollArea for scrollable UI
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        
        tab_widget = self.ui.tabWidget
        layout = self.ui.layout()
        
        if layout and tab_widget:
            layout.removeWidget(tab_widget)
            scroll_area.setWidget(tab_widget)
            layout.addWidget(scroll_area, 0, 0)
        
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
        self._init_sandbox()
        self._init_settings()
        self._init_blacklist_tab()
        
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
        
        # Connect rules_changed signal to refresh Rules table
        self.available_rules_handler.rules_changed.connect(
            self.rules_table_handler.refresh_rules_table
        )

    def _init_sandbox(self):
        """Khởi tạo Sandbox Handler"""
        self.sandbox_handler = SandboxHandler(self.ui)

    def _init_settings(self):
        """Khởi tạo Settings Handler"""
        self.settings_handler = SettingsHandler(self.ui)

    def _init_blacklist_tab(self):
        """Khởi tạo Blacklist Handler"""
        self.blacklist_handler = BlacklistHandler(self.ui)




    
    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        # Có thể dừng monitoring nếu cần
        if hasattr(self, 'monitor'):
             self.monitor.stop_monitoring()
        # self.client.stop_monitoring()
        event.accept()

        
if __name__ == "__main__":
    # Check for root privileges
    import os
    if os.geteuid() != 0:
        import subprocess
        print("Not running as root. Restarting with pkexec...")
        
        # Prepare the command
        # We need to preserve DISPLAY and XAUTHORITY for GUI to work
        env = os.environ.copy()
        
        # Basic command to restart self
        script_path = os.path.abspath(__file__)
        args = ["pkexec", "env"]
        
        # Pass essential X11 variables
        if "DISPLAY" in env:
            args.append(f"DISPLAY={env['DISPLAY']}")
        if "XAUTHORITY" in env:
            args.append(f"XAUTHORITY={env['XAUTHORITY']}")
            
        args.extend([sys.executable, script_path] + sys.argv[1:])
        
        try:
            # Replace the current process
            os.execvpe("pkexec", args, env)
        except OSError as e:
            print(f"Error restarting as root: {e}")
            sys.exit(1)

    # Ensure working directory is the project root (pkexec might change it)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec())

