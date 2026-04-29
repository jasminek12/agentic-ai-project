# Evaluation Evidence Kit

This `evaluation/` directory is the evidence package for 4 grading criteria.  
Each criterion has:
- one detailed CSV with row-level data
- one `summary.csv` with the final metric(s) used in reporting

## What each folder contains

### 1) `correctness-benchmark/`
- `benchmark_questions.csv`: one row per evaluated Q/A pair; includes `correctness_label` and binary `correctness_score` (`1` correct, `0` not correct).
- `summary.csv`: total correctness %, baseline %, improved %, and delta.

### 2) `clarity-structure-review/`
- `scored_responses.csv`: one row per response with 1-5 scores for flow/readability/formatting plus `overall_clarity_score`.
- `summary.csv`: average clarity baseline vs improved, delta, and % meeting minimum standard.

### 3) `depth-analysis/`
- `scored_depth.csv`: one row per response with depth indicators (`gives_reasoning`, `includes_examples`, `includes_tradeoffs`) and `depth_score_1_to_5`.
- `summary.csv`: average depth baseline vs improved, delta, and rates for reasoning/examples/tradeoffs.

### 4) `relevance-alignment/`
- `jd_alignment.csv`: one row per response with job-role context, seeded JD keywords, `relevance_score_1_to_5`, and keyword coverage %.
- `summary.csv`: baseline vs improved relevance and keyword coverage with deltas.

## Baseline vs Improved (important)

- In these CSVs, `baseline` and `improved` are **run labels**, not different model names.
- They are assigned by `evaluation/bootstrap_from_raw.py` based on session order from raw exports:
  - first half of discovered `session_id` values -> `baseline`
  - second half -> `improved`

## Quick start

1. Auto-seed templates from historical raw data:

```bash
python evaluation/bootstrap_from_raw.py
```

2. (Optional) review or edit seeded values in each CSV.
3. Run metric summaries:

```bash
python evaluation/run_evaluation.py
```

3. Review generated summaries:

- `evaluation/correctness-benchmark/summary.csv`
- `evaluation/clarity-structure-review/summary.csv`
- `evaluation/depth-analysis/summary.csv`
- `evaluation/relevance-alignment/summary.csv`
- `evaluation/overall_summary.md`

These files are the final documentation-ready evidence for the evaluation section.
