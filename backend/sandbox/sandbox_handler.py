from PyQt6.QtWidgets import QFileDialog, QLineEdit, QMainWindow, QMessageBox
from PyQt6.QtCore import QProcess, pyqtSlot
import shutil
import subprocess
import time
import os
from backend.sandbox.vmware_manager import VMWareManager
from PyQt6.QtWidgets import QInputDialog, QFileDialog, QLineEdit, QMainWindow, QMessageBox
##########################################
# Ensure dotenv is loaded to get config
from dotenv import load_dotenv, set_key
##########################################


class SandboxHandler:
    """Handler for Sandbox tab interactions"""
    
    def __init__(self, ui: QMainWindow):
        self.ui = ui
        self.process = QProcess()
        self.process.finished.connect(self.on_process_finished)
        self.process.errorOccurred.connect(self.on_process_error)
        self.process.readyReadStandardOutput.connect(self.on_ready_read_stdout)
        self.process.readyReadStandardError.connect(self.on_ready_read_stderr)
        
        self.output_buffer = ""
        self.error_buffer = ""
        
        self._setup_connections()
        
    def _setup_connections(self):
        """Connect signals to slots"""
        # Connect Browse button
        if hasattr(self.ui, 'btn_selectFile'):
            self.ui.btn_selectFile.clicked.connect(self.on_browse_clicked)
            
        # Connect Send File button
        if hasattr(self.ui, 'btn_importImage'):
            self.ui.btn_importImage.clicked.connect(self.on_send_clicked)

        # Connect Run Test button
        if hasattr(self.ui, 'btn_run_sandbox'):
            self.ui.btn_run_sandbox.clicked.connect(self.on_run_clicked)
            
        # Connect Stop Test button
        if hasattr(self.ui, 'btn_stop_sandbox'):
            self.ui.btn_stop_sandbox.clicked.connect(self.on_stop_clicked)
            
    def on_browse_clicked(self):
        """Handle Browse button click to select rootfs/image"""
        if hasattr(self.ui, 'lineEdit_imagePath'):
            current_path = self.ui.lineEdit_imagePath.text()
            # Heuristic: If it ends with .vmx, we are in VM mode context probably
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.ui,
            "Select File (Malware or VMX or Image)",
            "",
            "All Files (*);;VMWare Config (*.vmx);;Disk Images (*.img *.qcow2 *.raw)"
        )
        
        if file_path:
            # Update line edit
            if hasattr(self.ui, 'lineEdit_imagePath'):
                self.ui.lineEdit_imagePath.setText(file_path)

    def _get_vmware_config(self):
        """Get VMware config, prompting if necessary"""
        # Load env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(env_path)
        
        vmx = os.getenv("VMWARE_VMX_PATH", "")
        user = os.getenv("VMWARE_USER", "")
        password = os.getenv("VMWARE_PASSWORD", "")
        
        # Check if the file selected in UI is a VMX file
        ui_path = self.ui.lineEdit_imagePath.text().strip()
        if ui_path.endswith(".vmx"):
            vmx = ui_path

        if not vmx:
            # Ask user for VMX
            vmx, ok = QFileDialog.getOpenFileName(self.ui, "Select VMWare .vmx File", "", "VMX Files (*.vmx)")
            if not ok or not vmx:
                return None, None, None
            
            # Save to env?
            # set_key(env_path, "VMWARE_VMX_PATH", vmx) 

        if not user:
             user, ok = QInputDialog.getText(self.ui, "VMWare Auth", "Guest Username (e.g. ubuntu):")
             if not ok: return None, None, None
             set_key(env_path, "VMWARE_USER", user)

        if not password:
             password, ok = QInputDialog.getText(self.ui, "VMWare Auth", "Guest Password:", QLineEdit.EchoMode.Password)
             if not ok: return None, None, None
             set_key(env_path, "VMWARE_PASSWORD", password)

        return vmx, user, password

    def on_send_clicked(self):
        """Handle Send button click. Supports both nspawn (image copy) and VMware (malware copy)."""
        if not hasattr(self.ui, 'lineEdit_imagePath'):
            return
            
        path = self.ui.lineEdit_imagePath.text().strip()
        if not path:
            QMessageBox.warning(self.ui, "Warning", "Please select a file first.")
            return

        # VMWare Mode Detection
        # If the user selected a .vmx file previously, we might store it. 
        # But here 'path' IS the file they want to send/run.
        # If path is NOT a .vmx, but we have a configured VMX, proceed with VMware?
        # Or if path IS a .vmx, we just save it as config?
        
        if path.endswith(".vmx"):
             QMessageBox.information(self.ui, "Config", "VMX file selected. Now select the MALWARE file to analyze.")
             set_key(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), "VMWARE_VMX_PATH", path)
             self.ui.lineEdit_imagePath.clear()
             return

        # If we have VMWare config, assume VMWare mode?
        # Let's ask or heuristic.
        # For now: Try to get VMWare config. If exists, use VMWare.
        # To avoid breaking nspawn, we might need a toggle. 
        # But user asked FOR VMWare.
        
        vmx, user, password = self._get_vmware_config()
        
        if vmx and user and password:
            # VMWare Mode
            try:
                manager = VMWareManager(vmx, user, password)
                
                # 1. Start VM if needed
                # manager.start_vm() # This might take time.
                
                # 2. Copy file
                # Destination in guest: /home/user/filename
                dest_name = os.path.basename(path)
                guest_dest = f"/home/{user}/{dest_name}" # Changed from Desktop
                
                reply = QMessageBox.question(
                    self.ui, 
                    "Confirm Send (VMWare)", 
                    f"Send file to VM?\nHost: {path}\nGuest: {guest_dest}\n\nNote: VM must be powered on.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No: return

                manager.copy_file_to_guest(path, guest_dest)
                QMessageBox.information(self.ui, "Success", f"File sent to VM at {guest_dest}")
                
            except Exception as e:
                QMessageBox.critical(self.ui, "VMWare Error", f"Failed to send file: {e}")
            return

        # Fallback to Original systemd-nspawn Logic
        
        # Sandbox paths
        sandbox_root = "/var/sandbox/ubuntu"
        sandbox_inner_path = "/home/giap/downloads"
        sandbox_host_path = f"{sandbox_root}{sandbox_inner_path}"
        
        # Destination
        dest_name = os.path.basename(path)
        dest_host_file = f"{sandbox_host_path}/{dest_name}"
        
        # Confirmation
        reply = QMessageBox.question(
            self.ui, 
            "Confirm Send", 
            f"Are you sure you want to send:\n{path}\n\nTo Sandbox:\n{dest_host_file}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return

        # Transfer Step
        try:
            is_root = (os.geteuid() == 0)
            def get_cmd(cmd_list):
                return cmd_list if is_root else ["pkexec"] + cmd_list

            # Ensure dir exists
            mkdir_cmd = get_cmd(["mkdir", "-p", sandbox_host_path])
            subprocess.run(mkdir_cmd, check=True)

            # Copy file
            cp_cmd = get_cmd(["cp", path, dest_host_file])
            subprocess.run(cp_cmd, check=True)
            
            # Make executable
            chmod_cmd = get_cmd(["chmod", "+x", dest_host_file])
            subprocess.run(chmod_cmd, check=True)
            
            QMessageBox.information(self.ui, "Success", f"File sent successfully to sandbox!\n\nYou can now click 'Run Test'.")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self.ui, "Transfer Failed", f"Could not copy file:\n{e}")
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"An error occurred:\n{e}")

    def on_run_clicked(self):
        """Handle Run Test button"""
        if not hasattr(self.ui, 'lineEdit_imagePath'):
            return
            
        path = self.ui.lineEdit_imagePath.text().strip()
        if not path:
             QMessageBox.warning(self.ui, "Warning", "Please select and send a file first.")
             return
        
        # Check VMware config
        vmx, user, password = self._get_vmware_config()
        
        if vmx and user and password:
            # VMware Execution
            try:
                manager = VMWareManager(vmx, user, password)
                
                # Revert to snapshot?
                # For safety, ask user or auto-revert.
                # Since user wants "monitor", maybe they don't want to revert immediately if they just sent the file?
                # Usually: Revert -> Copy (again?) -> Run.
                # If we rely on on_send_clicked having done the copy, we can't revert NOW.
                # Correct flow: Revert -> Start -> Copy -> Run.
                # If we revert now, we lose the file we just sent in on_send_clicked if on_send_clicked didn't account for snapshot state.
                # BUT on_send_clicked copied to RUNNING VM.
                # If we don't revert, we run in dirty state.
                
                # User instructions: 
                # 1. Send File (copies to current state)
                # 2. Run Test (executes)
                
                # Execute
                dest_name = os.path.basename(path) if path else "sample"
                guest_dest = f"/home/{user}/{dest_name}" # SAME path as send
                
                # Make executable? vmrun runProgramInGuest might need help.
                # Usually on linux we need `chmod +x`.
                # We can run bash -c "chmod +x ... && ./..."
                
                cmd = f"chmod +x '{guest_dest}' && '{guest_dest}'"
                
                print(f"Running in VM: {cmd}")
                output = manager.run_program("/bin/bash", f"-c \"{cmd}\"")
                
                QMessageBox.information(self.ui, "VMWare Execution Finished", f"Output:\n{output}")
                
            except Exception as e:
                QMessageBox.critical(self.ui, "VMWare Execution Failed", str(e))
                
            return

        # Legacy nspawn logic
             
        # Start Process

        
        sandbox_root = "/var/sandbox/ubuntu"
        sandbox_inner_path = "/home/giap/downloads"
        dest_name = os.path.basename(path)
        
        is_root = (os.geteuid() == 0)
        
        nspawn_base = [
            "systemd-nspawn", 
            "-M", "ubuntu", 
            "-D", sandbox_root, 
            "--", 
            "/bin/bash", "-c", 
            f"cd {sandbox_inner_path} && ./'{dest_name}'"
        ]
        
        if not is_root:
            nspawn_base = ["pkexec"] + nspawn_base

        program = nspawn_base[0]
        arguments = nspawn_base[1:]
        
        self.process.setProgram(program)
        self.process.setArguments(arguments)
        
        # Cleanup existing machine before running
        try:
            # Check if running
            subprocess.run(["machinectl", "status", "ubuntu"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # If success, it's running. Terminate.
            print("Found existing 'ubuntu' machine, terminating...")
            cleanup_cmd = ["machinectl", "terminate", "ubuntu"]
            if not is_root:
                cleanup_cmd = ["pkexec"] + cleanup_cmd
            subprocess.run(cleanup_cmd, check=False)
            time.sleep(1) # Wait for cleanup
        except subprocess.CalledProcessError:
            # Not running
            pass

        
        # Clear buffers
        self.output_buffer = ""
        self.error_buffer = ""
        
        print(f"Starting process: {program} {arguments}")
        self.process.start()
        
        # Update UI
        self.ui.btn_run_sandbox.setEnabled(False)
        self.ui.btn_stop_sandbox.setEnabled(True)
        self.ui.btn_importImage.setEnabled(False) # Disable send while running
        
    def on_stop_clicked(self):
        """Handle Stop Test button"""
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            
            # Explicitly kill the machine to ensure it releases the directory
            is_root = (os.geteuid() == 0)
            kill_cmd = ["machinectl", "terminate", "ubuntu"]
            if not is_root:
                kill_cmd = ["pkexec"] + kill_cmd
                
            QProcess.execute(kill_cmd[0], kill_cmd[1:])

            
    def on_ready_read_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.output_buffer += data
        print(f"[Sandbox STDOUT]: {data}", end="")

    def on_ready_read_stderr(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.error_buffer += data
        print(f"[Sandbox STDERR]: {data}", end="")

    def on_process_finished(self, exit_code, exit_status):
        """Handle process finished"""
        self.ui.btn_run_sandbox.setEnabled(True)
        self.ui.btn_stop_sandbox.setEnabled(False)
        self.ui.btn_importImage.setEnabled(True)
        
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            msg = "Execution finished successfully."
            if self.output_buffer:
                msg += f"\n\nOutput:\n{self.output_buffer}"
            QMessageBox.information(self.ui, "Success", msg)
            
        elif exit_status == QProcess.ExitStatus.CrashExit:
            QMessageBox.warning(self.ui, "Stopped", f"Process was stopped or crashed.\n\nError Output:\n{self.error_buffer}")
        else:
            # Combine exit code with captured stderr for better debugging
            error_msg = f"Execution failed with exit code: {exit_code}\n\n"
            if self.error_buffer:
                error_msg += f"Error Output:\n{self.error_buffer}\n"
            if self.output_buffer:
                error_msg += f"\nStandard Output:\n{self.output_buffer}"
                
            QMessageBox.warning(self.ui, "Failed", error_msg)

    def on_process_error(self, error):
        """Handle process error"""
        self.ui.btn_run_sandbox.setEnabled(True)
        self.ui.btn_stop_sandbox.setEnabled(False)
        self.ui.btn_importImage.setEnabled(True)
        QMessageBox.critical(self.ui, "Error", f"Process error: {self.process.errorString()}")

