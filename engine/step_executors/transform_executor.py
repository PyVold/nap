# ============================================================================
# engine/step_executors/transform_executor.py
# Transform Step Executor - Execute Python scripts to transform data
# ============================================================================

from typing import Dict, Any
from sqlalchemy.orm import Session
import re
import json

from utils.logger import setup_logger

logger = setup_logger(__name__)

# SECURITY: Restricted built-ins for script execution
# Only allow safe operations - no file I/O, imports, or code execution
SAFE_BUILTINS = {
    # Type conversions
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'list': list,
    'dict': dict,
    'tuple': tuple,
    'set': set,
    # Safe operations
    'len': len,
    'range': range,
    'enumerate': enumerate,
    'zip': zip,
    'map': map,
    'filter': filter,
    'sorted': sorted,
    'reversed': reversed,
    'sum': sum,
    'min': min,
    'max': max,
    'abs': abs,
    'round': round,
    'all': all,
    'any': any,
    # String/data operations
    'isinstance': isinstance,
    'hasattr': hasattr,
    'getattr': getattr,
    'repr': repr,
    'json': json,  # Allow JSON operations
    # Explicitly blocked (not included): exec, eval, compile, __import__, open,
    # input, globals, locals, vars, dir, delattr, setattr, type, object
}

# SECURITY: Patterns that indicate potentially dangerous code
DANGEROUS_PATTERNS = [
    r'__\w+__',        # Dunder methods (except allowed ones)
    r'\bimport\b',     # Import statements
    r'\bexec\b',       # Nested exec calls
    r'\beval\b',       # Eval calls
    r'\bcompile\b',    # Compile calls
    r'\bopen\b',       # File operations
    r'\bgetattr\s*\([^)]*[\'"]__',  # getattr to access dunders
    r'\.read\s*\(',    # File reading
    r'\.write\s*\(',   # File writing
    r'\bos\.',         # OS module access
    r'\bsys\.',        # Sys module access
    r'\bsubprocess',   # Subprocess module
]


class TransformExecutor:
    """Execute transform steps - run Python scripts to process data

    SECURITY: Scripts are executed in a restricted environment with:
    - Limited built-ins (no exec, eval, import, open, etc.)
    - Pattern-based blocking of dangerous code
    - No access to file system or network
    """

    def __init__(self, db: Session):
        self.db = db

    def _validate_script(self, script: str) -> None:
        """
        SECURITY: Validate script for dangerous patterns before execution

        Raises:
            ValueError: If script contains potentially dangerous code
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, script, re.IGNORECASE):
                raise ValueError(
                    f"Script contains disallowed pattern. "
                    f"For security, the following are not permitted: "
                    f"import, exec, eval, compile, open, file I/O, os/sys access"
                )

    async def execute(self, step, context) -> Any:
        """
        Execute a transform step in a restricted environment

        Args:
            step: WorkflowStep with type='transform'
            context: WorkflowContext

        Returns:
            Transformed data
        """
        logger.info(f"Executing transform script for step '{step.name}'")

        # SECURITY: Validate script before execution
        self._validate_script(step.script)

        # Build execution context for script
        script_context = {
            **context.variables,
            **context.step_outputs
        }

        # Execute Python script in restricted environment
        try:
            # SECURITY: Use restricted built-ins instead of full __builtins__
            exec_globals = {"__builtins__": SAFE_BUILTINS}
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
