"""
Notifications module - email và system notifications
"""

from .mailer import send_attack_alert, send_malware_alert, send_performance_alert
from .notification import send_notification

__all__ = [
    'send_attack_alert',
    'send_malware_alert',
    'send_performance_alert',
    'send_notification',
]

