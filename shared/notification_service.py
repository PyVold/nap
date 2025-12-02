"""
Email Notification Service

Handles sending email notifications using SMTP settings from system configuration.
Supports multiple recipients and various notification types.
"""

import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email notifications"""

    def __init__(self):
        self.smtp_server = None
        self.smtp_port = 587
        self.smtp_username = None
        self.smtp_password = None
        self.smtp_enabled = False
        self.use_localhost = False  # Use local mail server (no auth)
        self.default_recipients = []

    def load_smtp_settings(self, db: Session):
        """Load SMTP settings from database"""
        try:
            from db_models import SystemConfigDB

            # Get system settings
            config = db.query(SystemConfigDB).filter(
                SystemConfigDB.key == "system_settings"
            ).first()

            if config:
                settings = json.loads(config.value)
                self.smtp_enabled = settings.get('smtpEnabled', False)
                self.use_localhost = settings.get('useLocalhost', False)
                # Use host.docker.internal for Docker environments to reach host's mail server
                default_localhost = 'host.docker.internal' if self.use_localhost else None
                self.smtp_server = settings.get('smtpServer', default_localhost)
                self.smtp_port = settings.get('smtpPort', 25 if self.use_localhost else 587)
                self.smtp_username = settings.get('smtpUsername')
                self.smtp_password = settings.get('smtpPassword')

                logger.info(f"SMTP settings loaded: enabled={self.smtp_enabled}, localhost={self.use_localhost}, server={self.smtp_server}")
            else:
                logger.warning("No SMTP settings found in database")

            # Get notification settings for default recipients
            notif_config = db.query(SystemConfigDB).filter(
                SystemConfigDB.key == "notification_settings"
            ).first()

            if notif_config:
                notif_settings = json.loads(notif_config.value)
                self.default_recipients = notif_settings.get('emailRecipients', [])
                logger.info(f"Default recipients loaded: {len(self.default_recipients)}")

        except Exception as e:
            logger.error(f"Error loading SMTP settings: {e}")
            self.smtp_enabled = False

    def send_email(
        self,
        subject: str,
        body: str,
        recipients: Optional[List[str]] = None,
        html: bool = False,
        db: Optional[Session] = None
    ) -> Dict:
        """
        Send an email notification

        Args:
            subject: Email subject
            body: Email body (plain text or HTML)
            recipients: List of recipient email addresses (uses default if None)
            html: If True, body is HTML. If False, plain text.
            db: Database session (optional, used to reload settings)

        Returns:
            Dict with success status and message
        """
        # Reload settings if database session provided
        if db:
            self.load_smtp_settings(db)

        # Check if SMTP is enabled
        if not self.smtp_enabled:
            logger.warning("SMTP is not enabled, cannot send email")
            return {
                "success": False,
                "message": "SMTP is not enabled in system settings"
            }

        # Validate SMTP configuration
        # For localhost mode, we don't need username/password
        if not self.use_localhost:
            if not self.smtp_server or not self.smtp_username:
                logger.error("SMTP configuration incomplete")
                return {
                    "success": False,
                    "message": "SMTP configuration is incomplete (missing server or username)"
                }
        elif not self.smtp_server:
            # Localhost mode but no server specified, default to host.docker.internal for Docker
            self.smtp_server = 'host.docker.internal'
            self.smtp_port = 25

        # Use default recipients if none provided
        if not recipients:
            recipients = self.default_recipients

        if not recipients:
            logger.warning("No recipients specified and no default recipients configured")
            return {
                "success": False,
                "message": "No recipients specified"
            }

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username if self.smtp_username else 'no-reply@audit.tool'
            msg['To'] = ', '.join(recipients)
            msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Attach body
            if html:
                part = MIMEText(body, 'html')
            else:
                part = MIMEText(body, 'plain')
            msg.attach(part)

            # Connect to SMTP server and send
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port} (localhost={self.use_localhost})")

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.ehlo()

                # For localhost, skip TLS and authentication
                if not self.use_localhost:
                    # Try STARTTLS if supported
                    if server.has_extn('STARTTLS'):
                        logger.info("Starting TLS...")
                        server.starttls()
                        server.ehlo()

                    # Login if credentials provided
                    if self.smtp_password:
                        logger.info(f"Logging in as: {self.smtp_username}")
                        server.login(self.smtp_username, self.smtp_password)
                else:
                    logger.info("Using local mail server (no authentication)")

                # Send email
                logger.info(f"Sending email to: {recipients}")
                server.send_message(msg)

            logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")

            return {
                "success": True,
                "message": f"Email sent to {len(recipients)} recipient(s)",
                "recipients": recipients
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                "success": False,
                "message": f"SMTP authentication failed: {str(e)}"
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "success": False,
                "message": f"SMTP error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }

    def send_backup_failure_notification(
        self,
        device_hostname: str,
        error_message: str,
        db: Session
    ):
        """Send notification about backup failure"""
        subject = f"[NAP] Backup Failed: {device_hostname}"

        body = f"""
Configuration Backup Failure

Device: {device_hostname}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Error: {error_message}

Please check the device connectivity and credentials.

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_quota_exceeded_notification(
        self,
        quota_type: str,
        current: int,
        max_allowed: int,
        db: Session
    ):
        """Send notification about quota being exceeded"""
        subject = f"[NAP] Quota Exceeded: {quota_type.title()}"

        body = f"""
Quota Limit Exceeded

Quota Type: {quota_type.title()}
Current Usage: {current}
Maximum Allowed: {max_allowed}

Please upgrade your license or reduce usage.

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_license_expiry_notification(
        self,
        days_until_expiry: int,
        license_tier: str,
        db: Session
    ):
        """Send notification about upcoming license expiry"""
        subject = f"[NAP] License Expiring in {days_until_expiry} Days"

        body = f"""
License Expiry Warning

Your {license_tier.title()} license will expire in {days_until_expiry} days.

Please contact sales to renew your license:
sales@ipdevops.com

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_audit_failure_notification(
        self,
        device_hostname: str,
        audit_name: str,
        error_message: str,
        db: Session
    ):
        """Send notification about audit failure"""
        subject = f"[NAP] Audit Failed: {device_hostname}"

        body = f"""
Audit Execution Failure

Device: {device_hostname}
Audit: {audit_name}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Error: {error_message}

Please check the device connectivity and audit configuration.

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_test_email(self, recipient: str, db: Session):
        """Send a test email to verify SMTP configuration"""
        subject = "[NAP] Test Email - SMTP Configuration"

        body = f"""
SMTP Configuration Test

This is a test email from Network Audit Platform.

If you received this email, your SMTP configuration is working correctly!

Sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

---
Network Audit Platform
"""

        return self.send_email(subject, body, recipients=[recipient], db=db)

    def send_health_check_failure_notification(
        self,
        device_hostname: str,
        status: str,
        details: str,
        db: Session
    ):
        """Send notification about health check failure"""
        subject = f"[NAP] Health Check Failed: {device_hostname}"

        body = f"""
Health Check Failure

Device: {device_hostname}
Status: {status.upper()}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Details: {details}

Please check the device connectivity and network configuration.

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_device_offline_notification(
        self,
        device_hostname: str,
        last_seen: str,
        consecutive_failures: int,
        db: Session
    ):
        """Send notification when device goes offline"""
        subject = f"[NAP] Device Offline: {device_hostname}"

        body = f"""
Device Offline Alert

Device: {device_hostname}
Status: OFFLINE
Last Seen: {last_seen}
Consecutive Failures: {consecutive_failures}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

The device has been unreachable after multiple connection attempts.
Please check:
- Network connectivity
- Device power status
- Firewall rules
- Device credentials

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)

    def send_compliance_issue_notification(
        self,
        device_hostname: str,
        compliance_score: float,
        threshold: float,
        critical_findings: int,
        db: Session
    ):
        """Send notification about compliance issues"""
        subject = f"[NAP] Compliance Alert: {device_hostname} ({compliance_score:.1f}%)"

        body = f"""
Compliance Issue Detected

Device: {device_hostname}
Compliance Score: {compliance_score:.1f}%
Alert Threshold: {threshold:.1f}%
Critical Findings: {critical_findings}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

The device compliance score has fallen below the configured threshold.
Please review the audit findings and take corrective action.

This is an automated notification from Network Audit Platform.
"""

        return self.send_email(subject, body, db=db)


# Singleton instance
notification_service = NotificationService()
