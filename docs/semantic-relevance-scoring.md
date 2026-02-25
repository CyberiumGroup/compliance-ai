# Software Requirements Specification

## Semantic Relevance Scoring Engine (Max Cosine + Percentage Normalization)

---

# 1. Purpose

The system shall map short textual “requirements” to the most relevant documents within the given corpus using deterministic semantic similarity scoring.

For each:

```text
(requirement, document)
```

pair, the system shall produce:

1. A raw cosine similarity score
2. A normalized percentage relevance score suitable for human interpretation

The system shall not use generative LLM scoring for primary relevance computation.

---

# 2. Scope

This specification covers:

1. Document chunking
2. Embedding generation and storage
3. Cosine similarity computation
4. Maximum similarity aggregation
5. Conversion of cosine similarity into a human-readable percentage

Out of scope:

* UI implementation
* Human feedback retraining
* Re-ranking models
* LLM explanations

---

# 3. Functional Requirements

---

# 3.1 Document Ingestion and Chunking

## 3.1.1 Chunking Requirement

The system shall split each document into semantic chunks prior to embedding.

## 3.1.2 Chunk Size

* Target chunk size: ~300 tokens (~1200 characters, using 4 chars/token approximation)
* Overlap: ~37 tokens (~150 characters, ~12% of chunk size)
* Chunk boundaries should preserve paragraph structure where possible

Rationale: Smaller chunks produce more focused embeddings. A 750-token chunk covering multiple policy topics dilutes the embedding vector, reducing discriminability between relevant and irrelevant chunks. A ~300-token chunk typically covers a single policy clause or paragraph, yielding a sharper semantic signal.

## 3.1.3 Determinism

Given identical document input and configuration:

* Chunk boundaries must be identical across runs
* No randomness is permitted

## 3.1.4 Stored Chunk Metadata

Each chunk must store:

* `chunk_id`
* `document_id`
* `chunk_index`
* `chunk_text`
* `token_count`
* `embedding_vector`
* `embedding_model_version`
* `created_at`

---

# 3.2 Embedding Generation

## 3.2.1 Model Consistency

The system shall use a single embedding model version for both:

* Document chunks
* Requirements

The embedding model version must be:

* Explicitly stored
* Immutable for a given index

If the embedding model changes:

* All embeddings must be regenerated
* Mixed-model embeddings are prohibited

## 3.2.2 Requirement Embedding

Each requirement shall:

* Be embedded using the same model as document chunks
* Produce exactly one embedding vector
* Not be chunked (unless exceeding model limits)

### Requirement Text Composition

The text submitted for embedding is built from the requirement's own fields and its immediate parent's fields, joined by ` | `:

```
{parent_code}: {parent_name} — {parent_description} | {code} | {name} | {description} | Implementation guidance: {guidance}
```

Field inclusion rules:
- Parent block (`{parent_code}: {parent_name} — {parent_description}`) is included only when the requirement has an immediate parent; the parent description is omitted if null
- `{name}` is omitted if identical to `{code}` (common in NIST CSF subcategories)
- `{description}` and `{guidance}` are omitted if null

**Example — NIST CSF `GV.OC-01`:**
```
GV.OC: Organizational Context — The circumstances surrounding the organization's cybersecurity risk management decisions are understood. | GV.OC-01 | The organizational mission is understood and informs cybersecurity risk management | Implementation guidance: Articulate the organizational mission...
```

Rationale: Requirement descriptions are often a single sentence. Adding the parent category anchors the subcategory within its broader topic domain, improving recall when policy text discusses a topic at the category level rather than the specific subcategory wording. Adding the implementation guidance captures the concrete controls and activities associated with the requirement, aligning more closely with the language used in policy documents.

### Re-indexing Requirement

If the requirement text composition formula changes, all requirement embeddings must be cleared (`UPDATE framework_requirements SET embedding = NULL`) and regenerated before scoring. Only requirements with a null embedding are re-embedded on each scoring run.

---

# 3.3 Similarity Computation

## 3.3.1 Similarity Metric

The system shall compute:

```
cosine_similarity(requirement_embedding, chunk_embedding)
```

No alternative similarity metrics are permitted unless explicitly configured.

---

# 3.4 Document-Level Aggregation (Maximum Only)

Because documents contain multiple chunks, chunk-level similarities must be aggregated into a single document-level score.

The system shall use **maximum cosine similarity only**.

## 3.4.1 Aggregation Formula

For document D with chunk similarities:

```
doc_score_raw = max(similarity_chunk_1, similarity_chunk_2, ..., similarity_chunk_n)
```

This represents the highest semantic alignment between any chunk in the document and the requirement.

No averaging, weighting, or top-k strategies are permitted.

## 3.4.2 Source Excerpt

The chunk that produces `doc_score_raw` (the best chunk) is stored in full as the `source_excerpt` for the mapping. This gives reviewers a direct reference to the most semantically relevant section of the policy document.

No sentence-level extraction or summarisation is performed. The stored excerpt is the complete text of the best-scoring chunk, truncated only by database column limits.

---

# 4. Percentage Normalization for Human Interpretation

Raw cosine similarity values are typically in the range:

* [-1, 1] mathematically
* ~[0.2, 0.9] in practice for embeddings

To provide a consistent and interpretable relevance score, the system shall convert the raw cosine similarity into a percentage.

---

# 4.1 Normalization Formula

The system shall compute a normalized relevance percentage as follows:

```
relevance_percentage = ((doc_score_raw + 1) / 2) * 100
```

Where:

* `doc_score_raw` ∈ [-1, 1]
* `relevance_percentage` ∈ [0, 100]

This performs linear scaling of cosine similarity into a 0–100 range.

---

# 4.2 Example Conversions

| Raw Cosine | Relevance % |
| ---------- | ----------- |
| 1.0        | 100%        |
| 0.8        | 90%         |
| 0.5        | 75%         |
| 0.0        | 50%         |
| -1.0       | 0%          |

---

# 4.3 Determinism Requirement

Given identical:

* Requirement text
* Corpus
* Chunking configuration
* Embedding model

The following must be identical across runs:

* Raw cosine similarity
* Maximum aggregated score
* Percentage relevance score

No randomness is permitted.

---

# 5. Output Requirements

For each (requirement, document) pair that meets the relevance threshold, the system stores a `PolicyMapping` record containing:

| Field | Description |
|---|---|
| `requirement_id` | FK to the matched `FrameworkRequirement` |
| `policy_id` | FK to the source `Policy` document |
| `confidence_score` | Raw cosine similarity (`doc_score_raw`), range [-1, 1] |
| `relevance_percentage` | Normalised score (0–100), rounded to 2 decimal places |
| `source_excerpt` | Full text of the best-scoring chunk |
| `is_approved` | Defaults to `false`; set to `true` by human reviewer |

Pairs where `relevance_percentage < mapping_relevance_threshold` are discarded and not stored.

---

# 6. Non-Functional Requirements

## 6.1 Determinism

The scoring pipeline must be fully deterministic.

Prohibited:

* Temperature > 0 in any scoring component
* LLM-generated numeric scoring
* Randomized ranking

## 6.2 Reproducibility

Given identical inputs and configuration, the system must produce identical results.

## 6.3 Version Tracking

The system must track:

* Chunking configuration version
* Embedding model version

Changes require full re-indexing.

---

# 7. Configuration Parameters

The following must be externally configurable:

| Parameter | Default | Description |
|---|---|---|
| `chunk_size_chars` | 1200 | Target chunk size in characters (~300 tokens at 4 chars/token) |
| `chunk_overlap_chars` | 150 | Overlap between adjacent chunks in characters (~37 tokens, ~12%) |
| `embedding_model` | `text-embedding-3-small` | OpenAI embedding model for both chunks and requirements |
| `mapping_relevance_threshold` | 70.0 | Minimum `relevance_percentage` to store a mapping |

> **Note:** Changing `chunk_size_chars` or `chunk_overlap_chars` invalidates all existing chunk embeddings. Existing policy chunks must be deleted and re-generated before scoring. Changing `embedding_model` invalidates both chunk and requirement embeddings — all must be regenerated.

---

# 8. Acceptance Criteria

The system is accepted when:

1. Running the same requirement twice against the same corpus produces identical raw and percentage scores.
2. Changing the embedding model forces full re-indexing.
3. The percentage value strictly follows the normalization formula.
4. The highest-scoring chunk per document matches the reported maximum.

---

# 9. Success Definition

The system successfully produces:

```
Requirement → Ranked list of documents
```

Where ranking is determined solely by:

* Maximum cosine similarity
* Deterministic linear normalization into percentage