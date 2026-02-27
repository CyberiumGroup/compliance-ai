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

May include:

* Policies
* Procedures
* Evidence
* Process documentation

Depth depends on assessment type:

* Design
* Design + Implementation
* Design + Implementation + Operating Effectiveness

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

## 3.1 Score 1 — Requirement Met by Design (0–100%)

Based on:

* Control documentation
* Assessment depth

Plus:

* Executive explanation
* Structured deficiency list
* Improvement guidance aligned to depth

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

# Phase 2 — Control Evaluation Against Elements (1 LLM Call)

LLM must classify each element based on assessment depth.

Allowed classifications vary by depth:

### Design

* Fully Addressed
* Partially Addressed
* Not Addressed

### Design + Implementation

* Fully Designed and Implemented
* Designed but Not Implemented
* Partially Implemented
* Not Addressed

### Design + Implementation + Operating Effectiveness

* Fully Designed, Implemented, and Operating Effectively
* Implemented but Not Operating Consistently
* Designed but Not Implemented
* Not Addressed

Structured JSON required with:

* Status
* Evidence reference
* Deficiency summary

---

# Phase 3 — Deterministic Score 1 Calculation

System shall compute:

Score1 = (Sum(element_values) / Total_possible_value) × 100

Numeric mapping must be deterministic and configurable.

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
