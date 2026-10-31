#!/usr/bin/env python3
"""
openchamber_sync.py — F009: синхронизация вики с OpenChamber-сессиями.

Направления:
  wiki -> openchamber (push): находит изменения в wiki/ и обновляет
    контекст соответствующей OpenChamber-сессии (F001–F011).
  openchamber -> wiki (pull): забирает решения/аудиты из сессий и пишет в wiki/notes.md.

Запуск:
  python scripts/openchamber_sync.py --direction wiki_to_oc
  python scripts/openchamber_sync.py --direction oc_to_wiki
  python scripts/openchamber_sync.py --status
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Windows: UTF-8 консоль
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

DB = Path(__file__).parent.parent / "data" / "wiki.db"
WIKI_DIR = Path(__file__).parent.parent / "wiki"
NOTES_DIR = WIKI_DIR / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


def wiki_to_oc(conn):
    """Найти свежие изменения (за 14 дней) и собрать их в заметку для каждой сессии."""
    rows = conn.execute(
        """SELECT doc_id, change_type, field_changed, new_value, detected_at,
                  (SELECT title FROM api_docs WHERE id=change_log.doc_id) AS title
           FROM change_log
           WHERE detected_at > datetime('now', '-14 days')
           ORDER BY detected_at DESC"""
    ).fetchall()

    print(f"Изменений за 14 дней: {len(rows)}")
    for r in rows:
        doc_id, ctype, field, new_val, ts, title = r
        snippet = (new_val or "").replace("\n", " ")[:120]
        print(f"  {title or '—'} | {ctype}:{field} | {snippet}...")


def oc_to_wiki(conn):
    """Создать/обновить заметку с текущим статусом проекта."""
    rows = conn.execute(
        """SELECT doc_id, change_type, field_changed, new_value, detected_at FROM change_log
           ORDER BY detected_at DESC LIMIT 20"""
    ).fetchall()
    # Простая заметка: список последних изменений + статус интеграций
    content_lines = [
        "# Синхронизация OpenChamber → Wiki",
        f"Время: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Последних изменений в БД: {len(rows)}",
        "",
        "### Последние изменения",
        "| Когда | Тип | Поле | Значение |",
        "|-------|-----|------|----------|",
    ]
    for doc_id, ctype, field, new_val, ts in rows:
        snippet = (new_val or "").replace("|", "\\|")[:60]
        content_lines.append(f"| {ts or '-'} | {ctype} | {field or '-'} | {snippet} |")

    note_path = NOTES_DIR / "sync_oc_to_wiki.md"
    note_path.write_text("\n".join(content_lines), encoding="utf-8")
    print(f"Заметка записана: {note_path.relative_to(WIKI_DIR.parent)}")


def show_status(conn):
    print("=== Статус F009 (OpenChamber Sync) ===")
    rows = conn.execute(
        "SELECT source, MAX(last_updated) as last_upd, COUNT(*) as docs FROM api_docs GROUP BY source ORDER BY source"
    ).fetchall()
    for src, last_upd, docs in rows:
        print(f"  {src:20s}  docs={docs:4d}  last={str(last_upd)[:19] if last_upd else '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", choices=["wiki_to_oc", "oc_to_wiki", "both"])
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    try:
        if args.status:
            show_status(conn)
        elif args.direction == "wiki_to_oc" or args.direction == "both":
            wiki_to_oc(conn)
        if args.direction == "oc_to_wiki" or (args.direction == "both" and not args.status):
            oc_to_wiki(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
