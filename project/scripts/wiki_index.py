#!/usr/bin/env python3
"""
wiki_index.py — генератор многоуровневых индексов вики.

Создаёт:
  wiki/index.md              — главный индекс (Markdown, с оглавлением)
  wiki/index.json            — машинно-читаемый индекс (для агентов)
  wiki/<source>/index.md     — индекс по каждому источнику
  wiki/_data/entities.json   — граф знаний: сущности, типы, свойства
  wiki/_data/triples.jsonl   — граф знаний: триплеты (субъект-предикат-объект)
  wiki/_data/graph.json      — граф знаний: узлы + рёбра + статистика

Запуск:
  python scripts/wiki_index.py            # сгенерировать
  python scripts/wiki_index.py --stats    # только статистика
  python scripts/wiki_index.py --verify   # проверить актуальность индекса

Проект (SDD): docs/specs/SPEC-F001-wiki-index.md
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import Verdict, check_mutation_allowed  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
DATA_DIR = WIKI_DIR / "_data"
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"

# ── Онтология: типы сущностей вики ─────────────────────────────
# Каждая сущность вики — это API-документ. Тип определяется по категории
# и source. Это минимальная, но рабочая онтология.
ENTITY_TYPES = {
    "discovery": "MachineReadableApiSpec",
    "guide": "UsageGuide",
    "reference": "ApiReference",
    "setup": "SetupProcedure",
    "audit": "AuditChecklist",
    "optimization": "OptimizationRecipe",
    "schema": "DataSchema",
    "test": "VerificationSuite",
}

# Свойства сущности -> предикат графа
PREDICATES = {
    "source": "has_source",
    "category": "has_category",
    "version": "has_version",
    "endpoint_count": "has_endpoint_count",
    "title": "has_title",
    "last_updated": "last_updated_at",
    "doc_id": "identified_by",
}


def connect():
    if not DB_PATH.exists():
        sys.exit(f"[!] БД не найдена: {DB_PATH}\n    Запусти: python scripts/init_db.py")
    return sqlite3.connect(DB_PATH)


def build_graph(conn):
    """Строит граф знаний: сущности + триплеты."""
    docs = conn.execute(
        """SELECT d.id, d.source, d.category, d.title, d.version, d.url,
                  d.last_updated, COUNT(e.id) AS ep_count
           FROM api_docs d
           LEFT JOIN api_endpoints e ON e.doc_id = d.id AND e.resource <> ''
           GROUP BY d.id
           ORDER BY d.source, d.title"""
    ).fetchall()

    entities = []
    triples = []
    by_source = defaultdict(list)

    for (doc_id, source, category, title, version, url,
         last_updated, ep_count) in docs:
        etype = ENTITY_TYPES.get(category, "Document")
        eid = f"doc:{doc_id}"

        entities.append(
            {
                "id": eid,
                "type": etype,
                "title": title,
                "source": source,
                "category": category,
                "version": version,
                "url": url,
                "endpoint_count": ep_count,
                "last_updated": last_updated,
            }
        )

        # Триплеты: субъект-предикат-объект
        for pred in ("source", "category", "version", "endpoint_count", "title"):
            value = locals().get(pred)
            if value is None or value == "":
                continue
            triples.append(
                {
                    "subject": eid,
                    "predicate": PREDICATES[pred],
                    "object": str(value),
                    "object_type": "literal",
                }
            )
        triples.append(
            {
                "subject": eid,
                "predicate": PREDICATES["last_updated"],
                "object": str(last_updated or ""),
                "object_type": "literal",
            }
        )

        by_source[source].append(eid)

    # Рёбра между сущностями: "share_source" внутри одного source
    for source, eids in by_source.items():
        for i, a in enumerate(eids):
            for b in eids[i + 1:]:
                triples.append(
                    {
                        "subject": a,
                        "predicate": "shares_source_with",
                        "object": b,
                        "object_type": "entity",
                    }
                )

    # Рёбра: "exposes_endpoint" (entity -> endpoint resource)
    endpoint_rows = conn.execute(
        """SELECT e.doc_id, e.resource, e.method, e.method_name
           FROM api_endpoints e WHERE e.resource <> ''
           GROUP BY e.doc_id, e.resource"""
    ).fetchall()
    resource_nodes = set()
    for doc_id, resource, method, method_name in endpoint_rows:
        rid = f"resource:{resource}"
        resource_nodes.add(rid)
        triples.append(
            {
                "subject": f"doc:{doc_id}",
                "predicate": "exposes_resource",
                "object": rid,
                "object_type": "entity",
            }
        )

    graph = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entity_count": len(entities),
        "triple_count": len(triples),
        "resource_count": len(resource_nodes),
        "types": dict(Counter(e["type"] for e in entities)),
        "sources": {s: len(e) for s, e in sorted(by_source.items())},
        "predicates": dict(Counter(t["predicate"] for t in triples)),
    }
    return entities, triples, graph, by_source


def write_indexes(conn):
    if not check_mutation_allowed(Verdict("F001"), "write_indexes (wiki indexes)"):
        print("[SKIP] write_indexes заблокирован: ALLOW_MUTATIONS != 1")
        return
    entities, triples, graph, by_source = build_graph(conn)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. entities.json
    (DATA_DIR / "entities.json").write_text(
        json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2. triples.jsonl
    with open(DATA_DIR / "triples.jsonl", "w", encoding="utf-8") as fh:
        for t in triples:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    # 3. graph.json
    (DATA_DIR / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4. wiki/index.json — машинно-читаемый индекс
    index_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_docs": len(entities),
        "total_endpoints": graph["resource_count"],
        "sources": {
            src: {
                "doc_count": len(eids),
                "entities": eids,
            }
            for src, eids in sorted(by_source.items())
        },
        "entities": [
            {"id": e["id"], "title": e["title"], "type": e["type"], "source": e["source"]}
            for e in entities
        ],
    }
    (WIKI_DIR / "index.json").write_text(
        json.dumps(index_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 5. wiki/index.md — главный Markdown-индекс
    lines = [
        "# Wiki Index",
        "",
        f"> Generated by `scripts/wiki_index.py` on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
        f"Do not edit by hand — regenerate instead.",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Documents | {len(entities)} |",
        f"| API resources | {graph['resource_count']} |",
        f"| Knowledge triples | {len(triples)} |",
        f"| Sources | {len(by_source)} |",
        "",
        "## Sources",
        "",
    ]

    source_titles = {e["source"]: e["title"] for e in entities}
    for src, eids in sorted(by_source.items()):
        lines.append(f"### {src} ({len(eids)} docs)")
        lines.append("")
        lines.append(f"**Source:** {source_titles.get(src, src)}")
        lines.append("")
        for e in entities:
            if e["source"] == src:
                rel = e["url"].replace("local://", "")
                lines.append(
                    f"- [{e['title']}]({rel}) — `{e['type']}`, "
                    f"{e['endpoint_count']} endpoints"
                    + (f", version {e['version']}" if e["version"] else "")
                )
        lines.append("")

    lines += [
        "## Knowledge Graph",
        "",
        "Machine-readable artifacts:",
        "",
        "- [`_data/entities.json`](_data/entities.json) — entities with types and properties",
        "- [`_data/triples.jsonl`](_data/triples.jsonl) — subject-predicate-object triples",
        "- [`_data/graph.json`](_data/graph.json) — graph statistics and type counts",
        "",
        "### Ontology",
        "",
        "| Entity type | Meaning |",
        "|-------------|---------|",
    ]
    for etype, meaning in ENTITY_TYPES.items():
        lines.append(f"| `{etype}` | {meaning} |")

    lines += [
        "",
        "### Predicates",
        "",
        "| Predicate | Direction |",
        "|-----------|-----------|",
    ]
    for pred, count in sorted(graph["predicates"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{pred}` | {count} triples |")

    lines += [
        "",
        "## Notes",
        "",
        "Session notes live in [`notes/`](notes/).",
        "",
    ]

    (WIKI_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")

    # 6. Per-source индексы
    for src, eids in by_source.items():
        src_dir = WIKI_DIR / src
        src_dir.mkdir(parents=True, exist_ok=True)
        src_lines = [
            f"# {src}",
            "",
            f"{len(eids)} documents. "
            f"Generated by `scripts/wiki_index.py`.",
            "",
        ]
        for e in entities:
            if e["source"] == src:
                rel = e["url"].replace("local://", "")
                src_lines.append(f"- [{e['title']}]({rel}) — {e['endpoint_count']} endpoints")
        (src_dir / "index.md").write_text("\n".join(src_lines), encoding="utf-8")

    return graph, len(entities), len(triples)


def show_stats(conn):
    entities, triples, graph, by_source = build_graph(conn)
    print("\n=== WIKI GRAPH STATS ===")
    print(f"Entities:      {graph['entity_count']}")
    print(f"Resources:     {graph['resource_count']}")
    print(f"Triples:       {graph['triple_count']}")
    print(f"Sources:       {len(by_source)}")
    print("\nTypes:")
    for t, c in sorted(graph["types"].items(), key=lambda x: -x[1]):
        print(f"  {t:28s} {c}")
    print("\nPredicates:")
    for p, c in sorted(graph["predicates"].items(), key=lambda x: -x[1]):
        print(f"  {p:28s} {c}")
    print("\nSources:")
    for s, c in sorted(graph["sources"].items()):
        print(f"  {s:28s} {c}")


def verify(conn):
    """Проверяет, что индексы актуальны относительно БД."""
    idx = WIKI_DIR / "index.json"
    if not idx.exists():
        print("[FAIL] wiki/index.json не найден — запустите без --verify")
        return 1
    data = json.loads(idx.read_text(encoding="utf-8"))
    entities, triples, graph, by_source = build_graph(conn)

    problems = []
    if data.get("total_docs") != len(entities):
        problems.append(
            f"total_docs: index={data.get('total_docs')} vs db={len(entities)}"
        )
    for src, eids in by_source.items():
        idx_src = data.get("sources", {}).get(src, {}).get("doc_count")
        if idx_src != len(eids):
            problems.append(f"source '{src}': index={idx_src} vs db={len(eids)}")

    if problems:
        print("[FAIL] Индекс устарел:")
        for p in problems:
            print(f"  - {p}")
        print("  Обновить: python scripts/wiki_index.py")
        return 1

    print(f"[OK] Индекс актуален: {len(entities)} docs, {len(by_source)} sources")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    conn = connect()
    try:
        if args.verify:
            sys.exit(verify(conn))
        if args.stats:
            show_stats(conn)
            return
        result = write_indexes(conn)
        if result is None:
            print("[SKIP] Индексы не записаны (ALLOW_MUTATIONS != 1)")
            return
        graph, n_ent, n_tri = result
        print("\n=== WIKI INDEX GENERATED ===")
        print(f"Entities:        {n_ent}")
        print(f"Triples:         {n_tri}")
        print(f"API resources:   {graph['resource_count']}")
        print("\nCreated:")
        for rel in [
            "wiki/index.md",
            "wiki/index.json",
            "wiki/_data/entities.json",
            "wiki/_data/triples.jsonl",
            "wiki/_data/graph.json",
        ]:
            p = PROJECT_ROOT / rel
            print(f"  {rel} ({p.stat().st_size if p.exists() else 0} bytes)")
        print(f"  wiki/<source>/index.md ({len(graph['sources'])} files)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
