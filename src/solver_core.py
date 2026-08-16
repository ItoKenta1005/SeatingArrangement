from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

import pulp


BLOCK_COUNT = 4
BLOCK_CAPACITY = 40
BLOCKS = list(range(1, BLOCK_COUNT + 1))
TAG_ORDER = ["spca", "spcb", "reda", "redb", "blua", "blub", "grna", "grnb"]

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


@dataclass(frozen=True)
class SolveResult:
    rows: List[UserRow]
    assignment: Dict[int, int]
    block_tag_counts: List[Dict[str, int]]
    soft_scores: List[Dict[str, int | str]]
    total_soft_score: int


def read_input(path: Path) -> List[UserRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return read_rows(f)


def read_rows(source: Iterable[str]) -> List[UserRow]:
    reader = csv.reader(source)
    rows: List[UserRow] = []
    for raw in reader:
        if not raw:
            continue
        if len(raw) < 2:
            raise ValueError(f"Invalid row: {raw!r}")
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

    for i in range(n):
        model += pulp.lpSum(x[i, b] for b in BLOCKS) == 1, f"assign_{i}"

    for b in BLOCKS:
        model += pulp.lpSum(x[i, b] for i in range(n)) == BLOCK_CAPACITY, f"capacity_{b}"

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
            soft_terms.append(1 * split2 + 99 * split3)
        else:
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


def build_block_tag_counts(rows: Sequence[UserRow], assignment: Dict[int, int]) -> List[Dict[str, int]]:
    counts = [{tag: 0 for tag in TAG_ORDER} for _ in BLOCKS]
    for i, row in enumerate(rows):
        counts[assignment[i] - 1][row.tag] += 1
    return counts


def build_soft_scores(rows: Sequence[UserRow], assignment: Dict[int, int]) -> tuple[List[Dict[str, int | str]], int]:
    groups = build_groups(rows)
    order: List[tuple[str, bool]] = [(tag, False) for tag in TAG_ORDER] + [
        ("red_pair", True),
        ("blue_pair", True),
        ("green_pair", True),
    ]

    rows_out: List[Dict[str, int | str]] = []
    total = 0
    for group_name, is_pair in order:
        member_indices = groups[group_name]
        blocks_used: Set[int] = {assignment[i] for i in member_indices}
        score = score_split(len(blocks_used), is_pair)
        total += score
        rows_out.append({"item": group_name, "score": score})

    rows_out.insert(0, {"item": "total_optimal_score", "score": total})
    return rows_out, total


def solve_problem(rows: Sequence[UserRow]) -> SolveResult:
    assignment = solve_assignment(rows)
    block_tag_counts = build_block_tag_counts(rows, assignment)
    soft_scores, total_soft_score = build_soft_scores(rows, assignment)
    return SolveResult(
        rows=list(rows),
        assignment=assignment,
        block_tag_counts=block_tag_counts,
        soft_scores=soft_scores,
        total_soft_score=total_soft_score,
    )


def rows_to_output_csv(rows: Sequence[UserRow], assignment: Dict[int, int]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)
    for i, row in enumerate(rows):
        writer.writerow([row.user, assignment[i]])
    return buffer.getvalue()


def block_counts_to_csv(block_tag_counts: Sequence[Dict[str, int]]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["block", *TAG_ORDER, "total"])
    for index, counts in enumerate(block_tag_counts, start=1):
        row = [index, *[counts[tag] for tag in TAG_ORDER], sum(counts.values())]
        writer.writerow(row)
    totals = [sum(counts[tag] for counts in block_tag_counts) for tag in TAG_ORDER]
    writer.writerow(["total", *totals, sum(totals)])
    return buffer.getvalue()


def soft_scores_to_csv(soft_scores: Sequence[Dict[str, int | str]]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["item", "score"])
    for row in soft_scores:
        writer.writerow([row["item"], row["score"]])
    return buffer.getvalue()


def tag_counts_to_csv(rows: Sequence[UserRow]) -> str:
    from collections import Counter
    from io import StringIO

    counts = Counter(row.tag for row in rows)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["tag", "count"])
    for tag in TAG_ORDER:
        if tag in counts:
            writer.writerow([tag, counts[tag]])
    for tag in sorted(counts):
        if tag not in TAG_ORDER:
            writer.writerow([tag, counts[tag]])
    return buffer.getvalue()
