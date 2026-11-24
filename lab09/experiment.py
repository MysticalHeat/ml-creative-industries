#!/usr/bin/env python3
"""Fixed train-only quarter stump, validation comparison; no writes."""
import argparse
import csv
import hashlib
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

DATA_HASH = "82cd0538aa2b0fa5b8d84cef3e52c8777e6e12f9be71426e91208477cbd71220"
BASELINE_HASH = "6e6db1a6d92e257f5afda1ddaf6ba27a6e83c3fe5169753114890d64e59a03da"


def quarter_number(value):
    if not re.fullmatch(r"\d{4}Q[1-4]", value):
        raise ValueError("Некорректный квартал")
    return int(value[:4]) * 4 + int(value[-1]) - 1


def metrics(pairs):
    count = Counter(pairs)
    tn, fp, fn, tp = (count[x] for x in ((0, 0), (0, 1), (1, 0), (1, 1)))
    def ratio(a, b):
        return Fraction(a, b) if b else None
    r0, r1 = ratio(tn, tn + fp), ratio(tp, tp + fn)
    return {"TN": tn, "FP": fp, "FN": fn, "TP": tp,
            "recall0": r0, "recall1": r1,
            "BA": (r0 + r1) / 2 if r0 is not None and r1 is not None else None,
            "precision1": ratio(tp, tp + fp)}


def predict(q, threshold, high):
    return int(q >= threshold if high else q < threshold)


def main():
    parser = argparse.ArgumentParser(description="Сравнение на разрешённых локальных данных ЛР6/7")
    parser.add_argument("--data", type=Path, required=True, help="путь к CSV выпуска v1")
    parser.add_argument("--baseline", type=Path, required=True, help="путь к прогнозам validation ЛР7")
    args = parser.parse_args()
    data, baseline_path = args.data, args.baseline
    print("Python:", sys.version.split()[0])
    for path, expected in ((data, DATA_HASH), (baseline_path, BASELINE_HASH)):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"SHA-256 {path.name}: {digest}")
        if digest != expected:
            raise ValueError(f"Другая версия: {path}")

    train, validation = [], []
    with data.open(encoding="utf-8", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            if row["split"] not in ("train", "validation"):
                continue
            q = quarter_number(row["quarter"])
            label = int(row["implemented_90d"])
            if label not in (0, 1):
                raise ValueError("Некорректная метка")
            item = (line, row["quarter"], q, label)
            (train if row["split"] == "train" else validation).append(item)
    if len(train) != 6304 or len(validation) != 1059:
        raise ValueError("Несовпадение размеров split")
    if {v[1] for v in validation} != {"2025Q4"}:
        raise ValueError("Несовпадение квартала validation")
    quarters = sorted({q for _, _, q, _ in train})
    if len(quarters) < 2:
        raise ValueError("Недостаточно кварталов train")
    candidates = []
    for threshold in quarters[1:]:
        for high in (True, False):
            score = metrics([(y, predict(q, threshold, high)) for _, _, q, y in train])["BA"]
            if score is None:
                raise ValueError("На train отсутствует класс")
            candidates.append((score, threshold, high))
    score, threshold, high = min(candidates, key=lambda c: (-c[0], c[1], not c[2]))
    print(f"Train: n={len(train)}, порог={threshold}, ориентация={'greater-or-equal' if high else 'less'}, BA={score}")

    with baseline_path.open(encoding="utf-8", newline="") as f:
        baseline = list(csv.DictReader(f))
    if len(baseline) != len(validation):
        raise ValueError("Несовпадение числа прогнозов baseline")
    for row, (line, quarter, _, actual) in zip(baseline, validation):
        if (int(row["line_in_release_csv"]), row["quarter"], int(row["actual"])) != (line, quarter, actual):
            raise ValueError("Baseline не совпадает с validation выпуска")
        if row["prediction"] != "0":
            raise ValueError("Baseline отличается от ЛР7")
    base_metrics = metrics([(int(r["actual"]), int(r["prediction"])) for r in baseline])
    new_pairs = [(y, predict(q, threshold, high)) for _, _, q, y in validation]
    new_metrics = metrics(new_pairs)
    if base_metrics["BA"] != Fraction(1, 2) or new_metrics["BA"] != Fraction(1, 2):
        raise ValueError("Не пройдена проверка структурного ограничения")
    print(f"Validation: n={len(validation)}, квартал=2025Q4, прогнозы={dict(Counter(p for _, p in new_pairs))}")
    print("Baseline:", base_metrics)
    print("Пень:", new_metrics)
    accepted = new_metrics["BA"] >= Fraction(51, 100) and new_metrics["recall1"] > 0
    print("Критерий ЛР8:", "выполнен" if accepted else "не выполнен; оставить baseline")
    print("Готово; входы не изменялись, результаты на test не вычислялись.")


if __name__ == "__main__":
    main()
