# ============================================================================
# engine/workflow_parser.py
# YAML Workflow Parser and Validator
# ============================================================================

import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """Represents a single workflow step"""
    name: str
    type: str  # query, template, audit, remediate, transform, notification, api_call
    description: Optional[str] = None
    command: Optional[str] = None
    parser: Optional[str] = None
    output_var: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    on_error: str = "fail"  # fail, continue, retry
    vendor_specific: Optional[Dict[str, Any]] = None
    template: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None
    script: Optional[str] = None
    config_source: Optional[str] = None
    compare: Optional[Dict[str, str]] = None
    validation: Optional[List[Dict[str, Any]]] = None
    # API call specific fields
    api_url: Optional[str] = None
    api_method: Optional[str] = None  # GET, POST, PUT, DELETE, PATCH
    api_headers: Optional[Dict[str, str]] = None
    api_body: Optional[Dict[str, Any]] = None
    api_params: Optional[Dict[str, Any]] = None
    api_auth: Optional[Dict[str, Any]] = None  # {type: "bearer", token: "..."} or {type: "basic", user: "...", pass: "..."}
    max_retries: int = 0
    retry_delay: int = 5
    timeout: Optional[int] = None


@dataclass
class WorkflowDefinition:
    """Parsed workflow definition"""
    name: str
    description: Optional[str] = None
    execution_mode: str = "sequential"
    variables: Dict[str, Any] = field(default_factory=dict)
    steps: List[WorkflowStep] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    completion_criteria: Dict[str, Any] = field(default_factory=dict)


class WorkflowParser:
    """Parse and validate YAML workflow definitions"""

    VALID_STEP_TYPES = ['query', 'template', 'audit', 'remediate', 'transform', 'notification', 'api_call']
    VALID_EXECUTION_MODES = ['sequential', 'dag', 'hybrid']
    VALID_ERROR_ACTIONS = ['fail', 'continue', 'retry']

    def parse(self, yaml_content: str) -> WorkflowDefinition:
        """
        Parse YAML workflow definition

        Args:
            yaml_content: YAML string

        Returns:
            WorkflowDefinition object

        Raises:
            ValueError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {str(e)}")

        # Validate required fields
        if 'name' not in data:
            raise ValueError("Workflow must have a 'name' field")

        if 'steps' not in data or not isinstance(data['steps'], list):
            raise ValueError("Workflow must have a 'steps' list")

        # Parse workflow definition
        workflow = WorkflowDefinition(
            name=data['name'],
            description=data.get('description'),
            execution_mode=data.get('execution_mode', 'sequential'),
            variables=data.get('variables', {}),
            settings=data.get('settings', {}),
            completion_criteria=data.get('completion_criteria', {})
        )

        # Validate execution mode
        if workflow.execution_mode not in self.VALID_EXECUTION_MODES:
            raise ValueError(f"Invalid execution_mode: {workflow.execution_mode}")

        # Parse steps
        for idx, step_data in enumerate(data['steps']):
            try:
                step = self._parse_step(step_data, idx)
                workflow.steps.append(step)
            except ValueError as e:
                raise ValueError(f"Error parsing step {idx + 1}: {str(e)}")

        # Validate workflow
        self._validate_workflow(workflow)

        return workflow

    def _parse_step(self, step_data: Dict[str, Any], index: int) -> WorkflowStep:
        """Parse a single step"""
        if 'name' not in step_data:
            raise ValueError(f"Step {index + 1} must have a 'name' field")

        if 'type' not in step_data:
            raise ValueError(f"Step {index + 1} must have a 'type' field")

        step_type = step_data['type']
        if step_type not in self.VALID_STEP_TYPES:
            raise ValueError(f"Invalid step type: {step_type}")

        # Parse on_error action
        on_error = step_data.get('on_error', 'fail')
        if on_error not in self.VALID_ERROR_ACTIONS:
            raise ValueError(f"Invalid on_error action: {on_error}")

        step = WorkflowStep(
            name=step_data['name'],
            type=step_type,
            description=step_data.get('description'),
            command=step_data.get('command'),
            parser=step_data.get('parser'),
            output_var=step_data.get('output_var'),
            depends_on=step_data.get('depends_on', []),
            condition=step_data.get('condition'),
            on_error=on_error,
            vendor_specific=step_data.get('vendor_specific'),
            template=step_data.get('template'),
            template_vars=step_data.get('template_vars'),
            script=step_data.get('script'),
            config_source=step_data.get('config_source'),
            compare=step_data.get('compare'),
            validation=step_data.get('validation'),
            # API call fields
            api_url=step_data.get('api_url'),
            api_method=step_data.get('api_method'),
            api_headers=step_data.get('api_headers'),
            api_body=step_data.get('api_body'),
            api_params=step_data.get('api_params'),
            api_auth=step_data.get('api_auth'),
            max_retries=step_data.get('max_retries', 0),
            retry_delay=step_data.get('retry_delay', 5),
            timeout=step_data.get('timeout')
        )

        # Validate step-specific fields
        self._validate_step(step)

        return step

    def _validate_step(self, step: WorkflowStep):
        """Validate step has required fields for its type"""
        if step.type == 'query':
            if not step.command and not step.vendor_specific:
                raise ValueError(f"Query step '{step.name}' must have 'command' or 'vendor_specific'")

        elif step.type == 'template':
            if not step.template:
                raise ValueError(f"Template step '{step.name}' must have 'template' field")

        elif step.type == 'audit':
            if not step.compare:
                raise ValueError(f"Audit step '{step.name}' must have 'compare' field")

        elif step.type == 'remediate':
            if not step.config_source:
                raise ValueError(f"Remediate step '{step.name}' must have 'config_source' field")

        elif step.type == 'transform':
            if not step.script:
                raise ValueError(f"Transform step '{step.name}' must have 'script' field")

        elif step.type == 'api_call':
            if not step.api_url:
                raise ValueError(f"API call step '{step.name}' must have 'api_url' field")
            if not step.api_method:
                raise ValueError(f"API call step '{step.name}' must have 'api_method' field")
            valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
            if step.api_method.upper() not in valid_methods:
                raise ValueError(f"API call step '{step.name}' has invalid method '{step.api_method}'. Must be one of: {valid_methods}")

    def _validate_workflow(self, workflow: WorkflowDefinition):
        """Validate workflow structure and dependencies"""
        step_names = {step.name for step in workflow.steps}

        # Check for duplicate step names
        if len(step_names) != len(workflow.steps):
            raise ValueError("Workflow has duplicate step names")

        # Check dependencies exist
        for step in workflow.steps:
            for dep in step.depends_on:
                if dep not in step_names:
                    raise ValueError(f"Step '{step.name}' depends on non-existent step '{dep}'")

        # Check for circular dependencies (if DAG mode)
        if workflow.execution_mode in ['dag', 'hybrid']:
            self._check_circular_dependencies(workflow.steps)

    def _check_circular_dependencies(self, steps: List[WorkflowStep]):
        """Check for circular dependencies in DAG"""
        def has_cycle(step_name: str, visited: set, rec_stack: set) -> bool:
            visited.add(step_name)
            rec_stack.add(step_name)

            step = next((s for s in steps if s.name == step_name), None)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(step_name)
            return False

        visited = set()
        rec_stack = set()

        for step in steps:
            if step.name not in visited:
                if has_cycle(step.name, visited, rec_stack):
                    raise ValueError(f"Circular dependency detected involving step '{step.name}'")

    def to_yaml(self, workflow: WorkflowDefinition) -> str:
        """Convert WorkflowDefinition back to YAML"""
        data = {
            'name': workflow.name,
            'description': workflow.description,
            'execution_mode': workflow.execution_mode,
            'variables': workflow.variables,
            'steps': [],
            'settings': workflow.settings,
            'completion_criteria': workflow.completion_criteria
        }

        for step in workflow.steps:
            step_dict = {
                'name': step.name,
                'type': step.type,
            }
            if step.description:
                step_dict['description'] = step.description
            if step.command:
                step_dict['command'] = step.command
            if step.parser:
                step_dict['parser'] = step.parser
            if step.output_var:
                step_dict['output_var'] = step.output_var
            if step.depends_on:
                step_dict['depends_on'] = step.depends_on
            if step.condition:
                step_dict['condition'] = step.condition
            if step.on_error != 'fail':
                step_dict['on_error'] = step.on_error
            if step.vendor_specific:
                step_dict['vendor_specific'] = step.vendor_specific
            if step.template:
                step_dict['template'] = step.template
            if step.template_vars:
                step_dict['template_vars'] = step.template_vars
            if step.script:
                step_dict['script'] = step.script
            if step.config_source:
                step_dict['config_source'] = step.config_source
            if step.compare:
                step_dict['compare'] = step.compare
            if step.validation:
                step_dict['validation'] = step.validation

            data['steps'].append(step_dict)

        return yaml.dump(data, default_flow_style=False, sort_keys=False)
