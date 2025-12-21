from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QTableWidgetItem, QPushButton, QMessageBox
from backend.blacklist.blacklist_manager import BlacklistManager

class BlacklistHandler:
    """Handler cho tab Blacklist UI"""
    
    def __init__(self, ui):
        self.ui = ui
        self.manager = BlacklistManager()
        
        # Cache references
        self.table = getattr(self.ui, 'tableBlacklist', None)
        self.btn_refresh = getattr(self.ui, 'btnRefreshBlacklist', None)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Thiết lập kết nối và cấu hình UI ban đầu"""
        if self.table:
            self.table.setColumnWidth(0, 200) # IP Address
            self.table.setColumnWidth(1, 300) # Rule details
            self.table.setColumnWidth(2, 100) # Action
            
        if self.btn_refresh:
            self.btn_refresh.clicked.connect(self.refresh_blacklist)
            
        # Load data initially
        self.refresh_blacklist()
        
    def refresh_blacklist(self):
        """Tải lại danh sách IP bị chặn"""
        if not self.table:
            return
            
        self.table.setRowCount(0)
        blocked_ips = self.manager.get_blacklist()
        
        for ip_info in blocked_ips:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            source_ip = ip_info.get('ip', 'Unknown')
            reason = ip_info.get('reason', '')
            timestamp = ip_info.get('timestamp', '')
            
            details = f"{reason} ({timestamp})"
            
            # Column 0: IP Address
            self.table.setItem(row, 0, QTableWidgetItem(source_ip))
            
            # Column 1: Rule Details
            self.table.setItem(row, 1, QTableWidgetItem(details))
            
            # Column 2: Unblock Button
            btn_unblock = QPushButton("Unblock")
            btn_unblock.setStyleSheet("""
                background-color: #e74c3c; 
                color: white; 
                border-radius: 4px; 
                padding: 4px;
                font-weight: bold;
            """)
            btn_unblock.clicked.connect(lambda _, ip=source_ip: self.unblock_ip_clicked(ip))
            self.table.setCellWidget(row, 2, btn_unblock)
            
    def unblock_ip_clicked(self, ip):
        """Xử lý sự kiện click nút Unblock"""
        reply = QMessageBox.question(
            None, 
            "Confirm Unblock", 
            f"Are you sure you want to unblock IP: {ip}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.manager.unblock_ip(ip):
                QMessageBox.information(None, "Success", f"IP {ip} has been unblocked.")
                
                # Clear from LogTab cache to allow re-blocking
                try:
                    from backend.ui.log_tab import remove_from_blocked_ips
                    remove_from_blocked_ips(ip)
                except ImportError:
                    print("⚠️ Could not import remove_from_blocked_ips from log_tab")

                self.refresh_blacklist()
            else:
                QMessageBox.critical(None, "Error", f"Failed to unblock {ip}. Check console for details.")
