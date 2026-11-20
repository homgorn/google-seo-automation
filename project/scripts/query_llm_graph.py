#!/usr/bin/env python3
"""
query_llm_graph.py — семантический поиск по вики LLM: data/llm_knowledge.db

Использование:
  python scripts/query_llm_graph.py --subject feature:F015
  python scripts/query_llm_graph.py --query "inp 200ms threshold"
  python scripts/query_llm_graph.py --predicate enforces
"""

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "llm_knowledge.db"


def query(subject=None, predicate=None, text=None, entity_type=None):
    if not DB_PATH.exists():
        print(f"[!] БД не найдена: {DB_PATH}\n    Запусти: python scripts/build_llm_knowledge.py")
        return 2

    conn = sqlite3.connect(DB_PATH)
    rows = []
    if subject:
        for (s, p, o) in conn.execute(
            "SELECT subject, predicate, object FROM triples WHERE subject = ?", (subject,)
        ).fetchall():
            rows.append((s, p, o))
        for (s, p, o) in conn.execute(
            "SELECT subject, predicate, object FROM ontology WHERE subject = ?", (subject,)
        ).fetchall():
            rows.append((s, p, o))
    else:
        clauses, args = [], []
        if predicate:
            clauses.append("predicate = ?")
            args.append(predicate)
        if text:
            like = f"%{text.lower()}%"
            clauses.append("LOWER(subject || ' ' || predicate || ' ' || object) LIKE ?")
            args.append(like)
        for (s, p, o) in conn.execute(
            "SELECT subject, predicate, object FROM triples" + (" WHERE " + " AND ".join(clauses) if clauses else ""),
            args,
        ).fetchall():
            rows.append((s, p, o))
        for (s, p, o) in conn.execute(
            "SELECT subject, predicate, object FROM ontology" + (" WHERE " + " AND ".join(clauses) if clauses else ""),
            args,
        ).fetchall():
            rows.append((s, p, o))
    conn.close()
    for s, p, o in rows:
        print(f"  {s} - {p} -> {o}")
    return 0 if rows else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--predicate")
    ap.add_argument("--query")
    ap.add_argument("--entity-type")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    return query(subject=args.subject, predicate=args.predicate, text=args.query,
                 entity_type=args.entity_type)


if __name__ == "__main__":
    sys.exit(main())
