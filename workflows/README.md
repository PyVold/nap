# Workflow Manager

The Workflow Manager enables orchestration of complex network automation tasks through YAML-defined workflows. It supports sequential, parallel (DAG), and hybrid execution modes with vendor-specific capabilities.

## Features

- **YAML-Based Definitions**: Define workflows in human-readable YAML format
- **Multiple Execution Modes**: Sequential, DAG (parallel), and Hybrid
- **7 Step Types**: Query, Template, Audit, Remediate, Transform, API Call, Notification
- **Vendor-Specific Support**: Nokia (pySROS/XPath) and Cisco (NETCONF/XML)
- **Templating**: Jinja2 template rendering with variable substitution
- **Conditional Execution**: Execute steps based on previous results
- **Retry Logic**: Automatic retry with configurable attempts
- **Scheduling**: Cron-based scheduling and event-triggered execution
- **Step Logging**: Complete audit trail with timestamps and results

## Workflow Structure

```yaml
name: "Workflow Name"
description: "Workflow description"
execution_mode: sequential|dag|hybrid
variables:
  key: value

steps:
  - name: step_name
    type: query|template|audit|remediate|transform|api_call|notification
    output_var: variable_name
    depends_on: [step1, step2]  # For DAG/hybrid modes
    condition: "{{ previous_step.success }}"  # Optional conditional
    retry_count: 3  # Optional retry
    timeout: 300  # Optional timeout in seconds
```

## Step Types

### 1. Query Step
Execute commands on network devices and collect data.

```yaml
- name: collect_isis_neighbors
  type: query
  output_var: isis_data
  vendor_specific:
    nokia:
      method: pysros
      xpath: "/state/router[router-name='Base']/isis"
    cisco:
      method: netconf
      filter: "<isis-state/>"
```

### 2. Template Step
Render Jinja2 templates with collected data.

```yaml
- name: render_twamp_config
  type: template
  output_var: twamp_config
  template_file: "twamp_config.j2"
  template_vars:
    isis_neighbors: "{{ isis_data.neighbors }}"
    router_id: "{{ device.management_ip }}"
```

### 3. Audit Step
Compare expected vs actual configurations.

```yaml
- name: audit_twamp_config
  type: audit
  output_var: audit_result
  diff_mode: true
  compare:
    expected: "{{ twamp_config.rendered_config }}"
    actual: "{{ current_config.raw_output }}"
  thresholds:
    pass_threshold: 95
```

### 4. Remediate Step
Push configurations to devices.

```yaml
- name: deploy_config
  type: remediate
  output_var: deploy_result
  config_source: "{{ twamp_config }}"
  rollback_on_error: true
  vendor_specific:
    nokia:
      method: pysros
      xpath_operations:
        - action: update
          xpath: "/configure/service/twamp"
      commit: true
      commit_comment: "TWAMP workflow deployment"
    cisco:
      method: netconf
      edit_config:
        target: candidate
        operation: merge
      commit: true
```

### 5. Transform Step
Execute Python scripts to transform data.

```yaml
- name: process_neighbors
  type: transform
  output_var: processed_data
  script: |
    neighbors = isis_data.get('neighbors', [])
    result = {
        'count': len(neighbors),
        'active': [n for n in neighbors if n['status'] == 'Up']
    }
```

### 6. API Call Step
Make HTTP requests to external systems.

```yaml
- name: create_servicenow_ticket
  type: api_call
  output_var: ticket_response
  api_url: "https://instance.service-now.com/api/now/table/incident"
  api_method: POST
  api_auth:
    type: basic
    username: "{{ servicenow_user }}"
    password: "{{ servicenow_password }}"
  api_headers:
    Content-Type: "application/json"
  api_body:
    short_description: "Config deployed on {{ device.hostname }}"
    category: "Network"
    priority: 3
```

Supported auth types:
- `basic`: Basic authentication with username/password
- `bearer`: Bearer token authentication

Supported HTTP methods: GET, POST, PUT, DELETE, PATCH

### 7. Notification Step
Send alerts via email, webhook, or Slack.

```yaml
- name: send_notification
  type: notification
  output_var: notification_result
  channels: [slack, webhook]
  message_template: |
    Workflow {{ workflow.name }} completed on {{ device.hostname }}
    Status: {{ audit_result.compliance }}% compliant
```

## Execution Modes

### Sequential
Steps execute one after another in order.

```yaml
execution_mode: sequential
steps:
  - name: step1
  - name: step2  # Runs after step1
  - name: step3  # Runs after step2
```

### DAG (Directed Acyclic Graph)
Steps execute in parallel based on dependencies.

```yaml
execution_mode: dag
steps:
  - name: query_isis
    depends_on: []
  - name: query_interfaces
    depends_on: []
  - name: render_config
    depends_on: [query_isis, query_interfaces]  # Waits for both
```

### Hybrid
Mix sequential and parallel execution.

```yaml
execution_mode: hybrid
steps:
  - name: collect_data
    depends_on: []
  - name: parallel_task1
    depends_on: [collect_data]
  - name: parallel_task2
    depends_on: [collect_data]  # Runs in parallel with parallel_task1
  - name: final_task
    depends_on: [parallel_task1, parallel_task2]
```

## Variable Substitution

Use Jinja2 syntax for variable substitution:

```yaml
variables:
  monitoring_api_token: "secret-token-123"

steps:
  - name: api_call
    api_url: "https://api.example.com/device/{{ device.hostname }}"
    api_headers:
      Authorization: "Bearer {{ monitoring_api_token }}"
    api_body:
      ip: "{{ device.management_ip }}"
      data: "{{ previous_step.output }}"
```

Available context variables:
- `{{ device.* }}`: Device properties (hostname, management_ip, vendor, etc.)
- `{{ workflow.* }}`: Workflow properties (name, id, etc.)
- `{{ step_name.* }}`: Output from previous steps
- Custom variables from `variables` section

## Conditional Execution

Execute steps conditionally based on previous results:

```yaml
- name: deploy_config
  condition: "{{ audit_result.compliance < 100 }}"

- name: send_alert
  condition: "{{ deploy_config.executed and deploy_config.success }}"
```

## Scheduling

### Manual Execution
Execute workflows on-demand via UI or API.

### Scheduled Execution
Use cron expressions for recurring execution:

```python
# API: POST /workflows/{id}/schedules
{
  "cron_expression": "0 2 * * *",  # Daily at 2 AM
  "enabled": true,
  "device_group_id": 1
}
```

### Event-Triggered Execution
Trigger workflows based on events (e.g., config drift detected, device down).

## API Endpoints

- `GET /workflows` - List all workflows
- `GET /workflows/{id}` - Get workflow details
- `POST /workflows` - Create workflow from YAML
- `PUT /workflows/{id}` - Update workflow
- `DELETE /workflows/{id}` - Delete workflow
- `POST /workflows/{id}/execute` - Execute workflow
- `GET /executions` - List executions
- `GET /executions/{id}` - Get execution details
- `GET /executions/{id}/steps` - Get step logs
- `POST /executions/{id}/cancel` - Cancel execution

## Example: TWAMP Audit & Deployment

See `workflows/examples/twamp_audit_deployment.yaml` for a complete example demonstrating:
- ISIS neighbor collection
- Interface querying
- Configuration templating
- Config auditing
- Automatic remediation
- ServiceNow ticket creation
- Monitoring system integration
- Notifications

## Best Practices

1. **Use descriptive step names**: Makes logs easier to read
2. **Set appropriate timeouts**: Prevent hanging on slow operations
3. **Enable rollback**: Use `rollback_on_error: true` for remediation steps
4. **Test workflows**: Start with small device groups
5. **Monitor executions**: Check step logs for errors
6. **Use conditions wisely**: Avoid unnecessary steps
7. **Store sensitive data securely**: Use variables for credentials
8. **Version control workflows**: Keep YAML files in git

## Troubleshooting

### Workflow fails to parse
- Check YAML syntax (indentation, quotes)
- Validate step types and required fields
- Ensure no circular dependencies in DAG mode

### Step execution errors
- Check step logs: `GET /executions/{id}/steps`
- Verify device connectivity
- Validate template syntax
- Check variable references

### Performance issues
- Use DAG mode for independent steps
- Set appropriate timeouts
- Consider breaking large workflows into smaller ones

## Database Tables

- `workflows`: Workflow definitions
- `workflow_executions`: Execution tracking
- `workflow_step_logs`: Step-level logs
- `workflow_schedules`: Cron schedules
- `workflow_triggers`: Event triggers
