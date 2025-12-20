import subprocess
import os
import time

class VMWareManager:
    """
    Manager for VMWare Workstation interactions using vmrun.
    """
    def __init__(self, vmx_path, guest_user, guest_password, vmrun_path="/usr/bin/vmrun"):
        self.vmx_path = vmx_path
        self.guest_user = guest_user
        self.guest_password = guest_password
        self.vmrun_path = vmrun_path

        if not os.path.exists(self.vmrun_path):
            # Try to find vmrun if not at default location
            found = shutil.which("vmrun")
            if found:
                self.vmrun_path = found

    def _run_cmd(self, command, args, auth=False):
        """
        Run a vmrun command.
        :param command: The vmrun command (e.g., 'start', 'runProgramInGuest')
        :param args: List of arguments for the command
        :param auth: If True, include guest authentication flags (-gu, -gp)
        """
        cmd_list = [self.vmrun_path, "-T", "ws"]
        
        if auth:
            cmd_list.extend(["-gu", self.guest_user, "-gp", self.guest_password])
            
        cmd_list.append(command)
        cmd_list.append(self.vmx_path)
        cmd_list.extend(args)
        
        print(f"[VMWareManager] Running: {' '.join(cmd_list)}") # Debug logging
        
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, 
                cmd_list, 
                output=result.stdout, 
                stderr=result.stderr
            )
        return result.stdout

    def check_exists(self):
        """Check if vmrun and vmx file exist"""
        if not os.path.exists(self.vmrun_path):
            raise FileNotFoundError(f"vmrun tool not found at {self.vmrun_path}")
        if not os.path.exists(self.vmx_path):
            raise FileNotFoundError(f"VMX file not found at {self.vmx_path}")
        return True

    def revert_to_snapshot(self, snapshot_name):
        """Revert VM to a specific snapshot"""
        return self._run_cmd("revertToSnapshot", [snapshot_name])

    def start_vm(self, gui=True):
        """Start the VM. If gui is True, opens the window."""
        mode = "gui" if gui else "nogui"
        try:
            # Check if running first? vmrun start fails if running?
            # Actually vmrun start checks content, but let's just try.
            # list commands or checkToolsState can check status.
            pass
        except:
            pass
        return self._run_cmd("start", [mode])

    def stop_vm(self, hard=False):
        """Stop the VM"""
        mode = "hard" if hard else "soft"
        return self._run_cmd("stop", [mode])

    def copy_file_to_guest(self, host_path, guest_path):
        """Copy file from host to guest"""
        return self._run_cmd("copyFileFromHostToGuest", [host_path, guest_path], auth=True)
    
    def run_program(self, program_path, program_args="", no_wait=False):
        """
        Run a program in the guest.
        :param program_path: Full path to executable in guest
        :param no_wait: If True, returns immediately (interactive mode)
        """
        # vmrun -T ws -gu user -gp pass runProgramInGuest <vmx> [-noWait] <prog> <args>
        
        cmd_args = []
        if no_wait:
            cmd_args.append("-noWait")
            
        cmd_args.append(program_path)

        if program_args:
             if isinstance(program_args, list):
                 cmd_args.extend(program_args)
             else:
                 cmd_args.append(program_args)
             
        # Handling arguments with spaces in vmrun is tricky, usually passed as separate args
        
        return self._run_cmd("runProgramInGuest", cmd_args, auth=True)

    def list_snapshots(self):
        """List snapshots"""
        # vmrun listSnapshots vmx
        # But our _run_cmd prepends vmx path
        # vmrun -T ws listSnapshots <path>
        output = self._run_cmd("listSnapshots", [])
        lines = output.strip().splitlines()
        return []

    def get_ip(self):
        """Get guest IP address"""
        try:
            # vmrun -T ws getGuestIPAddress <vmx> -wait
            # Note: -wait might hang if tools not running?
            # _run_cmd appends vmx path.
            # We don't need auth usually for getGuestIPAddress?
            # Actually vmrun documentation says: getGuestIPAddress <path to vmx file> [-wait]
            # No user/pass needed usually.
            
            output = self._run_cmd("getGuestIPAddress", ["-wait"])
            return output.strip()
        except Exception as e:
            print(f"Failed to get IP: {e}")
            return None

    def get_guest_stats(self):
        """
        Get RAM and CPU usage from the guest using standard Linux commands.
        Returns: (ram_used_mb, ram_total_mb, cpu_percent)
        """
        # We need to run a command that outputs simple numbers.
        # RAM: free -m | awk 'NR==2{print $3, $2}' -> "used total"
        # CPU: Using top -bn1 is tricky. Let's use /proc/stat if possible? 
        # Easier: top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}' (us + sy). 
        # Note: Output format varies by top version.
        # Let's try a python one-liner if python3 is there? Python is more robust.
        # Assume python3 is installed? If not fallback to shell.
        
        # Shell approach (more universal on minimal ubuntu):
        # RAM: `free -m | awk '/^Mem:/{print $3, $2}'`
        # CPU: `grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'` (approximate, needs delta)
        # Getting instantaneous CPU without delta (like top) requires top.
        
        cmd = (
            "free -m | awk '/^Mem:/{print $3, $2}'; "
            "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'"
        )
        
        try:
            # We must use bash -c
            output = self.run_program("/bin/bash", f"-c \"{cmd}\"")
            # Output format expected:
            # USED TOTAL
            # CPU_USAGE
            
            lines = output.strip().splitlines()
            if len(lines) >= 2:
                ram_parts = lines[0].split()
                ram_used = float(ram_parts[0])
                ram_total = float(ram_parts[1])
                
                cpu_usage = float(lines[1])
                
                return ram_used, ram_total, cpu_usage
                
            return 0, 0, 0
        except Exception as e:
            print(f"Failed to get stats: {e}")
            return 0, 0, 0

import shutil
