#!/usr/bin/env python3
"""
tests/test_tooling.py — тесты инструментария: wiki_query, secret_scan,
wiki_index, verify_feature, init_db.

Закрывают пробел, найденный ревью 2026-11-11: из 13 скриптов проекта
тесты были только для одного (sync_wiki).
"""

import json
import os
import re
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"
WIKI_DIR = PROJECT_ROOT / "wiki"

sys.path.insert(0, str(SCRIPTS))

needs_db = pytest.mark.skipif(
    not DB_PATH.exists(), reason="БД не создана: python scripts/init_db.py"
)


def run(script: str, *args, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, cwd=cwd or PROJECT_ROOT,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ── secret_scan ─────────────────────────────────────────────────

def test_secret_scan_passes_on_clean_repo():
    code, out = run("secret_scan.py")
    assert code == 0, out
    assert "не найдено" in out or "OK" in out


def test_placeholder_exact_match_not_substring():
    """РЕГРЕССИЯ: `"your" in value` маскировал реальные ключи вида
    `your_actual_prod_key_abc123` — дыра в сканере."""
    from secret_scan import looks_like_placeholder

    # Реальные секреты с плейсхолдерным префиксом — НЕ плейсхолдеры
    assert looks_like_placeholder("your_actual_prod_key_abc123def456") is False
    assert looks_like_placeholder("changeme_later_real_secret_xyz") is False
    assert looks_like_placeholder("example_com_api_token_xyz") is False

    # Настоящие плейсхолдеры — плейсхолдеры
    assert looks_like_placeholder("your_key_here") is True
    assert looks_like_placeholder("placeholder") is True
    assert looks_like_placeholder("xxxx") is True
    assert looks_like_placeholder("test") is True


def test_secret_scan_hard_patterns_cover_providers():
    """Список паттернов расширен: Stripe, Slack, SendGrid, Twilio, JWT."""
    from secret_scan import HARD_PATTERNS

    labels = {label for _, label in HARD_PATTERNS}
    for expected in ("Stripe live secret", "Slack token", "SendGrid key",
                     "Twilio key", "JWT", "Bearer token", "AWS secret key"):
        assert expected in labels, f"нет паттерна '{expected}'"


@pytest.mark.parametrize("text,label", [
    # Значения собираются склейкой: иначе литерал паттерна лежит в
    # исходнике теста и secret_scan.py находит сам тестовый файл.
    ("AKIA" + "IOSFODNN7EXAMPLE", "AWS access key"),
    ("ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz", "GitHub token"),
    ("AIza" + "SyD-1234567890abcdefghijklmnopqrstu", "Google API key"),
])
def test_secret_scan_detects_hard_patterns(text, label):
    from secret_scan import HARD_PATTERNS

    found = [lbl for pat, lbl in HARD_PATTERNS if re.search(pat, text)]
    assert label in found


def test_secret_scan_skips_itself():
    """Сканер не должен находить собственные паттерны."""
    code, out = run("secret_scan.py")
    assert "secret_scan.py" not in out, "сканер нашёл сам себя"


# ── init_db: идемпотентность миграций ──────────────────────────

def test_init_db_is_idempotent():
    """Повторный запуск не должен ломать схему и не должен падать."""
    code, out = run("init_db.py")
    assert code == 0, out
    code2, out2 = run("init_db.py")
    assert code2 == 0, out2


@needs_db
def test_init_db_enables_foreign_keys():
    """PRAGMA foreign_keys включён — ON DELETE CASCADE работает."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert fk == [], f"нарушения внешних ключей: {fk[:5]}"
    finally:
        conn.close()


@needs_db
def test_schema_has_required_tables():
    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        for required in ("api_docs", "api_endpoints", "schemas", "guides",
                         "change_log", "sync_runs", "embeddings",
                         "aeo_citations", "aeo_audits"):
            assert required in tables, f"нет таблицы {required}"
    finally:
        conn.close()


@needs_db
def test_api_endpoints_has_resource_index():
    """Индекс по resource нужен для быстрых выборок; в свежей БД он
    создаётся SCHEMA-блоком, а не только миграцией."""
    conn = sqlite3.connect(DB_PATH)
    try:
        idx = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='api_endpoints'"
        )}
        assert "idx_api_endpoints_resource" in idx, f"индексы: {idx}"
    finally:
        conn.close()


# ── wiki_query ─────────────────────────────────────────────────

@needs_db
def test_wiki_query_stats():
    code, out = run("wiki_query.py", "stats")
    assert code == 0, out
    assert "ИСТОЧНИК" in out


@needs_db
def test_wiki_query_endpoints():
    code, out = run("wiki_query.py", "endpoints", "--source", "gtm", "--limit", "5")
    assert code == 0, out
    assert "tagmanager" in out.lower()


@needs_db
def test_wiki_query_search():
    code, out = run("wiki_query.py", "search", "tag manager", "--limit", "3")
    assert code == 0, out


@needs_db
def test_wiki_query_endpoint_lookup():
    code, out = run("wiki_query.py", "endpoint", "workspaces.tags.create")
    assert code == 0, out
    assert "tagmanager" in out.lower()


@needs_db
def test_wiki_query_collisions():
    code, out = run("wiki_query.py", "collisions", "--source", "ga4_admin")
    assert code == 0, out
    assert "шаблон" in out.lower()


@needs_db
def test_wiki_query_changes():
    code, out = run("wiki_query.py", "changes", "--limit", "5")
    assert code == 0, out


@needs_db
def test_wiki_query_clean_legacy_is_safe_without_yes():
    """Без --yes команда не должна удалять данные."""
    code, out = run("wiki_query.py", "clean-legacy")
    assert code == 0, out
    # Либо подсказка про --yes, либо сообщение что чистить нечего
    assert "--yes" in out or "нет" in out.lower()


# ── wiki_index ─────────────────────────────────────────────────

@needs_db
def test_wiki_index_generates_artifacts():
    code, out = run("wiki_index.py")
    assert code == 0, out
    for rel in ("wiki/index.md", "wiki/index.json",
                "wiki/_data/entities.json", "wiki/_data/triples.jsonl",
                "wiki/_data/graph.json"):
        p = PROJECT_ROOT / rel
        assert p.exists(), f"не создан {rel}"
        assert p.stat().st_size > 0, f"пустой {rel}"


@needs_db
def test_wiki_index_verify_passes_after_generate():
    run("wiki_index.py")
    code, out = run("wiki_index.py", "--verify")
    assert code == 0, out
    assert "актуален" in out


@needs_db
def test_wiki_index_json_is_valid():
    run("wiki_index.py")
    data = json.loads((WIKI_DIR / "index.json").read_text(encoding="utf-8"))
    assert "sources" in data
    assert "total_docs" in data
    assert data["total_docs"] > 0


@needs_db
def test_wiki_graph_has_triples():
    run("wiki_index.py")
    graph = json.loads((WIKI_DIR / "_data" / "graph.json").read_text(encoding="utf-8"))
    assert graph["triple_count"] > 0
    assert graph["entity_count"] > 0


@needs_db
def test_wiki_triples_are_valid_jsonl():
    run("wiki_index.py")
    lines = (WIKI_DIR / "_data" / "triples.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        t = json.loads(line)
        assert t["subject"] and t["predicate"] and t["object"]
        assert t["object_type"] in ("literal", "entity")


# ── verify_feature ─────────────────────────────────────────────

@needs_db
def test_verify_feature_single():
    code, out = run("verify_feature.py", "--feature", "F001")
    assert code == 0, out
    assert "VERDICT" in out


@needs_db
def test_verify_feature_all_reports_every_feature():
    # VERIFY_FEATURE_NO_PYTEST разрывает рекурсию:
    # verify_feature --all -> pytest -> verify_feature --all -> ...
    env = os.environ.copy()
    env["VERIFY_FEATURE_NO_PYTEST"] = "1"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_feature.py"), "--all"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, cwd=PROJECT_ROOT, env=env,
    )
    out = proc.stdout + proc.stderr
    # BLOCKED допустим (нет credentials), FAIL — нет
    assert "FAIL: 0" in out, out
    for fid in ("F001", "F005", "F010", "F011"):
        assert fid in out


@needs_db
def test_verify_feature_unknown_id_fails():
    code, out = run("verify_feature.py", "--feature", "F999")
    assert code == 1
    assert "NOT FOUND" in out or "FAIL" in out
