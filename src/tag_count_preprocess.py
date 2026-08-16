from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

TAG_ORDER = ["spca", "spcb", "reda", "redb", "blua", "blub", "grna", "grnb"]
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "output" / "tag_counts.csv"


def read_tag_counts(input_path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                raise ValueError(f"Invalid row in {input_path}: {row!r}")
            tag = row[1].strip()
            if not tag:
                raise ValueError(f"Empty tag in {input_path}: {row!r}")
            counts[tag] += 1
    return counts


def write_tag_counts(output_path: Path, counts: Counter[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tag", "count"])
        for tag in TAG_ORDER:
            if tag in counts:
                writer.writerow([tag, counts[tag]])
        for tag in sorted(counts):
            if tag not in TAG_ORDER:
                writer.writerow([tag, counts[tag]])


def main() -> None:
    parser = argparse.ArgumentParser(description="Count tags in input.csv and write a summary CSV.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input CSV path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    counts = read_tag_counts(input_path)
    write_tag_counts(output_path, counts)


if __name__ == "__main__":
    main()
