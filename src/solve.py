from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.solver_core import (
    block_counts_to_csv,
    read_input,
    rows_to_output_csv,
    soft_scores_to_csv,
    solve_problem,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "output" / "output.csv"
DEFAULT_BLOCK_SUMMARY_PATH = ROOT_DIR / "output" / "block_tag_counts.csv"
DEFAULT_SCORE_SUMMARY_PATH = ROOT_DIR / "output" / "soft_constraint_scores.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve the seating arrangement problem with PuLP/CBC.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input CSV path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path")
    parser.add_argument(
        "--block-summary",
        default=str(DEFAULT_BLOCK_SUMMARY_PATH),
        help="Block-tag summary CSV path",
    )
    parser.add_argument(
        "--score-summary",
        default=str(DEFAULT_SCORE_SUMMARY_PATH),
        help="Soft-constraint score summary CSV path",
    )
    parser.add_argument("--header", action="store_true", help="Write a header row to the output CSV")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    block_summary_path = Path(args.block_summary)
    score_summary_path = Path(args.score_summary)

    rows = read_input(input_path)
    result = solve_problem(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rows_to_output_csv(result.rows, result.assignment), encoding="utf-8")
    if args.header:
        output_path.write_text("user,block\r\n" + rows_to_output_csv(result.rows, result.assignment), encoding="utf-8")

    block_summary_path.parent.mkdir(parents=True, exist_ok=True)
    block_summary_path.write_text(block_counts_to_csv(result.block_tag_counts), encoding="utf-8")

    score_summary_path.parent.mkdir(parents=True, exist_ok=True)
    score_summary_path.write_text(soft_scores_to_csv(result.soft_scores), encoding="utf-8")


if __name__ == "__main__":
    main()
