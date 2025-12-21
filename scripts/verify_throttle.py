import time
import threading

# Mocking external dependencies
blocked_ips = set()

def block_ip(ip):
    print(f"[MOCK] IP Blocked: {ip}")

def send_notification(title, message):
    print(f"[MOCK] Notification: {title}")

def send_attack_alert(attack_type, src_ip, severity, log_time):
    print(f"[MOCK] Email Sent: {attack_type} from {src_ip}")

class MockLogTab:
    def __init__(self):
        self.last_alert_time = {}
        self.blocked_ips = blocked_ips
    
    def process_log(self, line):
        attack_patterns = {
            "SYN_FLOOD": ("SYN Flood", "High"),
        }
        
        for pattern, (attack_type, severity) in attack_patterns.items():
            if pattern in line:
                print(f"\n[Processing] Log: {line}")
                src_ip = "1.2.3.4" # Simplified
                log_time = "now"
                
                # Logic copied from LogTab
                
                # 📢 Gửi thông báo hệ thống
                send_notification("Title", "Message")
                
                # 🔒 Chặn IP (Luôn chặn để bảo vệ)
                if src_ip and src_ip not in self.blocked_ips:
                    self.blocked_ips.add(src_ip)
                    # threading.Thread(target=block_ip, args=(src_ip,), daemon=True).start()
                    block_ip(src_ip)

                # 📧 Email Alert (Throttled: 1 email / 1 phút)
                current_time = time.time()
                last_alert = self.last_alert_time.get(attack_type, 0)
                
                if current_time - last_alert >= 2: # Reduce to 2 seconds for test
                    # Mock sending email
                    try:
                        send_attack_alert(attack_type, src_ip, severity, log_time)
                    except Exception as e:
                        print("❌ Error sending alert email:", e)
                    
                    # Cập nhật thời gian gửi mail cuối cùng
                    self.last_alert_time[attack_type] = current_time
                else:
                    print(f"⏳ Skipped email for {attack_type} due to rate limit")
                
                return

# Run Test
tester = MockLogTab()

print("Test 1: First Attack (Should send email)")
tester.process_log("IPTables-INPUT: SYN_FLOOD: IN=eth0 SRC=1.2.3.4")

print("\nTest 2: Second Attack immediate (Should SKIP email)")
blocked_ips.clear() # Clear blocked to trigger logic again
tester.process_log("IPTables-INPUT: SYN_FLOOD: IN=eth0 SRC=1.2.3.4")

print("\nWaiting for cooldown (3s)...")
time.sleep(3)

print("\nTest 3: Third Attack after cooldown (Should send email)")
blocked_ips.clear()
tester.process_log("IPTables-INPUT: SYN_FLOOD: IN=eth0 SRC=1.2.3.4")
