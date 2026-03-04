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
2. Chunk cleaning (exclusion of boilerplate sections)
3. Embedding generation and storage
4. Cosine similarity computation
5. Maximum similarity aggregation
6. Conversion of cosine similarity into a human-readable percentage

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

## 3.1.2 Chunking Strategy

The system uses a **hybrid chunking strategy** that selects between two modes per document:

### Semantic mode (preferred)
When the document contains at least `chunk_min_sections` (default: 2) detected section headings, the document is split at heading boundaries. Detected heading patterns:
* Markdown headings: `## Title`
* Numbered sections: `3.2 `, `4.1.1.`
* ALLCAPS section titles: `ACCESS CONTROL POLICY`

Each section becomes one chunk. If a section exceeds `chunk_size_chars`, its body is sub-chunked using the fixed-size paragraph accumulator, with the heading prepended to every sub-chunk to preserve section context.

### Fixed-size mode (fallback)
When fewer than `chunk_min_sections` headings are detected (e.g. plain-text or poorly-formatted PDF), the system falls back to fixed-size paragraph accumulation:
* Target chunk size: ~300 tokens (~1200 characters, using 4 chars/token approximation)
* Overlap: ~37 tokens (~150 characters, ~12% of chunk size)
* Chunk boundaries preserve paragraph structure

### Strategy labelling
The strategy used (`'semantic'` or `'fixed'`) is stored on the `Policy` record at chunk time and displayed in the Documentation page UI.

Rationale: Semantic chunks produce coherent, topic-focused embeddings aligned with how compliance requirements are written. Fixed-size chunking is retained as a fallback to ensure correct behaviour for any document structure.

## 3.1.3 Chunk Cleaning

After chunking and before embedding, the system shall discard any chunk whose leading heading exactly matches (case-insensitive) an entry in the **excluded headings list**. These sections contain administrative boilerplate that adds noise to semantic similarity scores.

**Excluded headings (hardcoded):**

| Heading |
|---|
| `approval` |
| `approvals` |
| `history` |
| `related documents` |

**Leading heading detection:** a chunk's leading heading is its first line if that line is a single short string (≤ 120 characters, no embedded newline) followed by a blank line. This matches the output format of semantic-mode chunks, where the section heading is always prepended before the body. Fixed-size chunks without a detectable heading are never filtered.

**Numbering stripping:** before comparison, any leading numbering sequence is stripped from the heading (e.g. `"3.2 History"` → `"history"`, `"1. Approval"` → `"approval"`). This ensures numbered section headings are correctly matched.

Excluded chunks are not stored as `PolicyChunk` records and are never embedded.

**Small chunk merging:** after exclusion filtering, any chunk with ≤ 50 tokens is merged into the following chunk (separated by a double newline). Accumulation continues until the merged result exceeds the threshold. A trailing small chunk with no following chunk is merged into the preceding one instead. The threshold is controlled by `MERGE_MIN_TOKENS` in `chunk_cleaner.py`.

## 3.1.4 Determinism

Given identical document input and configuration:

* Chunk boundaries must be identical across runs
* No randomness is permitted

## 3.1.5 Stored Chunk Metadata

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

# 3.4 Document-Level Aggregation (Top-K Mean)

Because documents contain multiple chunks, chunk-level similarities must be aggregated into a single document-level score.

The system shall use **mean of the top-K cosine similarities**.

## 3.4.1 Aggregation Formula

For document D with chunk similarities sorted descending, taking the top K:

```
doc_score_raw = mean(top_K_similarities)
```

K is controlled by `mapping_top_k` (default: 5). If the document has fewer than K chunks, all chunks are used.

This rewards documents that address the requirement consistently across multiple passages, while remaining robust against documents that mention a topic only once incidentally.

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
| `chunk_min_sections` | 2 | Minimum detected headings required to use semantic chunking mode |
| `mapping_top_k` | 5 | Number of top chunk similarities to average for the document score |
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