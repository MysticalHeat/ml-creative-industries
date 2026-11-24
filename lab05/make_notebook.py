"""Собрать и выполнить автономный Colab-ноутбук без включения CSV."""
import tempfile
from pathlib import Path

import nbformat as n
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
analysis = (ROOT / "analysis.py").read_text(encoding="utf-8")
analysis = analysis.replace("ROOT = Path(__file__).resolve().parent", "ROOT = Path.cwd()")

figures = [
    ("01_split.png", "Объём частей",
     "Хватает ли записей для отдельной оценки?",
     "Train — 6304, validation — 1059, test — 1910 записей.",
     "Сохранять временные части раздельно; test не применять для выбора модели."),
    ("02_quarters.png", "Объём train по кварталам",
     "Равномерно ли представлены кварталы?",
     "От 1005 записей в 2024Q3 до 2088 в 2025Q1; объёмы различаются.",
     "Учитывать неодинаковые объёмы и проверять переносимость на новых периодах."),
    ("03_target.png", "Баланс целевой метки train",
     "Есть ли перекос классов?",
     "Класс 0 — 3254 записи, класс 1 — 3050; оба класса представлены.",
     "Контролировать качество по обоим классам, а не только accuracy."),
    ("04_effect.png", "Заполненность эффекта в train",
     "Что показывает поле эффекта?",
     "Поле пусто у 3243 записей и заполнено у 3061. Это индикатор заполненности, не сумма.",
     "Не считать пустоту нулевой суммой; не включать поле в модель из-за возможной утечки."),
    ("05_quarter_rate.png", "Доля реализации по кварталам train",
     "Меняется ли доля реализации со временем?",
     "По кварталам доля составляет 44,4%, 50,3%, 48,5% и 48,6%.",
     "Сохранить временную validation и проверить устойчивость на новых периодах."),
    ("06_effect_rate.png", "Реализация и заполненность эффекта",
     "Различаются ли группы по доле реализации?",
     "При пустом поле реализовано 71,5%, при заполненном — 23,9%.",
     "Исключить поле из модели: момент заполнения неизвестен и возможна утечка."),
    ("07_quarter_effect.png", "Сравнение внутри кварталов train",
     "Сохраняется ли различие внутри каждого квартала?",
     "Во всех четырёх кварталах доля выше в группе с пустым полем; связь описательная, не причинная.",
     "Не использовать поле в модели до подтверждения его доступности на момент прогноза."),
]

cells = [
    n.v4.new_markdown_cell("""# ЛР №5. Разведочный анализ и проверка качества данных
ДГТУ · МИК21 · Елманов Илья · проект «Кайдзен».

Цель — проверить качество данных и риски для прогноза реализации заявки за 90 дней. Все результаты ниже сохранены: для просмотра CSV не нужен. Для повторного запуска необходим согласованный `kaizen_v1.csv` в рабочей папке среды или путь в переменной `KAIZEN_CSV`. Код встроен в ноутбук; таблицы и графики записываются в `results/`. Сам набор данных в ноутбук не включён и не предназначен для публичной публикации. Для запуска нужны Python 3 и matplotlib. Результаты относятся к зафиксированной версии CSV, проверяемой по SHA-256.

Анализ по кварталам и группам выполнен на train; объёмы частей и Data Card приведены для всех частей. Test не используется для выбора модели."""),
    n.v4.new_code_cell(analysis),
    n.v4.new_code_cell("from IPython.display import display, Image, Markdown"),
]
for filename, title, question, result, decision in figures:
    cells.append(n.v4.new_markdown_cell(
        f"## {title}\n\n**Вопрос:** {question}\n\n"
        f"**Результат:** {result}\n\n**Решение:** {decision}"
    ))
    cells.append(n.v4.new_code_cell(f'display(Image(filename="results/figures/{filename}"))'))

cells += [
    n.v4.new_markdown_cell("## Обзор проверок, примеров и ограничений\nРезультаты проверки защищённого исходника отделены от проверок, воспроизводимых по v1. Примеры — агрегированные сочетания, не разбор отдельных исходных заявок."),
    n.v4.new_code_cell("""review = Path("results/quality_review.md").read_text(encoding="utf-8")
# Локальные ссылки из отдельного обзора в Colab не работают: материалы показаны ниже и выше.
review = review.replace(
    "Таблица проверок: [quality_checks.csv](quality_checks.csv); [карточка](data_card_update.md); [график внутри кварталов](figures/07_quarter_effect.png).",
    "Таблица проверок и Data Card приведены ниже, график внутри кварталов — выше."
)
display(Markdown(review))"""),
    n.v4.new_markdown_cell("## Обновлённая Data Card"),
    n.v4.new_code_cell('display(Markdown(Path("results/data_card_update.md").read_text(encoding="utf-8")))'),
    n.v4.new_markdown_cell("## Таблица проверок качества"),
    n.v4.new_code_cell("""with Path("results/quality_checks.csv").open(encoding="utf-8", newline="") as handle:
    checks = list(csv.reader(handle))
display(Markdown("\\n".join([" | ".join(checks[0]), " | ".join(["---"] * len(checks[0]))] + [" | ".join(r) for r in checks[1:]])))"""),
]
nb = n.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
# Выводы генерируются в изолированной рабочей папке; KAIZEN_CSV задаётся снаружи.
with tempfile.TemporaryDirectory(prefix="lab05-execution-") as workdir:
    NotebookClient(nb, timeout=120, kernel_name="python3",
                   resources={"metadata": {"path": workdir}}).execute()
n.write(nb, ROOT / "eda.ipynb")
