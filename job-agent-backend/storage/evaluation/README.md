## Evaluation Artifacts

This folder stores committed evaluation artifacts for review and benchmarking.

- `evaluation_dataset.jsonl`: one row per answered interview turn (Q/A + scoring metadata).
- `evaluation_results.json`: one row per completed interview session with final evaluation outputs.

Regenerate these files from local session memory snapshots:

```powershell
python job-agent-backend/scripts/export_evaluation_artifacts.py
```

Analyze current artifacts:

```powershell
python job-agent-backend/scripts/analyze_evaluation.py
```
