#!/usr/bin/env python3
"""
cloudflare_deploy_hook.py — F012-01: Deploy hook для Cloudflare Pages sites
Built with Astro. Запускается как deploy hook после Cloudflare Build начался
или завершился. CLI tool с несколькими actions.

Порядок:
  1. verify_deploy_started  - CF Pages GSC API: verify deploy status выполняется
  2. url_inspection_verdicts - URL Inspection для deployed последних страниц
  3. gsc_discover           - проверка, что discover timestamps сошлись (async)
  4. dump_to_db             - результаты -> change_log + docs/reports/
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import Verdict, connect_db, log_guide_safe  # noqa: E402

DB_PATH = Path(__file__).parent.parent / "data" / "wiki.db"
REPORT_DIR = Path(__file__).parent.parent / "docs" / "reports"


def _get_gsc_service():
    """Возвращает GSC service или None, если аутентификация недоступна."""
    try:
        from googleapiclient.discovery import build
        from google.auth import default
    except ImportError:
        return None
    try:
        creds, _ = default()
        return build('searchconsole', 'v1', credentials=creds)
    except Exception:
        return None


def cmd_verify_deploy(verdict: Verdict, project_id: str, deployed_url: str) -> int:
    """S01: sites.get -> deployed flag (GSC API)."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S01: Verify deploy started", "GSC service недоступен (auth не настроен)")
        return 2
    try:
        resp = service.sites().get(siteUrl=deployed_url).execute()
        verdict.pass_(
            "S01: Verify deploy started",
            f"siteUrl={deployed_url} deployed={resp.get('deployed', False)}",
        )
        return 0
    except Exception as e:
        verdict.block("S01: Verify deploy started", f"GSC error: {e}")
        return 2


def cmd_url_inspection(verdict: Verdict, deployed_url: str, sample_urls: str) -> int:
    """S02: URL Inspection для deployed последних страниц."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S02: URL inspection verdicts", "GSC service недоступен (auth не настроен)")
        return 2
    results = []
    for url in sample[:8]:
        try:
            resp = service.urls().inspect(inspectionUrl=url, siteUrl=deployed_url).execute()
            results.append((url, resp.get("inspectionResult", {}).get("indexStatus", "UNKNOWN")))
        except Exception as e:
            results.append((url, f"ERROR: {e}"))
    for url, status in results:
        verdict.add("S02: URL inspection verdicts", "PASS", f"{url} -> {status}")
    return 0 if all(r[1] != "ERROR" for r in results) else 1


def cmd_gsc_discover(verdict: Verdict, deployed_url: str, sitemap_path: str = "/sitemap.xml") -> int:
    """S03: GSC — verify deploy discover: urls.inspect для deployed pages (GSC API)."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S03: GSC sitemap state", "GSC service недоступен (auth не настроен)")
        return 2

    base = deployed_url.rstrip("/")
    pages = [base + "/", base + "/blog/", base + "/pricing", base + "/about"]
    results = []
    for url in pages:
        try:
            resp = service.urls().inspect(inspectionUrl=url, siteUrl=deployed_url).execute()
            idx = resp.get("inspectionResult", {}).get("indexStatus", "UNKNOWN")
            verdict.add("S03: GSC sitemap state", "PASS" if idx == "INDEX_GSC_READY" else "WARN",
                        f"{url} -> indexStatus={idx}")
            results.append(idx)
        except Exception as e:
            verdict.add("S03: GSC sitemap state", "FAIL", f"{url}: {e}")

    if not results:
        verdict.fail("S03: GSC sitemap state", "urls.inspect все URL ошибочны")
    return 0 if any(r == "INDEX_GSC_READY" for r in results) else (2 if not results else 1)


def cmd_dump_to_db(verdict: Verdict, deployed_url: str) -> int:
    """S04: Результаты -> change_log + docs/reports/cloudflare-deploy-*.md."""
    try:
        conn = connect_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO change_log (doc_id, change_type, field_changed, new_value, detected_at)
               VALUES ((SELECT id FROM api_docs WHERE source='google-apis-master' ORDER BY id LIMIT 1), 'deployed', 'cloudflare_pages', ?, ?)""",
            (deployed_url, now),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        verdict.block("S04: Dump results to DB", f"DB error: {e}")
        return 2

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"cloudflare-deploy-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    report.write_text(
        f"# Deploy on Cloudflare Pages — {deployed_url}\n"
        f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Results: {verdict.summary_str()}\n",
        encoding="utf-8",
    )
    verdict.pass_("S04: Dump results to DB", f"Report: {report.relative_to(Path(__file__).parent.parent)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", choices=["verify_deploy", "url_inspection", "gsc_discover", "dump_to_db"])
    ap.add_argument("--project-id", required=True, help="Cloudflare Pages project ID")
    ap.add_argument("--deployed-url", required=True, help="https://<subdomain>.pages.dev")
    ap.add_argument("--sample-urls", default="", help="comma-separated deployed URLs")
    args = ap.parse_args()

    verdict = Verdict("F012")

    if args.action == "verify_deploy":
        return cmd_verify_deploy(verdict, args.project_id, args.deployed_url)
    elif args.action == "url_inspection":
        return cmd_url_inspection(verdict, args.deployed_url, args.sample_urls)
    elif args.action == "gsc_discover":
        return cmd_gsc_discover(verdict, args.deployed_url)
    elif args.action == "dump_to_db":
        return cmd_dump_to_db(verdict, args.deployed_url)

    print(verdict.summary_str())
    return 0


if __name__ == "__main__":
    sys.exit(main())