from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from src.solver_core import (
    block_counts_to_csv,
    read_rows,
    rows_to_output_csv,
    soft_scores_to_csv,
    solve_problem,
)


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"


def load_rows(uploaded_file) -> tuple[str, list]:
    if uploaded_file is not None:
        raw_text = uploaded_file.getvalue().decode("utf-8")
        rows = read_rows(StringIO(raw_text))
        return raw_text, rows

    raw_text = DEFAULT_INPUT_PATH.read_text(encoding="utf-8")
    rows = read_rows(StringIO(raw_text))
    return raw_text, rows


def main() -> None:
    st.set_page_config(page_title="Seating Arrangement", layout="wide")
    st.title("Seating Arrangement Solver")
    st.caption("PuLP + CBC によるブロック分け最適化")

    with st.sidebar:
        st.header("Input")
        uploaded_file = st.file_uploader("input.csv を選択", type=["csv"])
        st.write("未指定の場合は `input/input.csv` を使用します。")
        solve_clicked = st.button("Solve", type="primary")

    if "raw_text" not in st.session_state or uploaded_file is not None:
        raw_text, rows = load_rows(uploaded_file)
        st.session_state["raw_text"] = raw_text
        st.session_state["rows"] = rows

    rows = st.session_state.get("rows")
    if rows is None:
        st.info("左のボタンから解を計算してください。")
        return

    st.subheader("Input Preview")
    st.dataframe(pd.DataFrame([{"user": r.user, "tag": r.tag} for r in rows]), use_container_width=True, height=280)

    if not solve_clicked and "result" not in st.session_state:
        st.info("Solve を押すと最適化を実行します。")
        return

    if solve_clicked:
        with st.spinner("Solving..."):
            result = solve_problem(rows)
        st.session_state["result"] = result

    result = st.session_state["result"]

    assignment_df = pd.DataFrame(
        [{"user": row.user, "block": result.assignment[i]} for i, row in enumerate(result.rows)]
    )
    block_counts_df = pd.DataFrame(
        [
            {"block": idx + 1, **counts, "total": sum(counts.values())}
            for idx, counts in enumerate(result.block_tag_counts)
        ]
    )
    total_row = {"block": "total"}
    for tag in [c for c in block_counts_df.columns if c not in {"block", "total"}]:
        total_row[tag] = int(block_counts_df[tag].sum())
    total_row["total"] = len(result.rows)
    block_counts_df.loc[len(block_counts_df)] = total_row
    score_df = pd.DataFrame(result.soft_scores)

    st.subheader("Results")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total optimal score", result.total_soft_score)
    with col2:
        st.metric("Users", len(result.rows))

    st.markdown("### Assignment")
    st.dataframe(assignment_df, use_container_width=True, height=300)

    st.markdown("### Block Tag Counts")
    st.dataframe(block_counts_df, use_container_width=True, height=250)

    st.markdown("### Soft Constraint Scores")
    st.dataframe(score_df, use_container_width=True, height=250)

    st.markdown("### Downloads")
    st.download_button(
        "Download output.csv",
        data=rows_to_output_csv(result.rows, result.assignment),
        file_name="output.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download block_tag_counts.csv",
        data=block_counts_to_csv(result.block_tag_counts),
        file_name="block_tag_counts.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download soft_constraint_scores.csv",
        data=soft_scores_to_csv(result.soft_scores),
        file_name="soft_constraint_scores.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
