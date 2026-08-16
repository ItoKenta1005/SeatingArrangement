from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.solver_core import read_input, tag_counts_to_csv


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "output" / "tag_counts.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Count tags in input.csv and write a summary CSV.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input CSV path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    rows = read_input(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tag_counts_to_csv(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
