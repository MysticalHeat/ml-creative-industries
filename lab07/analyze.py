"""Воспроизвести ЛР 5 и 7 из обезличенного CSV; Python 3.10+, без зависимостей."""
import csv
import json
import re
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPLITS = ("train", "validation", "test")


def table(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def chart(path, title, values, unit, percent=False):
    scale = max((v for _, v in values), default=1) if not percent else 100
    scale = max(1, scale)
    h = 90 + 30 * len(values)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="780" height="{h}" viewBox="0 0 780 {h}">',
        '<rect width="100%" height="100%" fill="#f4f8fc"/>',
        '<g font-family="sans-serif" fill="#18354b">',
        f'<text x="24" y="33" font-size="20" font-weight="bold">{escape(title)}</text>',
        f'<text x="24" y="57" font-size="13">{escape(unit)}</text>',
    ]
    for i, (key, value) in enumerate(values):
        y = 73 + i * 30
        width = 475 * value / scale
        label = f"{value:.1f}%" if percent else str(value)
        svg += [f'<text x="24" y="{y + 15}" font-size="14">{escape(str(key))}</text>',
                f'<rect x="163" y="{y}" width="{width:.2f}" height="20" rx="3" fill="#176e93"/>',
                f'<text x="{173 + width:.2f}" y="{y + 15}" font-size="14">{label}</text>']
    path.write_text("\n".join(svg + ["</g></svg>"]), encoding="utf-8")


def rate(rows):
    return 100 * sum(int(r["implemented_90d"]) for r in rows) / len(rows)


def main():
    with (ROOT / "data/kaizen_v1.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["quarter", "effect_declared", "implemented_90d", "split"]
        rows = list(reader)
    assert all(re.fullmatch(r"20\d\dQ[1-4]", r["quarter"]) and r["split"] in SPLITS
               and all(r[k] in {"0", "1"} for k in ("effect_declared", "implemented_90d"))
               for r in rows)
    min_group = min(Counter(tuple(r.values()) for r in rows).values())
    assert min_group >= 10
    parts = {s: [r for r in rows if r["split"] == s] for s in SPLITS}
    assert all(parts.values())
    quarters = {s: {r["quarter"] for r in part} for s, part in parts.items()}
    assert max(quarters["train"]) < min(quarters["validation"])
    assert max(quarters["validation"]) < min(quarters["test"])
    # EDA для проектирования смотрит на train. По val/test — только объёмы.
    train = parts["train"]
    by_quarter = [(q, [r for r in train if r["quarter"] == q]) for q in sorted(quarters["train"])]
    by_effect = [(v, [r for r in train if r["effect_declared"] == v]) for v in ("0", "1")]
    eda = ROOT / "lab05"
    figures = eda / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    charts = [
        ("01_split", "Объём выборок", [(s, len(rs)) for s, rs in parts.items()], False),
        ("02_train_quarter", "Train: заявки по кварталам", [(q, len(rs)) for q, rs in by_quarter], False),
        ("03_train_target", "Train: реализация за 90 дней", sorted(Counter(r["implemented_90d"] for r in train).items()), False),
        ("04_train_effect", "Train: признак заявленного эффекта", [(v, len(rs)) for v, rs in by_effect], False),
        ("05_train_quarter_rate", "Train: доля реализации по кварталам", [(q, rate(rs)) for q, rs in by_quarter], True),
        ("06_train_effect_rate", "Train: доля реализации по группам эффекта", [(v, rate(rs)) for v, rs in by_effect], True),
    ]
    for name, title, values, pct in charts:
        chart(figures / (name + ".svg"), title, values, "% заявок" if pct else "Число заявок, шт.", pct)
    table(eda / "eda_values.csv", ("figure", "category", "value"),
          [(name, k, round(v, 4)) for name, _, vals, _ in charts for k, v in vals])
    table(eda / "quality_checks.csv", ("check", "result"), [
        ("rows", len(rows)), ("missing_fields", sum(v == "" for r in rows for v in r.values())),
        ("schema_and_domains", "pass"), ("quarter_overlap", 0),
        ("smallest_group_including_label", min_group),
        ("identical_public_rows", len(rows) - len({tuple(r.values()) for r in rows})),
    ])
    model = ROOT / "lab07"
    model.mkdir(exist_ok=True)
    prediction = int(sum(int(r["implemented_90d"]) for r in train) * 2 > len(train))
    results = []
    for s, part in parts.items():
        outcomes = Counter((int(r["implemented_90d"]), prediction) for r in part)
        tn, fp, fn, tp = (outcomes[pair] for pair in ((0, 0), (0, 1), (1, 0), (1, 1)))
        div = lambda n, d: round(n / d, 6) if d else 0.0
        specificity, recall = div(tn, tn + fp), div(tp, tp + fn)
        results.append((s, len(part), prediction, tn, fp, fn, tp,
                        div(tn + tp, len(part)), round((specificity + recall) / 2, 6),
                        div(tp, tp + fp), recall, div(2 * tp, 2 * tp + fp + fn)))
    table(model / "metrics.csv", ("split", "n", "constant", "tn", "fp", "fn", "tp",
          "accuracy", "balanced_accuracy", "precision_1", "recall_1", "f1_1"), results)
    examples = {"correct": [], "error": []}
    for idx, r in enumerate(rows, start=2):
        if r["split"] == "test":
            actual = int(r["implemented_90d"])
            bucket = "correct" if actual == prediction else "error"
            if len(examples[bucket]) < 10:
                examples[bucket].append((bucket, idx, r["quarter"], r["effect_declared"], actual, prediction))
    assert all(len(v) == 10 for v in examples.values())
    table(model / "cases.csv", ("result", "line_in_release_csv", "quarter", "effect_declared",
          "actual", "prediction"), examples["correct"] + examples["error"])
    settings = dict(data="kaizen_v1", target="implemented_90d", estimator="train majority",
                    tie_breaker=0, prediction=prediction, seed_model=None, seed_export_order=42,
                    split_periods={s: sorted(qs) for s, qs in quarters.items()})
    (model / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
