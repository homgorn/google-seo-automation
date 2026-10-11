#!/usr/bin/env python3
"""
wiki_query.py — поиск и инспекция по вики-базе Google/Microsoft API.

Примеры:
  python scripts/wiki_query.py stats
  python scripts/wiki_query.py endpoints --source gtm --limit 15
  python scripts/wiki_query.py search "tag manager workspace"
  python scripts/wiki_query.py endpoint accounts.properties.get
  python scripts/wiki_query.py collisions --source ga4_admin
  python scripts/wiki_query.py changes --limit 10
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

DB_PATH = Path(__file__).parent.parent / "data" / "wiki.db"


def connect():
    if not DB_PATH.exists():
        sys.exit(f"[!] БД не найдена: {DB_PATH}\n    Запусти: python scripts/init_db.py")
    return sqlite3.connect(DB_PATH)


def cmd_stats(conn, args):
    print("=" * 62)
    print("  СОСТОЯНИЕ ВИКИ-БАЗЫ")
    print("=" * 62)

    rows = conn.execute(
        """SELECT d.source, COUNT(DISTINCT e.id), COUNT(DISTINCT d.id)
           FROM api_docs d LEFT JOIN api_endpoints e ON e.doc_id = d.id
           GROUP BY d.source ORDER BY 3 DESC, 2 DESC"""
    ).fetchall()

    print(f"\n{'ИСТОЧНИК':24s} {'ЭНДПОИНТОВ':>11s} {'ДОКУМЕНТОВ':>11s}")
    print("-" * 50)
    tot_ep = tot_doc = 0
    for src, ep, doc in rows:
        print(f"{src:24s} {ep:11d} {doc:11d}")
        tot_ep += ep
        tot_doc += doc
    print("-" * 50)
    print(f"{'ИТОГО':24s} {tot_ep:11d} {tot_doc:11d}")

    print("\nТоп HTTP-методов:")
    for m, c in conn.execute(
        "SELECT method, COUNT(*) c FROM api_endpoints GROUP BY method ORDER BY c DESC"
    ):
        bar = "#" * min(40, c // 3)
        print(f"  {m:7s} {c:5d}  {bar}")

    print("\nТоп ресурсов:")
    for r, c in conn.execute(
        """SELECT resource, COUNT(*) c FROM api_endpoints
           WHERE resource<>'' GROUP BY resource ORDER BY c DESC LIMIT 8"""
    ):
        print(f"  {c:4d}  {r}")

    orphan = conn.execute(
        "SELECT COUNT(*) FROM api_endpoints WHERE resource=''"
    ).fetchone()[0]
    if orphan:
        print(f"\n[!] Строк с resource='' (наследие миграции v1): {orphan}")
        print("    Почистить: python scripts/wiki_query.py clean-legacy")

    print("\nПоследние прогоны:")
    for r in conn.execute(
        """SELECT source, run_type, status, docs_created, docs_updated, completed_at
           FROM sync_runs ORDER BY id DESC LIMIT 5"""
    ):
        print(f"  {r[5] or '—':20s} {r[0]:20s} {r[1]:12s} {r[2]:10s} +{r[3]}/~{r[4]}")
    print()


def cmd_endpoints(conn, args):
    q = """SELECT e.method, e.resource, e.method_name, e.path, e.deprecated,
                  substr(coalesce(e.description,''),1,90)
           FROM api_endpoints e JOIN api_docs d ON d.id = e.doc_id"""
    params = []
    if args.source:
        q += " WHERE d.source = ?"
        params.append(args.source)
    q += " ORDER BY e.resource, e.method_name LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(q, params).fetchall()
    print(f"\n{'МЕТОД':7s} {'РЕСУРС':40s} {'RPC ID':38s}")
    print("-" * 88)
    for m, res, mname, path, dep, desc in rows:
        flag = " [DEPRECATED]" if dep else ""
        print(f"{m:7s} {res:40s} {mname}{flag}")
    print(f"\nПоказано: {len(rows)}")


def cmd_search(conn, args):
    """Полнотекстовый поиск по вики (SQLite FTS5)."""
    q = args.query
    try:
        rows = conn.execute(
            """SELECT d.source, d.category, d.title,
                      snippet(api_docs_fts, 1, '[', ']', '…', 12),
              bm25(api_docs_fts) AS rank
               FROM api_docs_fts
               JOIN api_docs d ON d.id = api_docs_fts.rowid
               WHERE api_docs_fts MATCH ? ORDER BY rank LIMIT ?""",
            (q, args.limit),
        ).fetchall()
    except sqlite3.OperationalError as e:
        sys.exit(f"[!] Ошибка FTS: {e}\n    Синтаксис FTS5, напр. 'gtm AND workspace'")

    if not rows:
        print(f"\nНичего не найдено: {q!r}")
        return
    print(f"\nНайдено: {len(rows)}\n" + "=" * 78)
    for src, cat, title, snip, rank in rows:
        print(f"\n[{src}/{cat}] {title}")
        print(f"  {snip.strip()}")


def cmd_endpoint(conn, args):
    """Поиск RPC по id.

    Реальные id в discovery выглядят как `tagmanager.accounts.get` —
    с префиксом имени API. Поэтому ищем и полное совпадение, и суффикс по
    границе точки: пользователь может написать accounts.get или accounts.get.
    """
    rid = args.rpc_id.strip()
    patterns = [rid, f"%.{rid}", f"{rid}.%", f"%.{rid}.%"]

    sql = f"""SELECT e.method, e.resource, e.path, e.full_url, e.description,
                     e.parameters, e.auth_scopes, e.deprecated, d.source, d.version,
                     e.method_name
              FROM api_endpoints e JOIN api_docs d ON d.id = e.doc_id
              WHERE {' OR '.join(['e.method_name LIKE ?'] * len(patterns))}
              ORDER BY e.method_name LIMIT 12"""
    rows = conn.execute(sql, patterns).fetchall()

    if not rows:
        sys.exit(f"[!] Не найдено: {rid}")

    for m, res, path, full, desc, params, scopes, dep, src, ver, mname in rows:
        print(f"\n{'=' * 74}\n{m}  {mname}   [источник: {src} {ver}]\n{'=' * 74}")
        print(f"Ресурс : {res}")
        print(f"HTTP   : {m}   deprecated={bool(dep)}")
        print(f"Шаблон : {path}")
        print(f"Полный : {full}")
        if desc:
            d = " ".join(desc.split())
            print(f"\nОписание:\n  {d[:700]}{'…' if len(d) > 700 else ''}")
        if params and params != "[]":
            print(f"\nПараметры ({len(json.loads(params))}):")
            print("  " + ", ".join(json.loads(params)))
        if scopes and scopes != "[]":
            print("\nOAuth scopes:")
            for s in json.loads(scopes):
                print(f"  - {s}")
        print()

    if len(rows) > 1:
        print(f"[*] Показано {len(rows)} совпадений — уточните запрос.")


def cmd_collisions(conn, args):
    """Показывает, где path-шаблоны совпадают у разных ресурсов."""
    q = """SELECT e.method, e.path, COUNT(DISTINCT e.resource), group_concat(DISTINCT e.resource)
           FROM api_endpoints e JOIN api_docs d ON d.id = e.doc_id
           WHERE e.resource <> ''"""
    params = []
    if args.source:
        q += " AND d.source = ?"
        params.append(args.source)
    q += " GROUP BY e.method, e.path HAVING COUNT(DISTINCT e.resource) > 1 ORDER BY 3 DESC LIMIT ?"
    params.append(args.limit)

    print(f"\n{'МЕТОД':7s} {'ПУТЬ-ШАБЛОН':30s} {'РЕСУРСОВ':>8s}")
    print("-" * 60)
    for m, path, cnt, owners in conn.execute(q, params):
        print(f"{m:7s} {path:30s} {cnt:8d}")
        if args.verbose:
            for o in owners.split(","):
                print(f"          - {o}")
    print("\nПримечание: это НЕ дубликаты. Google использует шаблоны путей;")
    print("конкретный маршрут получается подстановкой resource + name.")


def cmd_clean_legacy(conn, args):
    """Удаляет синтетические строки, оставшиеся после миграции v1 -> v2.

    Это производный кэш: он восстанавливается из discovery-документов
    командой sync_wiki.py --full, поэтому потеря не означает потерю данных.
    """
    n = conn.execute("SELECT COUNT(*) FROM api_endpoints WHERE resource=''").fetchone()[0]
    if n == 0:
        print("[OK] Устаревших строк нет.")
        return
    if not args.yes:
        print(f"Найдено строк с resource='': {n}")
        print("Это синтетические заглушки из миграции v1->v2, не реальные эндпоинты.")
        print("Повторите с --yes для удаления (данные восстанавливаются через sync_wiki.py --full).")
        return
    conn.execute("DELETE FROM api_endpoints WHERE resource=''")
    conn.commit()
    print(f"[OK] Удалено {n} строк. Пересчитать: sync_wiki.py --full")


def cmd_changes(conn, args):
    print(f"\n{'КОГДА':22s} {'ТИП':12s} {'ЧТО ИЗМЕНИЛОСЬ':46s}")
    print("-" * 84)
    for when, ctype, field in conn.execute(
        """SELECT detected_at, change_type, field_changed FROM change_log
           ORDER BY id DESC LIMIT ?""",
        (args.limit,),
    ):
        print(f"{when[:19]:22s} {ctype:12s} {str(field)[:46]:46s}")


def main():
    ap = argparse.ArgumentParser(description="Поиск по вики Google/Microsoft API")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats", help="Сводка по базе")

    p = sub.add_parser("endpoints", help="Список эндпоинтов")
    p.add_argument("--source")
    p.add_argument("--limit", type=int, default=30)

    p = sub.add_parser("search", help="Полнотекстовый поиск (FTS5)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)

    p = sub.add_parser("endpoint", help="Точный RPC по id")
    p.add_argument("rpc_id")

    p = sub.add_parser("collisions", help="Совпадения path-шаблонов")
    p.add_argument("--source")
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--verbose", action="store_true")

    p = sub.add_parser("clean-legacy", help="Удалить строки миграции v1->v2")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("changes", help="История изменений")
    p.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()
    conn = connect()
    {
        "stats": cmd_stats,
        "endpoints": cmd_endpoints,
        "search": cmd_search,
        "endpoint": cmd_endpoint,
        "collisions": cmd_collisions,
        "clean-legacy": cmd_clean_legacy,
        "changes": cmd_changes,
    }[args.cmd](conn, args)
    conn.close()


if __name__ == "__main__":
    main()