# Evaluation Evidence Kit

This folder is organized by the 4 core criteria:

- `correctness-benchmark`
- `clarity-structure-review`
- `depth-analysis`
- `relevance-alignment`

Use the provided CSV templates to record baseline and improved runs.

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

These artifacts are your evidence package for project documentation or resume bullets.
