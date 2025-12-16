from PyQt6.QtWidgets import QMainWindow, QMessageBox
import os
from dotenv import load_dotenv, set_key
from backend.notifications.mailer import send_test_email_sync
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class EmailTestWorker(QObject):
    """Worker thread để gửi email test mà không bị treo UI"""
    finished = pyqtSignal(bool, str) # success, message

    def __init__(self, sender, receiver, password):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.password = password

    def run(self):
        try:
            send_test_email_sync(self.sender, self.receiver, self.password)
            self.finished.emit(True, "Email verification successful!")
        except Exception as e:
            self.finished.emit(False, str(e))

class SettingsHandler:
    """Handler for Settings tab interactions"""
    
    def __init__(self, ui: QMainWindow):
        self.ui = ui
        # Path to backend/.env
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir) # up to backend/
        self.env_path = os.path.join(backend_dir, ".env")
        
        # Load existing values
        self._load_current_settings()
        self._setup_connections()
        
    def _load_current_settings(self):
        """Load current settings from .env and populate UI"""
        load_dotenv(self.env_path)
        
        sender = os.getenv("SENDER_EMAIL", "")
        receiver = os.getenv("RECEIVER_EMAIL", "")
        password = os.getenv("PASSWORD_EMAIL", "")
        
        if hasattr(self.ui, 'lineEditSender'):
            self.ui.lineEditSender.setText(sender)
            
        if hasattr(self.ui, 'lineEditReceiver'):
            self.ui.lineEditReceiver.setText(receiver)
            
        if hasattr(self.ui, 'lineEditPassword'):
            self.ui.lineEditPassword.setText(password)

        
    def _setup_connections(self):
        """Connect signals to slots"""
        if hasattr(self.ui, 'btnSaveSettings'):
            self.ui.btnSaveSettings.clicked.connect(self.on_save_clicked)
            
    def on_save_clicked(self):
        """Handle Save Configuration button click"""
        # Get values from UI
        sender = ""
        if hasattr(self.ui, 'lineEditSender'):
            sender = self.ui.lineEditSender.text().strip()
            
        receiver = ""
        if hasattr(self.ui, 'lineEditReceiver'):
            receiver = self.ui.lineEditReceiver.text().strip()
            
        password = ""
        if hasattr(self.ui, 'lineEditPassword'):
            password = self.ui.lineEditPassword.text().strip()
            
        # Validation
        if not sender or not receiver or not password:
            QMessageBox.warning(self.ui, "Validation Error", "All fields are required!")
            return

        try:
            # Create .env if not exists
            if not os.path.exists(self.env_path):
                with open(self.env_path, 'w') as f:
                    f.write("")
            
            # Save to .env file
            set_key(self.env_path, "SENDER_EMAIL", sender)
            set_key(self.env_path, "RECEIVER_EMAIL", receiver)
            set_key(self.env_path, "PASSWORD_EMAIL", password)
            
            # Update current environment variables immediately
            os.environ["SENDER_EMAIL"] = sender
            os.environ["RECEIVER_EMAIL"] = receiver
            os.environ["PASSWORD_EMAIL"] = password
            
            # Ensure the file is writable by everyone (so non-root user can edit)
            try:
                os.chmod(self.env_path, 0o666)
            except Exception as e:
                print(f"Warning: Could not set permissions on .env: {e}")

            # START THREADED VERIFICATION
            self._start_email_verification(sender, receiver, password)
            
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Could not save settings: {str(e)}")

    def _start_email_verification(self, sender, receiver, password):
        """Start the email verification in a separate thread"""
        
        # Disable button to prevent double click
        if hasattr(self.ui, 'btnSaveSettings'):
            self.ui.btnSaveSettings.setEnabled(False)
            self.ui.btnSaveSettings.setText("Verifying...")

        # Create thread and worker
        self.thread = QThread()
        self.worker = EmailTestWorker(sender, receiver, password)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_verification_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Start thread
        self.thread.start()

    def on_verification_finished(self, success, message):
        """Handle the result of email verification"""
        
        # Restore button state
        if hasattr(self.ui, 'btnSaveSettings'):
            self.ui.btnSaveSettings.setEnabled(True)
            self.ui.btnSaveSettings.setText("Save Configuration")

        if success:
             QMessageBox.information(
                self.ui, 
                "Success", 
                "Email configuration saved and VERIFIED successfully!\n"
                "A test email has been sent to the receiver address.\n"
                "The system will use the new settings immediately."
            )
        else:
            # Failure case
            if "Authentication failed" in message or "Username and Password not accepted" in message:
                 QMessageBox.warning(
                    self.ui, 
                    "Saved but Verification Failed", 
                    f"Settings were saved, BUT email verification failed.\n\n"
                    f"Error: Authentication failed.\n"
                    f"Please check your App Password and Email Address."
                )
            else:
                QMessageBox.warning(
                    self.ui, 
                    "Saved but Verification Failed", 
                    f"Settings were saved, BUT email verification failed.\n\n"
                    f"Error: {message}"
                )
