import subprocess
import os
from backend.blacklist.blacklist_storage import BlacklistStorage

class BlacklistManager:
    """Quản lý danh sách IP bị chặn sử dụng JSON storage làm source of truth và đồng bộ với iptables"""
    
    def get_blacklist(self):
        """
        Lấy danh sách các IP bị chặn từ JSON file
        
        Returns:
            list: List các dict {'ip': str, 'reason': str, 'timestamp': str}
        """
        # Load from storage (JSON)
        # return list of dicts: {'ip', 'reason', 'timestamp'}
        blocked_ips = BlacklistStorage.load_blocked_ips()
        return blocked_ips

    def block_ip(self, ip, reason="Manual Block"):
        """
        Chặn IP: Thêm vào JSON và thực thi lệnh iptables
        """
        try:
            # 1. Check if already in iptables (optional optimization)
            # 2. Add to iptables
            cmd = ["iptables", "-I", "INPUT", "1", "-s", ip, "-j", "DROP"]
            if os.geteuid() != 0:
                cmd.insert(0, "sudo")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to block IP {ip} in iptables: {result.stderr}")
                # We might still want to add to JSON if we think iptables failed transiently, 
                # but usually we want consistency.
                return False
                
            print(f"🚫 Successfully blocked IP {ip} in iptables")
            
            # 3. Add to Storage
            BlacklistStorage.save_blocked_ip(ip, reason)
            return True
            
        except Exception as e:
            print(f"❌ Exception blocking IP {ip}: {e}")
            return False

    def unblock_ip(self, ip):
        """
        Bỏ chặn IP: Xóa khỏi JSON và xóa rule iptables
        """
        try:
            # 1. Remove from iptables
            # Note: This removes one instance. Loop to remove all? Usually one is enough if we manage it well.
            cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
            if os.geteuid() != 0:
                cmd.insert(0, "sudo")
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                 print(f"✅ Successfully unblocked {ip} in iptables")
            else:
                 print(f"⚠️ Failed to unblock {ip} in iptables (maybe not found?): {result.stderr}")
            
            # 2. Remove from Storage
            # Even if iptables failed (e.g. rule gone), we should clean up JSON
            if BlacklistStorage.remove_blocked_ip(ip):
                print(f"✅ Removed {ip} from JSON storage")
                return True
            else:
                print(f"⚠️ {ip} was not found in JSON storage")
                return True # Treat as success if it's gone
                
        except Exception as e:
            print(f"❌ Exception unblocking {ip}: {e}")
            return False
