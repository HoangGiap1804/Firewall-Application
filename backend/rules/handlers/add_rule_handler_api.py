"""Handler xử lý logic thêm rule mới sử dụng API Service"""

from PyQt6.QtWidgets import QMessageBox
from service.api_client import get_client


class AddRuleHandlerAPI:
    """Xử lý logic thêm rule mới vào iptables sử dụng API"""
    
    PROTOCOL_MAP = {"TCP": "tcp", "UDP": "udp", "ICMP": "icmp"}
    
    def __init__(self, ui):
        self.ui = ui
        self.client = get_client()


    
    def _get_widget_text(self, widget_name, default=""):
        """Lấy text từ widget nếu tồn tại"""
        widget = getattr(self.ui, widget_name, None)
        return widget.text().strip() if widget else default
    
    def _get_combo_text(self, widget_name, default=""):
        """Lấy text từ combobox nếu tồn tại"""
        widget = getattr(self.ui, widget_name, None)
        return widget.currentText().strip() if widget else default
    
    def _normalize_protocol(self, protocol):
        """Chuẩn hóa protocol về lowercase"""
        return self.PROTOCOL_MAP.get(protocol.upper(), protocol.lower())
    
    def _normalize_action(self, action):
        """Chuẩn hóa action về uppercase"""
        return action.upper() if action else ""
    
    def on_add_rule_clicked(self, refresh_callback):
        """Lấy dữ liệu từ tab Add Rule và gọi API để thêm rule"""
        data = {
            "state": self._get_widget_text("editState"),
            "interface": self._get_widget_text("editInterface"),
            "protocol": self._normalize_protocol(self._get_combo_text("comboProtocol")),
            "action": self._normalize_action(self._get_combo_text("comboAction")),
            "port": self._get_widget_text("editPort"),
            "ip": self._get_widget_text("editSource"),
            "dst": self._get_widget_text("editDestination"),
            "chain": "INPUT"
        }
        
        self._call_add_rule_api(data, refresh_callback)
    
    def on_add_rule_in_frame_clicked(self, refresh_callback):
        """Lấy dữ liệu từ frameAddRule và gọi API để thêm rule"""
        # Get values from UI
        interface = self._get_widget_text("editAddRuleInterface")
        protocol = self._get_combo_text("comboAddRuleProtocol")
        action = self._get_combo_text("comboAddRuleAction")
        chain = self._get_widget_text("editAddRuleChain") or "INPUT"
        
        # Validate required fields
        protocol_normalized = self._normalize_protocol(protocol)
        action_normalized = self._normalize_action(action)
        if not protocol_normalized or not action_normalized:
            QMessageBox.warning(None, "Lỗi", "Protocol và Action là bắt buộc!")
            return
        
        data = {
            "interface": self._get_widget_text("editAddRuleInterface"),
            "protocol": protocol_normalized,
            "action": action_normalized,
            "detail": self._get_widget_text("editAddRuleDetail"),
            "ip": self._get_widget_text("editAddRuleSource"),
            "dst": self._get_widget_text("editAddRuleDestination"),
            "chain": chain
        }
        
        print(f"DTO Payload from Handler: {data}")
        self._call_add_rule_api(data, refresh_callback, clear_form=True)
    
    def _call_add_rule_api(self, data, refresh_callback, clear_form=False):
        """Gọi API để thêm rule và xử lý response"""
        try:
            result = self.client.add_rule(**data)
            print(f"✅ {result.get('message', 'Đã thêm rule')}")
            
            if clear_form:
                self._clear_add_rule_form()
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Lỗi khi thêm rule: {error_msg}")
            QMessageBox.warning(None, "Lỗi", f"Không thể thêm rule: {error_msg}")
        
        refresh_callback()
    
    def _clear_add_rule_form(self):
        """Xóa nội dung form sau khi thêm rule thành công"""
        fields = [
            "editAddRuleInterface",
            "editAddRuleDetail", "editAddRuleSource", "editAddRuleDestination",
            "editAddRuleChain"
        ]
        for field in fields:
            widget = getattr(self.ui, field, None)
            if widget:
                widget.clear()

