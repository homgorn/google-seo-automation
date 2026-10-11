#!/usr/bin/env python3
"""
sync_wiki.py — синхронизация вики Google/Microsoft API с официальными источниками.

Источники (машиночитаемые, без парсинга HTML):
  - Google Discovery Documents ($discovery/rest?version=X) → api_endpoints
  - Локальные markdown-вики (wiki/*.md) → api_docs + FTS
  - Change detection по SHA256

Использование:
  python3 scripts/sync_wiki.py --full
  python3 scripts/sync_wiki.py --incremental
  python3 scripts/sync_wiki.py --source ga4
  python3 scripts/sync_wiki.py --check-freshness
"""

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Windows-консоль по умолчанию cp1252/cp866 — не печатает кириллицу.
# Форсируем UTF-8 на уровне stdout/stderr, иначе скрипт падает на первом же print().
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"
WIKI_DIR = PROJECT_ROOT / "wiki"
STALE_DAYS = 14

# ─────────────────────────────────────────────────────────────
# Discovery documents: официальные машиночитаемые спецификации
# ─────────────────────────────────────────────────────────────
DISCOVERY_SOURCES = {
    "ga4_data": {
        "name": "Google Analytics Data API v1beta",
        "url": "https://analyticsdata.googleapis.com/$discovery/rest?version=v1beta",
        "version": "v1beta",
    },
    "ga4_admin": {
        "name": "Google Analytics Admin API v1alpha",
        "url": "https://analyticsadmin.googleapis.com/$discovery/rest?version=v1alpha",
        "version": "v1alpha",
    },
    "gtm": {
        "name": "Google Tag Manager API v2",
        "url": "https://tagmanager.googleapis.com/$discovery/rest?version=v2",
        "version": "v2",
    },
    "gsc": {
        # НЕ webmasters/v3 — тот discovery отдаёт 404. Живой документ: searchconsole:v1
        "name": "Google Search Console API v1",
        "url": "https://searchconsole.googleapis.com/$discovery/rest?version=v1",
        "version": "v1",
    },
    "indexing": {
        "name": "Google Indexing API v3",
        "url": "https://indexing.googleapis.com/$discovery/rest?version=v3",
        "version": "v3",
    },
    "pagespeed": {
        "name": "PageSpeed Insights API v5",
        "url": "https://www.googleapis.com/discovery/v1/apis/pagespeedonline/v5/rest",
        "version": "v5",
    },
    "business_profile": {
        # v4 (mybusiness.googleapis.com) отдаёт 404. Живой документ:
        # mybusinessbusinessinformation:v1 — accounts/locations/attributes/categories
        "name": "Google Business Profile (Business Information) API v1",
        "url": "https://mybusinessbusinessinformation.googleapis.com/$discovery/rest?version=v1",
        "version": "v1",
    },
    "merchant": {
        "name": "Google Merchant API v1",
        "url": "https://merchantapi.googleapis.com/$discovery/rest?version=v1",
        "version": "v1",
        # ИЗМЕРЕНО 2026-10-12: документ существует (revision 20261006), но
        # resources = {} пустой, есть только schemas ProductChange и
        # ProductStatusChangeMessage. Методов в discovery нет.
        # Стратегия для merchant — отдельная (proto/HTML), см. docs/architecture.md
        "known_empty": True,
    },
}

USER_AGENT = "google-seo-automation-wiki/1.0 (+https://github.com/homgorn)"
HTTP_TIMEOUT = 45


# ─────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────
def connect():
    if not DB_PATH.exists():
        print(f"[!] DB не найден: {DB_PATH}")
        print("    Сначала: python3 scripts/init_db.py")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def start_run(conn, source, run_type):
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sync_runs (source, run_type, status, run_id) VALUES (?,?,?,?)",
        (source, run_type, "running", run_id),
    )
    conn.commit()
    return run_id


def finish_run(conn, run_id, status, processed=0, created=0, updated=0, errors=None):
    conn.execute(
        """UPDATE sync_runs
           SET completed_at=?, status=?, docs_processed=?, docs_created=?,
               docs_updated=?, errors=?
           WHERE run_id=?""",
        (
            datetime.now(timezone.utc).isoformat(),
            status,
            processed,
            created,
            updated,
            json.dumps(errors or [], ensure_ascii=False),
            run_id,
        ),
    )
    conn.commit()


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def age_days(ts):
    """Возраст строки в днях. SQLite CURRENT_TIMESTAMP отдаёт naive-строку
    ('2026-10-12 10:00:00'), а мы пишем ISO-aware — сравнение падало бы
    с TypeError. Приводим к UTC-aware перед вычитанием."""
    try:
        dt = datetime.fromisoformat(ts.replace(" ", "T"))
    except (ValueError, AttributeError):
        return 999
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


# ─────────────────────────────────────────────────────────────
# Discovery fetch + extraction
# ─────────────────────────────────────────────────────────────
def fetch_json(url):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} — {url}")
    except URLError as e:
        raise RuntimeError(f"Сеть недоступна: {e.reason}")


def extract_methods(discovery):
    """Извлекает все методы из discovery-документа РЕКУРСИВНО.

    Почему рекурсия, а не один проход: Tag Manager v2 вложен на 4 уровня
    (accounts -> containers -> workspaces -> tags). Однопроходный разбор
    давал 3 эндпоинта вместо 106 — ИЗМЕРЕНО 2026-10-12.

    Поддерживает две формы:
      1) {"resources": {"X": {"methods": {"list": {"path": ..., "httpMethod": ...}}}}}
      2) {"resources": {"X": {"list": {"path": ...}}}}  — без обёртки "methods"
    """
    out = []

    def walk(res, prefix):
        for res_name, r in (res.get("resources") or {}).items():
            if not isinstance(r, dict):
                continue

            path_here = f"{prefix}{res_name}" if prefix else res_name

            # Форма 1: обёртка "methods"
            for verb, m in (r.get("methods") or {}).items():
                if isinstance(m, dict) and "path" in m:
                    out.append(_mk(path_here, m, verb))

            # Форма 2: методы лежат прямо на ресурсе
            for verb, m in r.items():
                if verb in ("methods", "resources") or not isinstance(m, dict):
                    continue
                if "path" in m and ("httpMethod" in m or "id" in m):
                    out.append(_mk(path_here, m, verb))

            # Рекурсия ВСЕГДА, а не только когда своих методов нет.
            # Ресурс может иметь и свои методы, и вложенные ресурсы
            # (GTM: accounts имеет 3 метода И содержит containers/versions/...).
            # Условная рекурсия теряла 103 из 106 эндпоинтов GTM.
            walk(r, f"{path_here}.")

    walk(discovery, "")
    return out


def _mk(resource, m, verb):
    return {
        "resource": resource,
        "method_name": m.get("id") or f"{resource}.{verb}",
        "http_method": (m.get("httpMethod") or "GET").upper(),
        "path": m["path"],
        "description": (m.get("description") or "").strip(),
        "scopes": list(m.get("scopes") or []),
        "params": list((m.get("parameters") or {}).keys()),
    }


def sync_discovery(conn, key, cfg):
    """Синхронизирует один discovery-документ. Возвращает статистику."""
    stats = {"processed": 0, "created": 0, "updated": 0}
    run_id = start_run(conn, key, "incremental")

    try:
        doc = fetch_json(cfg["url"])
    except RuntimeError as e:
        finish_run(conn, run_id, "failed", errors=[{"source": key, "error": str(e)}])
        print(f"  [FAIL] {key}: {e}")
        return stats, []

    base_url = doc.get("baseUrl") or doc.get("rootUrl") or ""
    methods = extract_methods(doc)
    errors = []

    # 1) Документ целиком → api_docs (для семантического поиска)
    title = cfg["name"]
    body = json.dumps(
        {
            "baseUrl": base_url,
            "version": doc.get("version"),
            "revision": doc.get("revision"),
            "method_count": len(methods),
            "methods": methods,
        },
        ensure_ascii=False,
        indent=2,
    )
    h = sha256(body)
    existing = conn.execute(
        "SELECT id, content_hash FROM api_docs WHERE url=?", (cfg["url"],)
    ).fetchone()

    if existing is None:
        conn.execute(
            """INSERT INTO api_docs
               (source, category, title, url, content, content_hash, version, metadata)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                key,
                "discovery",
                title,
                cfg["url"],
                body,
                h,
                cfg["version"],
                json.dumps({"base_url": base_url, "methods": len(methods)}),
            ),
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        stats["created"] += 1
        is_new = True
    else:
        doc_id = existing[0]
        is_new = False
        if existing[1] != h:
            conn.execute(
                """UPDATE api_docs SET content=?, content_hash=?, last_updated=?
                   WHERE id=?""",
                (body, h, datetime.now(timezone.utc).isoformat(), doc_id),
            )
            conn.execute(
                """INSERT INTO change_log (doc_id, change_type, field_changed, new_value, sync_run_id)
                   VALUES (?,?,?,?,?)""",
                (doc_id, "updated", "discovery_document", f"sha256:{h[:12]}", run_id),
            )
            stats["updated"] += 1
        else:
            conn.execute(
                "UPDATE api_docs SET last_fetched=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), doc_id),
            )

    stats["processed"] = len(methods)

    # 2) Каждый метод → api_endpoints
    for m in methods:
        full_url = base_url.rstrip("/") + "/" + m["path"].lstrip("/")
        # Идентичность — (doc_id, resource, method_name), НЕ (method, path):
        # пути Google это ШАБЛОНЫ ({+name}), одни и те же у десятков методов.
        row = conn.execute(
            """SELECT id, description FROM api_endpoints
               WHERE doc_id=? AND resource=? AND method_name=?""",
            (doc_id, m["resource"], m["method_name"]),
        ).fetchone()

        if row is None:
            conn.execute(
                """INSERT INTO api_endpoints
                   (doc_id, resource, method_name, method, path, full_url,
                    description, parameters, auth_scopes, deprecated)
                   VALUES (?,?,?,?,?,?,?,?,?,0)""",
                (
                    doc_id,
                    m["resource"],
                    m["method_name"],
                    m["http_method"],
                    m["path"],
                    full_url,
                    m["description"],
                    json.dumps(m["params"]),
                    json.dumps(m["scopes"]),
                ),
            )
        elif row[1] != m["description"]:
            conn.execute(
                """UPDATE api_endpoints
                   SET description=?, parameters=?, auth_scopes=?, path=?, method=?
                   WHERE id=?""",
                (
                    m["description"],
                    json.dumps(m["params"]),
                    json.dumps(m["scopes"]),
                    m["path"],
                    m["http_method"],
                    row[0],
                ),
            )
            conn.execute(
                """INSERT INTO change_log (doc_id, change_type, field_changed, sync_run_id)
                   VALUES (?,?,?,?)""",
                (doc_id, "updated", f"endpoint:{m['method_name']}", run_id),
            )

    conn.commit()
    finish_run(conn, run_id, "completed", stats["processed"], stats["created"], stats["updated"], errors)

    flag = "NEW" if is_new else ("UPD" if stats["updated"] else "=  ")
    print(f"  [{flag}] {key:18s} {len(methods):4d} endpoints  ({stats['created']} docs created)")
    return stats, errors


# ─────────────────────────────────────────────────────────────
# Local wiki markdown ingest
# ─────────────────────────────────────────────────────────────
def parse_frontmatter(md):
    """Достаёт YAML-frontmatter без зависимости на PyYAML."""
    if not md.startswith("---"):
        return {}, md
    parts = md.split("---", 2)
    if len(parts) < 3:
        return {}, md
    fm = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, parts[2].lstrip("\n")


def sync_local_wiki(conn, sources=None):
    """Ингестит wiki/*.md в api_docs. Возвращает статистику."""
    stats = {"processed": 0, "created": 0, "updated": 0}
    if not WIKI_DIR.exists():
        print(f"  [SKIP] {WIKI_DIR} не существует")
        return stats

    run_id = start_run(conn, "local_wiki", "incremental")

    for md_path in sorted(WIKI_DIR.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        source = fm.get("source") or md_path.parent.name
        if sources and source not in sources and md_path.stem not in sources:
            continue

        url = f"local://{md_path.relative_to(PROJECT_ROOT).as_posix()}"
        h = sha256(raw)
        existing = conn.execute(
            "SELECT id, content_hash FROM api_docs WHERE url=?", (url,)
        ).fetchone()

        stats["processed"] += 1
        if existing is None:
            conn.execute(
                """INSERT INTO api_docs
                   (source, category, title, url, content, content_hash, version, metadata)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    source,
                    fm.get("category", "guide"),
                    fm.get("title", md_path.stem),
                    url,
                    raw,
                    h,
                    fm.get("version"),
                    json.dumps({k: v for k, v in fm.items() if k not in ("title",)}, ensure_ascii=False),
                ),
            )
            stats["created"] += 1
            print(f"  [NEW] {md_path.relative_to(PROJECT_ROOT).as_posix()}")
        elif existing[1] != h:
            conn.execute(
                """UPDATE api_docs SET content=?, content_hash=?, last_updated=?, version=? WHERE id=?""",
                (raw, h, datetime.now(timezone.utc).isoformat(), fm.get("version"), existing[0]),
            )
            conn.execute(
                """INSERT INTO change_log (doc_id, change_type, field_changed, new_value, sync_run_id)
                   VALUES (?,?,?,?,?)""",
                (existing[0], "updated", "local_markdown", f"sha256:{h[:12]}", run_id),
            )
            stats["updated"] += 1
            print(f"  [UPD] {md_path.relative_to(PROJECT_ROOT).as_posix()}")

    conn.commit()
    finish_run(conn, run_id, "completed", stats["processed"], stats["created"], stats["updated"])
    return stats


# ─────────────────────────────────────────────────────────────
# Freshness
# ─────────────────────────────────────────────────────────────
def check_freshness(conn):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)).isoformat()
    rows = conn.execute(
        """SELECT source, MAX(last_fetched), MAX(last_updated), COUNT(*)
           FROM api_docs GROUP BY source ORDER BY source"""
    ).fetchall()

    print()
    print(f"{'ИСТОЧНИК':22s} {'ПОСЛ. ЗАГРУЗКА':22s} {'ВОЗРАСТ':>8s}  {'ДОК':>5s}  СТАТУС")
    print("─" * 78)

    stale = []
    for source, last_fetch, last_upd, count in rows:
        ts = last_fetch or last_upd
        if ts is None:
            age_d, status = 999, "НЕТ ДАННЫХ"
        else:
            age_d = age_days(ts)
            status = "OK" if age_d <= STALE_DAYS else "УСТАРЕЛ"
            if age_d > STALE_DAYS:
                stale.append(source)
        print(f"{source:22s} {(ts or '—')[:19]:22s} {age_d:6d}d  {count:5d}  {status}")

    print()
    total_docs = conn.execute("SELECT COUNT(*) FROM api_docs").fetchone()[0]
    total_ep = conn.execute("SELECT COUNT(*) FROM api_endpoints").fetchone()[0]
    print(f"Всего документов: {total_docs}   Эндпоинтов: {total_ep}")

    if stale:
        print(f"\n[!] Устаревшие (> {STALE_DAYS} дней): {', '.join(stale)}")
        print(f"    Обновить: python3 scripts/sync_wiki.py --source {stale[0]}")
    else:
        print(f"[OK] Все источники свежие (< {STALE_DAYS} дней)")
    return stale


# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Sync Google/Microsoft API wiki")
    ap.add_argument("--full", action="store_true", help="Полный ресинк всех источников")
    ap.add_argument("--incremental", action="store_true", help="Только изменения (по умолчанию)")
    ap.add_argument("--source", help="Один источник (ga4_data, gtm, gsc, ...)")
    ap.add_argument("--check-freshness", action="store_true", help="Только проверка свежести")
    ap.add_argument("--local-only", action="store_true", help="Только локальные .md файлы")
    args = ap.parse_args()

    conn = connect()

    if args.check_freshness:
        check_freshness(conn)
        return

    targets = (
        {args.source: DISCOVERY_SOURCES[args.source]}
        if args.source
        else DISCOVERY_SOURCES
    )
    if args.source and args.source not in DISCOVERY_SOURCES:
        print(f"[!] Неизвестный источник: {args.source}")
        print(f"    Доступные: {', '.join(DISCOVERY_SOURCES)}")
        sys.exit(1)

    mode = "full" if args.full else "incremental"
    print(f"=== sync_wiki: {mode} | источников: {len(targets)} ===\n")

    totals = {"processed": 0, "created": 0, "updated": 0}
    all_errors = []

    if not args.local_only:
        for key, cfg in targets.items():
            stats, errs = sync_discovery(conn, key, cfg)
            all_errors.extend(errs)
            for k in totals:
                totals[k] += stats[k]
            time.sleep(0.4)  # вежливо к API Google

    print()
    loc = sync_local_wiki(conn)
    for k in totals:
        totals[k] += loc[k]

    print()
    print("─── ИТОГ ───")
    print(f"  обработано: {totals['processed']}")
    print(f"  создано:    {totals['created']}")
    print(f"  обновлено:  {totals['updated']}")
    if all_errors:
        print(f"  ошибок:     {len(all_errors)}")
    print()
    check_freshness(conn)
    conn.close()


if __name__ == "__main__":
    main()