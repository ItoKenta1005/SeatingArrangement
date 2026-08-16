from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set

import pulp


BLOCK_COUNT = 4
BLOCK_CAPACITY = 40
BLOCKS = list(range(1, BLOCK_COUNT + 1))
TAG_ORDER = ["spca", "spcb", "reda", "redb", "blua", "blub", "grna", "grnb"]
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = ROOT_DIR / "input" / "input.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "output" / "output.csv"
DEFAULT_BLOCK_SUMMARY_PATH = ROOT_DIR / "output" / "block_tag_counts.csv"
DEFAULT_SCORE_SUMMARY_PATH = ROOT_DIR / "output" / "soft_constraint_scores.csv"

PRIORITY_TAGS = {"spca": 1000, "spcb": 1}

PAIR_GROUPS = {
    "red_pair": {"reda", "redb"},
    "blue_pair": {"blua", "blub"},
    "green_pair": {"grna", "grnb"},
}

SOFT_TAG_SCORE = {2: 3, 3: 300}
SOFT_PAIR_SCORE = {2: 1, 3: 100}


@dataclass(frozen=True)
class UserRow:
    user: str
    tag: str


def read_input(path: Path) -> List[UserRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = []
        for raw in reader:
            if not raw:
                continue
            if len(raw) < 2:
                raise ValueError(f"Invalid row in {path}: {raw!r}")
            rows.append(UserRow(user=raw[0].strip(), tag=raw[1].strip()))
    return rows


def build_groups(rows: Sequence[UserRow]) -> Dict[str, List[int]]:
    groups: Dict[str, List[int]] = {}
    for idx, row in enumerate(rows):
        groups.setdefault(row.tag, []).append(idx)

    for pair_name, tags in PAIR_GROUPS.items():
        groups[pair_name] = [idx for idx, row in enumerate(rows) if row.tag in tags]

    return groups


def score_split(blocks_used: int, pair_group: bool) -> int:
    if blocks_used <= 1:
        return 0
    if blocks_used >= 3:
        return SOFT_PAIR_SCORE[3] if pair_group else SOFT_TAG_SCORE[3]
    return SOFT_PAIR_SCORE[2] if pair_group else SOFT_TAG_SCORE[2]


def solve_assignment(rows: Sequence[UserRow]) -> Dict[int, int]:
    n = len(rows)
    if n != BLOCK_COUNT * BLOCK_CAPACITY:
        raise ValueError(
            f"Expected {BLOCK_COUNT * BLOCK_CAPACITY} rows, got {n}. "
            "This solver is written for the current specification."
        )

    groups = build_groups(rows)
    model = pulp.LpProblem("seating_arrangement", pulp.LpMinimize)

    x = {
        (i, b): pulp.LpVariable(f"x_{i}_{b}", cat="Binary")
        for i in range(n)
        for b in BLOCKS
    }

    # Each user must be assigned to exactly one block.
    for i in range(n):
        model += pulp.lpSum(x[i, b] for b in BLOCKS) == 1, f"assign_{i}"

    # Each block must contain exactly 40 users.
    for b in BLOCKS:
        model += pulp.lpSum(x[i, b] for i in range(n)) == BLOCK_CAPACITY, f"capacity_{b}"

    # Stage 1: prioritize spca, then spcb. Other tags do not affect this stage.
    priority_expr = pulp.lpSum(
        weight * b * x[i, b]
        for i, row in enumerate(rows)
        for b in BLOCKS
        if (weight := PRIORITY_TAGS.get(row.tag)) is not None
    )

    model.setObjective(priority_expr)
    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Stage 1 did not solve optimally: {pulp.LpStatus[status]}")

    best_priority = int(round(pulp.value(priority_expr)))
    model += priority_expr == best_priority, "fix_priority_optimum"

    # Stage 2: minimize split penalties.
    soft_terms = []

    for group_name, member_indices in groups.items():
        if not member_indices:
            continue

        y = {
            b: pulp.LpVariable(f"y_{group_name}_{b}", cat="Binary")
            for b in BLOCKS
        }

        for b in BLOCKS:
            for i in member_indices:
                model += y[b] >= x[i, b], f"cover_{group_name}_{b}_{i}"
            model += y[b] <= pulp.lpSum(x[i, b] for i in member_indices), f"link_{group_name}_{b}"

        used_blocks = pulp.lpSum(y[b] for b in BLOCKS)

        split2 = pulp.LpVariable(f"split2_{group_name}", cat="Binary")
        split3 = pulp.LpVariable(f"split3_{group_name}", cat="Binary")

        model += used_blocks <= 1 + (BLOCK_COUNT - 1) * split2, f"split2_ub_{group_name}"
        model += used_blocks >= 2 * split2, f"split2_lb_{group_name}"
        model += used_blocks <= 2 + (BLOCK_COUNT - 2) * split3, f"split3_ub_{group_name}"
        model += used_blocks >= 3 * split3, f"split3_lb_{group_name}"

        if group_name in PAIR_GROUPS:
            # 1 point if split into 2 blocks, 100 points if split into 3+ blocks.
            soft_terms.append(1 * split2 + 99 * split3)
        else:
            # 3 points if split into 2 blocks, 300 points if split into 3+ blocks.
            soft_terms.append(3 * split2 + 297 * split3)

    model.setObjective(pulp.lpSum(soft_terms))
    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Stage 2 did not solve optimally: {pulp.LpStatus[status]}")

    assignment: Dict[int, int] = {}
    for i in range(n):
        chosen = None
        for b in BLOCKS:
            if pulp.value(x[i, b]) > 0.5:
                chosen = b
                break
        if chosen is None:
            raise RuntimeError(f"User {rows[i].user} was not assigned to any block")
        assignment[i] = chosen

    return assignment


def write_output(path: Path, rows: Sequence[UserRow], assignment: Dict[int, int], header: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(["user", "block"])
        for i, row in enumerate(rows):
            writer.writerow([row.user, assignment[i]])


def write_block_tag_counts(path: Path, rows: Sequence[UserRow], assignment: Dict[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {
        b: {tag: 0 for tag in TAG_ORDER}
        for b in BLOCKS
    }

    for i, row in enumerate(rows):
        block = assignment[i]
        counts[block][row.tag] += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["block", *TAG_ORDER, "total"])
        for b in BLOCKS:
            row = [b, *[counts[b][tag] for tag in TAG_ORDER], sum(counts[b].values())]
            writer.writerow(row)
        totals = [sum(counts[b][tag] for b in BLOCKS) for tag in TAG_ORDER]
        writer.writerow(["total", *totals, sum(totals)])


def write_soft_constraint_scores(path: Path, rows: Sequence[UserRow], assignment: Dict[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    groups = build_groups(rows)
    order: List[tuple[str, bool]] = [(tag, False) for tag in TAG_ORDER] + [
        ("red_pair", True),
        ("blue_pair", True),
        ("green_pair", True),
    ]

    rows_out = []
    total = 0
    for group_name, is_pair in order:
        member_indices = groups[group_name]
        blocks_used: Set[int] = {assignment[i] for i in member_indices}
        score = score_split(len(blocks_used), is_pair)
        total += score
        rows_out.append((group_name, score))

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item", "score"])
        writer.writerow(["total_optimal_score", total])
        for name, score in rows_out:
            writer.writerow([name, score])


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
    assignment = solve_assignment(rows)
    write_output(output_path, rows, assignment, header=args.header)
    write_block_tag_counts(block_summary_path, rows, assignment)
    write_soft_constraint_scores(score_summary_path, rows, assignment)


if __name__ == "__main__":
    main()
