from PyQt6.QtWidgets import QFileDialog, QLineEdit, QMainWindow, QMessageBox
from PyQt6.QtCore import QProcess, pyqtSlot
import os
import subprocess
import time


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
        file_path, _ = QFileDialog.getOpenFileName(
            self.ui,
            "Select Rootfs or Image",
            "",
            "All Files (*);;Disk Images (*.img *.qcow2 *.raw);;Rootfs Directories (*)"
        )
        
        if file_path:
            # Update line edit
            if hasattr(self.ui, 'lineEdit_imagePath'):
                self.ui.lineEdit_imagePath.setText(file_path)

    def on_send_clicked(self):
        """Handle Send button click to copy file/dir to /var/lib/machines"""
        if not hasattr(self.ui, 'lineEdit_imagePath'):
            return
            
        path = self.ui.lineEdit_imagePath.text().strip()
        if not path:
            QMessageBox.warning(self.ui, "Warning", "Please select a file first.")
            return


        
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

