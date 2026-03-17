# NAP Feature Brainstorm: AI & MCP Integration Roadmap

> **Author**: Product Management
> **Date**: 2026-03-04
> **Status**: Draft / Ideation
> **Context**: NAP v2.0.0 — Network Audit Platform with multi-vendor compliance, config management, and workflow automation

---

## Executive Summary

NAP already has strong foundations: a rule engine, workflow DAG executor, config drift detection, multi-vendor connectors, and an integration hub. The next leap is **making NAP intelligent** — using AI to move from reactive auditing to proactive network assurance, and using MCP to make NAP a first-class data source for AI-powered operations teams.

---

## Part 1: AI-Powered Features

### 1.1 Natural Language Rule Builder

**Problem**: Writing audit rules today requires knowledge of XPath, XML filters, and vendor-specific config structures. This limits rule creation to senior network engineers.

**Feature**: Allow users to describe compliance checks in plain English and have AI generate the corresponding rule definition.

**Examples**:
- *"Ensure all BGP peers have MD5 authentication enabled"* → generates XPath + XML filter for Cisco IOS-XR and Nokia SR OS
- *"Check that NTP is configured with at least 2 servers"* → multi-vendor rule with proper severity

**Implementation**:
- LLM integration in `rule-service` with vendor-specific config schema context
- Validation step: AI-generated rules are shown to user for review before saving
- Feedback loop: user corrections improve future suggestions
- Store prompt templates per vendor/feature area

**Value**: 10x faster rule creation, democratizes compliance policy authoring to security/compliance teams who know *what* to check but not *how* to encode it.

**Priority**: P0 — High impact, aligns with core product value

---

### 1.2 Intelligent Remediation Advisor

**Problem**: When an audit fails, operators see what's wrong but must manually figure out the fix. The current remediation workflow requires pre-authored steps.

**Feature**: AI-generated remediation plans based on audit findings, device context, and config history.

**How it works**:
1. Audit result shows: "BGP peer 10.0.0.1 missing authentication"
2. AI analyzes: current config, vendor, OS version, similar devices that are compliant
3. AI generates: step-by-step remediation with exact CLI/NETCONF commands
4. User reviews and approves → workflow engine executes

**Safeguards**:
- AI suggestions are NEVER auto-applied — always human-in-the-loop
- Dry-run mode: show what *would* change before committing
- Rollback plan generated alongside every remediation
- Risk scoring for each suggested change

**Priority**: P0 — Directly reduces MTTR (Mean Time To Remediate)

---

### 1.3 Config Change Impact Analysis

**Problem**: Before pushing a configuration change, operators have no way to predict its blast radius. A BGP policy change could inadvertently affect traffic paths.

**Feature**: AI-powered impact analysis that predicts the consequences of a proposed config change.

**Capabilities**:
- Parse proposed config diff and identify affected protocols/features
- Cross-reference with topology data (BGP peers, IGP adjacencies, MPLS LSPs)
- Predict which services/traffic flows could be impacted
- Flag potential outage risks with confidence scores
- Suggest safer change windows based on traffic patterns

**Data Sources**: Config backups, device metadata (BGP/IGP/MPLS), audit history, change event history

**Priority**: P1 — Differentiator, requires topology awareness

---

### 1.4 Anomaly Detection & Drift Intelligence

**Problem**: Config drift detection today is binary — it tells you *something changed* but not whether that change is *concerning*. Alert fatigue is real.

**Feature**: ML-based anomaly scoring for configuration changes.

**Capabilities**:
- Learn "normal" change patterns per device/group (maintenance windows, standard changes)
- Score each detected drift event: routine (0.1) → suspicious (0.5) → critical (0.9)
- Cluster similar changes across devices to identify coordinated modifications
- Detect "config entropy" — gradual config deviation from baseline across fleet
- Alert only on genuinely anomalous changes, reducing noise by ~80%

**Training Data**: `ConfigChangeEventDB` history, `AuditLogDB` user actions, time-of-day patterns

**Priority**: P1 — Reduces alert fatigue, improves security posture

---

### 1.5 Compliance Posture Prediction

**Problem**: Compliance scores are reactive — you only know your score *after* running an audit.

**Feature**: Predictive compliance scoring that forecasts future compliance posture.

**Capabilities**:
- Trend analysis: "At current drift rate, you'll drop below 90% compliance in 14 days"
- What-if scenarios: "If you apply this rule to all devices, expected compliance impact is..."
- Risk forecasting: identify devices most likely to drift out of compliance
- Proactive alerts before compliance SLA breaches

**Priority**: P2 — Nice to have, builds on existing trend data

---

### 1.6 AI-Powered Config Optimization

**Problem**: Network configs accumulate cruft over years — stale ACLs, unused route-maps, redundant policy statements.

**Feature**: AI analysis of configurations to identify optimization opportunities.

**Capabilities**:
- Detect unused/unreachable config blocks (ACLs with zero hits, route-maps not applied)
- Identify redundant configurations across device groups
- Suggest config simplification while preserving intent
- Benchmark against vendor best practices and CIS guidelines
- Generate cleanup plans as executable workflows

**Priority**: P2 — Operational hygiene, long-term value

---

### 1.7 Natural Language Network Query

**Problem**: Getting answers about network state requires navigating multiple dashboards or writing API queries.

**Feature**: Chat-based interface to query network state using natural language.

**Examples**:
- *"Which devices failed their last BGP audit?"*
- *"Show me all config changes in the last 24 hours on core routers"*
- *"What's the compliance trend for the DC-WEST group?"*
- *"Compare the running config of router-A and router-B"*

**Implementation**:
- LLM with function-calling against NAP's REST API
- Context-aware: understands device groups, rule categories, time ranges
- Results rendered as tables, charts, or diffs depending on query type
- Conversation history for follow-up questions

**Priority**: P1 — Massive UX improvement, showcases AI value immediately

---

### 1.8 Automated Compliance Report Generation

**Problem**: Generating audit reports for compliance officers is manual and time-consuming.

**Feature**: AI-generated executive summaries and detailed compliance reports.

**Capabilities**:
- Transform raw audit data into human-readable narratives
- Framework-specific formatting (SOX, PCI-DSS, NIST, ISO 27001)
- Executive summary with key risk callouts
- Trend visualization with AI-generated commentary
- Scheduled report generation and delivery
- Customizable templates per audience (CTO vs. auditor vs. NOC)

**Priority**: P1 — High business value, directly supports compliance workflows

---

## Part 2: MCP (Model Context Protocol) Features

### 2.1 NAP as an MCP Server

**Problem**: AI assistants (Claude, etc.) can't directly access network state when engineers ask questions or need help troubleshooting.

**Feature**: Expose NAP's capabilities as an MCP server so any MCP-compatible AI client can interact with network infrastructure.

**MCP Tools to Expose**:

```
Tool: nap_get_devices
Description: List and filter network devices by vendor, group, status, compliance score
Parameters: vendor?, group?, status?, min_compliance_score?

Tool: nap_get_device_config
Description: Retrieve current or historical configuration for a device
Parameters: device_id, version? (latest, baseline, or timestamp)

Tool: nap_compare_configs
Description: Compare two configurations and return the diff
Parameters: device_id, version_a, version_b

Tool: nap_run_audit
Description: Execute compliance audit on a device or group
Parameters: target (device_id or group_id), rule_ids?

Tool: nap_get_audit_results
Description: Retrieve audit results with findings and compliance scores
Parameters: device_id?, group_id?, date_range?, severity?

Tool: nap_get_compliance_score
Description: Get current compliance score for device/group/fleet
Parameters: target?, breakdown_by? (rule, category, severity)

Tool: nap_get_config_changes
Description: List configuration changes with diffs and metadata
Parameters: device_id?, date_range?, severity?

Tool: nap_get_hardware_inventory
Description: Retrieve hardware inventory for a device
Parameters: device_id, component_type?

Tool: nap_search_rules
Description: Search audit rules by keyword, category, or severity
Parameters: query?, category?, severity?

Tool: nap_get_health_status
Description: Get device health check results (ping, NETCONF, SSH)
Parameters: device_id?, group_id?

Tool: nap_create_rule
Description: Create a new audit rule (with human approval gate)
Parameters: name, description, vendor, checks[], severity

Tool: nap_execute_workflow
Description: Trigger a workflow execution (with human approval gate)
Parameters: workflow_id, variables?
```

**MCP Resources to Expose**:

```
Resource: nap://devices
Description: Live device inventory with status

Resource: nap://devices/{id}/config
Description: Current running configuration

Resource: nap://compliance/dashboard
Description: Fleet-wide compliance overview

Resource: nap://changes/recent
Description: Recent configuration changes feed

Resource: nap://alerts/active
Description: Active health and compliance alerts
```

**MCP Prompts to Expose**:

```
Prompt: network-troubleshoot
Description: Guided troubleshooting for a device using NAP data
Arguments: device_id, symptom

Prompt: compliance-review
Description: Comprehensive compliance review of a device or group
Arguments: target, framework?

Prompt: change-review
Description: Review recent changes for risk assessment
Arguments: time_range, scope?
```

**Priority**: P0 — This is transformative. Makes NAP data accessible to any AI workflow.

---

### 2.2 MCP-Powered Integration Hub

**Problem**: Current integrations (NetBox, ServiceNow, Ansible, Git) are hard-coded with custom adapters. Adding new integrations requires code changes.

**Feature**: Use MCP as the universal integration protocol. Instead of building custom adapters, NAP connects to other tools via their MCP servers.

**Architecture**:
```
NAP ←→ MCP Client ←→ NetBox MCP Server
                   ←→ ServiceNow MCP Server
                   ←→ Git MCP Server
                   ←→ Ansible MCP Server
                   ←→ Slack MCP Server
                   ←→ PagerDuty MCP Server
                   ←→ Custom MCP Servers
```

**Benefits**:
- Add new integrations without code changes — just register an MCP server
- Bidirectional: NAP consumes and provides MCP services
- Standardized authentication and capability discovery
- Community-built MCP servers for common tools

**New Integrations Enabled**:
- **PagerDuty/OpsGenie**: AI-enriched alerting with full context
- **Jira/Linear**: Auto-create tickets from audit findings
- **Confluence/Notion**: Auto-publish compliance reports
- **Terraform**: Config-as-code bidirectional sync
- **Observability** (Datadog, Splunk, ELK): Correlated network + config events

**Priority**: P1 — Reduces integration maintenance cost, future-proofs the platform

---

### 2.3 MCP-Based Multi-Agent Network Operations

**Problem**: Complex network operations (planned migrations, troubleshooting, capacity planning) require orchestrating multiple data sources and actions.

**Feature**: Multi-agent system where specialized AI agents collaborate through MCP to handle complex network operations.

**Agent Architecture**:
```
┌─────────────────────────────────────────────┐
│              Orchestrator Agent              │
│  (understands user intent, delegates tasks)  │
└──────┬──────────┬──────────┬───────────┬────┘
       │          │          │           │
  ┌────▼───┐ ┌───▼────┐ ┌──▼────┐ ┌───▼─────┐
  │Audit   │ │Config  │ │Health │ │Report   │
  │Agent   │ │Agent   │ │Agent  │ │Agent    │
  │        │ │        │ │       │ │         │
  │Runs    │ │Manages │ │Checks │ │Generates│
  │audits, │ │backups,│ │device │ │reports, │
  │creates │ │diffs,  │ │reach- │ │summaries│
  │rules   │ │drift   │ │ability│ │trends   │
  └────────┘ └────────┘ └───────┘ └─────────┘
```

**Use Cases**:
- **Migration Planning**: "Plan the migration of core-router-01 from IOS-XR 7.3 to 7.9"
  - Config Agent: backs up current config, identifies version-specific syntax
  - Audit Agent: checks current compliance, flags rules needing updates
  - Health Agent: verifies pre-migration health baseline
  - Report Agent: generates migration plan document

- **Incident Response**: "BGP sessions are flapping on PE routers"
  - Health Agent: checks reachability of all PE devices
  - Config Agent: looks for recent config changes on affected devices
  - Audit Agent: verifies BGP-related compliance rules
  - Report Agent: generates incident timeline and RCA draft

**Priority**: P2 — Advanced capability, builds on 2.1 and 2.2

---

### 2.4 MCP Sampling for Autonomous Monitoring

**Problem**: Current health checks and audits run on fixed schedules. They can't dynamically adjust based on conditions.

**Feature**: Use MCP's sampling capability to enable AI-driven adaptive monitoring.

**How it works**:
1. NAP exposes monitoring context via MCP resources
2. AI model (via MCP sampling) continuously evaluates network state
3. When conditions change (new device added, config drift detected, health degradation), AI autonomously:
   - Increases audit frequency on affected devices
   - Triggers targeted health checks
   - Escalates alerts with enriched context
   - Suggests preventive actions

**Scenarios**:
- Device compliance drops below threshold → AI triggers deep audit, checks related devices
- Multiple devices show simultaneous changes → AI flags potential unauthorized access
- Health check failures correlate with recent changes → AI links cause and effect

**Priority**: P2 — Requires mature MCP server (2.1) first

---

## Part 3: AI Infrastructure Features

### 3.1 Embedding-Based Config Search

**Problem**: Finding specific config patterns across hundreds of devices is slow and requires exact-match queries.

**Feature**: Vector embeddings for network configurations enabling semantic search.

**Capabilities**:
- "Find all devices with similar BGP configuration to router-A" (not exact match, semantic similarity)
- "Which devices have ACLs that look like they're doing rate limiting?"
- Cluster devices by config similarity for group management
- Detect outlier configurations within a device group

**Implementation**:
- Embed config blocks using a fine-tuned model aware of network config semantics
- Store embeddings in pgvector (PostgreSQL extension) — minimal infra change
- Update embeddings on config backup
- Expose via search API and MCP tools

**Priority**: P2 — Powerful but requires embedding infrastructure

---

### 3.2 Fine-Tuned Network Config LLM

**Problem**: General-purpose LLMs lack deep understanding of vendor-specific network configurations.

**Feature**: Fine-tuned model (or RAG system) specialized in Cisco IOS-XR and Nokia SR OS configurations.

**Training Data** (all available within NAP):
- Historical config backups (anonymized)
- Audit rules and their explanations
- Remediation workflows and their outcomes
- Config change events with context
- Vendor documentation (via RAG)

**Applications**:
- Powers all other AI features with higher accuracy
- Understands config hierarchy and dependencies
- Knows vendor-specific best practices
- Reduces hallucination risk for network-specific queries

**Priority**: P3 — Long-term investment, start with RAG over vendor docs

---

### 3.3 AI Feedback & Learning Loop

**Problem**: AI suggestions improve only with model updates. No mechanism to learn from user corrections.

**Feature**: Closed-loop learning system where user feedback improves AI accuracy over time.

**Mechanisms**:
- Thumbs up/down on AI-generated rules → improves rule builder
- Accepted/rejected remediation plans → improves advisor
- Corrected anomaly scores → improves drift detection
- User-edited AI reports → improves report generation

**Storage**: `AIFeedbackDB` table linking AI predictions to user outcomes

**Priority**: P2 — Critical for long-term AI accuracy

---

## Part 4: Feature Prioritization Matrix

| Feature | Impact | Effort | Priority | Dependencies |
|---------|--------|--------|----------|-------------|
| NAP as MCP Server (2.1) | Very High | Medium | **P0** | None |
| NL Rule Builder (1.1) | Very High | Medium | **P0** | LLM API access |
| Remediation Advisor (1.2) | Very High | Medium | **P0** | LLM API access |
| NL Network Query (1.7) | High | Medium | **P1** | LLM + NAP API |
| Report Generation (1.8) | High | Low | **P1** | LLM API access |
| MCP Integration Hub (2.2) | High | High | **P1** | MCP Server (2.1) |
| Config Impact Analysis (1.3) | High | High | **P1** | Topology data |
| Anomaly Detection (1.4) | High | High | **P1** | Historical data |
| Compliance Prediction (1.5) | Medium | Medium | **P2** | Trend data |
| Config Optimization (1.6) | Medium | Medium | **P2** | Config corpus |
| Multi-Agent Ops (2.3) | High | Very High | **P2** | MCP Server (2.1) |
| Adaptive Monitoring (2.4) | Medium | High | **P2** | MCP Server (2.1) |
| Config Embeddings (3.1) | Medium | High | **P2** | pgvector |
| AI Feedback Loop (3.3) | Medium | Medium | **P2** | Any AI feature |
| Fine-Tuned LLM (3.2) | High | Very High | **P3** | Training pipeline |

---

## Part 5: Recommended Roadmap

### Phase 1: "AI Foundation" (Q2 2026)
- [x] Feature brainstorm and roadmap
- [x] NAP MCP Server (core tools: devices, configs, audits, compliance)
- [x] LLM integration layer (provider-agnostic: Claude, OpenAI, local models)
- [x] Natural Language Rule Builder (v1: single vendor, guided)
- [x] AI Chat interface in frontend (basic NL query)

### Phase 2: "Intelligent Operations" (Q3 2026)
- [x] Remediation Advisor with human-in-the-loop approval
- [x] Automated Compliance Report Generation
- [x] MCP Integration Hub (replace hardcoded integrations)
- [x] Anomaly scoring for config drift events
- [x] NL Rule Builder v2: multi-vendor, batch generation

### Phase 3: "Proactive Assurance" (Q4 2026)
- [x] Config Change Impact Analysis
- [x] Compliance Posture Prediction
- [x] Config Optimization recommendations
- [x] Embedding-based config search (LLM-based semantic matching; pgvector planned)
- [x] AI Feedback & Learning Loop (feedback widget + interaction history + analytics)

### Phase 4: "Autonomous Operations" (2027)
- [x] Multi-Agent Network Operations
- [x] MCP Sampling for adaptive monitoring
- [x] Domain-specific RAG with vendor knowledge base
- [x] Self-healing workflows (AI-initiated, human-approved)

---

## Part 6: Technical Architecture for AI/MCP

### Proposed Architecture Addition

```
                    ┌──────────────────────┐
                    │   AI Gateway Service  │
                    │      (Port 3006)      │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  LLM Adapter    │  │
                    │  │  (Claude/GPT/   │  │
                    │  │   Local)        │  │
                    │  └─────────────────┘  │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  MCP Server     │  │
                    │  │  (stdio/SSE)    │  │
                    │  └─────────────────┘  │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  Prompt         │  │
                    │  │  Templates      │  │
                    │  └─────────────────┘  │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  Feedback       │  │
                    │  │  Store          │  │
                    │  └─────────────────┘  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──┐   ┌───────▼───────┐  ┌────▼──────┐
    │ Device     │   │ Rule          │  │ Backup    │
    │ Service    │   │ Service       │  │ Service   │
    └────────────┘   └───────────────┘  └───────────┘
```

### New Database Models

```python
# AI interaction tracking
class AIInteractionDB:
    id: UUID
    user_id: UUID
    interaction_type: str  # "rule_builder", "remediation", "query", "report"
    input_prompt: str
    ai_response: JSON
    model_used: str
    tokens_used: int
    feedback: str  # "accepted", "rejected", "modified"
    created_at: datetime

# MCP connection registry
class MCPConnectionDB:
    id: UUID
    name: str
    server_url: str
    transport: str  # "stdio", "sse"
    capabilities: JSON
    auth_config: JSON  # encrypted
    status: str
    last_connected: datetime

# AI-generated rules awaiting approval
class AIRuleDraftDB:
    id: UUID
    source_prompt: str
    generated_rule: JSON
    confidence_score: float
    status: str  # "pending", "approved", "rejected", "modified"
    approved_by: UUID
    created_at: datetime
```

### License Tier Mapping

| Feature | Starter | Professional | Enterprise |
|---------|---------|-------------|------------|
| MCP Server (read-only) | - | Yes | Yes |
| MCP Server (read-write) | - | - | Yes |
| NL Rule Builder | 5/month | 50/month | Unlimited |
| Remediation Advisor | - | Yes | Yes |
| NL Query | 10/month | 100/month | Unlimited |
| Report Generation | - | 10/month | Unlimited |
| Anomaly Detection | - | - | Yes |
| Multi-Agent Ops | - | - | Yes |
| Custom MCP Integrations | - | - | Yes |

---

## Appendix: Competitive Differentiation

Most network automation platforms offer rule-based compliance. NAP's AI/MCP strategy differentiates through:

1. **MCP-first**: Only platform exposing network state via MCP — engineers use their preferred AI tools
2. **Human-in-the-loop AI**: Enterprise-safe AI that suggests but never acts autonomously without approval
3. **Closed-loop learning**: Gets smarter from every user interaction
4. **Multi-vendor intelligence**: AI understands both Cisco IOS-XR and Nokia SR OS semantics
5. **Workflow integration**: AI suggestions feed directly into existing DAG workflow engine

The vision: **NAP becomes the intelligent network operations brain** — not just an audit tool, but an AI-powered network assurance platform.
