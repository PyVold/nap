# ============================================================================
# engine/workflow_engine.py
# Workflow Execution Engine with DAG Support
# ============================================================================

import asyncio
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from jinja2 import Template, Environment, BaseLoader

from engine.workflow_parser import WorkflowParser, WorkflowDefinition, WorkflowStep
from engine.step_executors import (
    QueryExecutor, TemplateExecutor, AuditExecutor, RemediateExecutor,
    TransformExecutor, ApiCallExecutor, NotificationExecutor
)
from db_models import (
    WorkflowDB, WorkflowExecutionDB, WorkflowStepLogDB, DeviceDB
)
from shared.logger import setup_logger

logger = setup_logger(__name__)


class WorkflowContext:
    """Shared context for workflow execution"""

    def __init__(self, workflow: WorkflowDefinition, device: DeviceDB, variables: Dict[str, Any]):
        self.workflow = workflow
        self.device = device
        self.variables = variables.copy()
        self.step_outputs = {}  # Store outputs from each step
        self.executed_steps = set()  # Track which steps have been executed

    def get_variable(self, var_name: str) -> Any:
        """Get variable from context with fallback to workflow defaults"""
        if var_name in self.variables:
            return self.variables[var_name]
        return self.workflow.variables.get(var_name)

    def set_step_output(self, step_name: str, output: Any):
        """Store step output in context"""
        self.step_outputs[step_name] = output

    def get_step_output(self, step_name: str) -> Any:
        """Get output from a previous step"""
        return self.step_outputs.get(step_name)

    def render_template_string(self, template_str: str) -> str:
        """Render Jinja2 template string with current context"""
        env = Environment(loader=BaseLoader())
        template = env.from_string(template_str)

        # Build template context
        template_context = {
            'workflow': {
                'name': self.workflow.name,
                'description': self.workflow.description
            },
            'device': {
                'id': self.device.id,
                'hostname': self.device.hostname,
                'ip': self.device.ip_address,
                'vendor': self.device.vendor,
                'model': self.device.model
            },
            **self.variables,
            **self.step_outputs
        }

        return template.render(**template_context)

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string safely without using eval()"""
        if not condition:
            return True

        try:
            # Render Jinja2 template first
            rendered = self.render_template_string(condition)

            # Simple boolean evaluation
            if rendered.lower() in ['true', '1', 'yes']:
                return True
            elif rendered.lower() in ['false', '0', 'no', '']:
                return False

            # Safe expression evaluation using simple comparisons
            rendered = rendered.strip()

            # Build safe context for evaluation
            context = {
                **self.variables,
                **self.step_outputs
            }

            # Use safe_eval helper instead of eval()
            return self._safe_evaluate_expression(rendered, context)
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    def _safe_evaluate_expression(self, expr: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a simple boolean expression without using eval()"""
        import operator

        # Supported comparison operators (check longer ones first)
        ops = [
            ('>=', operator.ge),
            ('<=', operator.le),
            ('!=', operator.ne),
            ('==', operator.eq),
            ('>', operator.gt),
            ('<', operator.lt),
        ]

        # Try simple comparisons first
        for op_str, op_func in ops:
            if op_str in expr:
                parts = expr.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    return op_func(left, right)

        # Check for 'not in' operator (check before 'in')
        if ' not in ' in expr:
            parts = expr.split(' not in ', 1)
            if len(parts) == 2:
                left = self._resolve_value(parts[0].strip(), context)
                right = self._resolve_value(parts[1].strip(), context)
                return left not in right

        # Check for 'in' operator
        if ' in ' in expr:
            parts = expr.split(' in ', 1)
            if len(parts) == 2:
                left = self._resolve_value(parts[0].strip(), context)
                right = self._resolve_value(parts[1].strip(), context)
                return left in right

        # Try to resolve as a single value (truthy check)
        value = self._resolve_value(expr, context)
        return bool(value)

    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """Resolve a value from string representation safely"""
        value_str = value_str.strip()

        # Handle quoted strings
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # Handle numeric values
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Handle boolean literals
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        if value_str.lower() == 'none':
            return None

        # Handle list literals [a, b, c]
        if value_str.startswith('[') and value_str.endswith(']'):
            inner = value_str[1:-1]
            if not inner.strip():
                return []
            items = [self._resolve_value(item.strip(), context) for item in inner.split(',')]
            return items

        # Look up in context (supports dot notation like step1.result)
        if '.' in value_str:
            parts = value_str.split('.')
            current = context
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return value_str  # Return as string if not found
            return current

        # Simple context lookup
        if value_str in context:
            return context[value_str]

        # Return as-is (string)
        return value_str


class WorkflowEngine:
    """Execute workflows with sequential or DAG-based execution"""

    def __init__(self, db: Session):
        self.db = db
        self.parser = WorkflowParser()

        # Initialize step executors
        self.executors = {
            'query': QueryExecutor(db),
            'template': TemplateExecutor(db),
            'audit': AuditExecutor(db),
            'remediate': RemediateExecutor(db),
            'transform': TransformExecutor(db),
            'api_call': ApiCallExecutor(db),
            'notification': NotificationExecutor(db)
        }

    async def execute_workflow(
        self,
        workflow: WorkflowDB,
        device: DeviceDB,
        trigger_type: str = "manual",
        started_by: str = None,
        override_vars: Dict[str, Any] = None
    ) -> WorkflowExecutionDB:
        """
        Execute a workflow on a device

        Args:
            workflow: Workflow definition from DB
            device: Target device
            trigger_type: manual, scheduled, or event
            started_by: Username who started the workflow
            override_vars: Variables to override defaults

        Returns:
            WorkflowExecutionDB record
        """
        # Parse YAML workflow
        try:
            workflow_def = self.parser.parse(workflow.workflow_yaml)
        except Exception as e:
            logger.error(f"Error parsing workflow {workflow.name}: {e}")
            raise ValueError(f"Invalid workflow YAML: {str(e)}")

        # Create execution record
        execution = WorkflowExecutionDB(
            workflow_id=workflow.id,
            device_id=device.id,
            trigger_type=trigger_type,
            status="running",
            started_by=started_by,
            start_time=datetime.utcnow(),
            step_results={},
            context_data={}
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        logger.info(f"Starting workflow '{workflow.name}' on device '{device.hostname}' (execution_id={execution.id})")

        # Initialize context
        variables = workflow_def.variables.copy()
        if override_vars:
            variables.update(override_vars)

        context = WorkflowContext(workflow_def, device, variables)

        try:
            # Execute based on mode
            if workflow_def.execution_mode == "sequential":
                await self._execute_sequential(workflow_def, context, execution)
            elif workflow_def.execution_mode == "dag":
                await self._execute_dag(workflow_def, context, execution)
            elif workflow_def.execution_mode == "hybrid":
                await self._execute_hybrid(workflow_def, context, execution)

            # Mark as completed
            execution.status = "completed"
            execution.end_time = datetime.utcnow()
            execution.context_data = context.step_outputs

            logger.info(f"Workflow '{workflow.name}' completed successfully on '{device.hostname}'")

        except Exception as e:
            logger.error(f"Workflow '{workflow.name}' failed on '{device.hostname}': {e}")
            execution.status = "failed"
            execution.end_time = datetime.utcnow()
            execution.error_message = str(e)

        self.db.commit()
        return execution

    async def _execute_sequential(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        execution: WorkflowExecutionDB
    ):
        """Execute steps sequentially in order"""
        for step in workflow.steps:
            # Check if step should be executed (condition)
            if step.condition and not context.evaluate_condition(step.condition):
                logger.info(f"Skipping step '{step.name}' - condition not met")
                self._log_step(execution, step, "skipped", None, None, "Condition not met")
                continue

            # Execute step
            await self._execute_step(step, context, execution)

    async def _execute_dag(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        execution: WorkflowExecutionDB
    ):
        """Execute steps in DAG order with parallel execution where possible"""
        # Build dependency graph
        pending_steps = {step.name: step for step in workflow.steps}
        ready_steps = []

        # Find steps with no dependencies
        for step in workflow.steps:
            if not step.depends_on:
                ready_steps.append(step)

        while ready_steps or pending_steps:
            if not ready_steps:
                # Deadlock - circular dependency or missing dependency
                raise ValueError("Workflow has unresolved dependencies or circular references")

            # Execute all ready steps in parallel
            tasks = []
            for step in ready_steps:
                # Check condition
                if step.condition and not context.evaluate_condition(step.condition):
                    logger.info(f"Skipping step '{step.name}' - condition not met")
                    self._log_step(execution, step, "skipped", None, None, "Condition not met")
                    context.executed_steps.add(step.name)
                    continue

                tasks.append(self._execute_step(step, context, execution))

            # Wait for all parallel steps to complete
            if tasks:
                await asyncio.gather(*tasks)

            # Mark ready steps as executed
            for step in ready_steps:
                context.executed_steps.add(step.name)
                if step.name in pending_steps:
                    del pending_steps[step.name]

            # Find next ready steps
            ready_steps = []
            for step_name, step in list(pending_steps.items()):
                if all(dep in context.executed_steps for dep in step.depends_on):
                    ready_steps.append(step)

    async def _execute_hybrid(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        execution: WorkflowExecutionDB
    ):
        """
        Hybrid execution: Sequential within dependency groups, parallel across groups
        """
        # For now, use sequential execution
        # Can be enhanced later to detect independent step groups
        await self._execute_sequential(workflow, context, execution)

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        execution: WorkflowExecutionDB
    ) -> Any:
        """Execute a single workflow step"""
        logger.info(f"Executing step '{step.name}' (type: {step.type})")

        start_time = datetime.utcnow()
        execution.current_step = step.name
        self.db.commit()

        try:
            # Get executor for step type
            executor = self.executors.get(step.type)
            if not executor:
                raise ValueError(f"Unknown step type: {step.type}")

            # Execute step with retries
            result = await self._execute_with_retries(executor, step, context)

            # Store result in context
            if step.output_var:
                context.set_step_output(step.output_var, result)

            # Log success
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            self._log_step(execution, step, "completed", result, None, None, start_time, end_time, duration_ms)

            logger.info(f"Step '{step.name}' completed successfully ({duration_ms}ms)")
            return result

        except Exception as e:
            logger.error(f"Step '{step.name}' failed: {e}")

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            self._log_step(execution, step, "failed", None, str(e), None, start_time, end_time, duration_ms)

            # Handle error based on on_error setting
            if step.on_error == "fail":
                raise
            elif step.on_error == "continue":
                logger.warning(f"Step '{step.name}' failed but continuing workflow")
                return None
            # retry is handled by _execute_with_retries

    async def _execute_with_retries(
        self,
        executor: Any,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Any:
        """Execute step with retry logic"""
        max_attempts = step.max_retries + 1  # Initial attempt + retries

        for attempt in range(max_attempts):
            try:
                result = await executor.execute(step, context)
                return result
            except Exception as e:
                if attempt < max_attempts - 1 and step.on_error == "retry":
                    logger.warning(f"Step '{step.name}' failed (attempt {attempt + 1}/{max_attempts}), retrying in {step.retry_delay}s...")
                    await asyncio.sleep(step.retry_delay)
                else:
                    raise

    def _log_step(
        self,
        execution: WorkflowExecutionDB,
        step: WorkflowStep,
        status: str,
        output: Any,
        error: str,
        skip_reason: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        duration_ms: int = None
    ):
        """Log step execution to database"""
        step_log = WorkflowStepLogDB(
            execution_id=execution.id,
            step_name=step.name,
            step_type=step.type,
            status=status,
            output_data=output if isinstance(output, dict) else {"result": str(output)} if output else None,
            error_message=error or skip_reason,
            start_time=start_time or datetime.utcnow(),
            end_time=end_time,
            duration_ms=duration_ms
        )
        self.db.add(step_log)
        self.db.commit()
