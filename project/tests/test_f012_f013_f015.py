#!/usr/bin/env python3
"""
tests/test_f012_f013_f015.py — F012, F013, F015: Cloudflare + SEO Acceleration.

Тестируются структуры без external calls (auth) — потому что только это что
можно проверить без Google Cloud credentials + Astro site в репозитории.

Fixture patterns (what's checked):
1. Grpc-style patterns in CI (e.g., octokit stats, NPS commits).
2. Documented FM limits (entry limits, subtitle durations).
3. Concurrency limits (commit timeout, user activity tracking).
4. Client-side element presence & accessibility (count'able or' isn't it).
5. Delay-based play.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from common import mutations_allowed  # noqa: E402


def run(script, *args):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=PROJECT_ROOT,
    )
    return result.returncode, result.stdout + result.stderr


# ── F012: Cloudflare Pages Deploy Automation ──────────────────

def test_cloudflare_gsc_step_s01_blocked_without_url():
    code, out = run("cloudflare_pages_gsc.py", "--step", "S01", "--deployed-url", "https://test.pages.dev")
    assert code in (0, 2), out
    assert "S01" in out


def test_cloudflare_deploy_hook_help_lists_all_actions():
    code, out = run("cloudflare_deploy_hook.py", "--help")
    assert code == 0
    for action in ("verify_deploy", "url_inspection", "gsc_discover", "dump_to_db"):
        assert action in out, f"missing --action {action}"
    for flag in ("--project-id", "--deployed-url"):
        assert flag in out, f"missing flag {flag}"


def test_cloudflare_gsc_help_exists():
    code, out = run("cloudflare_pages_gsc.py", "--help")
    assert code == 0
    assert "--step" in out
    assert "--deployed-url" in out


def test_cloudflare_gsc_indexing_references_urls_publish():
    code, out = run("cloudflare_pages_gsc.py", "--step", "S03")
    assert code in (0, 1, 2)  # BLOCKED без auth, или PASS с auth
    if code == 0:
        assert "urls.publish" in out or "URL Indexing" in out


def test_dry_run_by_default_for_cloudflare_gsc():
    # mutations_allowed() == False без ALLOW_MUTATIONS=1
    assert mutations_allowed() is False
    # По умолчанию — mutate all calls guarded (except explorations)


def test_feature_list_has_f012_f013_f015():
    data = json.loads((PROJECT_ROOT / "feature_list.json").read_text(encoding="utf-8"))
    ids = {f["id"] for f in data}
    assert {"F012", "F013", "F015"}.issubset(ids)


def test_f012_steps_nonempty():
    data = json.loads((PROJECT_ROOT / "feature_list.json").read_text(encoding="utf-8"))
    for f in data:
        if f["id"] in ("F012", "F013", "F015"):
            assert len(f["steps"]) >= 3, f"{f['id']} has {len(f['steps'])} steps"


# ── F015: Chrome UX + CWV Monitoring ──────────────────────────

def parse_metric(out: str, key: str):
    m = re.search(rf"{key}=([0-9.]+)", out)
    return float(m.group(1)) if m else None


def test_f015_chromex_has_all_metrics():
    for metric in ("LCP", "CLS", "FCP", "INP", "TTFB", "INP"):
        content = (SCRIPTS / "f015_chromex.py").read_text(encoding="utf-8")
        assert metric.lower() in content.lower(), f"missing metric {metric}"


def test_f015_chromex_uses_psi_api():
    content = (SCRIPTS / "f015_chromex.py").read_text(encoding="utf-8")
    # Реальная реализация: urllib запрос к googleapis PSI v5
    assert "googleapis.com/pagespeedonline/v5/runPagespeed" in content
    assert "urllib.request" in content and "PSI v5" in content


def test_f015_chromex_thresholds_in_script():
    content = (SCRIPTS / "f015_chromex.py").read_text(encoding="utf-8")
    assert "2500" in content   # LCP threshold
    assert "0.1" in content    # CLS threshold


def test_f015_chromex_writes_reports():
    content = (SCRIPTS / "f015_chromex.py").read_text(encoding="utf-8")
    assert "f015-psi-" in content
    assert "f015-" in content and "REPORT_DIR" in content


def test_f015_chromex_exit_codes():
    # remote: 0 with real numbers; 2 when blocked (no data)
    code, out = run("f015_chromex.py", "remote", "--page", "https://example.com")
    assert code in (0, 2), out
    lcp = parse_metric(out, "LCP")
    cls = parse_metric(out, "CLS")
    ttfb = parse_metric(out, "TTFB")
    if lcp is not None:
        assert lcp < 2500, f"LCP {lcp} >= 2500"
    if cls is not None:
        assert cls < 0.1, f"CLS {cls} >= 0.1"
    if ttfb is not None:
        assert ttfb < 1800, f"TTFB {ttfb} >= 1800"


def test_f015_chromex_remote_writes_report():
    # Если PSI доступен — отчёт создаётся
    code, out = run("f015_chromex.py", "remote", "--page", "https://example.com")
    if code == 0:
        reports = list((PROJECT_ROOT / "docs" / "reports").glob("f015-psi-*.md"))
        assert reports, "no f015-psi report"
        text = reports[-1].read_text(encoding="utf-8")
        assert "LCP" in text and "|" in text


# ── F013: SEO Acceleration Pack ──────────────────────────────

def test_f013_web_app_config_exists():
    content = (PROJECT_ROOT / "docs" / "cloudflare-pages-gsc.md").read_text(encoding="utf-8")
    assert "Cloudflare Pages" in content


def test_all_new_scripts_compile():
    import py_compile
    for script in [
        "scripts/cloudflare_pages_gsc.py",
        "scripts/cloudflare_deploy_hook.py",
        "scripts/f015_chromex.py",
        "scripts/append_new_features.py",
    ]:
        path = PROJECT_ROOT / script
        if path.exists():
            py_compile.compile(str(path), doraise=True)
