"""Создать учебную выборку локально. Исходный реестр в комплект не входит."""
import argparse
import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("quarter", "effect_declared", "implemented_90d", "split")
HORIZON = timedelta(days=90)
MIN_GROUP = 10
VALIDATION = date(2025, 10, 1)
TEST = date(2026, 4, 1)
BUFFER = timedelta(days=92)


def parse_date(value):
    return date.fromisoformat("-".join(reversed(value.strip().split(".")))) if value.strip() else None


def realized_within_window(filed, actual):
    return int(actual is not None and filed <= actual <= filed + HORIZON)


def annotation_decision(filed, actual, rejected):
    if (actual and actual < filed) or (rejected and rejected < filed) or (actual and rejected):
        return None
    return realized_within_window(filed, actual)


def prepare(raw, output_dir=ROOT):
    example = date(2024, 1, 1)
    assert [realized_within_window(example, example + timedelta(days=d))
            for d in (-1, 0, 90, 91)] == [0, 1, 1, 0]
    assert realized_within_window(example, None) == 0
    with raw.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f, delimiter=";"))
    dates = [parse_date(row["Подано"]) for row in records]
    # Последняя дата подачи — консервативная отсечка, не дата экспорта.
    cutoff = max(d for d in dates if d is not None)
    ids = Counter("".join(r["№ КП"].split()) for r in records)
    audit = Counter(raw=len(records), agreement_checked=0, rule_disagreements=0)
    candidates = []
    for row, filed in zip(records, dates):
        key = "".join(row["№ КП"].split())
        if not key or filed is None:
            audit["missing_key_or_date"] += 1
            continue
        if ids[key] > 1:
            audit["duplicate_id_rows"] += 1
            continue
        split, boundary = ("train", VALIDATION) if filed < VALIDATION else (
            ("validation", TEST) if filed < TEST else ("test", cutoff))
        if (split != "test" and filed >= boundary - BUFFER) or filed + HORIZON > cutoff:
            audit["incomplete_window_or_gap"] += 1
            continue
        actual = parse_date(row["Реализовано"])
        rejected = parse_date(row["Отклонено"])
        label = annotation_decision(filed, actual, rejected)
        if label is None:
            audit["inconsistent_status_or_date"] += 1
            continue
        check = int(actual is not None and 0 <= (actual - filed).days <= HORIZON.days)
        audit["agreement_checked"] += 1
        audit["rule_disagreements"] += label != check
        quarter = f"{filed.year}Q{(filed.month - 1) // 3 + 1}"
        candidates.append((quarter, int(bool(row["Условно-годовой ЭЭ"].strip())), label, split))
    assert audit["rule_disagreements"] == 0
    counts = Counter(candidates)
    released = [row for row in candidates if counts[row] >= MIN_GROUP]
    audit["removed_small_groups"] = len(candidates) - len(released)
    audit["released"] = len(released)
    audit["smallest_released_group"] = min(Counter(released).values())
    assert audit["raw"] == audit["released"] + sum(audit[k] for k in (
        "missing_key_or_date", "duplicate_id_rows", "incomplete_window_or_gap",
        "inconsistent_status_or_date", "removed_small_groups"))
    # Не сохраняем исходный порядок строк, ключи, даты или таблицу соответствия.
    Random(42).shuffle(released)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)
    (output_dir / "lab06").mkdir(exist_ok=True)
    with (output_dir / "data/kaizen_v1.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(released)
    (output_dir / "lab06/preparation_audit.json").write_text(
        json.dumps(dict(audit), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path, help="Локальный исходный CSV (не публиковать)")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Корень вывода data/ и lab06/")
    args = parser.parse_args()
    prepare(args.raw, args.output_dir)
