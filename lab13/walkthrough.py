"""Воспроизводимый фактический показ CLI на временной синтетической БД."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(db, *args, expected=0):
    command = [sys.executable, '-B', str(ROOT / 'demo.py'), '--db', db, *args]
    print('\n$ python3 -B demo.py --db <временная-БД> ' + ' '.join(args), flush=True)
    p = subprocess.run(command, text=True, capture_output=True, cwd=ROOT)
    print(p.stdout, end='')
    print(p.stderr, end='')
    print('Код выхода:', p.returncode, flush=True)
    if p.returncode != expected:
        raise RuntimeError('Неожиданный код выхода')


def main():
    print('A13-alpha-2.0: синтетическая заявка; технический показ, не пользовательский пилот.', flush=True)
    with tempfile.TemporaryDirectory() as directory:
        db = str(Path(directory) / 'history.sqlite3')
        run(db, 'new', 'demo-01', '--evidence', 'enough')
        run(db, 'act', 'demo-01', 'correct', '--reason', 'учебное основание', '--class', '1')
        run(db, 'show', 'demo-01')
        run(db, 'new', 'demo-02', '--evidence', 'insufficient')
        run(db, 'act', 'demo-02', 'confirm', '--reason', 'учебный тест', expected=2)
        run(db, 'act', 'demo-02', 'review', '--reason', 'недостаточно сведений', '--recipient', 'условный эксперт', '--next-step', 'уточнить сведения')
        run(db, 'new', 'demo-03', '--evidence', 'enough', '--simulate-model-error')
        run(db, 'act', 'demo-03', 'review', '--reason', 'модель недоступна', '--recipient', 'условный эксперт', '--next-step', 'рассмотреть вручную')
        run(db, 'show', 'demo-03')
        run(db, 'new', 'недопустимый ID', '--evidence', 'enough', expected=2)
    print('\nДЕМО ЗАВЕРШЕНО: временная база удалена; сетевой отправки и реальных данных нет.', flush=True)


if __name__ == '__main__':
    main()
