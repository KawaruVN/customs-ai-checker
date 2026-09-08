# TASK-001 Patch - Apply Instructions

Copy/extract the contents of this package into the repository root.

Expected merge targets include:

- `pyproject.toml`
- `.gitignore`
- `.env.example`
- `config/app.yaml`
- `src/customs_ai/config.py`
- `src/customs_ai/logger.py`
- `src/customs_ai/main.py`
- `src/customs_ai/api/routes/health.py`
- `tests/unit/test_config.py`
- `tests/integration/test_health.py`

Then update:

`tasks/in_progress/TASK-001-project-foundation.md`

Change:

`Status: TODO`

to:

`Status: IN_PROGRESS`

Install and test:

```powershell
py -3.12 -m pip install -e ".[test]"
py -3.12 -m pytest -v
```

Run the app:

```powershell
py -3.12 -m uvicorn customs_ai.main:app --reload
```

Health check:

`http://127.0.0.1:8000/health`

Expected:

```json
{"status":"ok"}
```
