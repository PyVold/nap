# ============================================================================
# engine/step_executors/template_executor.py
# Template Step Executor - Render Jinja2 templates
# ============================================================================

import os
from typing import Dict, Any
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, Template

from shared.logger import setup_logger

logger = setup_logger(__name__)


class TemplateExecutor:
    """Execute template steps - render Jinja2 templates with context data"""

    def __init__(self, db: Session):
        self.db = db
        # Setup Jinja2 environment for file templates
        template_dir = os.path.join(os.path.dirname(__file__), '../../templates/workflows')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    async def execute(self, step, context) -> str:
        """
        Execute a template step

        Args:
            step: WorkflowStep with type='template'
            context: WorkflowContext

        Returns:
            Rendered template string
        """
        device = context.device

        # Build template context
        template_context = {}

        # Add template variables from step
        if step.template_vars:
            for var_name, var_value in step.template_vars.items():
                # Render variable values (they might contain templates too)
                if isinstance(var_value, str):
                    template_context[var_name] = context.render_template_string(var_value)
                else:
                    template_context[var_name] = var_value

        # Add workflow variables
        template_context.update(context.variables)

        # Add step outputs
        template_context.update(context.step_outputs)

        # Handle vendor-specific templates
        if step.vendor_specific:
            vendor_config = step.vendor_specific.get(device.vendor.lower())
            if not vendor_config:
                raise ValueError(f"No vendor-specific template for vendor '{device.vendor}'")

            template_file = vendor_config.get('template')
            output_format = vendor_config.get('output_format', 'text')
        else:
            template_file = step.template
            output_format = 'text'

        logger.info(f"Rendering template '{template_file}' for {device.hostname}")

        # Load and render template
        try:
            template = self.jinja_env.get_template(template_file)
            rendered = template.render(**template_context)

            # Return rendered output
            if output_format == 'xml':
                return {'rendered_config': rendered, 'format': 'xml'}
            else:
                return {'rendered_config': rendered, 'format': 'text'}

        except Exception as e:
            logger.error(f"Error rendering template '{template_file}': {e}")
            raise ValueError(f"Template rendering failed: {str(e)}")
