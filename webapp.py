from __future__ import annotations

import csv
import html
import secrets
from io import StringIO
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.solver_core import (
    block_counts_to_csv,
    read_input,
    read_rows,
    rows_to_output_csv,
    soft_scores_to_csv,
    solve_problem,
    tag_counts_to_csv,
)


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"

app = FastAPI(title="Seating Arrangement")
RESULTS: Dict[str, Dict[str, str]] = {}


def render_page(content: str, title: str = "Seating Arrangement") -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      background: #f6f7fb;
      color: #1c2430;
    }}
    .wrap {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(25, 32, 44, 0.08);
      padding: 20px;
      margin-bottom: 20px;
    }}
    h1, h2 {{ margin-top: 0; }}
    form {{ display: grid; gap: 12px; }}
    button, .btn {{
      display: inline-block;
      background: #17324d;
      color: white;
      padding: 10px 16px;
      border: 0;
      border-radius: 10px;
      text-decoration: none;
      cursor: pointer;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid #e5e8ef;
      padding: 8px 10px;
      text-align: left;
      font-size: 14px;
    }}
    th {{ background: #f1f4f8; }}
    .muted {{ color: #5f6b7a; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    pre {{
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      padding: 16px;
      border-radius: 12px;
      overflow: auto;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {content}
  </div>
</body>
</html>"""


def table_html_from_csv(csv_text: str) -> str:
    reader = csv.reader(StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return "<p class='muted'>No data.</p>"
    header = rows[0]
    body = rows[1:]
    thead = "".join(f"<th>{html.escape(cell)}</th>" for cell in header)
    tbody = []
    for row in body:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        tbody.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(tbody)}</tbody></table>"


def load_rows_from_upload(upload: UploadFile | None):
    if upload is not None and upload.filename:
        raw_text = upload.file.read().decode("utf-8")
        return read_rows(StringIO(raw_text))
    return read_input(DEFAULT_INPUT_PATH)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    content = """
    <div class="card">
      <h1>Seating Arrangement Solver</h1>
      <p class="muted">Upload input.csv, run the optimizer, and download CSV outputs.</p>
      <form action="/solve" method="post" enctype="multipart/form-data">
        <label>
          input.csv
          <input type="file" name="file" accept=".csv">
        </label>
        <button type="submit">Solve</button>
      </form>
      <p class="muted">If no file is uploaded, the app uses <code>input/input.csv</code>.</p>
    </div>
    """
    return render_page(content)


@app.post("/solve")
def solve(file: UploadFile | None = File(default=None)) -> RedirectResponse:
    rows = load_rows_from_upload(file)
    result = solve_problem(rows)

    token = secrets.token_urlsafe(8)
    RESULTS[token] = {
        "assignment": rows_to_output_csv(result.rows, result.assignment),
        "block_counts": block_counts_to_csv(result.block_tag_counts),
        "soft_scores": soft_scores_to_csv(result.soft_scores),
        "tag_counts": tag_counts_to_csv(result.rows),
        "score": str(result.total_soft_score),
    }

    return RedirectResponse(url=f"/result/{token}", status_code=303)


@app.get("/result/{token}", response_class=HTMLResponse)
def result_page(token: str) -> str:
    data = RESULTS.get(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Result not found")

    content = f"""
    <div class="card">
      <h1>Seating Arrangement Solver</h1>
      <p class="muted">Solved successfully.</p>
      <p><strong>Total optimal score:</strong> {html.escape(data["score"])}</p>
      <div style="display:flex; gap:12px; flex-wrap:wrap; margin: 16px 0;">
        <a class="btn" href="/download/{token}/assignment.csv">Download output.csv</a>
        <a class="btn" href="/download/{token}/block_tag_counts.csv">Download block_tag_counts.csv</a>
        <a class="btn" href="/download/{token}/soft_constraint_scores.csv">Download soft_constraint_scores.csv</a>
        <a class="btn" href="/download/{token}/tag_counts.csv">Download tag_counts.csv</a>
      </div>
    </div>
    <div class="grid">
      <div class="card">
        <h2>Assignment</h2>
        {table_html_from_csv(data["assignment"])}
      </div>
      <div class="card">
        <h2>Block Tag Counts</h2>
        {table_html_from_csv(data["block_counts"])}
      </div>
      <div class="card">
        <h2>Soft Constraint Scores</h2>
        {table_html_from_csv(data["soft_scores"])}
      </div>
      <div class="card">
        <h2>Input Tag Counts</h2>
        {table_html_from_csv(data["tag_counts"])}
      </div>
    </div>
    """
    return render_page(content)


@app.get("/download/{token}/{filename}")
def download_csv(token: str, filename: str) -> Response:
    data = RESULTS.get(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Result not found")

    mapping = {
        "assignment.csv": ("output.csv", data["assignment"]),
        "block_tag_counts.csv": ("block_tag_counts.csv", data["block_counts"]),
        "soft_constraint_scores.csv": ("soft_constraint_scores.csv", data["soft_scores"]),
        "tag_counts.csv": ("tag_counts.csv", data["tag_counts"]),
    }
    if filename not in mapping:
        raise HTTPException(status_code=404, detail="File not found")

    download_name, csv_text = mapping[filename]
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
