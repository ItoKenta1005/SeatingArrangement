# SeatingArrangement

This project solves the seating arrangement problem with `python + pulp (CBC)` and provides a local web app.

## Directory Layout

```text
.
├─ app.py
├─ webapp.py
├─ docs/
│  └─ desc.txt
├─ input/
│  └─ input.csv
├─ output/
│  ├─ output.csv
│  ├─ block_tag_counts.csv
│  ├─ soft_constraint_scores.csv
│  └─ tag_counts.csv
├─ src/
│  ├─ __init__.py
│  ├─ solve.py
│  ├─ solver_core.py
│  └─ tag_count_preprocess.py
├─ requirements.txt
├─ render.yaml
└─ README.md
```

## Setup

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

Tag count preprocessing:

```powershell
.\venv\Scripts\python.exe src\tag_count_preprocess.py
```

Solver:

```powershell
.\venv\Scripts\python.exe src\solve.py
```

Web app:

```powershell
.\venv\Scripts\python.exe -m uvicorn webapp:app --host 0.0.0.0 --port 8000
```

## Output CSVs

- `output/output.csv`: user-to-block assignment
- `output/block_tag_counts.csv`: tag counts in each block
- `output/soft_constraint_scores.csv`: total optimized score and score breakdown
- `output/tag_counts.csv`: tag counts in the input file

## Web App

- Upload `input/input.csv` or use the default input file
- Run the solver from the browser
- View results and download CSV files

## Render Deploy

- `render.yaml` is included for a free web service
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn webapp:app --host 0.0.0.0 --port $PORT`

