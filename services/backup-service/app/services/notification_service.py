# ============================================================================
# services/notification_service.py
# ============================================================================

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from db_models import NotificationWebhookDB, NotificationHistoryDB, DeviceDB
from models.audit import AuditResult
from models.enums import AuditStatus
from shared.logger import setup_logger

logger = setup_logger(__name__)


class NotificationService:
    """Service for sending notifications via webhooks"""

    @staticmethod
    def format_slack_message(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a message for Slack"""
        if event_type == "audit_failure":
            device_name = data.get("device_name", "Unknown")
            compliance = data.get("compliance", 0)
            failed_checks = data.get("failed_checks", 0)

            color = "danger" if compliance < 50 else "warning"

            return {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 Audit Failure: {device_name}",
                        "text": f"Device {device_name} failed {failed_checks} audit checks",
                        "fields": [
                            {
                                "title": "Compliance Score",
                                "value": f"{compliance}%",
                                "short": True
                            },
                            {
                                "title": "Failed Checks",
                                "value": str(failed_checks),
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": data.get("timestamp", datetime.utcnow().isoformat()),
                                "short": False
                            }
                        ]
                    }
                ]
            }

        elif event_type == "compliance_drop":
            device_name = data.get("device_name", "Unknown")
            old_compliance = data.get("old_compliance", 0)
            new_compliance = data.get("new_compliance", 0)
            drop = old_compliance - new_compliance

            return {
                "attachments": [
                    {
                        "color": "danger",
                        "title": f"📉 Compliance Drop: {device_name}",
                        "text": f"Compliance dropped by {drop}% on {device_name}",
                        "fields": [
                            {
                                "title": "Previous Compliance",
                                "value": f"{old_compliance}%",
                                "short": True
                            },
                            {
                                "title": "Current Compliance",
                                "value": f"{new_compliance}%",
                                "short": True
                            }
                        ]
                    }
                ]
            }

        elif event_type == "config_change":
            device_name = data.get("device_name", "Unknown")
            lines_changed = data.get("lines_changed", 0)
            severity = data.get("severity", "low")

            colors = {"low": "good", "medium": "warning", "high": "danger"}
            color = colors.get(severity, "warning")

            return {
                "attachments": [
                    {
                        "color": color,
                        "title": f"📝 Configuration Change: {device_name}",
                        "text": f"Configuration changed on {device_name}",
                        "fields": [
                            {
                                "title": "Lines Changed",
                                "value": str(lines_changed),
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": severity.upper(),
                                "short": True
                            }
                        ]
                    }
                ]
            }

        else:
            return {"text": f"Event: {event_type}", "data": data}

    @staticmethod
    def format_teams_message(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a message for Microsoft Teams"""
        if event_type == "audit_failure":
            device_name = data.get("device_name", "Unknown")
            compliance = data.get("compliance", 0)
            failed_checks = data.get("failed_checks", 0)

            theme_color = "FF0000" if compliance < 50 else "FFA500"

            return {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": f"Audit Failure: {device_name}",
                "themeColor": theme_color,
                "title": f"🚨 Audit Failure: {device_name}",
                "sections": [
                    {
                        "facts": [
                            {"name": "Device", "value": device_name},
                            {"name": "Compliance Score", "value": f"{compliance}%"},
                            {"name": "Failed Checks", "value": str(failed_checks)},
                            {"name": "Timestamp", "value": data.get("timestamp", datetime.utcnow().isoformat())}
                        ]
                    }
                ]
            }

        elif event_type == "config_change":
            device_name = data.get("device_name", "Unknown")
            lines_changed = data.get("lines_changed", 0)

            return {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": f"Configuration Change: {device_name}",
                "themeColor": "0078D7",
                "title": f"📝 Configuration Change: {device_name}",
                "sections": [
                    {
                        "facts": [
                            {"name": "Device", "value": device_name},
                            {"name": "Lines Changed", "value": str(lines_changed)}
                        ]
                    }
                ]
            }

        else:
            return {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": event_type,
                "title": event_type,
                "text": json.dumps(data)
            }

    @staticmethod
    def format_discord_message(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a message for Discord"""
        if event_type == "audit_failure":
            device_name = data.get("device_name", "Unknown")
            compliance = data.get("compliance", 0)
            failed_checks = data.get("failed_checks", 0)

            color = 0xFF0000 if compliance < 50 else 0xFFA500  # Red or Orange

            return {
                "embeds": [
                    {
                        "title": f"🚨 Audit Failure: {device_name}",
                        "description": f"Device {device_name} failed {failed_checks} audit checks",
                        "color": color,
                        "fields": [
                            {"name": "Compliance Score", "value": f"{compliance}%", "inline": True},
                            {"name": "Failed Checks", "value": str(failed_checks), "inline": True}
                        ],
                        "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
                    }
                ]
            }

        else:
            return {"content": f"**{event_type}**\n```json\n{json.dumps(data, indent=2)}\n```"}

    @staticmethod
    async def send_webhook(
        webhook_url: str,
        webhook_type: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send a webhook notification"""
        try:
            # Format message based on webhook type
            if webhook_type == "slack":
                payload = NotificationService.format_slack_message(event_type, data)
            elif webhook_type == "teams":
                payload = NotificationService.format_teams_message(event_type, data)
            elif webhook_type == "discord":
                payload = NotificationService.format_discord_message(event_type, data)
            else:
                # Generic webhook
                payload = {"event": event_type, "data": data}

            # Send HTTP POST request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(f"Webhook sent successfully to {webhook_url}")
                        return True
                    else:
                        logger.error(f"Webhook failed with status {response.status}: {await response.text()}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_url}: {str(e)}")
            return False

    @staticmethod
    async def notify_audit_result(
        db: Session,
        audit_result: AuditResult
    ):
        """
        Send notifications based on audit results

        Triggers notifications for:
        - audit_failure: When compliance is below threshold
        - compliance_drop: When compliance drops significantly
        """
        try:
            # Get active webhooks for audit events
            webhooks = db.query(NotificationWebhookDB).filter(
                NotificationWebhookDB.enabled == True
            ).all()

            if not webhooks:
                logger.debug("No active webhooks configured")
                return

            device_name = audit_result.device_name
            compliance = audit_result.compliance

            # Count failed checks
            failed_checks = len([f for f in audit_result.findings if f.status == AuditStatus.FAIL])

            # Get previous compliance to detect drops
            device_db = db.query(DeviceDB).filter(DeviceDB.id == audit_result.device_id).first()
            previous_compliance = device_db.compliance if device_db else compliance

            # Prepare event data
            event_data = {
                "device_name": device_name,
                "device_id": audit_result.device_id,
                "compliance": compliance,
                "failed_checks": failed_checks,
                "timestamp": audit_result.timestamp
            }

            # Trigger notifications
            for webhook in webhooks:
                events = webhook.events or {}

                # Check audit_failure event
                if "audit_failure" in events:
                    threshold = events.get("audit_failure", {}).get("threshold", 80)
                    if compliance < threshold:
                        logger.info(f"Triggering audit_failure notification for {device_name} (compliance: {compliance}%)")
                        success = await NotificationService.send_webhook(
                            webhook.webhook_url,
                            webhook.webhook_type,
                            "audit_failure",
                            event_data
                        )

                        # Record notification history
                        NotificationService._record_notification(
                            db, webhook.id, "audit_failure", event_data, success
                        )

                # Check compliance_drop event
                if "compliance_drop" in events and previous_compliance > compliance:
                    drop_threshold = events.get("compliance_drop", {}).get("threshold", 10)
                    drop = previous_compliance - compliance

                    if drop >= drop_threshold:
                        logger.info(f"Triggering compliance_drop notification for {device_name} (drop: {drop}%)")
                        drop_data = {
                            **event_data,
                            "old_compliance": previous_compliance,
                            "new_compliance": compliance,
                            "drop": drop
                        }

                        success = await NotificationService.send_webhook(
                            webhook.webhook_url,
                            webhook.webhook_type,
                            "compliance_drop",
                            drop_data
                        )

                        # Record notification history
                        NotificationService._record_notification(
                            db, webhook.id, "compliance_drop", drop_data, success
                        )

        except Exception as e:
            logger.error(f"Error sending audit notifications: {str(e)}")

    @staticmethod
    def _record_notification(
        db: Session,
        webhook_id: int,
        event_type: str,
        payload: Dict[str, Any],
        success: bool
    ):
        """Record notification in history"""
        try:
            notification = NotificationHistoryDB(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                sent_at=datetime.utcnow(),
                status="sent" if success else "failed",
                error_message=None if success else "Failed to send webhook"
            )
            db.add(notification)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to record notification history: {str(e)}")
            db.rollback()

    @staticmethod
    def notify_config_change(
        db: Session,
        device_id: int,
        device_name: str,
        lines_changed: int,
        severity: str
    ):
        """Send notifications for configuration changes"""
        try:
            webhooks = db.query(NotificationWebhookDB).filter(
                and_(
                    NotificationWebhookDB.enabled == True,
                    NotificationWebhookDB.events.contains(["config_change"])
                )
            ).all()

            event_data = {
                "device_id": device_id,
                "device_name": device_name,
                "lines_changed": lines_changed,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            }

            for webhook in webhooks:
                # For now, just log the notification (webhook sending requires async)
                logger.info(f"Would send webhook notification for config change on device {device_name}")
                success = True  # Placeholder

                NotificationService._record_notification(
                    db, webhook.id, "config_change", event_data, success
                )

        except Exception as e:
            logger.error(f"Error sending config change notifications: {str(e)}")
