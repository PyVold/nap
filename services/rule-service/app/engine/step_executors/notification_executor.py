# ============================================================================
# engine/step_executors/notification_executor.py
# Notification Step Executor - Send notifications via email/webhook
# ============================================================================

import aiohttp
from typing import Dict, Any
from sqlalchemy.orm import Session

from utils.logger import setup_logger

logger = setup_logger(__name__)


class NotificationExecutor:
    """Execute notification steps - send alerts via email, webhook, etc."""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Dict[str, Any]:
        """
        Execute a notification step

        Args:
            step: WorkflowStep with type='notification'
            context: WorkflowContext

        Returns:
            Notification result
        """
        # Render message template
        message = context.render_template_string(step.message_template) if hasattr(step, 'message_template') else "Workflow notification"

        channels = step.channels if hasattr(step, 'channels') else ['webhook']

        logger.info(f"Sending notification via channels: {channels}")

        results = {}

        for channel in channels:
            try:
                if channel == 'email':
                    result = await self._send_email(message, context)
                    results['email'] = result

                elif channel == 'webhook':
                    result = await self._send_webhook(message, context)
                    results['webhook'] = result

                elif channel == 'slack':
                    result = await self._send_slack(message, context)
                    results['slack'] = result

                else:
                    logger.warning(f"Unknown notification channel: {channel}")

            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")
                results[channel] = {'success': False, 'error': str(e)}

        return results

    async def _send_email(self, message: str, context) -> Dict[str, Any]:
        """Send email notification"""
        # TODO: Implement email sending
        logger.info("Email notification not yet implemented")
        return {'success': True, 'method': 'email'}

    async def _send_webhook(self, message: str, context) -> Dict[str, Any]:
        """Send webhook notification"""
        # Get webhook URL from workflow variables
        webhook_url = context.get_variable('webhook_url')
        if not webhook_url:
            logger.warning("No webhook_url configured")
            return {'success': False, 'error': 'No webhook_url configured'}

        # Send POST request to webhook
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json={
                        'workflow': context.workflow.name,
                        'device': context.device.hostname,
                        'message': message
                    }
                ) as response:
                    return {
                        'success': response.status < 400,
                        'status_code': response.status,
                        'method': 'webhook'
                    }
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _send_slack(self, message: str, context) -> Dict[str, Any]:
        """Send Slack notification"""
        slack_webhook = context.get_variable('slack_webhook_url')
        if not slack_webhook:
            logger.warning("No slack_webhook_url configured")
            return {'success': False, 'error': 'No slack_webhook_url configured'}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    slack_webhook,
                    json={'text': message}
                ) as response:
                    return {
                        'success': response.status < 400,
                        'status_code': response.status,
                        'method': 'slack'
                    }
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return {'success': False, 'error': str(e)}
