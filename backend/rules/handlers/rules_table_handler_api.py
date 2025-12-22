"""
Handler xử lý logic cho Rules Table sử dụng API Service
"""

from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from service.api_client import get_client


class RulesRefreshWorker(QThread):
    """Worker thread để lấy rules từ API không block UI"""
    rules_loaded = pyqtSignal(list)  # Emit rules list
    
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    def run(self):
        """Lấy rules từ API trong thread riêng"""
        try:
            rules = self.client.list_rules()
            self.rules_loaded.emit(rules)
        except ConnectionError as e:
            print(f"❌ Lỗi kết nối khi lấy danh sách rules: {e}")
            print("💡 Gợi ý: Kiểm tra xem Firewall Service có đang chạy không, hoặc kiểm tra OUTPUT chain policy")
            self.rules_loaded.emit([])
        except TimeoutError as e:
            print(f"⏱️ Timeout khi lấy danh sách rules: {e}")
            self.rules_loaded.emit([])
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách rules: {e}")
            import traceback
            traceback.print_exc()
            self.rules_loaded.emit([])


class RulesTableHandlerAPI:
    """Xử lý logic cho bảng hiển thị rules sử dụng API"""
    
    def __init__(self, ui, parent=None):
        """
        Args:
            ui: UI object từ uic.loadUi
            parent: Parent QObject cho timer (thường là MainWindow instance)
        """
        self.ui = ui
        self.client = get_client()
        self.current_filter = ""
        self.is_refreshing = False  # Flag để tránh refresh đồng thời
        self.is_refreshing = False  # Flag để tránh refresh đồng thời
        
        # Connect returnPressed for search
        if hasattr(self.ui, 'editRules'):
            self.ui.editRules.returnPressed.connect(self.on_search_clicked)
        
        self.worker = None  # Worker thread
    
    def refresh_rules_table(self):
        """Lấy danh sách rule từ API và hiển thị trên tableRules (async)"""
        # Nếu đang refresh, bỏ qua
        if self.is_refreshing:
            return
        
        # Nếu worker đang chạy, bỏ qua
        if self.worker and self.worker.isRunning():
            return
        
        self.is_refreshing = True
        
        # Tạo và chạy worker thread
        self.worker = RulesRefreshWorker(self.client)
        self.worker.rules_loaded.connect(self._on_rules_loaded)
        self.worker.finished.connect(lambda: setattr(self, 'is_refreshing', False))
        self.worker.start()
    
    def _on_rules_loaded(self, rules):
        """Xử lý khi rules đã được load xong"""
        try:
            # Debug: in số lượng rules và chains
            if rules:
                chains = set(r.get("chain", "INPUT") for r in rules)
                print(f"Đã lấy {len(rules)} rule(s) từ {len(chains)} chain(s): {', '.join(sorted(chains))}")
        except Exception as e:
            print(f"Lỗi khi xử lý rules: {e}")
            import traceback
            traceback.print_exc()
            self.is_refreshing = False
            return
        
        filter_text = self.current_filter.lower().strip()
        table = self.ui.tableRules
        
        table.setRowCount(0)
        table.setColumnCount(12)
        headers = [
            "num", "pkts", "bytes", "target", "prot",
            "in", "out", "source", "destination", "chain", "detail", "Action"
        ]
        table.setHorizontalHeaderLabels(headers)

        row_index = 0
        for rule in rules:
            # Chain filtering
            chain = rule.get("chain", "INPUT")
            
            # Lấy detail từ rule_key
            rule_key = rule.get("rule_key", "")
            detail = ""
            if rule_key:
                parts = rule_key.split()
                if len(parts) > 7:
                    detail = " ".join(parts[7:])
            
            # Filter logic: Check all fields
            if filter_text:
                # Prepare fields for searching
                search_fields = [
                    chain,
                    rule.get("target", ""),
                    rule.get("in_", ""),
                    rule.get("out", ""),
                    rule.get("opt", ""),
                    rule.get("source", ""),
                    rule.get("destination", ""),
                    str(rule.get("pkts", "")),  
                    str(rule.get("bytes", "")),
                    detail
                ]
                
                # Check if filter_text exists in any field (case-insensitive)
                match = any(filter_text in str(field).lower() for field in search_fields)
                if not match:
                    continue
            
            table.insertRow(row_index)
            values = [
                rule["num"], rule["pkts"], rule["bytes"], rule["target"],
                rule["prot"], rule["in_"], rule["out"], 
                rule["source"], rule["destination"], chain, detail
            ]
            
            # Set items in the table read-only
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, col_index, item)

            # Add Delete Button for each row
            from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout
            
            # Create a container widget to center the button
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_delete = QPushButton("Delete")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setMinimumWidth(60)
            btn_delete.setMinimumHeight(24)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444; 
                    color: white; 
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
                QPushButton:pressed {
                    background-color: #b91c1c;
                }
            """)
            
            # Connect signal using closure to capture current rule info
            # rule["num"] and chain are captured
            btn_delete.clicked.connect(lambda checked, n=rule["num"], c=chain: self.on_delete_clicked(n, c))
            
            layout.addWidget(btn_delete)
            table.setCellWidget(row_index, 11, container)
            
            # Ensure row has enough height
            table.setRowHeight(row_index, 40)
            
            row_index += 1

        table.resizeColumnsToContents()
    
    def on_search_clicked(self):
        """Lọc theo chain"""
        chain_name = self.ui.editRules.text().strip()
        self.current_filter = chain_name
        print(f"Filter applied: {chain_name if chain_name else 'All rules shown'}")
        self.refresh_rules_table()
    
    def on_delete_clicked(self, num, chain):
        """Xử lý khi nút Xóa trên 1 dòng được nhấn"""
        reply = QMessageBox.question(
            self.ui, 
            "Confirm Delete", 
            f"Are you sure you want to delete rule #{num} from chain {chain}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Call delete with chain info
                result = self.client.delete_rule(num, chain=chain)
                
                if result.get("status") == "success":
                    print(f"✅ Rule #{num} deleted from {chain}")
                    # Refresh table to show changes
                    self.refresh_rules_table()
                else:
                    error = result.get("error", "Unknown error")
                    QMessageBox.warning(self.ui, "Delete Failed", f"Could not delete rule: {error}")
            except Exception as e:
                QMessageBox.critical(self.ui, "Error", f"An error occurred: {str(e)}")

