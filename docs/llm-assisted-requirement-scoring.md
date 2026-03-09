# Software Requirements Specification

## LLM-Assisted Security Framework Requirement Scoring Engine

### (Cost-Optimized OpenAI Implementation)

---

# 1. Purpose

The system shall evaluate a single security framework requirement (e.g., a NIST CSF control) and produce three structured assessment scores (0–100%) with detailed LLM-generated explanations.

The system must:

* Use deterministic numeric scoring logic
* Use LLMs only for structured classification and narrative explanation
* Minimize OpenAI API cost per requirement
* Support three assessment depths:

  * Design
  * Design + Implementation
  * Design + Implementation + Operating Effectiveness

Excluded from scope:

* Reviewer overrides
* Score aggregation across requirements
* Calibration learning
* Historical model training

---

# 1a. Policy Statement Extraction (Pre-Scoring Stage)

Before the scoring phases, users may run a **Policy Statement Extraction** step for any requirement. This is an on-demand, user-triggered LLM call that extracts specific policy statements from mapped documents.

## Purpose

Extract concrete, specific policy statements (commitments, rules, procedures) from mapped policy documents that are directly relevant to the requirement. The extracted statements serve as structured input for future scoring phases.

## Trigger

User-initiated from the Scores page, per requirement. Extraction is independent of scoring — a user may run it at any time, in any order relative to scoring.

## Qualifying Documents

Policy-type documents only (`document_type = "policy"`). Same threshold logic as scoring:
- `is_rejected = False`
- `relevance_percentage >= threshold` (per-requirement override → assessment default → 80%)
- Document has `content_text`

Evidence documents are excluded from this stage.

## LLM Inputs

1. **Requirement** — code, name, description
2. **Implementation examples** — optional list from framework metadata (e.g., NIST CSF `implementation_examples`); used to help the LLM identify genuinely relevant statements
3. **Policy documents** — all qualifying mapped policy documents (title + content)

## LLM Output

A list of structured statement objects:

```json
{
  "statements": [
    {
      "statement": "Full extracted policy statement text with all detail",
      "document_title": "Exact document title from available_document_titles",
      "document_section": "Section or clause name, or null"
    }
  ]
}
```

There may be zero, one, or many statements. The LLM is instructed to search ALL provided documents.

## Persistence

Statements are saved per `(assessment_id, requirement_id)` in the `policy_statements` table. Re-running extraction deletes all existing statements for that pair and generates fresh ones.

## User Controls

- **Run Extraction** — triggers the LLM call
- **Re-run Extraction** — clears existing statements and re-extracts
- **Mark as Irrelevant** — deletes a specific statement from the saved set

## UI Indicators

- Green checkmark: statements were found
- Red X: extraction ran but no relevant statements found
- Status shown in collapsed accordion header for at-a-glance awareness

## Implementation Examples (NIST CSF)

NIST CSF 2.0 subcategories include `implementation_examples` loaded from the official NIST documentation. These are included in the extraction prompt when available. Other frameworks may add `implementation_examples` to requirement `extra_metadata` to enable the same behavior.

---

---

# 2. Inputs

Each assessment instance shall receive:

## 2.1 Control Documentation (Input 1)

Two categories of documents are supported, stored in the `policies` table with a `document_type` column:

| `document_type` | Purpose |
|---|---|
| `policy` | Design-level documentation — policies, procedures, standards. Used in Phase 2 (Documentation Score). Policy statements are extracted from these documents before scoring. |
| `evidence` | Implementation evidence — configuration exports, audit logs, test results, screenshots. Used in Phase 2 at implementation depth to assess evidence support for each policy statement. |

Depth determines which document types are evaluated:

* Design — policy documents only (Phase 2 design variant)
* Design + Implementation — policy documents + evidence documents (Phase 2 implementation variant)
* Design + Implementation + Operating Effectiveness — same as implementation

---

## 2.2 Risk Profile (Input 2)

Structured metadata describing:

* Nature of information handled

---

## 2.3 Company Profile (Input 3)

Structured metadata, including:

* Industry
* Business description (e.g. company size, operational context)
* Product/service description (e.g. what is product, how is data stored, etc)

---

## 2.4 Best Practice Context (Input 4)

LLM-derived contextual expectations for:

* North American companies
* Industry peers
* Similar risk profile organizations

---

# 3. Outputs

For each requirement, the system must produce:

---

## 3.1 Score 1 — Requirement Met by Documentation

Score 1 is a single coverage label mapped to a numeric value:

| Coverage Label | Score 1 Value |
|---|---|
| `Covered` | 100 |
| `Partial` | 50 |
| `Gap` | 0 |

The label is produced by Phase 2 (Documentation Score LLM call) based on extracted policy statements
and (at implementation depth) supporting evidence for each statement.

Score 1 is skipped when:

| Depth | Policy statements | Evidence docs | Result |
|---|---|---|---|
| design | 0 | — | skipped (`no_policy_statements`) |
| design | > 0 | — | scored |
| implementation | 0 | 0 | skipped (`no_documentation`) |
| implementation | 0 | > 0 | scored (evidence-only variant) |
| implementation | > 0 | any | scored |

Each sub-score produces its own explanation:
* `score1_design_explanation` — executive summary, supporting documents, deficiencies, improvements
* `score1_implementation_explanation` — same structure with implementation-specific vocabulary

Plus:

* `score1_explanation` — top-level explanation (same as `score1_design_explanation`)
* Supporting documents anchored to exact document titles from `available_document_titles`

---

## 3.2 Score 2 — Risk-Based Best Practice Adequacy (0–100%)

Based on:

* Control documentation
* Risk profile
* North American best practices

Plus:

* Gap explanation
* Risk-weighted improvement recommendations

---

## 3.3 Score 3 — Peer Alignment (Industry + Risk) (0–100%)

Based on:

* Control documentation
* Risk profile
* Company profile
* North American peer best practices

Plus:

* Peer-alignment explanation
* Industry-specific improvement guidance

---

# 4. Cost-Effective Model Specification (OpenAI API)

Because scoring occurs per requirement and assessments may contain hundreds of requirements, API cost control is mandatory.

---

## 4.1 Approved Model Tiers

The system shall support configurable model tiers:

### Tier 1 — Default (Cost-Optimized)

Use a small or mini model (e.g., GPT-4o-mini or equivalent).

Use for:

* Requirement decomposition
* Mechanism extraction
* Classification tasks
* Structured scoring
* Standard explanations

This tier shall be the default for production.

---

### Tier 2 — Enhanced (Optional)

Use a mid-tier model (e.g., GPT-4.1 or equivalent) only if:

* Output quality falls below threshold
* Requirement complexity exceeds threshold
* Manual override flag triggers escalation

Escalation must be explicit and configurable.

---

## 4.2 Token Budget Requirements

The system must:

* Target ≤ 6,000 input tokens per LLM call
* Target ≤ 1,200 output tokens per call
* Enforce hard output length caps in prompts
* Avoid redundant context duplication across calls

If documentation exceeds token limits:

* Summarize once (single LLM call)
* Reuse summary for subsequent phases

---

## 4.3 Maximum API Calls Per Requirement

The system shall not exceed:

4 LLM calls per requirement

Target consolidation:

* Prefer 3 calls if token limits allow

---

## 4.4 Prompt Optimization Rules

All prompts must:

* Use structured JSON output
* Set temperature = 0
* Prohibit free numeric scoring
* Prohibit verbose narrative beyond specified limits
* Include explicit response schema

---

## 4.5 Estimated Cost Targets

The system shall be architected to approximate:

* ~$0.005–$0.02 per requirement using Tier 1 model
* <$20 for a 200-requirement assessment under normal conditions

These targets assume:

* 3–4 LLM calls per requirement
* Optimized token usage
* Controlled explanation length

---

# 5. Scoring Architecture

---

# Policy Extraction Stage — Policy Statement Extraction (1 LLM Call, on-demand)

User-triggered. See Section 1a for full specification.

Inputs: requirement, implementation examples (if available), qualifying policy documents.
Output: list of `{ statement, document_title, document_section }` objects saved to `policy_statements` table.

---

# Phase 2 — Documentation Score (1 LLM Call)

LLM evaluates extracted policy statements against the requirement and returns a single coverage label.
Policy statements are sourced from the `policy_statements` table (see Section 1a for extraction).

## Skip Logic

* **Design depth**: skip if zero policy statements exist for this requirement (skip_reason: `no_policy_statements`)
* **Implementation depth**: skip if zero policy statements AND zero qualifying evidence documents (skip_reason: `no_documentation`)

## Coverage Label

The LLM returns one of three labels:

| Label | Score 1 Value | Meaning |
|-------|--------------|---------|
| `Covered` | 100 | All key aspects of the requirement are addressed in policy |
| `Partial` | 50 | Some aspects are covered but gaps exist |
| `Gap` | 0 | No meaningful policy coverage found |

## Prompt Variants

**Design depth** — Inputs: requirement, policy statements, implementation examples (if any).
LLM evaluates whether the statements collectively satisfy the requirement.

**Implementation depth with statements** — Inputs: requirement, policy statements, implementation examples,
evidence documents. LLM additionally evaluates per-statement evidence support:

```json
{
  "coverage_label": "Covered|Partial|Gap",
  "explanation": "...",
  "recommendations": [{"type": "Policy|Evidence", "action": "..."}],
  "policy_statement_evaluations": [
    {
      "statement_id": "S1",
      "statement": "...",
      "has_evidence": true,
      "supporting_evidence": "..."
    }
  ]
}
```

**Implementation depth without statements (evidence-only)** — Used when policy statements are absent but
evidence documents exist. LLM evaluates evidence directly and notes the absence of policy documentation.

## Rubrics

**Design depth:**
* `Covered` — Statements collectively address all key aspects of the requirement
* `Partial` — Some aspects covered but meaningful gaps remain
* `Gap` — No statements or statements do not address the requirement

**Implementation depth:**
* `Covered` — Complete policy coverage AND each policy statement has supporting evidence
* `Partial` — Partial policy coverage OR some statements lack supporting evidence
* `Gap` — No policy documentation at all (or all statements lack evidence)

Output stored in: `phase2_output` (DB column), `score1_explanation`

---

# Phase 3 — Deterministic Score 1 Calculation

System maps the coverage label from Phase 2 to a numeric score:

* `Covered` → 100.0
* `Partial` → 50.0
* `Gap` → 0.0

Score 1 is a single value regardless of assessment depth. No sub-scores exist.
LLM must not perform arithmetic.

---

# Phase 4 — Expected Mechanism Extraction (1 LLM Call)

Using:

* Risk profile
* Company profile
* Best practice context

LLM must return:

```json
{
  "risk_based_mechanisms": [...],
  "peer_based_mechanisms": [...]
}
```

Each mechanism must include:

* Description
* Risk criticality (High / Medium / Low)

---

# Phase 5 — Mechanism Evaluation (1 LLM Call)

For each mechanism, LLM must classify:

* Present and Robust
* Present but Weak
* Missing

Must also provide:

* Gap explanation
* Improvement recommendation
* Depth-sensitive commentary

Structured JSON required.

**Compliance Picture (replacing raw documents):**
Phases 4 and 5 receive a `company_compliance_picture` (structured findings from Phase 2)
instead of raw document text. This reduces token usage and improves accuracy by providing structured
policy statement findings. The compliance picture contains:

```json
{
  "policy_statements": [
    {
      "statement": "...",
      "document_title": "...",
      "has_evidence": true,
      "supporting_evidence": "..."
    }
  ],
  "coverage_summary": "2-3 sentence Phase 2 explanation"
}
```

The compliance picture includes NO coverage label — it provides factual information only (statements and evidence support), leaving subjective interpretation to the LLM in Phase 5.

---

# Phase 6 — Deterministic Score 2 Calculation

Map status:

* Present and Robust = 1.0
* Present but Weak = 0.5
* Missing = 0.0

Risk weights:

* High = 3
* Medium = 2
* Low = 1

Score2 formula:

Score2 = (Sum(status_value × risk_weight) / Sum(max_possible_weighted_score)) × 100

---

# Phase 7 — Deterministic Score 3 Calculation

Same formula as Score2, applied to peer-based mechanisms only.

---

# 6. Explanation Requirements

## Score 1 (Phase 2 output)

The Phase 2 LLM call produces:

1. `coverage_label` — one of `Covered`, `Partial`, `Gap`
2. `explanation` — 1-3 sentence rationale for the label
3. `recommendations` — list of `{ type: "Policy"|"Evidence", action: "..." }` items
4. `policy_statement_evaluations` (implementation depth only) — per-statement evidence assessment

## Scores 2 and 3 (Phase 5 output)

For each of Scores 2 and 3, the LLM must produce:

1. Executive summary (≤ 3 sentences)
2. Structured deficiency list
3. Improvement guidance aligned to:

   * Design level
   * Implementation level
   * Operating effectiveness level

Explanations must:

* Avoid generic language
* Reflect risk and industry context
* Stay within token cap

---

# 7. Determinism Requirements

* All numeric scoring logic deterministic
* LLM classifications constrained to predefined categories
* No LLM-generated numeric fields
* Prompt templates version-controlled
* Same inputs must produce identical numeric outputs

---

# 8. Success Criteria

The system is successful if:

1. Numeric scores are reproducible.
2. Depth level materially affects scoring.
3. Risk weighting affects Score 2 and Score 3.
4. Explanations are aligned with structured deficiencies.
5. API usage stays within defined cost envelope.
