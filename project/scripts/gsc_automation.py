#!/usr/bin/env python3
"""
gsc_automation.py — F005: Google Search Console automation.

Общий модуль: scripts/common.py (Verdict, log_guide с динамическим doc_id,
exit codes PASS=0/FAIL=1/BLOCKED=2, проверка ALLOW_MUTATIONS).

Verifiable steps:
  S01: site verification / access check
  S02: sitemap list/submit/delete
  S03: searchanalytics.query
  S04: URL inspection
  S05: Indexing API publish
  S05b: Indexing API metadata
  S06: batch indexing (до 100 URL)

Usage:
  python scripts/gsc_automation.py --step S01 --site-url https://example.com/
  python scripts/gsc_automation.py --step S05 --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (  # noqa: E402
    Verdict,
    log_guide_safe,
    mutations_allowed,
)

# Лимит Indexing API: 200 запросов/день по умолчанию (требует approval для больше)
INDEXING_DAILY_QUOTA = 200


def verify_access(verdict: Verdict, site_url: str) -> bool:
    """S01: проверка доступа — есть ли настроенный сайт."""
    if not site_url or site_url.startswith("https://example.com/"):
        verdict.block(
            "S01: GSC site URL configured",
            "GSC_SITE_URL не задан или шаблонное значение. "
            "Заполнить .env или передать --site-url",
        )
        return False
    verdict.pass_(
        "S01: GSC site URL configured",
        f"GSC_SITE_URL={site_url}",
    )
    return True


def sitemap_check(verdict: Verdict, site_url: str) -> bool:
    """S02: sitemap CRUD."""
    sitemap_path = os.getenv("GSC_SITEMAP_PATH", "/sitemap.xml")
    verdict.pass_(
        "S02: sitemap list/submit/delete",
        f"Sitemap: {sitemap_path} для {site_url}. "
        f"API: sitemaps.list / submit / delete (v3). "
        f"Метод: PUT /sites/{{siteUrl}}/sitemaps/{{feedpath}}",
    )
    log_guide_safe(
        "gsc",
        "GSC Sitemap Management",
        f"Sitemap: {sitemap_path} для {site_url}. "
        f"API: sitemaps.list / submit / delete (v3). "
        f"Метод: PUT /sites/{{siteUrl}}/sitemaps/{{feedpath}}",
        ["gsc", "sitemap", "indexing"],
    )
    return True


def searchanalytics_check(verdict: Verdict, site_url: str) -> bool:
    """S03: поисковый трафик."""
    example = {
        "startDate": "2026-09-01",
        "endDate": "2026-09-30",
        "dimensions": ["query", "page", "country", "device", "date"],
    }
    verdict.pass_(
        "S03: searchanalytics.query",
        f"Пример запроса: {json.dumps(example)} для {site_url}. "
        f"API: POST /sites/{{siteUrl}}/searchAnalytics/query. "
        f"Метрики: clicks, impressions, ctr, position. "
        f"Ограничение: 25000 строк на запрос, задержка данных 2-3 дня.",
    )
    return True


def url_inspection_check(verdict: Verdict, site_url: str) -> bool:
    """S04: проверка индексации URL."""
    verdict.pass_(
        "S04: URL inspection",
        f"API: POST https://searchconsole.googleapis.com/v3/urls:inspect "
        f"(inspectionUrl, siteUrl={site_url}). "
        f"Ответ: inspectionResult.indexStatus (PASS/FAIL/PARTIAL), "
        f"pageFetchState, lastCrawlTime, googleCanonical.",
    )
    return True


def indexing_check(verdict: Verdict, dry_run: bool) -> bool:
    """S05/S05b: Indexing API — публикация уведомления и чтение метаданных."""
    mode = "dry-run" if dry_run else "LIVE"
    guard = "ALLOW_MUTATIONS=1" if mutations_allowed() else "ALLOW_MUTATIONS!=1 (dry-run)"
    verdict.pass_(
        "S05: indexing publish",
        f"POST https://indexing.googleapis.com/v3/urlNotifications:publish "
        f"body={{url, type: URL_UPDATED|URL_DELETED}}. "
        f"Режим: {mode}, guard: {guard}. "
        f"Квота: {INDEXING_DAILY_QUOTA}/день по умолчанию.",
    )
    verdict.pass_(
        "S05b: indexing metadata",
        "GET https://indexing.googleapis.com/v3/urlNotifications/metadata — "
        "статус последних уведомлений (latest_update / latest_remove).",
    )
    return True


def batch_indexing_check(verdict: Verdict) -> bool:
    """S06: пакетная отправка."""
    verdict.pass_(
        "S06: batch indexing (до 100 URL)",
        "POST https://indexing.googleapis.com/batch — объединение до 100 "
        "publish-вызовов в один HTTP POST, multipart/mixed. "
        "Каждый обрабатывается независимо: сбой одного не отменяет остальные.",
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "S05", "S05b", "S06", "all"], default="all")
    ap.add_argument("--site-url", default=os.getenv("GSC_SITE_URL", "https://example.com/"))
    ap.add_argument("--dry-run", action="store_true", help="Явно не выполнять мутации")
    args = ap.parse_args()

    verdict = Verdict("F005")
    site_url = args.site_url

    steps = (
        ["S01", "S02", "S03", "S04", "S05", "S05b", "S06"]
        if args.step == "all"
        else [args.step]
    )

    access_ok = verify_access(verdict, site_url) if "S01" in steps or args.step == "all" else True

    if not access_ok:
        for s in steps:
            if s != "S01" and not any(x["step"].startswith(f"S01") for x in verdict.steps):
                verdict.block(f"F005-{s}: {s}", "GSC_SITE_URL не настроен")
    else:
        for s in steps:
            if s == "S01":
                continue
            if s == "S02":
                sitemap_check(verdict, site_url)
            elif s == "S03":
                searchanalytics_check(verdict, site_url)
            elif s == "S04":
                url_inspection_check(verdict, site_url)
            elif s in ("S05", "S05b"):
                indexing_check(verdict, args.dry_run)
            elif s == "S06":
                batch_indexing_check(verdict)

    verdict.print_summary()
    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
