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
        # Command to fetch all stats in one go
        # 5. Network (proc/net/dev)
        cmd = (
            "top -bn2 -d 0.5 | grep 'Cpu(s)' | tail -1; "
            "echo '---SPLIT---'; "
            "cat /proc/meminfo; "
            "echo '---SPLIT---'; "
            "df -B1 --output=avail / | tail -1; "
            "echo '---SPLIT---'; "
            "systemctl list-units --type=service --state=running --no-pager --no-legend | wc -l; "
            "echo '---SPLIT---'; "
            "cat /proc/net/dev"
        )
        
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
                return 0, 0, 0, 0, 0, 0, 0
                
            # Parse Sections
            parts = result.stdout.strip().split("---SPLIT---")
            
            # Default values
            cpu_usage = 0
            mem_total = 0
            mem_available = 0
            disk_free_gb = 0
            service_count = 0
            
            # Section 1: CPU
            if len(parts) > 0:
                cpu_lines = parts[0].strip().splitlines()
                for line in cpu_lines:
                    if "Cpu(s)" in line:
                         try:
                             line_parts = line.split(',')
                             for p in line_parts:
                                 if 'id' in p:
                                     # p like " 98.0 id"
                                     idle_str = p.strip().split()[0]
                                     cpu_usage = 100.0 - float(idle_str)
                                     break
                         except:
                             pass
            
            # Section 2: RAM
            if len(parts) > 1:
                mem_lines = parts[1].strip().splitlines()
                for line in mem_lines:
                    if line.startswith("MemTotal:"):
                        p = line.split()
                        if len(p) >= 2: mem_total = int(p[1]) # kB
                    elif line.startswith("MemAvailable:"):
                        p = line.split()
                        if len(p) >= 2: mem_available = int(p[1]) # kB

            # Section 3: Disk
            if len(parts) > 2:
                try:
                    disk_bytes = int(parts[2].strip())
                    disk_free_gb = disk_bytes / (1024**3)
                except:
                    pass

            # Section 4: Services
            if len(parts) > 3:
                try:
                    service_count = int(parts[3].strip())
                except:
                    pass
            
            # Section 5: Network Traffic
            rx_bytes = 0
            tx_bytes = 0
            if len(parts) > 4:
                net_lines = parts[4].strip().splitlines()
                # Skip headers (usually first 2 lines)
                for line in net_lines:
                    if ':' in line:
                         # Clean line: replace : with space to handle "eth0:123" case
                         clean_line = line.replace(':', ' ')
                         p = clean_line.split()
                         # p[0] is interface name
                         interface = p[0]
                         if interface == 'lo': 
                             continue
                         
                         # p[1] is RX bytes, p[9] is TX bytes (based on standard output)
                         if len(p) >= 10:
                             try:
                                 rx_bytes += int(p[1])
                                 tx_bytes += int(p[9])
                             except:
                                 pass
            
            # RAM Calculation
            ram_used_mb = (mem_total - mem_available) / 1024
            ram_total_mb = mem_total / 1024
            
            return ram_used_mb, ram_total_mb, cpu_usage, disk_free_gb, service_count, rx_bytes, tx_bytes

        except Exception as e:
            print(f"SSH Monitor Exception: {e}")
            return 0, 0, 0, 0, 0, 0, 0
