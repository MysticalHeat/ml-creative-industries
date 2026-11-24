#!/usr/bin/env python3
"""Read-only aggregate verification; never print rows or predictions."""
import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

DATA_HASH = "82cd0538aa2b0fa5b8d84cef3e52c8777e6e12f9be71426e91208477cbd71220"
PRED_HASH = "6e6db1a6d92e257f5afda1ddaf6ba27a6e83c3fe5169753114890d64e59a03da"
EXPECTED = {("0", "0"): 102, ("0", "1"): 377,
            ("1", "0"): 445, ("1", "1"): 135}


def read_summary():
    with (Path(__file__).resolve().parent / "СЕГМЕНТЫ.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2 or {r["effect_declared"] for r in rows} != {"0", "1"}:
        raise ValueError("Неверный состав сегментов")
    groups = {}
    for row in rows:
        tn, fp, fn, tp, n = (int(row[k]) for k in ("TN", "FP", "FN", "TP", "n"))
        if fp != 0 or tp != 0 or n != tn + fn or min(tn, fn) < 0:
            raise ValueError("Неверная матрица сегмента")
        groups[(row["effect_declared"], "0")] = tn
        groups[(row["effect_declared"], "1")] = fn
    return groups


def check_aggregates(groups):
    if groups != EXPECTED:
        raise ValueError("Сегменты не совпадают с зафиксированными агрегатами")
    tn = sum(n for (effect, actual), n in groups.items() if actual == "0")
    fn = sum(n for (effect, actual), n in groups.items() if actual == "1")
    if (tn, fn, sum(groups.values())) != (547, 512, 1059):
        raise ValueError("Матрица или размер не совпадают")
    print(f"Validation baseline: TN={tn}, FP=0, FN={fn}, TP=0; BA=0.5")
    for effect in ("0", "1"):
        n0, n1 = groups[(effect, "0")], groups[(effect, "1")]
        print(f"effect_declared={effect}: n={n0+n1}, TN={n0}, FN={n1}")


def read_checked(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Хеш не совпал: {path.name}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    if (args.data is None) != (args.baseline is None):
        parser.error("Укажите оба файла либо ни одного")
    summary = read_summary()
    check_aggregates(summary)
    if args.data is None:
        print("Проверена только согласованность таблицы с ожидаемыми агрегатами, не исходные данные.")
        return
    release = read_checked(args.data, DATA_HASH)
    predictions = read_checked(args.baseline, PRED_HASH)
    validation = [(i, r) for i, r in enumerate(release, 2) if r["split"] == "validation"]
    if len(validation) != 1059 or len(predictions) != len(validation):
        raise ValueError("Несовпадение объёма")
    groups = Counter()
    first = Counter()
    for index, (pred, (line, source)) in enumerate(zip(predictions, validation)):
        if (int(pred["line_in_release_csv"]) != line
                or pred["quarter"] != source["quarter"]
                or pred["effect_declared"] != source["effect_declared"]
                or pred["actual"] != source["implemented_90d"]
                or pred["prediction"] != "0"
                or pred["quarter"] != "2025Q4"
                or pred["actual"] not in ("0", "1")
                or pred["effect_declared"] not in ("0", "1")):
            raise ValueError("Прогноз не соответствует выпуску")
        groups[(pred["effect_declared"], pred["actual"])] += 1
        if index < 10:
            first[pred["actual"]] += 1
    if first != {"0": 5, "1": 5}:
        raise ValueError("Ручная десятка не совпадает")
    check_aggregates(groups)
    if groups != summary:
        raise ValueError("Таблица сегментов не соответствует исходным данным")
    print("Первые 10: TN=5, FP=0, FN=5, TP=0")
    print("Хеши, соответствие строк и агрегаты проверены; файлы не записаны.")


if __name__ == "__main__":
    main()
