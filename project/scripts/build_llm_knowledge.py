#!/usr/bin/env python3
"""
build_llm_knowledge.py — F001 LLM-субсистема: семантическая БД.

Создаёт `data/llm_knowledge.db` (SQLite) с:
  - entities: сущности (features, scripts, docs, research, thresholds)
  - ontology: (субъект, предикат, объект) — как связаны сущности
  - triples: триплеты (субъект, предикат, объект) — знания
  - edges: BFS-связи (src, dst, weight, type)
  - feature_metrics: F015 метрики + пороги из feature_list.json + docs

Источники: feature_list.json, scripts/, wiki/llm/, docs/cloudflare-pages-gsc.md,
wiki/llm/research/*.md (фетчи с web.dev).

Запуск: python scripts/build_llm_knowledge.py   # создаёт/обновляет БД
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "llm_knowledge.db"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from common import Verdict  # noqa: E402,F401


def read_feature_metrics():
    """F015 метрики из feature_list.json + пороги из документации."""
    feats = json.loads((PROJECT_ROOT / "feature_list.json").read_text(encoding="utf-8"))
    metrics = {}
    for f in feats:
        if f["id"] in ("F015", "F013"):
            metrics[f["id"]] = {
                "category": f["category"],
                "description": f["description"],
                "steps": len(f["steps"]),
                "status": f.get("status", "in_progress"),
                "passes": f.get("passes", False),
                "depends_on": f.get("depends_on", []),
                "script": f.get("script"),
            }
    return metrics


ENTITIES = [
    # (id, type, name, properties json)
    ("feature:F001", "feature", "F001 — GA4 Automation", "{}"),
    ("feature:F002", "feature", "F002 — Wiki Database", "{}"),
    ("feature:F003", "feature", "F003 — GA4 Automation (Python)", "{}"),
    ("feature:F004", "feature", "F004 — GTM Automation", "{}"),
    ("feature:F005", "feature", "F005 — GSC Automation", "{}"),
    ("feature:F006", "feature", "F006 — Google Ads Automation", "{}"),
    ("feature:F007", "feature", "F007 — Bing Ads Automation", "{}"),
    ("feature:F008", "feature", "F008 — AEO Automation", "{}"),
    ("feature:F009", "feature", "F009 — OS Automation", "{}"),
    ("feature:F010", "feature", "F010 — Testing Framework", "{}"),
    ("feature:F011", "feature", "F011 — Recovery Runbooks", "{}"),
    ("feature:F012", "feature", "F012 — Cloudflare Pages Deploy Automation", '{"priority": 1, "category": "integration", "steps": 14}'),
    ("feature:F013", "feature", "F013 — SEO Acceleration Pack", '{"priority": 1}'),
    ("feature:F015", "feature", "F015 — Chrome UX + CWV Monitoring", '{"priority": 2, "status": "in_progress"}'),
    ("threshold:LCP", "threshold", "LCP threshold (Core Web Vitals)", '{"unit": "ms", "good": 2500, "improve": 5000, "source": "web.dev/articles/inp (Stability Index)", "f015_pass": "< 2500"}'),
    ("threshold:CLS", "threshold", "CLS threshold (Core Web Vitals)", '{"unit": "none", "good": 0.1, "improve": 0.25, "source": "web.dev/articles/cls (Stability Index)", "f015_pass": "< 0.1"}'),
    ("threshold:FCP", "threshold", "FCP threshold", '{"unit": "ms", "good": 2000, "source": "web.dev/articles/fcp"}'),
    ("threshold:INP", "threshold", "INP threshold", '{"unit": "ms", "good": 200, "improve": 500, "source": "web.dev/articles/inp"}'),
    ("threshold:TTFB", "threshold", "TTFB threshold", '{"unit": "ms", "good": 1800, "source": "web.dev/articles/ttfb"}'),
    ("script:cloudflare_pages_gsc.py", "script", "F012 CLI: GSC declaration + Sitemap + Indexing API", '{"path": "scripts/cloudflare_pages_gsc.py", "status": "structural (auth-blocked)"}'),
    ("script:cloudflare_deploy_hook.py", "script", "F012-01: deploy hook verify", '{"path": "scripts/cloudflare_deploy_hook.py"}'),
    ("script:cloudflare_pages_automation.py", "script", "F012: worker VERDICT engine", '{"path": "scripts/cloudflare_pages_automation.py"}'),
    ("script:f015_chromex.py", "script", "F015: remote (PSI) + analyze (Lighthouse)", '{"path": "scripts/f015_chromex.py", "status": "in_progress"}'),
    ("script:append_new_features.py", "script", "F012–F015 feature_list appender", '{"path": "scripts/append_new_features.py"}'),
    ("script:enrich_feature_list.py", "script", "F002: enrichment stub", '{"path": "scripts/enrich_feature_list.py"}'),
    ("script:gsc_automation.py", "script", "F005 + F011: Google Search Console automation (GSC API)", '{"path": "scripts/gsc_automation.py", "functions": ["gsc_sites_list", "gsc_sitemap_list", "gsc_urls_inspect", "gsc_get_change_log_doc"]}'),
    ("script:verify_feature.py", "script", "F010: verification wrapper (read_csv_journal, write_csv_journal)", '{"path": "scripts/verify_feature.py", "journal_dir": "docs/gsc/gsc_status_reports"}'),
    ("docs:cloudflare-pages-gsc.md", "doc", "docs/cloudflare-pages-gsc.md — F012 deployment automation", '{}'),
    ("research:webdev-cwv-thresholds.md", "research", "research/webdev-cwv-thresholds.md — INP/CLS thresholds + definitions", '{}'),
]

ONTOLOGY = [
    # (subject, predicate, object)
    ("feature:F012", "is_priority", "1"),
    ("feature:F015", "is_priority", "2"),
    ("feature:F012", "category", "integration"),
    ("feature:F013", "category", "functional"),
    ("feature:F012", "is_dependent_of", "auth:GCP_service_account"),
    ("feature:F012", "requires", "auth:GCP_service_account"),
    ("feature:F013", "requires", "auth:GCP_service_account"),
    ("feature:F013", "prerequisite", "feature:F012"),
    ("feature:F015", "monitored_by", "script:f015_chromex.py"),
    ("feature:F015", "documents_thresholds", "threshold:LCP,threshold:CLS,threshold:FCP,threshold:INP,threshold:TTFB"),
    ("script:cloudflare_pages_gsc.py", "implements", "feature:F012"),
    ("script:cloudflare_deploy_hook.py", "implements", "feature:F012"),
    ("script:cloudflare_pages_automation.py", "implements", "feature:F012"),
    ("script:f015_chromex.py", "implements", "feature:F015"),
    ("script:append_new_features.py", "enables", "feature:F012,feature:F013,feature:F015"),
    ("feature:F015", "affected_by", "threshold:LCP"),
    ("feature:F015", "affected_by", "threshold:CLS"),
    ("feature:F012", "submission_tools", "sitemaps.submit (GSC API v3), Indexing API urls.publish URL_UPDATED"),
    ("feature:F012", "waits_on", "GSC index queue (async up to 16h)"),
    ("script:f015_chromex.py", "enforces", "threshold:LCP,threshold:CLS,threshold:FCP,threshold:INP,threshold:TTFB"),
    ("script:f015_chromex.py", "reads_metric", "Lighthouse audits: largest-contentful-paint, cumulative-layout-shift(+semantic), first-contentful-paint, interaction-to-next-paint, server-response-time"),
    ("script:verify_feature.py", "implements", "feature:F010"),
    ("script:gsc_automation.py", "implements", "feature:F005, feature:F011"),
    ("feature:F010", "maps_to", "verify_feature.read_csv_journal + write_csv_journal, gsc_automation.py script_map"),
    ("feature:F010", "tests", "tests/test_f010_verify.py + tests/test_gsc_automation.py (21+ tests)"),
    ("feature:F010", "docs", "docs/gsc/ (README.md, gsc_declaration.md, check-in/, gsc_status_reports/)"),
    ("feature:F011", "mapped_to", "gsc_automation.gsc_sites_list, gsc_sitemap_list, gsc_urls_inspect, gsc_get_change_log_doc"),
    ("feature:F011", "affected_by", "docs/gsc/* (journal, check-in, README)"),
    ("feature:F011", "exit_codes", "gsc_automation: 0 PASS, 2 BLOCKED (verify_access template default)"),
    ("docs:cloudflare-pages-gsc.md", "documents", "feature:F012, feature:F015"),
    ("research:webdev-cwv-thresholds.md", "informs", "threshold:LCP, threshold:CLS, threshold:INP, threshold:FCP"),
    ("feature:F012", "protects", "pre-stage domain budget (indexing quorum), GSC crawl budget"),
    ("feature:F013", "includes", "Robots.txt auto-generation, AI crawler allow/deny (GPTBot/PerplexityBot/ClaudeBot/LLaMABot/Applebot), structured data validation, sitemap interlinks, CWV telemetry, PageSpeed alerts"),
    ("feature:F015", "uses_tools", "PageSpeedInsights v5 (PSI), Lighthouse, CrUX metrics"),
]

TRIPLES = [
    # (subject, predicate, object) — знания, которые нельзя извлечь из ontology
    ("feature:F012", "submits_sitemap", "sitemaps.submit"),
    ("feature:F012", "submits_indexing", "Indexing API urls.publish URL_UPDATED"),
    ("feature:F012", "watches", "sitemap.xml, robots.txt, GSC URL inspection"),
    ("feature:F013", "adds", "robots.txt AI crawler allow/deny for 5 crawlers"),
    ("feature:F013", "validates", "OG + JSON-LD structured data (WebVital E-E-A-T extensions)"),
    ("feature:F015", "thresholds", "LCP < 2500, CLS < 0.1, FCP < 2000, INP < 200, TTFB < 1800"),
    ("feature:F015", "reports", "docs/reports/f015-*.md, f015-psi-*.md"),
    ("script:f015_chromex.py", "exit_codes", "0 = pass, 1 = fail, 2 = blocked"),
    ("script:f015_chromex.py", "retry", "3 attempts, backoff 1.5s on 429/5xx"),
    ("script:f015_chromex.py", "tools", "PSI v5 urllib, Lighthouse via npx"),
    ("feature:F015", "reads", "PSI lighthouseResult.audits: largest-contentful-paint, cumulative-layout-shift-semantic (fallback cumulative-layout-shift), server-response-time, interaction-to-next-paint"),
    ("feature:F015", "research_sources", "web.dev/articles/inp, web.dev/articles/cls (fetched 2026-11-19)"),
    ("docs:cloudflare-pages-gsc.md", "commands", "python scripts/cloudflare_pages_gsc.py --step S01/S02/S03/S04 --deployed-url https://test.pages.dev"),
    ("script:cloudflare_pages_gsc.py", "mutations", "sitemaps().submit, urls().publish — guarded by check_mutation_allowed (dry-run default, ALLOW_MUTATIONS=1 to enable)"),
    ("script:cloudflare_deploy_hook.py", "actions", "verify_deploy, url_inspection, gsc_discover, dump_to_db"),
]

EDGES = [
    # (src, dst, weight, type) — связи для BFS/семантического поиска
    ("feature:F012", "script:cloudflare_pages_gsc.py", 1.0, "implements"),
    ("feature:F012", "script:cloudflare_deploy_hook.py", 0.8, "deploy_hook"),
    ("feature:F015", "threshold:LCP", 0.9, "enforces"),
    ("feature:F015", "threshold:CLS", 0.9, "enforces"),
    ("feature:F013", "auth:GCP_service_account", 0.7, "requires"),
    ("feature:F012", "auth:GCP_service_account", 0.9, "requires"),
    ("docs:cloudflare-pages-gsc.md", "feature:F012", 1.0, "documents"),
    ("research:webdev-cwv-thresholds.md", "threshold:CLS", 0.8, "informs"),
    ("feature:F012", "feature:F013", 0.6, "same_domain_layer"),
    ("feature:F012", "feature:F015", 0.7, "same_domain_layer"),
]


def build_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE entities(
        id TEXT PRIMARY KEY, type TEXT, name TEXT, properties TEXT)""")
    c.execute("""CREATE TABLE ontology(
        subject TEXT, predicate TEXT, object TEXT,
        PRIMARY KEY (subject, predicate, object))""")
    c.execute("""CREATE TABLE triples(
        subject TEXT, predicate TEXT, object TEXT, source TEXT)""")
    c.execute("""CREATE TABLE edges(
        src TEXT, dst TEXT, weight REAL, type TEXT)""")
    c.execute("""CREATE TABLE feature_metrics(
        feature_id TEXT PRIMARY KEY, category TEXT, status TEXT,
        script TEXT, steps INTEGER, passes INTEGER,
        metric_f015 TEXT, metric_f013 TEXT,
        updated_at TEXT)""")

    now = datetime.now(timezone.utc).isoformat()
    c.executemany("INSERT INTO entities VALUES (?,?,?,?)", ENTITIES)
    c.executemany("INSERT INTO ontology VALUES (?,?,?)", ONTOLOGY)
    c.executemany(
        "INSERT INTO triples VALUES (?,?,?,?)",
        [(s, p, o, f"llm_wiki_v1 ({now})") for s, p, o in TRIPLES],
    )
    c.executemany(
        "INSERT INTO edges VALUES (?,?,?,?)",
        [(s, d, w, t) for s, d, w, t in EDGES],
    )
    for fid, m in read_feature_metrics().items():
        c.execute(
            "INSERT INTO feature_metrics(feature_id, category, status, script, steps, passes, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (fid, m["category"], m["status"], m["script"], m["steps"], 1 if m["passes"] else 0, now),
        )
    conn.commit()
    conn.close()
    print(f"Built {DB_PATH}")
    print(f"  entities={len(ENTITIES)} ontology={len(ONTOLOGY)} triples={len(TRIPLES)} edges={len(EDGES)}")
    return 0


if __name__ == "__main__":
    sys.exit(build_db())
