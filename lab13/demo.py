#!/usr/bin/env python3
"""Локальный учебный демонстратор: синтетические данные, без сети."""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
import baseline

ROOT = Path(__file__).resolve().parent
VERSION = "A13-alpha-2.0"
RULES = json.loads((ROOT / "rules.json").read_text(encoding="utf-8"))


def connect(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""CREATE TABLE IF NOT EXISTS cases
        (case_id TEXT PRIMARY KEY, request TEXT NOT NULL, response TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT NOT NULL REFERENCES cases(case_id), payload TEXT NOT NULL);""")
    return db


def create(db, case_id, evidence, fail=False):
    if evidence not in ("enough", "insufficient"):
        raise ValueError("evidence: enough или insufficient")
    request = {"schema_version": "1.0", "request_id": case_id}
    model = baseline.handle(json.dumps(request), ROOT / "__missing_model__.json" if fail else None)
    if model["status"] == "error" and model["error"]["code"] == "invalid_input":
        raise ValueError("invalid_input: ID — 1–64 латинских букв, цифр, _ или -")
    decision = "manual_review" if model["status"] != "ok" or evidence == "insufficient" else "expert_action"
    reason = ("Модель недоступна" if model["status"] != "ok" else
              "Недостаточно сведений" if evidence == "insufficient" else "Сведения отмечены как достаточные")
    result = {"version": VERSION, "request": {**request, "evidence": evidence}, "model": model,
              "knowledge": {"version": RULES["version"], "source": RULES["source"],
                            "rule": RULES["rule"], "reason": reason},
              "route": decision, "final_class": None}
    with db:
        db.execute("INSERT INTO cases VALUES (?,?,?)", (case_id, json.dumps(result["request"], ensure_ascii=False),
                                                         json.dumps(result, ensure_ascii=False)))
    return result


def history(db, case_id):
    row = db.execute("SELECT response FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not row:
        raise ValueError("Случай не найден")
    result = json.loads(row[0])
    result["actions"] = [{"id": i, **json.loads(payload)} for i, payload in db.execute(
        "SELECT id,payload FROM actions WHERE case_id=? ORDER BY id", (case_id,))]
    return result


def act(db, case_id, action, reason, corrected=None, recipient=None, next_step=None):
    try:
        db.execute("BEGIN IMMEDIATE")
        h = history(db, case_id)
        if h["actions"] and h["actions"][-1]["action"] != "review":
            raise ValueError("Случай уже завершён")
        if action not in ("confirm", "correct", "review") or not reason or not reason.strip() or len(reason) > 500:
            raise ValueError("Требуются допустимое действие и причина до 500 символов")
        if h["route"] == "manual_review" and action != "review":
            raise ValueError("Нет оснований для класса: доступна только ручная проверка")
        if action == "correct":
            if type(corrected) is not int or corrected not in (0, 1) or corrected == h["model"]["prediction"]["class"]:
                raise ValueError("Исправленный класс должен отличаться от прогноза")
        elif corrected is not None:
            raise ValueError("Класс разрешён только при исправлении")
        if action == "review":
            if not all(isinstance(x, str) and 0 < len(x.strip()) <= 500 for x in (recipient, next_step)):
                raise ValueError("Для проверки нужны роль и следующий шаг")
        elif recipient is not None or next_step is not None:
            raise ValueError("Роль и шаг только для проверки")
        result_class = None if action == "review" else corrected if action == "correct" else h["model"]["prediction"]["class"]
        event = {"action": action, "reason": reason, "result_class": result_class,
                 "status": "pending_review" if action == "review" else "recorded",
                 "recipient_role": recipient, "next_step": next_step,
                 "actor_role": "условный эксперт", "type": "simulation", "model_updated": False,
                 "previous_id": h["actions"][-1]["id"] if h["actions"] else None,
                 "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        db.execute("INSERT INTO actions(case_id,payload) VALUES (?,?)", (case_id, json.dumps(event, ensure_ascii=False)))
        db.commit()
        return history(db, case_id)
    except Exception:
        db.rollback()
        raise


def main():
    p = argparse.ArgumentParser(description="Синтетический локальный демонстратор, не для реальных решений")
    p.add_argument("--db", default="history.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)
    n = sub.add_parser("new"); n.add_argument("id"); n.add_argument("--evidence", required=True, choices=["enough", "insufficient"]); n.add_argument("--simulate-model-error", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    a = sub.add_parser("act"); a.add_argument("id"); a.add_argument("action", choices=["confirm", "correct", "review"]); a.add_argument("--reason", required=True); a.add_argument("--class", dest="corrected", type=int); a.add_argument("--recipient"); a.add_argument("--next-step")
    args = p.parse_args()
    try:
        with connect(args.db) as db:
            if args.command == "new":
                print("Ожидание: выполняются проверка и вызов модели...", flush=True)
                result = create(db, args.id, args.evidence, args.simulate_model_error)
            elif args.command == "show":
                result = history(db, args.id)
            else:
                result = act(db, args.id, args.action, args.reason, args.corrected, args.recipient, args.next_step)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, sqlite3.Error, OSError) as exc:
        print("Ошибка: действие не подтверждено:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
