"""
Handler xử lý logic cho Available Rules Tab
"""

import subprocess
import json
import os
from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt, QObject
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox, QWidget, QHBoxLayout, QLabel, QPushButton
from backend.rules.core import AvailableRules

OUTBOUND_RULES_FILE = "outbound_rules.json"


class ToggleRuleWorker(QThread):
    """Worker thread để chạy toggleRule không block UI"""
    finished = pyqtSignal(str, bool, str)  # group_name, enable, result
    
    def __init__(self, available_rules, group_name, enable):
        super().__init__()
        self.available_rules = available_rules
        self.group_name = group_name
        self.enable = enable
    
    def run(self):
        """Chạy toggleRule trong thread riêng"""
        try:
            result = self.available_rules.toggleRule(self.group_name, self.enable)
            self.finished.emit(self.group_name, self.enable, result)
        except Exception as e:
            import traceback
            error_msg = f"ERROR: {str(e)}\n{traceback.format_exc()}"
            self.finished.emit(self.group_name, self.enable, error_msg)


class AvailableRulesHandler(QObject):
    """Xử lý logic cho tab Available Rules"""
    
    rules_changed = pyqtSignal()  # Signal emitted when rules change
    
    def __init__(self, ui):
        """
        Args:
            ui: UI object từ uic.loadUi
        """
        super().__init__()
        self.ui = ui
        self.available_rules = AvailableRules()
        self.available_rule_map = self._build_rule_map()
        self.processing_checkboxes = set()  # Track checkboxes đang xử lý
        self.worker = None  # Current worker thread
        self.pending_toggle = None  # (group_name, enable, checkbox)
        self.outbound_rules = []  # Lưu danh sách outbound rules đã thêm (format: {"protocol": "tcp", "port": "80", "rule_info": "TCP:80"})
        self._load_outbound_rules()  # Load rules từ file
        self._init_outbound_ui()
        self._hide_removed_features()
    
    def _build_rule_map(self):
        """Tạo map checkbox -> group name"""
        rule_map = {}
        checkbox_names = {
            "checkBoxICMPFlood": "ICMP Flood",
            "checkBoxSYNFlood": "SYN Flood",
            "checkBoxPortScan": "Port Scan",
            # "checkBoxIpSpoofing": "IP Spoofing",      # Hidden
            # "checkBoxInvalidPacket": "Invalid Packet", # Hidden
            # "checkBoxBroadcast": "Broadcast Control",  # Hidden
            # "checkBoxOutbound": "Outbound Protection", # Hidden
            "checkBoxFinXmasNullScan": "FIN/XMAS/NULL Scan",
            "checkBoxSSH_FTP": "SSH/FTP Brute Force",
        }
        
        for checkbox_name, group_name in checkbox_names.items():
            if hasattr(self.ui, checkbox_name):
                checkbox = getattr(self.ui, checkbox_name)
                rule_map[checkbox] = group_name
            else:
                print(f"Warning: Checkbox {checkbox_name} không tồn tại trong UI")
        
        return rule_map
    
    def connect_checkboxes(self, toggle_callback):
        """
        Kết nối event handlers cho các checkboxes
        
        Args:
            toggle_callback: Function được gọi khi checkbox thay đổi state
        """
        for checkbox, group_name in self.available_rule_map.items():
            try:
                checkbox.stateChanged.connect(lambda state, g=group_name: toggle_callback(g, state))
            except Exception as e:
                print(f"Error connecting checkbox for {group_name}: {e}")
    
    def on_available_rule_toggled(self, group_name, state):
        """Khi bật/tắt checkbox => gọi toggleRule trong backend (async)."""
        enable = bool(state)
        
        # Xử lý đặc biệt cho Outbound Protection
        if group_name == "Outbound Protection":
            self._handle_outbound_toggle(enable)
            # Vẫn gọi toggleRule để cập nhật status
            # Nhưng logic chính đã được xử lý ở _handle_outbound_toggle
        
        # Tìm checkbox tương ứng
        checkbox = None
        for cb, name in self.available_rule_map.items():
            if name == group_name:
                checkbox = cb
                break
        
        if not checkbox:
            return
        
        # Nếu đang xử lý checkbox này, bỏ qua
        if checkbox in self.processing_checkboxes:
            # Khôi phục lại trạng thái cũ
            checkbox.blockSignals(True)
            checkbox.setChecked(not enable)
            checkbox.blockSignals(False)
            return
        
        # Nếu đang có worker khác chạy, đợi nó xong
        if self.worker and self.worker.isRunning():
            # Lưu lại toggle này để xử lý sau
            self.pending_toggle = (group_name, enable, checkbox)
            # Khôi phục lại trạng thái cũ
            checkbox.blockSignals(True)
            checkbox.setChecked(not enable)
            checkbox.blockSignals(False)
            return
        
        # Disable checkbox và bắt đầu xử lý
        checkbox.setEnabled(False)
        self.processing_checkboxes.add(checkbox)
        
        print(f"Toggling {group_name}: {'ON' if enable else 'OFF'}")
        
        # Tạo và chạy worker thread
        self.worker = ToggleRuleWorker(self.available_rules, group_name, enable)
        self.worker.finished.connect(lambda g, e, r: self._on_toggle_finished(g, e, r, checkbox))
        self.worker.start()
    
    def _on_toggle_finished(self, group_name, enable, result, checkbox):
        """Xử lý khi toggleRule hoàn thành"""
        # Re-enable checkbox
        checkbox.setEnabled(True)
        self.processing_checkboxes.discard(checkbox)
        
        print(result)
        
        # Kiểm tra lỗi
        if "error" in result.lower() or "err" in result.lower():
            print(f"⚠️ Có lỗi khi toggle {group_name}: {result}")
            # Khôi phục lại trạng thái checkbox nếu có lỗi
            checkbox.blockSignals(True)
            checkbox.setChecked(not enable)
            checkbox.blockSignals(False)
        else:
            # Emit signal to refresh rules table
            self.rules_changed.emit()
        
        # Xử lý pending toggle nếu có
        if self.pending_toggle:
            pending_group, pending_enable, pending_checkbox = self.pending_toggle
            self.pending_toggle = None
            # Đợi một chút rồi xử lý
            QTimer.singleShot(100, lambda: self._process_pending_toggle(pending_group, pending_enable, pending_checkbox))
        
        # Cleanup worker
        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None

    
    def _process_pending_toggle(self, group_name, enable, checkbox):
        """Xử lý toggle đang chờ"""
        checkbox.blockSignals(True)
        checkbox.setChecked(enable)
        checkbox.blockSignals(False)
        self.on_available_rule_toggled(group_name, enable)
    
    def load_available_rules_status(self):
        """Cập nhật trạng thái checkbox theo available_rules.json"""
        try:
            status_data = self.available_rules.getStatus()

            if not isinstance(status_data, dict):
                print("Warning: available_rules.getStatus() did not return dict.")
                return

            for checkbox, group_name in self.available_rule_map.items():
                try:
                    info = status_data.get(group_name, {})
                    enabled = info.get("enabled", False) if isinstance(info, dict) else bool(info)
                    checkbox.blockSignals(True)
                    checkbox.setChecked(enabled)
                    checkbox.blockSignals(False)
                except Exception as e:
                    print(f"Error loading status for {group_name}: {e}")
        except Exception as e:
            import traceback
            print(f"Error in load_available_rules_status: {e}")
            traceback.print_exc()
    
    def _load_outbound_rules(self):
        """Load outbound rules từ file JSON"""
        try:
            if os.path.exists(OUTBOUND_RULES_FILE):
                with open(OUTBOUND_RULES_FILE, "r", encoding='utf-8') as f:
                    self.outbound_rules = json.load(f)
                    print(f"✅ Đã load {len(self.outbound_rules)} outbound rule(s) từ file")
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"Error loading outbound rules file: {e}")
            self.outbound_rules = []
        except Exception as e:
            print(f"Unexpected error loading outbound rules: {e}")
            self.outbound_rules = []
    
    def _save_outbound_rules(self):
        """Lưu outbound rules vào file JSON"""
        try:
            with open(OUTBOUND_RULES_FILE, "w", encoding='utf-8') as f:
                json.dump(self.outbound_rules, f, indent=4, ensure_ascii=False)
            print(f"✅ Đã lưu {len(self.outbound_rules)} outbound rule(s) vào file")
        except (IOError, OSError, TypeError) as e:
            print(f"Error saving outbound rules file: {e}")
        except Exception as e:
            print(f"Unexpected error saving outbound rules: {e}")
    
    def _init_outbound_ui(self):
        """Khởi tạo UI cho Outbound Protection"""
        try:
            # Kết nối button thêm rule
            if hasattr(self.ui, 'buttonAddOutboundRule'):
                self.ui.buttonAddOutboundRule.clicked.connect(self._on_add_outbound_rule)
            
            # Load danh sách rules đã thêm
            self._refresh_outbound_rules_list()
        except Exception as e:
            print(f"Error initializing outbound UI: {e}")
    
    def _refresh_outbound_rules_list(self):
        """Cập nhật danh sách outbound rules trong listWidget với button xóa"""
        try:
            if hasattr(self.ui, 'listWidgetOutboundRules'):
                self.ui.listWidgetOutboundRules.clear()
                for rule_data in self.outbound_rules:
                    # Tạo custom widget cho mỗi item
                    widget = QWidget()
                    layout = QHBoxLayout(widget)
                    layout.setContentsMargins(8, 4, 8, 4)  # Tăng margin phải để button không bị che
                    layout.setSpacing(10)
                    
                    # Label hiển thị rule
                    label = QLabel(rule_data.get("rule_info", ""))
                    label.setStyleSheet("font-size: 13px; color: #333;")
                    layout.addWidget(label)
                    
                    # Spacer để đẩy button sang phải
                    layout.addStretch()
                    
                    # Button xóa
                    delete_btn = QPushButton("Xóa")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: white;
                            padding: 4px 12px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #c0392b;
                        }
                        QPushButton:pressed {
                            background-color: #a93226;
                        }
                    """)
                    delete_btn.setFixedSize(60, 25)
                    
                    # Kết nối signal xóa
                    rule_info = rule_data.get("rule_info")
                    delete_btn.clicked.connect(lambda checked, r=rule_data: self._delete_outbound_rule(r))
                    
                    layout.addWidget(delete_btn)
                    
                    # Tạo QListWidgetItem và set widget
                    item = QListWidgetItem()
                    widget.setMinimumHeight(35)  # Đảm bảo đủ chiều cao
                    item.setSizeHint(widget.sizeHint())
                    self.ui.listWidgetOutboundRules.addItem(item)
                    self.ui.listWidgetOutboundRules.setItemWidget(item, widget)
        except Exception as e:
            print(f"Error refreshing outbound rules list: {e}")
            import traceback
            traceback.print_exc()

    def _apply_outbound_rule(self, rule_data):
        """Áp dụng một outbound rule vào iptables"""
        try:
            protocol = rule_data.get("protocol")
            port = rule_data.get("port")
            
            if protocol == "icmp":
                cmd = ["sudo", "iptables", "-A", "OUTPUT", "-p", protocol, "-j", "ACCEPT"]
            else:
                if not port:
                    print(f"⚠️ Rule {rule_data.get('rule_info')} thiếu port, bỏ qua")
                    return False
                cmd = ["sudo", "iptables", "-A", "OUTPUT", "-p", protocol, "--dport", str(port), "-j", "ACCEPT"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Đã áp dụng rule: {rule_data.get('rule_info')}")
                return True
            else:
                print(f"⚠️ Không thể áp dụng rule {rule_data.get('rule_info')}: {result.stderr}")
                return False
        except Exception as e:
            print(f"⚠️ Lỗi khi áp dụng rule {rule_data.get('rule_info')}: {e}")
            return False

    def _on_add_outbound_rule(self):
        """Xử lý khi click button thêm outbound rule"""
        try:
            protocol = self.ui.comboBoxProtocol.currentText().lower()
            port = self.ui.lineEditPort.text().strip()
            
            # ICMP không cần port
            if protocol == "icmp":
                rule_info = f"{protocol.upper()}"
                existing_rule = next((r for r in self.outbound_rules if r.get("rule_info") == rule_info), None)
                if existing_rule:
                    QMessageBox.information(None, "Thông báo", "Rule này đã tồn tại!")
                    return
                
                # Thêm rule ICMP
                cmd = ["sudo", "iptables", "-A", "OUTPUT", "-p", protocol, "-j", "ACCEPT"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    rule_data = {
                        "protocol": protocol,
                        "port": None,
                        "rule_info": rule_info
                    }
                    self.outbound_rules.append(rule_data)
                    self._save_outbound_rules()  # Lưu vào file
                    self._refresh_outbound_rules_list()
                    print(f"✅ Đã thêm rule: {protocol.upper()}")
                    self.ui.lineEditPort.clear()
                    self.rules_changed.emit()
                    return
                else:
                    error_msg = result.stderr if result.stderr else "Không thể thêm rule"
                    QMessageBox.warning(None, "Lỗi", f"Không thể thêm rule: {error_msg}")
                    return
            
            # TCP và UDP cần port
            if not port:
                QMessageBox.warning(None, "Lỗi", "Vui lòng nhập port!")
                return
            
            # Validate port
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    raise ValueError("Port phải từ 1 đến 65535")
            except ValueError as e:
                QMessageBox.warning(None, "Lỗi", f"Port không hợp lệ: {e}")
                return
            
            # Kiểm tra rule đã tồn tại chưa
            rule_info = f"{protocol.upper()}:{port_num}"
            existing_rule = next((r for r in self.outbound_rules if r.get("rule_info") == rule_info), None)
            if existing_rule:
                QMessageBox.information(None, "Thông báo", "Rule này đã tồn tại!")
                return
            
            # Thêm rule
            cmd = ["sudo", "iptables", "-A", "OUTPUT", "-p", protocol, "--dport", str(port_num), "-j", "ACCEPT"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Lưu rule vào danh sách
                rule_data = {
                    "protocol": protocol,
                    "port": str(port_num),
                    "rule_info": rule_info
                }
                self.outbound_rules.append(rule_data)
                self._save_outbound_rules()  # Lưu vào file
                self._refresh_outbound_rules_list()
                print(f"✅ Đã thêm rule: {protocol.upper()} port {port_num}")
                # Clear input
                self.ui.lineEditPort.clear()
                self.rules_changed.emit()
            else:
                error_msg = result.stderr if result.stderr else "Không thể thêm rule"
                QMessageBox.warning(None, "Lỗi", f"Không thể thêm rule: {error_msg}")
        except subprocess.TimeoutExpired:
            QMessageBox.warning(None, "Lỗi", "Timeout khi thêm rule!")
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()

    def _delete_outbound_rule(self, rule_data):
        """Xóa outbound rule"""
        try:
            protocol = rule_data.get("protocol")
            port = rule_data.get("port")
            rule_info = rule_data.get("rule_info")
            
            # Xóa rule khỏi iptables
            if protocol == "icmp":
                cmd = ["sudo", "iptables", "-D", "OUTPUT", "-p", protocol, "-j", "ACCEPT"]
            else:
                cmd = ["sudo", "iptables", "-D", "OUTPUT", "-p", protocol, "--dport", port, "-j", "ACCEPT"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Xóa khỏi danh sách
                self.outbound_rules = [r for r in self.outbound_rules if r.get("rule_info") != rule_info]
                self._save_outbound_rules()  # Lưu vào file
                self._refresh_outbound_rules_list()
                print(f"✅ Đã xóa rule: {rule_info}")
                self.rules_changed.emit()
            else:
                error_msg = result.stderr if result.stderr else "Không thể xóa rule"
                QMessageBox.warning(None, "Lỗi", f"Không thể xóa rule: {error_msg}")
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Lỗi khi xóa rule: {str(e)}")
            import traceback
            traceback.print_exc()

    def _handle_outbound_toggle(self, enable):
        """Xử lý khi toggle Outbound Protection"""
        try:
            if enable:
                # Set default policy DROP
                cmd = ["sudo", "iptables", "-P", "OUTPUT", "DROP"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Đã set OUTPUT chain policy thành DROP")
                    
                    # Thêm rule cho phép localhost trước (để service Flask có thể hoạt động)
                    localhost_cmd = ["sudo", "iptables", "-A", "OUTPUT", "-d", "127.0.0.1", "-j", "ACCEPT"]
                    localhost_result = subprocess.run(localhost_cmd, capture_output=True, text=True, timeout=10)
                    if localhost_result.returncode == 0:
                        print("✅ Đã thêm rule cho phép localhost (127.0.0.1)")
                    else:
                        print(f"⚠️ Không thể thêm rule localhost: {localhost_result.stderr}")
                    
                    # Đảm bảo các rule mặc định có trong danh sách
                    default_rules = [
                        {"protocol": "tcp", "port": "80", "rule_info": "TCP:80"},
                        {"protocol": "tcp", "port": "443", "rule_info": "TCP:443"},
                        {"protocol": "udp", "port": "53", "rule_info": "UDP:53"},
                    ]
                    
                    # Thêm các rule mặc định vào danh sách nếu chưa có
                    for default_rule in default_rules:
                        existing = next((r for r in self.outbound_rules if r.get("rule_info") == default_rule.get("rule_info")), None)
                        if not existing:
                            self.outbound_rules.append(default_rule)
                    
                    # Áp dụng lại TẤT CẢ các rules đã lưu (bao gồm cả rules mặc định và rules tùy chỉnh)
                    print(f"📋 Đang áp dụng {len(self.outbound_rules)} outbound rule(s)...")
                    for rule_data in self.outbound_rules:
                        self._apply_outbound_rule(rule_data)
                    
                    # Lưu danh sách rules đã cập nhật vào file
                    self._save_outbound_rules()
                    self._refresh_outbound_rules_list()
                    print(f"✅ Đã bật Outbound Protection với {len(self.outbound_rules)} rule(s)")
                else:
                    print(f"⚠️ Không thể set OUTPUT policy: {result.stderr}")
            else:
                # Set default policy ACCEPT
                cmd = ["sudo", "iptables", "-P", "OUTPUT", "ACCEPT"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Đã set OUTPUT chain policy thành ACCEPT")
                    # Lưu ý: Không xóa các rules khỏi danh sách, chỉ thay đổi policy
                    # Các rules vẫn được giữ lại trong file để có thể áp dụng lại khi bật lại
            
            self.rules_changed.emit()
        except Exception as e:
            print(f"Error handling outbound toggle: {e}")
            import traceback
            traceback.print_exc()


    def _hide_removed_features(self):
        """Ẩn các tính năng đã bị loại bỏ khỏi giao diện"""
        widgets_to_hide = [
            "checkBoxBroadcast",
            "checkBoxIpSpoofing", 
            "checkBoxInvalidPacket",
            "checkBoxOutbound",
            "listWidgetOutboundRules", 
            "buttonAddOutboundRule",
            "comboBoxProtocol",
            "lineEditPort"
        ]
        
        for widget_name in widgets_to_hide:
            if hasattr(self.ui, widget_name):
                widget = getattr(self.ui, widget_name)
                widget.setVisible(False)
