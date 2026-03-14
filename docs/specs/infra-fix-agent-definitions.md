# Fix Agent Definitions — Post-Validation Remediation

## Status: 🟡 DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-14 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.1 |
| Last Updated | 2026-03-14 |
| Zone | Infrastructure |
| Blocked By | infra-validate-agent-definitions.md (completed) |

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-fix-agent-definitions.md in its entirety.

This is a remediation spec addressing findings from the agent validation report
at reports/agent-validation-2026-03-14.md. Four things to do:

1. FIX @semantic-modeler (.claude/agents/semantic-modeler.md):
   - Rename "Star/Snowflake Schema Proposal Format" section to "Output Format"
     (keep the content, just fix the heading to match the standard)
   - Add output save path to Key Paths: `governance/models/` → Write — dimensional
     model proposals
   - Create the `governance/models/` directory with a .gitkeep

2. CREATE new agent @policy-engineer (.claude/agents/policy-engineer.md):
   - This is a NEW agent (agent #15) that owns ALL data access policy definitions
   - NOT just RLS/PII — this agent handles any policy that controls who can access
     what data under what conditions
   - Policy types this agent owns:
     a. Row-Level Security (RLS) policies — based on @pii-scanner sensitivity
        classifications (Confidential/Restricted fields get access controls)
     b. Data entitlement policies — business-rule-driven access (e.g., "only users
        entitled to financial sector data can query companies with SIC codes 6000-6999")
     c. Column-level masking policies — which fields get masked for which roles
     d. Retention policies — how long data versions are retained in Iceberg snapshots
     e. AI consumption policies — which governed data products can be exposed to
        which AI systems (relevant for the AI-ready zone and MCP server)
   - Consumes inputs from: @pii-scanner (sensitivity classifications), specs
     (business rules), data contracts (consumable zone access requirements)
   - Output goes to: `governance/policies/` (create this directory)
   - Policy format: JSON files, one per policy, with fields for: policy_id,
     policy_type, target (table/field), rule definition, justification, roles
     affected, agent that created it, spec reference, created timestamp
   - Must follow the same agent definition structure as all other agents: role
     summary, responsibilities, output format, scope boundaries, audit trail,
     key paths
   - This agent is NOT mandatory on every spec — it runs when a spec creates
     data products that need access policies, or when @pii-scanner flags fields
     that need protection
   - Scope boundaries: does NOT detect PII (that's @pii-scanner), does NOT
     implement access controls in code (it defines policies as artifacts), does
     NOT make business decisions about who should access what (it translates
     requirements from specs and classifications into formal policy definitions)

3. UPDATE @pii-scanner (.claude/agents/pii-scanner.md):
   - In Scope Boundaries, CHANGE the line "Create RLS policies — you inform
     policy decisions with your findings" to: "Create access policies — you
     classify sensitivity, @policy-engineer creates the policies based on
     your classifications"
   - Add a note in Responsibilities or a new "Downstream Handoff" section:
     "After scanning, your sensitivity classifications are consumed by
     @policy-engineer to generate RLS and access policies. Ensure your
     classifications include enough context (field, sensitivity level,
     PII category, justification) for @policy-engineer to act on them."

4. CLEAN UP validation artifacts:
   - The agent validation scenario tests wrote sample files to governance/,
     tests/, and docs/sessions/. These are test artifacts, not real pipeline
     output.
   - Remove any files created during validation that are NOT:
     - Agent definitions in .claude/agents/
     - The validation report in reports/
     - Spec files in docs/specs/
     - .gitkeep files
   - List every file you remove so we have a record
   - Do NOT remove the validation report itself
   - Do NOT remove any agent definition files
   - Do NOT remove any spec files

After all four tasks are complete:
- Verify @semantic-modeler has "Output Format" heading and governance/models/ in Key Paths
- Verify @policy-engineer exists with all required sections
- Verify governance/policies/.gitkeep exists
- Verify governance/models/.gitkeep exists
- Verify @pii-scanner references @policy-engineer as downstream consumer
- Verify @pii-scanner Scope Boundaries no longer claims it doesn't create policies
  (it should say @policy-engineer does that)
- Verify no stale validation artifacts remain
- Count agent files: should be 15 total
- List all changes made
```

---

## 1. Problem Statement

The agent validation (reports/agent-validation-2026-03-14.md) found one structural failure and four gaps. This spec addresses:

1. **Structural fix**: @semantic-modeler missing standard "Output Format" heading and output save path
2. **New agent**: @policy-engineer — owns all data access policy definitions (RLS, entitlements, masking, retention, AI consumption policies). This is a new agent (#15) that fills the RLS gap identified in validation AND provides a home for future policy types beyond PII-driven access controls.
3. **@pii-scanner update**: Clarify handoff to @policy-engineer
4. **Cleanup**: Remove validation test artifacts

## 2. Why a New Agent Instead of Expanding @pii-scanner

@pii-scanner detects PII and classifies sensitivity. Policy creation is a fundamentally different responsibility:

- **PII-driven policies** (RLS on officer names) are just one policy type
- **Business-rule policies** (entitle only financial sector companies to certain users) have nothing to do with PII
- **Retention policies** (how long Iceberg snapshots are kept) have nothing to do with PII
- **AI consumption policies** (which data products can be exposed via MCP server) have nothing to do with PII
- Mixing detection and policy creation in one agent violates separation of concerns

@pii-scanner stays focused: detect and classify. @policy-engineer takes classifications (from @pii-scanner) and business rules (from specs) and produces formal policy definitions.

## 3. @policy-engineer — Agent Design

### Role
Owns all data access policy definitions across the project. Translates sensitivity classifications, business rules, and data contract requirements into formal, structured policy artifacts.

### Policy Types

| Type | Trigger | Example |
|------|---------|---------|
| RLS (Row-Level Security) | @pii-scanner flags Confidential/Restricted fields | Officer names: redacted by default, full access for compliance |
| Data Entitlement | Spec defines business-rule access | Only financial sector analysts see SIC 6000-6999 companies |
| Column Masking | @pii-scanner flags fields needing partial visibility | Show last 4 digits of EIN, mask rest |
| Retention | Data contract specifies snapshot retention | Keep 24 months of Iceberg snapshots, archive older |
| AI Consumption | AI-ready zone spec defines model access | MCP server exposes revenue data but not PII fields |

### Pipeline Position
Not mandatory on every spec. Runs when:
- @pii-scanner produces new sensitivity classifications (downstream of PII scan)
- A spec explicitly defines business-rule access policies
- A consumable or AI-ready zone data contract specifies access requirements

### Output Location
`governance/policies/` — one JSON file per policy

### Policy Format
```json
{
  "policy_id": "POL-001",
  "policy_type": "rls",
  "target": {
    "table": "base.financial_facts",
    "field": "officer_name"
  },
  "rule": {
    "default_action": "REDACT",
    "role_overrides": {
      "compliance_officer": "FULL_ACCESS",
      "analyst": "REDACT",
      "public_api": "EXCLUDE"
    }
  },
  "justification": "Officer names classified as Confidential (Level 3) by @pii-scanner. Redacted by default, full access restricted to compliance roles.",
  "source_classification": "governance/pii-scans/company-facts-pii-scan.md",
  "agent": "@policy-engineer",
  "spec_reference": "docs/specs/raw-ingest-xbrl-company-facts.md",
  "created": "2026-03-14T12:00:00Z"
}
```

## 4. Deferred Gaps (Not Addressed Here)

| Gap | Resolution Plan | When |
|-----|----------------|------|
| Iceberg DDL execution | Expand @temporal-modeler scope when writing base zone specs | Phase 2 |
| Fiscal calendar alignment | Assign to @temporal-modeler when writing consumable zone spec | Phase 4 |

---

## Testing Checklist

- [ ] @semantic-modeler has "Output Format" section heading
- [ ] @semantic-modeler Key Paths includes `governance/models/`
- [ ] `governance/models/.gitkeep` exists
- [ ] @policy-engineer agent file exists at `.claude/agents/policy-engineer.md`
- [ ] @policy-engineer has all required sections (role, responsibilities, output format, scope boundaries, audit trail, key paths)
- [ ] @policy-engineer covers all 5 policy types (RLS, entitlement, masking, retention, AI consumption)
- [ ] @policy-engineer references @pii-scanner as upstream input
- [ ] @policy-engineer output goes to `governance/policies/`
- [ ] `governance/policies/.gitkeep` exists
- [ ] @pii-scanner references @policy-engineer as downstream consumer
- [ ] @pii-scanner Scope Boundaries no longer says it doesn't create policies (says @policy-engineer does)
- [ ] 15 agent files total in `.claude/agents/`
- [ ] No stale validation artifacts in governance/, tests/, or docs/sessions/
- [ ] Validation report still exists in reports/

---

## Appendix A: Related Specs

| Spec | Relevance |
|------|-----------|
| `infra-create-agent-definitions.md` | Created the original 14 agents |
| `infra-validate-agent-definitions.md` | Found the gaps this spec addresses |
| `infra-setup-duckdb-iceberg.md` | Next spec — blocked until agents are fixed |
