"""
API Client để giao tiếp với Firewall Service
"""

import requests
import json
from typing import List, Dict, Optional

SERVICE_URL = "http://127.0.0.1:5000/api"


class FirewallServiceClient:
    """Client để gọi API của Firewall Service"""
    
    def __init__(self, base_url: str = SERVICE_URL):
        self.base_url = base_url
        self.timeout = 5
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Thực hiện HTTP request"""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Không thể kết nối đến Firewall Service. Hãy đảm bảo service đang chạy.")
        except requests.exceptions.Timeout:
            raise TimeoutError("Request timeout. Service có thể đang quá tải.")
        except requests.exceptions.HTTPError as e:
            error_msg = "Lỗi HTTP"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", error_msg)
            except:
                pass
            raise Exception(f"{error_msg}: {e}")
    
    def health_check(self) -> bool:
        """Kiểm tra service có hoạt động không"""
        try:
            result = self._request("GET", "health")
            return result.get("status") == "ok"
        except:
            return False
    
    def start_monitoring(self) -> Dict:
        """Bắt đầu monitoring"""
        return self._request("POST", "monitoring/start")
    
    def stop_monitoring(self) -> Dict:
        """Dừng monitoring"""
        return self._request("POST", "monitoring/stop")
    
    def get_monitoring_data(self) -> Dict:
        """Lấy dữ liệu monitoring"""
        return self._request("GET", "monitoring/data")
    
    def list_rules(self) -> List[Dict]:
        """Lấy danh sách rules"""
        result = self._request("GET", "rules/list")
        return result.get("rules", [])
    
    def add_rule(self, ip: str = "", protocol: str = "", 
                 action: str = "", interface: str = "", in_interface: str = "", 
                 out_interface: str = "", detail: str = "", 
                 chain: str = "OUTPUT", dst: str = "") -> Dict:
        """Thêm rule mới"""
        data = {
            "ip": ip,
            "protocol": protocol,
            "action": action,
            "interface": interface,
            "in_interface": in_interface,
            "out_interface": out_interface,
            "detail": detail,
            "dst": dst
        }
        # Chỉ thêm chain nếu có giá trị
        if chain and isinstance(chain, str) and chain.strip():
            data["chain"] = chain.strip()
        
        return self._request("POST", "rules/add", data=data)
    
    def delete_rule(self, num: str, chain: str = "INPUT") -> Dict:
        """Xóa rule"""
        return self._request("POST", "rules/delete", data={"num": num, "chain": chain})
    
    def delete_many_rules(self, nums: List[str]) -> Dict:
        """Xóa nhiều rules"""
        return self._request("POST", "rules/delete-many", data={"nums": nums})
    
    def search_rules(self, query: str = "") -> List[Dict]:
        """Tìm kiếm rules"""
        result = self._request("GET", "rules/search", params={"q": query})
        return result.get("rules", [])


# Singleton instance
_client_instance = None

def get_client() -> FirewallServiceClient:
    """Lấy singleton instance của client"""
    global _client_instance
    if _client_instance is None:
        _client_instance = FirewallServiceClient()
    return _client_instance

