import json
import os
from datetime import datetime

BLOCKED_IPS_FILE = os.path.join(os.path.dirname(__file__), "blocked_ips.json")

class BlacklistStorage:
    """Manages reading and writing blocked IPs to a JSON file."""

    @staticmethod
    def load_blocked_ips():
        """
        Loads blocked IPs from the JSON file.
        Returns:
            list: List of dicts containing ip, date, reason.
        """
        if not os.path.exists(BLOCKED_IPS_FILE):
            return []
        
        try:
            with open(BLOCKED_IPS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading blocked IPs from JSON: {e}")
            return []

    @staticmethod
    def save_blocked_ip(ip, reason="Manual Block", timestamp=None):
        """
        Saves a blocked IP to the JSON file.
        """
        blocked_ips = BlacklistStorage.load_blocked_ips()
        
        # Check if already exists
        for entry in blocked_ips:
            if entry.get('ip') == ip:
                return # Already exists
        
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        blocked_ips.append({
            'ip': ip,
            'reason': reason,
            'timestamp': timestamp
        })
        
        try:
            with open(BLOCKED_IPS_FILE, 'w') as f:
                json.dump(blocked_ips, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving blocked IP to JSON: {e}")

    @staticmethod
    def remove_blocked_ip(ip):
        """
        Removes a blocked IP from the JSON file.
        """
        blocked_ips = BlacklistStorage.load_blocked_ips()
        
        new_list = [entry for entry in blocked_ips if entry.get('ip') != ip]
        
        if len(new_list) != len(blocked_ips):
            try:
                with open(BLOCKED_IPS_FILE, 'w') as f:
                    json.dump(new_list, f, indent=4)
                return True
            except Exception as e:
                print(f"❌ Error removing blocked IP from JSON: {e}")
                return False
        return False
