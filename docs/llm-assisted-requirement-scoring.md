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

# 2. Inputs

Each assessment instance shall receive:

## 2.1 Control Documentation (Input 1)

Two categories of documents are supported, stored in the `policies` table with a `document_type` column:

| `document_type` | Purpose |
|---|---|
| `policy` | Design-level documentation — policies, procedures, standards. Used in Phase 2a. |
| `evidence` | Implementation evidence — configuration exports, audit logs, test results, screenshots. Used in Phase 2b (implementation depth only). |

Depth determines which document types are evaluated:

* Design — policy documents only (Phase 2a)
* Design + Implementation — policy documents (Phase 2a) + evidence documents (Phase 2b)
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

## 3.1 Score 1 — Requirement Met by Documentation (0–100%)

Score 1 is a composite of two sub-scores:

**Score 1a — Design** (`score1_design`): Evaluated from policy documents via Phase 2a.
Always uses design-level status vocabulary (`Fully Addressed`, `Partially Addressed`, `Not Addressed`)
regardless of assessment depth, because policies describe intent, not deployment.

**Score 1b — Implementation** (`score1_implementation`): Evaluated from evidence documents via Phase 2b.
Only computed at implementation depth. `null` means N/A (design depth). `0.0` means no evidence
documents were mapped (penalised).

Status vocabulary for Phase 2b: `Fully Implemented`, `Partially Implemented`, `No Evidence Found`.

**Composite Score 1** (`score1`) = average of Score 1a and Score 1b (when both are present).
At design depth, Score 1 = Score 1a.

Edge cases:

| Depth | Policy docs | Evidence docs | Score 1a | Score 1b | Composite |
|---|---|---|---|---|---|
| design | ✓ | — | calculated | null (N/A) | = Score 1a |
| design | ✗ | — | skipped | null (N/A) | skipped |
| implementation | ✓ | ✓ | calculated | calculated | average |
| implementation | ✓ | ✗ | calculated | 0% + warning | average (penalised) |
| implementation | ✗ | ✓ | 0% + warning | calculated | average (penalised) |
| implementation | ✗ | ✗ | skipped | skipped | skipped |

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

# Phase 1 — Requirement Decomposition (1 LLM Call)

LLM shall decompose the requirement into atomic evaluative elements.

Structured JSON output:

```json
{
  "elements": [
    { "id": "E1", "description": "..." }
  ]
}
```

This output must be reused for Score 1.

---

# Phase 2a — Policy/Design Evaluation (1 LLM Call)

LLM classifies each requirement element against policy documents (design-level documentation).
This phase always runs if policy documents are available, regardless of assessment depth.

Allowed status values (always design-level vocabulary):

* Fully Addressed
* Partially Addressed
* Not Addressed

Structured JSON required with:

* Status per element
* Evidence reference
* Deficiency summary
* `score1_explanation` with executive summary, supporting documents, deficiencies, improvements

The Phase 2a prompt provides an `available_document_titles` list with exact `policy_name` values.
The LLM must select supporting document titles exclusively from this list (copied character-for-character).

Output stored in: `phase2_output` (DB column), `score1_design_explanation`

---

# Phase 2b — Implementation Evidence Evaluation (1 LLM Call, implementation depth only)

LLM classifies each requirement element against evidence documents (implementation artifacts).
This phase only runs at implementation depth. If no evidence documents are mapped, `score1_implementation = 0.0` with a warning explanation.

Allowed status values (implementation vocabulary):

* Fully Implemented
* Partially Implemented
* No Evidence Found

The prompt optionally receives `design_evaluation_context` (Phase 2a element evaluations) to help
the LLM judge whether the evidence confirms the documented design is deployed.

Output stored in: `phase2b_output` (DB column), `score1_implementation_explanation`

---

# Phase 2b Edge Case: No Design Context

If no policy documents exist but evidence documents do, Phase 2b runs without `design_evaluation_context`.
The prompt instructs the LLM to evaluate evidence directly and note where design documentation would be needed.

---

# Phase 3 — Deterministic Score 1 Calculation

System computes Score 1a (Design) from Phase 2a element evaluations and Score 1b (Implementation)
from Phase 2b element evaluations using the same formula:

Sub-score = (Sum(element_values) / Total_elements) × 100

Status → value mapping (design vocabulary):
* Fully Addressed → 1.0
* Partially Addressed → 0.5
* Not Addressed → 0.0

Status → value mapping (implementation vocabulary):
* Fully Implemented → 1.0
* Partially Implemented → 0.5
* No Evidence Found → 0.0

Composite Score 1 = (Score 1a + Score 1b) / 2 when both sub-scores are present.
At design depth, Score 1 = Score 1a (Score 1b is null/N/A).

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
Phase 5 receives a `company_compliance_picture` (structured findings distilled from Phases 2a/2b)
instead of raw document text. This reduces token usage and improves accuracy by providing structured,
element-level findings. The compliance picture contains:

```json
{
  "element_findings": [
    {
      "id": "E1",
      "description": "...",
      "design_status": "Fully Addressed",
      "design_evidence_reference": "...",
      "design_deficiency": null,
      "implementation_status": "Partially Implemented",
      "implementation_evidence_reference": "...",
      "implementation_deficiency": "..."
    }
  ],
  "design_coverage_summary": "2-3 sentence Phase 2a executive summary",
  "implementation_coverage_summary": "2-3 sentence Phase 2b executive summary"
}
```

Phase 4 also receives the compliance picture instead of raw documents.

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

For each of the three scores, LLM must produce:

1. Executive summary (≤ 3 sentences)
2. Structured deficiency list
3. Improvement guidance aligned to:

   * Design level
   * Implementation level
   * Operating effectiveness level

For Score 1 specifically, LLM must also produce:

4. Supporting documents — an accurate list of which provided context documents contained relevant information, with a brief description of what was found in each. Titles must match the `available_document_titles` list exactly.

Explanations must:

* Reference specific missing elements
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
