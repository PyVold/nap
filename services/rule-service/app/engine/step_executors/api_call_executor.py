# ============================================================================
# engine/step_executors/api_call_executor.py
# API Call Step Executor - Make HTTP requests to external APIs
# ============================================================================

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import base64

from shared.logger import setup_logger

logger = setup_logger(__name__)


class ApiCallExecutor:
    """Execute API call steps - make HTTP requests to external services"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Dict[str, Any]:
        """
        Execute an API call step

        Args:
            step: WorkflowStep with type='api_call'
            context: WorkflowContext

        Returns:
            API response data
        """
        # Render URL template
        url = context.render_template_string(step.api_url)
        method = step.api_method.upper()

        logger.info(f"Making {method} request to {url}")

        # Prepare headers
        headers = {}
        if step.api_headers:
            for key, value in step.api_headers.items():
                headers[key] = context.render_template_string(value)

        # Prepare authentication
        if step.api_auth:
            auth_type = step.api_auth.get('type', 'bearer')

            if auth_type == 'bearer':
                token = context.render_template_string(step.api_auth.get('token', ''))
                headers['Authorization'] = f'Bearer {token}'

            elif auth_type == 'basic':
                username = context.render_template_string(step.api_auth.get('username', ''))
                password = context.render_template_string(step.api_auth.get('password', ''))
                credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'

        # Prepare query parameters
        params = {}
        if step.api_params:
            for key, value in step.api_params.items():
                params[key] = context.render_template_string(str(value))

        # Prepare request body
        body = None
        if step.api_body:
            # Recursively render template strings in body
            body = self._render_dict_templates(step.api_body, context)

        # Make HTTP request
        timeout = aiohttp.ClientTimeout(total=step.timeout or 30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body if body else None
                ) as response:
                    # Get response
                    status_code = response.status
                    response_text = await response.text()

                    # Try to parse as JSON
                    try:
                        response_data = await response.json()
                    except:
                        response_data = response_text

                    logger.info(f"API call to {url} completed with status {status_code}")

                    # Check if request was successful
                    if status_code >= 400:
                        logger.warning(f"API call returned error status {status_code}: {response_text}")

                    return {
                        'status_code': status_code,
                        'success': status_code < 400,
                        'data': response_data,
                        'headers': dict(response.headers)
                    }

        except asyncio.TimeoutError:
            logger.error(f"API call to {url} timed out")
            raise ValueError(f"API request timed out after {step.timeout}s")

        except Exception as e:
            logger.error(f"API call to {url} failed: {e}")
            raise ValueError(f"API request failed: {str(e)}")

    def _render_dict_templates(self, data: Any, context) -> Any:
        """Recursively render Jinja2 templates in dictionary/list structures"""
        if isinstance(data, dict):
            return {k: self._render_dict_templates(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._render_dict_templates(item, context) for item in data]
        elif isinstance(data, str):
            return context.render_template_string(data)
        else:
            return data
