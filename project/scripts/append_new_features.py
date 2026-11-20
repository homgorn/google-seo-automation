#!/usr/bin/env python3
"""
append_new_features.py — добавляет F012–F015 в feature_list.json.
F012: Cloudflare Pages Deploy Automation (GSC + sitemap + URL indexing on deploy)
F013: SEO Acceleration Pack (robots, AI crawler, structured data, interlinks, CWV)
F015: Chrome UX + CWV monitoring
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FL = PROJECT_ROOT / "feature_list.json"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from enrich_feature_list import (
    ACCEPTANCE,
    DEPENDS_ON,
    BLOCKED_BY,
    TEST_REFS,
    SCRIPTS,
    SPECS,
)


def feature(fid, desc, cat, prio, steps):
    return {
        "id": fid,
        "category": cat,
        "description": desc,
        "steps": steps,
        "priority": prio,
        "passes": False,
    }


F12 = feature(
    "F012",
    "Cloudflare Pages Deploy Automation: sitemap submit, URL indexing, GSC verify, audit on deploy",
    "integration",
    1,
    [
        "At deploy: sitemaps.submit(deployed_url/sitemap.xml) to GSC",
        "At deploy: index_top_pages(top_pages[:5]) via Indexing API",
        "Verify: sitemaps.get — submission timestamp = deploy time (±1 min)",
        "Verify: urls.inspect — homepage + top pages all pass INDEX_GSC_READY",
        "Write deploy results to change_log + docs/reports/gsc-status-*.md",
        "Audit: GSC API calls count + quota used (log to change_log)",
        "Verify: sites.add for new domain (if not declared)",
    ],
)

F13 = feature(
    "F013",
    "SEO Acceleration Pack: Robots.txt, AI crawler allow/deny, structured data, interlinks, CWV telemetry",
    "functional",
    1,
    [
        "Parse Astro SSG: extract all internal links -> orphan pages",
        "Robots.txt: auto-generate (disallow /_site/, /admin/, /api/) + Sitemap header",
        "AI Crawler: verify GPTBot/PerplexityBot/ClaudeBot/LLaMABot/Applebot",
        "Structured Data: validate OG + JSON-LD for key pages",
        "Sitemap: interlinks (lastmod/changefreq) + hreflang merge",
        "CWV: Cloudflare KV telemetry + async optimization",
        "PageSpeed: LCP > 4000 / CLS > 0.1 alert",
        "Structured Data Audit: CLS > 0.15 adds E-E-A-T benefits blocks",
        "Sitemap Optimization: submit new pages on deploy (same as F012)",
        "Meta Tags: verify OG:title/description coverage",
        "Image Alt Text Audit: FTS index + manual review list",
        "Interlink Building: write report for Cloudflare Crawler Module",
    ],
)

F15 = feature(
    "F015",
    "Chrome UX + Core Web Vitals Monitoring on Cloudflare Pages Sites",
    "integration",
    2,
    [
        "Daily BigQuery query on chrome_ux — extract key metrics",
        "Parse stylesheets — check CLDFCS causes and layout shifts",
        "Pagespeed for key pages — report LCP/CLS/FID/INP",
        "Extract layout shifts from Astro output — critical pages",
        "Web.dev + Lighthouse impact analysis — real numbers for comparisons",
        "Critical action: top pages to optimize (main/LCP blocker)",
        "Short action: quickest wins (e.g., font preloading, defer tail scripts)",
        "CLS iterate: pages with CLS > 10% from search + fix via headless scan + add dimensions",
    ],
)

if __name__ == "__main__":
    data = json.loads(FL.read_text(encoding="utf-8"))
    new = [F12, F13, F15]
    for f in new:
        f["acceptance_criteria"] = ACCEPTANCE.get(f["id"], [])
        f["depends_on"] = DEPENDS_ON.get(f["id"], [])
        f["blocked_by"] = BLOCKED_BY.get(f["id"], [])
        f["test_refs"] = TEST_REFS.get(f["id"], [])
        f["script"] = SCRIPTS.get(f["id"])
        f["spec"] = SPECS.get(f["id"])
        f["estimate_steps"] = len(f["steps"])
        f["uncovered_steps"] = []
        f["status"] = "in_progress"
    data.extend(new)
    FL.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Added:", [f["id"] for f in new], "| Total:", len(data))
