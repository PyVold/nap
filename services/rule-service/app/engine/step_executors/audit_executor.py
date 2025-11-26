# ============================================================================
# engine/step_executors/audit_executor.py
# Audit Step Executor - Compare configurations
# ============================================================================

import difflib
from typing import Dict, Any
from sqlalchemy.orm import Session

from shared.logger import setup_logger

logger = setup_logger(__name__)


class AuditExecutor:
    """Execute audit steps - compare expected vs actual configurations"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Dict[str, Any]:
        """
        Execute an audit step

        Args:
            step: WorkflowStep with type='audit'
            context: WorkflowContext

        Returns:
            Audit result with comparison details
        """
        # Get expected and actual configurations
        expected_var = context.render_template_string(step.compare['expected'])
        actual_var = context.render_template_string(step.compare['actual'])

        expected_data = context.get_step_output(expected_var.strip('{}').strip())
        actual_data = context.get_step_output(actual_var.strip('{}').strip())

        logger.info(f"Auditing configuration: comparing {expected_var} vs {actual_var}")

        # Extract config strings
        if isinstance(expected_data, dict):
            expected_config = expected_data.get('rendered_config', str(expected_data))
        else:
            expected_config = str(expected_data)

        if isinstance(actual_data, dict):
            actual_config = actual_data.get('raw_output', str(actual_data))
        else:
            actual_config = str(actual_data)

        # Perform comparison
        if step.diff_mode:
            # Generate unified diff
            expected_lines = expected_config.splitlines(keepends=True)
            actual_lines = actual_config.splitlines(keepends=True)

            diff = list(difflib.unified_diff(
                actual_lines,
                expected_lines,
                fromfile='Actual',
                tofile='Expected',
                lineterm=''
            ))

            diff_output = ''.join(diff)
            has_differences = len(diff) > 0

            # Calculate compliance percentage
            if has_differences:
                # Simple line-based comparison
                matcher = difflib.SequenceMatcher(None, actual_config, expected_config)
                compliance = int(matcher.ratio() * 100)
            else:
                compliance = 100

        else:
            # Simple string comparison
            has_differences = expected_config != actual_config
            compliance = 100 if not has_differences else 0
            diff_output = None

        logger.info(f"Audit completed: compliance={compliance}%, has_differences={has_differences}")

        return {
            'compliance': compliance,
            'passed': compliance >= step.thresholds.get('pass_threshold', 100) if hasattr(step, 'thresholds') and step.thresholds else compliance == 100,
            'has_differences': has_differences,
            'diff': diff_output,
            'expected_config': expected_config,
            'actual_config': actual_config
        }
