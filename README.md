# SeatingArrangement

This project solves the seating arrangement problem with `python + pulp (CBC)` and provides a local Streamlit web app.

## Directory Layout

```text
.
├─ app.py
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
.\venv\Scripts\python.exe -m streamlit run app.py
```

## Output CSVs

- `output/output.csv`: user-to-block assignment
- `output/block_tag_counts.csv`: tag counts in each block
- `output/soft_constraint_scores.csv`: total optimized score and score breakdown
- `output/tag_counts.csv`: tag counts in the input file

## Web App

- Upload `input.csv` or use `input/input.csv`
- Run the solver from the browser
- View results and download CSV files

## Render Deploy

- `render.yaml` is included for a free web service
- Render build command: `pip install -r requirements.txt`
- Render start command: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`
