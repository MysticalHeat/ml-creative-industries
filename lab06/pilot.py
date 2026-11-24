"""Пилот на train: без исходных дат, номеров и других реквизитов в выводе."""
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from random import Random

from prepare import BUFFER, HORIZON, VALIDATION, annotation_decision, parse_date

SIZE = 24
SEED = 61


def sample(raw):
    with raw.open(encoding="utf-8-sig", newline="") as f:
        rows = [(parse_date(r["Подано"]), "".join(r["№ КП"].split()), r)
                for r in csv.DictReader(f, delimiter=";")]
    ids = Counter(key for _, key, _ in rows)
    # Отбор по исходным реквизитам, не по статусам или рассчитанным меткам.
    eligible = sorted((filed, key, row) for filed, key, row in rows
                      if filed and key and ids[key] == 1 and filed < VALIDATION - BUFFER)
    return [(filed, parse_date(row["Реализовано"]), parse_date(row["Отклонено"]))
            for filed, _, row in Random(SEED).sample(eligible, SIZE)]


def chronology(filed, actual, rejected):
    events = defaultdict(list)
    for day, code in ((filed, "П"), (filed + HORIZON, "Г"), (actual, "Р"), (rejected, "О")):
        if day is not None:
            events[day].append(code)
    return " < ".join("=".join(events[day]) for day in sorted(events))


def compare(cases, ratings):
    by_label = Counter()
    differences = []
    for i, (case, rated) in enumerate(zip(cases, ratings, strict=True), 1):
        decision = annotation_decision(*case)
        code = "X" if decision is None else str(decision)
        by_label[rated] += 1
        if rated != code:
            differences.append((i, rated, code))
    print(f"n={len(cases)}, 0={by_label['0']}, 1={by_label['1']}, "
          f"исключение={by_label['X']}, расхождения={len(differences)}")
    for i, rated, code in differences:
        print(f"Пилот №{i}: по инструкции={rated}, по коду={code}")
    return not differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--decisions", type=Path, help="По одному решению (0, 1, X) на строку")
    args = parser.parse_args()
    cases = sample(args.raw)
    if args.decisions is None:
        print("П — подача, Г — 90-й день, Р — реализация, О — отклонение")
        for i, case in enumerate(cases, 1):
            print(f"{i:02}: {chronology(*case)}")
    else:
        ratings = args.decisions.read_text(encoding="utf-8").split()
        if len(ratings) != SIZE or not set(ratings) <= {"0", "1", "X"}:
            parser.error(f"нужно {SIZE} решений: 0, 1 или X")
        if not compare(cases, ratings):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
