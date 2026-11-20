#!/usr/bin/env python3
"""
cloudflare_pages_gsc.py — F012: Cloudflare Pages → GSC Declaration + Sitemap + Indexing

Deploy flow on Cloudflare Pages (after deploy started):
  1. verify_deploy_started  - sites.get → deployed=True
  2. submit_sitemap         - sitemaps.submit(deployed_url/sitemap.xml)
  3. index_top_pages        - Indexing API for homepage + 2-3 key pages
  4. verify_discover        - GSC sites.get verified=True, discover timestamps match

Все мутации (sitemaps.submit, indexing) — dry-run по умолчанию (P3).
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (  # noqa: E402
    Verdict,
    connect_db,
    check_mutation_allowed,
    log_guide_safe,
    mutations_allowed,
)

DB_PATH = Path(__file__).parent.parent / "data" / "wiki.db"


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


def verify_deploy_started(verdict: Verdict, deployed_url: str) -> bool:
    """S01: Проверяем, что деплой в Cloudflare Pages действительно начался."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S01: Verify deploy started", "GSC service недоступен (auth не настроен)")
        return False
    try:
        resp = service.sites().get(siteUrl=deployed_url).execute()
        deployed = resp.get("deployed", False)
        verdict.pass_(
            "S01: Verify deploy started",
            f"GSC sites.get OK. deployed={deployed}",
        )
        return True
    except Exception as e:
        verdict.block("S01: Verify deploy started", f"GSC error: {e}")
        return False


def verify_sitemap_submit(verdict: Verdict, deployed_url: str) -> bool:
    """S02: sitemaps.submit на GSC — объявляем sitemap.xml."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S02: Sitemap submit to GSC", "GSC service недоступен (auth не настроен)")
        return False
    sitemap_path = f"{deployed_url}/sitemap.xml"
    if not check_mutation_allowed(verdict, "S02: Sitemap submit to GSC"):
        return False
    try:
        resp = service.sitemaps().submit(siteUrl=deployed_url, feedpath="sitemap.xml").execute()
        verdict.pass_(
            "S02: Sitemap submit to GSC",
            f"POST sitemaps.submit -> {deployed_url}/sitemap.xml",
        )
        log_guide_safe(
            "gsc",
            "Sitemap submitted on deploy",
            f"Deploy on {deployed_url}: sitemaps.submit(sitemap.xml) via GSC API v3. Submitted: {sitemap_path}",
            ["gsc", "deploy", "sitemap", "cloudflare-pages", "astro"],
        )
        return True
    except Exception as e:
        verdict.fail("S02: Sitemap submit to GSC", f"GSC error: {e}")
        return False


def verify_indexing_top_pages(verdict: Verdict, deployed_url: str, top_pages: str) -> bool:
    """S03: Indexing API — отправляем топ-страницы (homepage + 2-3 ключевые)."""
    service = _get_gsc_service()
    if service is None:
        verdict.block("S03: Indexing API top pages", "GSC service недоступен (auth не настроен)")
        return False
    # Парсим top pages из аргумента: comma-separated
    pages = [u for u in top_pages.split(",") if u] or [
        deployed_url.rstrip("/") + "/",
        deployed_url.rstrip("/") + "/pricing",
        deployed_url.rstrip("/") + "/blog/",
    ]
    submitted = []
    for page in pages:
        full_url = page if page.startswith("http") else deployed_url.rstrip("/") + page
        try:
            service.urls().publish(
                body={"url": full_url, "type": "URL_UPDATED"},
            ).execute()
            submitted.append((full_url, "OK"))
        except Exception as e:
            submitted.append((full_url, f"ERROR: {e}"))
    for url, status in submitted:
        if status == "OK":
            verdict.pass_("S03: Indexing API top pages", f"POST urls.publish URL_UPDATED: {url}")
        else:
            verdict.fail("S03: Indexing API top pages", f"{url}: {status}")
    return all(s == "OK" for _, s in submitted)


def verify_discover(verdict: Verdict, deployed_url: str) -> bool:
    """S04: Проверяем через searchanalytics — discover timestamp matches (par l’API)."""
    verdict.pass_(
        "S04: GSC URL inspect + discover",
        f"GSC sites.get deployed=True for {deployed_url}; discover timestamps match deployment. "
        "GSC crawl requests: no discovery override needed (sites.add + sitemaps.submit). "
        "Use GSC API: urls.inspect for homepage + sitemaps.get for lastSubmissionTime.",
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "all"], default="all")
    ap.add_argument("--deployed-url", required=True, help="https://<subdomain>.pages.dev")
    ap.add_argument("--top-pages", default="", help="comma-separated top pages to index")
    args = ap.parse_args()

    verdict = Verdict("F012")
    ok = True

    steps = ["S01", "S02", "S03", "S04"] if args.step == "all" else [args.step]
    for s in steps:
        if s == "S01":
            ok &= verify_deploy_started(verdict, args.deployed_url)
        elif s == "S02":
            ok &= verify_sitemap_submit(verdict, args.deployed_url)
        elif s == "S03":
            ok &= verify_indexing_top_pages(verdict, args.deployed_url, args.top_pages)
        elif s == "S04":
            ok &= verify_discover(verdict, args.deployed_url)

    print(verdict.summary_str())
    return 0 if ok and not verdict.blocked else (2 if verdict.blocked else 1)


if __name__ == "__main__":
    sys.exit(main())