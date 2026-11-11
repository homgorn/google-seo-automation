#!/usr/bin/env python3
"""
tests/test_automation_scripts.py — тесты всех automation-скриптов.

Каждый скрипт проверяется через реальный запуск в subprocess: так тестируется
фактический exit code, а не только внутренние функции.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2


def guide_content(title: str):
    """Читает полный текст гайда из БД (stdout обрезает evidence до 200 символов)."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT content FROM guides WHERE title = ? ORDER BY id DESC LIMIT 1",
            (title,),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def run(script: str, *args, env_extra=None):
    """Запускает скрипт и возвращает (returncode, stdout+stderr)."""
    env = os.environ.copy()
    # Изолируемся от пользовательского .env: суффиксы блокируются явно
    env.pop("GSC_SITE_URL", None)
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env.pop("GOOGLE_CLIENT_ID", None)
    env.pop("GOOGLE_CLIENT_SECRET", None)
    env.pop("GOOGLE_REFRESH_TOKEN", None)
    env["ALLOW_MUTATIONS"] = "0"
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=PROJECT_ROOT, env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ── GSC (F005) ──────────────────────────────────────────────────

def test_gsc_blocked_without_site_url():
    code, out = run("gsc_automation.py", "--step", "S01")
    assert code == EXIT_BLOCKED, out
    assert "BLOCKED" in out


def test_gsc_pass_with_site_url():
    code, out = run(
        "gsc_automation.py", "--step", "S02", "--site-url", "https://mysite.com/"
    )
    assert code == EXIT_PASS, out
    assert "PASS" in out


def test_gsc_all_steps_pass():
    code, out = run(
        "gsc_automation.py", "--step", "all", "--site-url", "https://mysite.com/"
    )
    assert code == EXIT_PASS, out
    # "FAIL=0" в строке счётчиков — это не провал
    assert "FAIL=0" in out
    assert "BLOCKED=0" in out


def test_gsc_indexing_step_mentions_quota():
    code, out = run("gsc_automation.py", "--step", "S05", "--site-url", "https://x.com/")
    assert code == EXIT_PASS, out
    assert "200" in out  # квота Indexing API


def test_gsc_weekly_digest_creates_report():
    """Дайджест создаётся файлом и содержит 7-дневние изменения."""
    code, out = run(
        "gsc_automation.py", "--step", "S07", "--site-url", "https://mysite.com/"
    )
    assert code == EXIT_PASS, out
    assert "Дайджест" in out or "digest" in out.lower()
    # файл отчёта создан
    reports = list((PROJECT_ROOT / "docs" / "reports").glob("gsc-digest-*.md"))
    assert reports, "файл дайджеста не создан"
    content = reports[0].read_text(encoding="utf-8")
    assert "Метрики GSC" in content


# ── Ads (F006) ──────────────────────────────────────────────────

def test_ads_budget_pass():
    code, out = run("ads_automation.py", "--step", "S01", "--amount-micros", "50000000")
    assert code == EXIT_PASS, out
    assert "$50" in out


def test_ads_budget_fail_on_dollars():
    """Передача долларов вместо микросов должна ловиться."""
    code, out = run("ads_automation.py", "--step", "S01", "--amount-micros", "50")
    assert code == EXIT_FAIL, out


def test_ads_campaign_paused():
    code, out = run("ads_automation.py", "--step", "S02")
    assert code == EXIT_PASS, out
    assert "PAUSED" in out


@pytest.mark.parametrize("channel", ["SEARCH", "DISPLAY", "PMax", "VIDEO"])
def test_ads_all_four_channels(channel):
    code, out = run("ads_automation.py", "--step", "S02", "--channel", channel)
    assert code == EXIT_PASS, out
    assert channel in out


def test_ads_activation_blocked_without_flag():
    code, out = run("ads_automation.py", "--step", "S07")
    assert code == EXIT_BLOCKED, out


def test_ads_activation_blocked_without_permission():
    """Даже с --activate мутация заблокирована без ALLOW_MUTATIONS=1."""
    code, out = run(
        "ads_automation.py", "--step", "S07", "--activate",
        env_extra={"ALLOW_MUTATIONS": "0"},
    )
    assert code == EXIT_BLOCKED, out
    assert "ALLOW_MUTATIONS" in out


def test_ads_activation_pass_with_permission():
    code, out = run(
        "ads_automation.py", "--step", "S07", "--activate",
        env_extra={"ALLOW_MUTATIONS": "1"},
    )
    assert code == EXIT_PASS, out


def test_ads_gaql_forbidden_join_detected():
    code, out = run(
        "ads_automation.py", "--step", "S03",
        "--gaql-snippet",
        "SELECT ad_group_criterion.text FROM search_term_view",
    )
    assert code == EXIT_FAIL, out


def test_ads_keyword_research_mentions_negative_candidates():
    code, out = run("ads_automation.py", "--step", "S04")
    assert code == EXIT_PASS, out
    content = guide_content("Keyword Research and Negative Keywords")
    assert content is not None, "гайд keyword research не записан"
    assert "search_term_view" in content.lower()
    assert "ad_group_criterion" in content.lower()


def test_ads_conversion_tracking_in_guides():
    code, out = run("ads_automation.py", "--step", "S06")
    assert code == EXIT_PASS, out
    content = guide_content("Google Ads Conversion Tracking Setup")
    assert content is not None, "гайд conversion tracking не записан"
    assert "counting_type" in content
    assert "include_in_conversions" in content


def test_ads_reporting_in_guides():
    code, out = run("ads_automation.py", "--step", "S08", "--channel", "PMax")
    assert code == EXIT_PASS, out
    content = guide_content("Google Ads Automated Reporting and Budget Optimization")
    assert content is not None, "гайд reporting не записан"
    assert "cost" in content
    assert "LIMITED_BUDGET" in content


# ── GTM (F004) ──────────────────────────────────────────────────

def test_gtm_workspace_blocked_without_ids():
    code, out = run("gtm_automation.py", "--step", "S01")
    assert code == EXIT_BLOCKED, out


def test_gtm_workspace_pass_with_ids():
    code, out = run(
        "gtm_automation.py", "--step", "S01",
        "--account-id", "123456", "--container-id", "789012",
    )
    assert code == EXIT_PASS, out
    assert "accounts/123456/containers/789012/workspaces/" in out


def test_gtm_publish_blocked_without_flag():
    code, out = run("gtm_automation.py", "--step", "S07")
    assert code == EXIT_BLOCKED, out


def test_gtm_audit_lists_six_checks():
    """Полный текст проверок читаем из БД: stdout обрезает evidence."""
    code, out = run("gtm_automation.py", "--step", "S06")
    assert code == EXIT_PASS, out
    content = guide_content("GTM Audit Checklist")
    assert content is not None, "гайд не записан в БД"
    for marker in ("duplicate", "broken triggers", "unused variables",
                   "consent", "orphan folders", "version drift"):
        assert marker in content.lower(), f"нет проверки '{marker}'"


def test_gtm_consent_mode_validates_status():
    code, out = run("gtm_automation.py", "--step", "S08")
    assert code == EXIT_PASS, out
    assert "consentStatus" in out
    assert "ad_storage" in out


def test_gtm_consent_mode_in_guides():
    run("gtm_automation.py", "--step", "S08")
    content = guide_content("GTM Consent Mode Configuration")
    assert content is not None, "гайд Consent Mode не записан"
    assert "not_set" in content
    assert "required" in content
    assert "not_required" in content


def test_gtm_tag_templates_in_guides():
    code, out = run("gtm_automation.py", "--step", "S09")
    assert code == EXIT_PASS, out
    content = guide_content("GTM Tag Template Library Management")
    assert content is not None, "гайд шаблонов не записан"
    assert "templates" in content.lower()


# ── AEO (F008) ──────────────────────────────────────────────────

def test_aeo_citations_blocked_without_query():
    code, out = run("aeo_automation.py", "--step", "S01", "--url", "https://x.com/p")
    assert code == EXIT_BLOCKED, out


def test_aeo_eeat_pass():
    code, out = run(
        "aeo_automation.py", "--step", "S02",
        "--url", "https://x.com/p", "--industry", "saas",
    )
    assert code == EXIT_PASS, out
    assert "70" in out  # порог для saas


def test_aeo_industry_thresholds_differ():
    _, saas = run("aeo_automation.py", "--step", "S02", "--url", "https://x.com/p", "--industry", "saas")
    _, health = run("aeo_automation.py", "--step", "S02", "--url", "https://x.com/p", "--industry", "healthcare")
    assert "min threshold=70" in saas
    assert "min threshold=85" in health


def test_aeo_schema_mentions_faqpage():
    code, out = run("aeo_automation.py", "--step", "S03", "--url", "https://x.com/p")
    assert code == EXIT_PASS, out
    assert "FAQPage" in out


def test_aeo_competitor_blocked_without_url():
    code, out = run("aeo_automation.py", "--step", "S04")
    assert code == EXIT_BLOCKED, out


def test_aeo_optimization_modes():
    for mode, marker in (("conservative", "10%"), ("balanced", "30%"), ("aggressive", "райт")):
        code, out = run(
            "aeo_automation.py", "--step", "S05",
            "--url", "https://x.com/p", "--mode", mode,
        )
        assert code == EXIT_PASS, out
        assert marker in out


# ── GA4 (F003) ──────────────────────────────────────────────────

def test_ga4_auth_blocked_without_credentials():
    code, out = run("ga4_automation.py", "--step", "S01", "--auth-method", "service_account")
    assert code == EXIT_BLOCKED, out


def test_ga4_oauth_blocked_without_credentials():
    code, out = run("ga4_automation.py", "--step", "S01", "--auth-method", "oauth")
    assert code == EXIT_BLOCKED, out
    assert "GOOGLE_CLIENT_ID" in out


def test_ga4_report_blocked_on_bad_property_format():
    """GA4 требует формат properties/<numeric_id> — '123456789' невалиден."""
    code, out = run("ga4_automation.py", "--step", "S03", "--property-id", "123456789")
    assert code == EXIT_BLOCKED, out
    assert "properties/123456789" in out


def test_ga4_report_pass_with_correct_format():
    code, out = run(
        "ga4_automation.py", "--step", "S03", "--property-id", "properties/123456789"
    )
    assert code == EXIT_PASS, out


def test_ga4_key_events_mentions_rename():
    """GA4 переименовала conversions -> key events в 2024."""
    code, out = run(
        "ga4_automation.py", "--step", "S04", "--property-id", "properties/1"
    )
    assert code == EXIT_PASS, out
    assert "key events" in out


def test_ga4_bigquery_mentions_latency():
    """Полный текст читаем из БД: stdout обрезает evidence."""
    code, out = run(
        "ga4_automation.py", "--step", "S07", "--property-id", "properties/1"
    )
    assert code == EXIT_PASS, out
    content = guide_content("GA4 BigQuery Export")
    assert content is not None, "гайд не записан в БД"
    assert "3" in content  # 3 дня задержки дневных таблиц
    assert "intraday" in content.lower()
