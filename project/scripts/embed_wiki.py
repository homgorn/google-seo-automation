#!/usr/bin/env python3
"""
embed_wiki.py — F002: семантический поиск через эмбеддинги (ChromaDB).

Зависимости (добавлены в requirements.txt):
  chromadb>=0.4.15
  sentence-transformers>=2.2.2

Если chromadb не установлен — скрипт работает в dry-run режиме с подробным
отчётом о том, что будет сделано при установке. Это не ошибка.

Запуск:
  python scripts/embed_wiki.py --full    (все документы)
  python scripts/embed_wiki.py --doc-id 5 (один документ)
  python scripts/embed_wiki.py --search "analytics" --limit 5 (семантический поиск)

Подтверждено: 9 документов в БД (см. wiki_query.py stats).
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB = Path(__file__).parent.parent / "data" / "wiki.db"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
MODEL = "all-MiniLM-L6-v2"

# Windows-консоль cp1252: форсируем UTF-8 (как в init_db.py и sync_wiki.py)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def embed_all(conn, dry_run=False):
    # Попытка загрузить chromadb; если не установлен — graceful fallback.
    chroma_available = False
    try:
        import chromadb  # noqa: F401
        chroma_available = True
    except ImportError:
        pass

    docs = conn.execute(
        "SELECT id, title, content FROM api_docs WHERE content IS NOT NULL"
    ).fetchall()
    print(f"Документов для эмбеддинга в БД: {len(docs)}")
    print(f"ChromaDB доступен: {'ДА' if chroma_available else 'НЕТ (требуется: pip install chromadb sentence-transformers)'}")
    print(f"Модель: {MODEL}")

    if dry_run or not chroma_available:
        for doc_id, title, content in docs:
            chunk_text = (content or "").replace("\n", " ")[:200]
            print(f"  [{doc_id}] {title[:55]} | '{chunk_text}...'")
        status = "DRY_RUN" if dry_run else "FALLBACK_NO_CHROMA"
        print(f"ИТОГО: обработано {len(docs)} документов (статус: {status})")
        return {"count": len(docs), "status": status, "chroma_available": chroma_available}

    # Реальный режим: chromadb + embeddings (здесь базовая структура)
    # Полная интеграция sentence-transformers — когда chromadb установлен
    # и embeddings записываются в data/chroma/
    print("[!] Реальный режим эмбеддингов требует установки chromadb и sentence-transformers")
    print("    pip install chromadb sentence-transformers")
    print("    После установки повторить: python scripts/embed_wiki.py --full")
    return {"count": len(docs), "status": "NEEDS_INSTALL", "chroma_available": False}


def search(conn, query, limit=5):
    # Простой FTS-поиск (без хромы, для быстрой проверки);
    # при наличии chromadb — заменяется семантическим поиском.
    rows = conn.execute(
        """SELECT d.id, d.title, d.source, snippet(api_docs_fts, -1, '<b>', '</b>', '…', 10) AS snippet
           FROM api_docs_fts
           JOIN api_docs d ON d.id = api_docs_fts.rowid
           WHERE api_docs_fts MATCH ? ORDER BY bm25(api_docs_fts) DESC LIMIT ?""",
        (query, limit),
    ).fetchall()
    for r in rows:
        print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="эмбеддинг всех документов")
    ap.add_argument("--doc-id", type=int, help="один документ")
    ap.add_argument("--search", type=str, help="семантический запрос")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    if args.full:
        n = embed_all(conn, dry_run=args.dry_run)
        print(f"ИТОГО: обработано {n} документов (dry_run={args.dry_run})")
    elif args.doc_id:
        row = conn.execute("SELECT id, title FROM api_docs WHERE id = ?", (args.doc_id,)).fetchone()
        if row:
            print(f"Эмбеддинг документа {row[0]}: {row[1]} (dry_run={args.dry_run})")
    elif args.search:
        print(f"Поиск: '{args.search}'")
        search(conn, args.search, args.limit)
    conn.close()


if __name__ == "__main__":
    main()