# ============================================================================
# engine/step_executors/transform_executor.py
# Transform Step Executor - Execute Python scripts to transform data
# ============================================================================

from typing import Dict, Any
from sqlalchemy.orm import Session

from utils.logger import setup_logger

logger = setup_logger(__name__)


class TransformExecutor:
    """Execute transform steps - run Python scripts to process data"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Any:
        """
        Execute a transform step

        Args:
            step: WorkflowStep with type='transform'
            context: WorkflowContext

        Returns:
            Transformed data
        """
        logger.info(f"Executing transform script for step '{step.name}'")

        # Build execution context for script
        script_context = {
            **context.variables,
            **context.step_outputs
        }

        # Execute Python script
        try:
            # Use exec to run the script
            exec_globals = {"__builtins__": __builtins__}
            exec_locals = script_context.copy()

            exec(step.script, exec_globals, exec_locals)

            # Get return value (script should set a 'result' variable or return a value)
            if 'result' in exec_locals:
                result = exec_locals['result']
            else:
                # Return the entire modified context
                result = {k: v for k, v in exec_locals.items() if k not in script_context}

            logger.info(f"Transform script completed successfully")
            return result

        except Exception as e:
            logger.error(f"Transform script failed: {e}")
            raise ValueError(f"Script execution failed: {str(e)}")
