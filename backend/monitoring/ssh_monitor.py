import subprocess

class SSHMonitor:
    def __init__(self, user, host):
        self.user = user
        self.host = host
        self.target = f"{user}@{host}"

    def get_stats(self):
        """
        Get RAM and CPU usage via SSH using `top` (for CPU) and /proc/meminfo (for RAM).
        Returns: (ram_used_mb, ram_total_mb, cpu_percent)
        """
        # CPU: "top -bn2 -d 0.5" gives 2 samples. The first is boot avg, second is current.
        # We grab the last "Cpu(s)" line.
        # RAM: cat /proc/meminfo is robust.
        
        cmd = "top -bn2 -d 0.5 | grep 'Cpu(s)' | tail -1; cat /proc/meminfo"
        
        # Add StrictHostKeyChecking=no to avoid issues when running as root (pkexec)
        # where known_hosts might be empty.
        ssh_cmd = [
            "ssh", 
            "-i", "/home/nqim/.ssh/id_ed25519", # Explicitly use nqim's key
            "-o", "BatchMode=yes", 
            "-o", "ConnectTimeout=4", # Increased timeout for top delay 
            "-o", "StrictHostKeyChecking=no", 
            "-o", "UserKnownHostsFile=/dev/null",
            self.target, 
            cmd
        ]
        
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=6)
            if result.returncode != 0:
                print(f"SSH Error: {result.stderr}")
                return 0, 0, 0
                
            lines = result.stdout.strip().splitlines()
            
            # Parse Data
            cpu_usage = 0
            mem_total = 0
            mem_available = 0
            
            # Line 0 should be Cpu(s)... but verify
            # Example: %Cpu(s):  1.0 us,  1.0 sy,  0.0 ni, 98.0 id, ...
            
            for line in lines:
                if "Cpu(s)" in line:
                     # Parse idle time and subtract from 100
                     # Flexible parsing: find 'id' token and take the number before it
                     try:
                         parts = line.split(',')
                         for p in parts:
                             if 'id' in p:
                                 # p like " 98.0 id"
                                 idle_str = p.strip().split()[0]
                                 cpu_usage = 100.0 - float(idle_str)
                                 break
                     except:
                         pass
                         
                elif line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2: mem_total = int(parts[1]) # kB
                elif line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2: mem_available = int(parts[1]) # kB
            
            # RAM Calculation
            ram_used_mb = (mem_total - mem_available) / 1024
            ram_total_mb = mem_total / 1024
            
            return ram_used_mb, ram_total_mb, cpu_usage

        except Exception as e:
            print(f"SSH Monitor Exception: {e}")
            return 0, 0, 0
