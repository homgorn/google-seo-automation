#!/usr/bin/env python3
"""
tests/test_common.py — тесты общего модуля.

Закрывают дефекты, найденные code review 2026-11-11:
  - exit codes: PASS=0, FAIL=1, BLOCKED=2
  - ALLOW_MUTATIONS реально enforcement (было не enforced)
  - doc_id определяется динамически по source, а не «зашит»
  - валидаторы property_id / budget / GAQL
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from common import (  # noqa: E402
    EXIT_BLOCKED,
    EXIT_FAIL,
    EXIT_PASS,
    MIN_BUDGET_MICROS,
    SOURCE_BY_FEATURE,
    Verdict,
    check_mutation_allowed,
    log_guide,
    max_mutation_micros,
    mutations_allowed,
    resolve_doc_id,
    validate_budget_micros,
    validate_gaql,
    validate_property_id,
)

DB_PATH = Path(__file__).parent.parent / "data" / "wiki.db"
needs_db = pytest.mark.skipif(
    not DB_PATH.exists(), reason="БД не создана: python scripts/init_db.py"
)


# ── Verdict и коды возврата ────────────────────────────────────

def test_verdict_empty_is_unknown():
    v = Verdict("F001")
    assert v.overall == "UNKNOWN"
    assert v.exit_code() == EXIT_FAIL


def test_verdict_pass_gives_zero():
    v = Verdict("F001")
    v.pass_("step1", "ok")
    assert v.overall == "PASS"
    assert v.exit_code() == EXIT_PASS


def test_verdict_fail_gives_one():
    v = Verdict("F001")
    v.pass_("s1", "ok")
    v.fail("s2", "broken")
    assert v.overall == "FAIL"
    assert v.exit_code() == EXIT_FAIL


def test_verdict_blocked_gives_two():
    """РЕГРЕССИЯ: gsc_automation раньше возвращал 0 при полном BLOCKED —
    CI считал бы провалившийся прогон успешным."""
    v = Verdict("F005")
    v.block("s1", "нет credentials")
    assert v.overall == "BLOCKED"
    assert v.exit_code() == EXIT_BLOCKED


def test_verdict_fail_beats_blocked():
    v = Verdict("F005")
    v.block("s1", "blocked")
    v.fail("s2", "failed")
    assert v.overall == "FAIL"
    assert v.exit_code() == EXIT_FAIL


def test_verdict_counts():
    v = Verdict("F001")
    v.pass_("a", "x")
    v.pass_("b", "x")
    v.fail("c", "x")
    v.block("d", "x")
    assert (v.passed, v.failed, v.blocked) == (2, 1, 1)
    assert len(v.steps) == 4


def test_verdict_summary_contains_verdict_line():
    v = Verdict("F001")
    v.pass_("a", "evidence here")
    s = v.summary_str()
    assert s.startswith("VERDICT: PASS")
    assert "evidence here" in s


# ── ALLOW_MUTATIONS enforcement ─────────────────────────────────

def test_mutations_disabled_by_default(monkeypatch):
    """РЕГРЕССИЯ: ALLOW_MUTATIONS был объявлен в .env.example, но код его
    не читал — принцип dry-run не enforced."""
    monkeypatch.delenv("ALLOW_MUTATIONS", raising=False)
    assert mutations_allowed() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_mutations_allowed_values(monkeypatch, value):
    monkeypatch.setenv("ALLOW_MUTATIONS", value)
    assert mutations_allowed() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "maybe"])
def test_mutations_disabled_values(monkeypatch, value):
    monkeypatch.setenv("ALLOW_MUTATIONS", value)
    assert mutations_allowed() is False


def test_check_mutation_allowed_blocks_when_disabled(monkeypatch):
    monkeypatch.delenv("ALLOW_MUTATIONS", raising=False)
    v = Verdict("F006")
    assert check_mutation_allowed(v, "S07") is False
    assert v.overall == "BLOCKED"


def test_check_mutation_allowed_passes_when_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_MUTATIONS", "1")
    monkeypatch.delenv("ADS_MAX_MUTATION_MICROS", raising=False)
    v = Verdict("F006")
    assert check_mutation_allowed(v, "S07") is True
    assert v.overall == "PASS"


def test_check_mutation_allowed_respects_cap(monkeypatch):
    """ADS_MAX_MUTATION_MICROS тоже был не enforced."""
    monkeypatch.setenv("ALLOW_MUTATIONS", "1")
    monkeypatch.setenv("ADS_MAX_MUTATION_MICROS", "1000000")
    v = Verdict("F006")
    assert check_mutation_allowed(v, "S07", amount_micros=5_000_000) is False
    assert v.overall == "FAIL"


def test_max_mutation_micros_absent_is_zero(monkeypatch):
    monkeypatch.delenv("ADS_MAX_MUTATION_MICROS", raising=False)
    assert max_mutation_micros() == 0


def test_max_mutation_micros_invalid_is_zero(monkeypatch):
    monkeypatch.setenv("ADS_MAX_MUTATION_MICROS", "not-a-number")
    assert max_mutation_micros() == 0


# ── Валидаторы ─────────────────────────────────────────────────

@pytest.mark.parametrize("pid", [
    "properties/123456789",
    "properties/1",
    "properties/999999999999",
])
def test_validate_property_id_accepts_valid(pid):
    ok, msg = validate_property_id(pid)
    assert ok is True, msg


@pytest.mark.parametrize("pid", [
    "",
    "123456789",
    "properties/abc",
    "properties/",
    "analytics/properties/123",
])
def test_validate_property_id_rejects_invalid(pid):
    ok, msg = validate_property_id(pid)
    assert ok is False
    assert msg  # сообщение непустое


def test_validate_budget_rejects_dollars_in_micros_range():
    """1000 «микросов» = 0.001$ — невалидно."""
    ok, msg, warning = validate_budget_micros(1000)
    assert ok is False
    assert "микрос" in msg.lower() or "less" in msg.lower() or "$1" in msg


def test_validate_budget_accepts_50_dollars():
    ok, msg, warning = validate_budget_micros(50_000_000)
    assert ok is True
    assert warning is None
    assert "$50" in msg


def test_validate_budget_warns_below_ten_dollars():
    ok, msg, warning = validate_budget_micros(5_000_000)
    assert ok is True
    assert warning is not None


def test_validate_budget_minimum_boundary():
    ok, _, _ = validate_budget_micros(MIN_BUDGET_MICROS)
    assert ok is True
    ok, _, _ = validate_budget_micros(MIN_BUDGET_MICROS - 1)
    assert ok is False


def test_validate_gaql_accepts_valid():
    ok, msg = validate_gaql(
        "SELECT campaign.id, metrics.impressions FROM campaign "
        "WHERE segments.date DURING LAST_30_DAYS"
    )
    assert ok is True


def test_validate_gaql_requires_select():
    ok, msg = validate_gaql("FROM campaign")
    assert ok is False
    assert "SELECT" in msg


def test_validate_gaql_requires_from():
    ok, msg = validate_gaql("SELECT campaign.id")
    assert ok is False
    assert "FROM" in msg


def test_validate_gaql_rejects_forbidden_join():
    """ad_group_criterion + search_term_view — запрещено (constraints.md)."""
    ok, msg = validate_gaql(
        "SELECT ad_group_criterion.keyword.text, search_term_view.search_term "
        "FROM search_term_view"
    )
    assert ok is False
    assert "ad_group_criterion" in msg


# ── doc_id: динамическое разрешение ────────────────────────────

def test_source_by_feature_covers_all_features():
    """Каждая фича, пишущая гайды, должна быть в SOURCE_BY_FEATURE."""
    for feature in ("gsc", "gtm", "ga4", "ads", "aeo"):
        assert feature in SOURCE_BY_FEATURE
        assert SOURCE_BY_FEATURE[feature]


@needs_db
def test_resolve_doc_id_matches_actual_source():
    """РЕГРЕССИЯ: doc_id был «зашит» (1,2,3,6) и указывал на ЧУЖИЕ
    документы — AEO-гайды попадали в gtm, GTM-гайды в ga4_data."""
    conn = sqlite3.connect(DB_PATH)
    try:
        for feature, source in SOURCE_BY_FEATURE.items():
            doc_id = resolve_doc_id(conn, source)
            actual = conn.execute(
                "SELECT source FROM api_docs WHERE id = ?", (doc_id,)
            ).fetchone()[0]
            assert actual == source, (
                f"feature '{feature}': doc_id={doc_id} указывает на "
                f"source='{actual}', ожидался '{source}'"
            )
    finally:
        conn.close()


@needs_db
def test_log_guide_writes_to_correct_document():
    """Проверка сквозного пути: log_guide -> правильный doc_id."""
    conn = sqlite3.connect(DB_PATH)
    try:
        title = "TEST guide routing probe"
        log_guide(conn, "gsc", title, "content", '["test"]')
        row = conn.execute(
            """SELECT d.source FROM guides g JOIN api_docs d ON d.id = g.doc_id
               WHERE g.title = ?""", (title,)
        ).fetchone()
        assert row is not None
        assert row[0] == "gsc"
    finally:
        conn.close()
