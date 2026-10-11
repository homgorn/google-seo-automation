#!/usr/bin/env python3
"""
tests/test_sync_wiki.py — регрессионные тесты sync_wiki.

Каждый тест закрывает конкретный баг, который реально случился при разработке
(все воспроизведены и исправлены 2026-10-12):

  1. Рекурсия была условной  -> GTM отдавал 3 эндпоинта вместо 106
  2. UNIQUE(method, path)    -> терялось 150 эндпоинтов из-за path-шаблонов
  3. naive vs aware datetime -> TypeError в check_freshness
  4. cp1252 stdout            -> UnicodeEncodeError на кириллице

Запуск:  python -m pytest tests/ -v
"""

import sys
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sync_wiki import (  # noqa: E402
    extract_methods,
    parse_frontmatter,
    age_days,
    DISCOVERY_SOURCES,
    STALE_DAYS,
)

PROJECT_ROOT = Path(__file__).parent.parent


# ── Фикстуры: локальный мини-discovery с вложенностью ───────────
@pytest.fixture
def nested_discovery():
    """Структура как у Tag Manager v2: resources внутри resources."""
    return {
        "baseUrl": "https://tagmanager.googleapis.com/",
        "revision": "20261007",
        "resources": {
            "accounts": {
                "methods": {
                    "get": {
                        "id": "tagmanager.accounts.get",
                        "path": "tagmanager/v2/{+path}",
                        "httpMethod": "GET",
                        "description": "Gets a GTM Account.",
                        "scopes": ["https://www.googleapis.com/auth/tagmanager.manage.accounts"],
                    }
                },
                "resources": {
                    "containers": {
                        "methods": {
                            "create": {
                                "id": "tagmanager.accounts.containers.create",
                                "path": "tagmanager/v2/{+parent}",
                                "httpMethod": "POST",
                                "description": "Creates a Container.",
                            }
                        },
                        "resources": {
                            "workspaces": {
                                "methods": {
                                    "get": {
                                        "id": "tagmanager.accounts.containers.workspaces.get",
                                        "path": "tagmanager/v2/{+path}",
                                        "httpMethod": "GET",
                                        "description": "Gets a Workspace.",
                                    }
                                },
                                "resources": {
                                    "tags": {
                                        "methods": {
                                            "create": {
                                                "id": "tagmanager.accounts.containers.workspaces.tags.create",
                                                "path": "tagmanager/v2/{+parent}/tags",
                                                "httpMethod": "POST",
                                                "description": "Creates a GTM Tag.",
                                            }
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            }
        },
    }


@pytest.fixture
def shared_path_discovery():
    """Структура как у GA4 Admin: десятки методов делят шаблон v1alpha/{+name}."""
    resources = {"properties": {"methods": {}}}
    for rname in ("dataStreams", "keyEvents", "customDimensions", "audiences"):
        resources["properties"]["resources"] = resources["properties"].get("resources", {})
        resources["properties"]["resources"][rname] = {
            "methods": {
                "get": {
                    "id": f"analyticsadmin.properties.{rname}.get",
                    "path": "v1alpha/{+name}",
                    "httpMethod": "GET",
                    "description": f"Get {rname}.",
                },
                "list": {
                    "id": f"analyticsadmin.properties.{rname}.list",
                    "path": "v1alpha/{+name}",
                    "httpMethod": "GET",
                    "description": f"List {rname}.",
                },
            }
        }
    return {"baseUrl": "https://analyticsadmin.googleapis.com/", "resources": resources}


# ── Тест 1: рекурсия (регрессия «3 вместо 106») ────────────────
def test_extract_finds_deeply_nested_methods(nested_discovery):
    """Вложенные методы на глубине 4 обязаны находиться."""
    methods = extract_methods(nested_discovery)
    names = {m["method_name"] for m in methods}
    assert "tagmanager.accounts.get" in names
    assert "tagmanager.accounts.containers.create" in names
    assert "tagmanager.accounts.containers.workspaces.get" in names
    # Ключевая проверка регрессии:
    assert "tagmanager.accounts.containers.workspaces.tags.create" in names


def test_extract_returns_full_resource_path(nested_discovery):
    """resource должен быть полным путём, а не последним сегментом."""
    by_id = {m["method_name"]: m for m in extract_methods(nested_discovery)}
    assert by_id["tagmanager.accounts.containers.workspaces.tags.create"]["resource"] == (
        "accounts.containers.workspaces.tags"
    )
    assert by_id["tagmanager.accounts.get"]["resource"] == "accounts"


def test_extract_carries_scopes_and_params(nested_discovery):
    m = extract_methods(nested_discovery)[0]
    assert m["http_method"] == "GET"
    assert m["scopes"] == ["https://www.googleapis.com/auth/tagmanager.manage.accounts"]


# ── Тест 2: path-шаблоны не схлопываются (регрессия «162») ────
def test_shared_path_keeps_all_methods(shared_path_discovery):
    """8 методов с ОДНИМ path-шаблоном должны остаться 8, а не схлопнуться в 2."""
    methods = extract_methods(shared_path_discovery)
    assert len(methods) == 8, f"ожидалось 8 методов, получено {len(methods)}"
    assert len({m["method_name"] for m in methods}) == 8


def test_shared_path_differs_by_resource(shared_path_discovery):
    methods = extract_methods(shared_path_discovery)
    paths = {m["path"] for m in methods}
    resources = {m["resource"] for m in methods}
    assert paths == {"v1alpha/{+name}"}          # путь один
    assert len(resources) == 4                    # а ресурсов четыре
    ids = {(m["resource"], m["method_name"]) for m in methods}
    assert len(ids) == 8                          # пара (resource, id) уникальна


# ── Тест 3: datetime (регрессия TypeError) ─────────────────────
def test_age_days_accepts_aware_iso():
    ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    assert age_days(ts) == 3


def test_age_days_accepts_naive_sqlite_string():
    """SQLite CURRENT_TIMESTAMP отдаёт 'YYYY-MM-DD HH:MM:SS' без таймзоны."""
    naive = (
        (datetime.now(timezone.utc) - timedelta(days=5))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    assert age_days(naive) == 5


def test_age_days_bad_input_is_not_fatal():
    assert age_days("не дата") == 999
    assert age_days(None) == 999


# ── Тест 4: frontmatter ─────────────────────────────────────────
def test_parse_frontmatter_reads_keys():
    md = '---\ntitle: "Тест"\nsource: gtm\nversion: v2\n---\n\n# Тело\n'
    fm, body = parse_frontmatter(md)
    assert fm["title"] == "Тест"
    assert fm["source"] == "gtm"
    assert fm["version"] == "v2"
    assert "Тело" in body and "---" not in body


def test_parse_frontmatter_without_marker_returns_whole_text():
    md = "# Просто текст\n"
    fm, body = parse_frontmatter(md)
    assert fm == {}
    assert body == md


# ── Тест 5: конфигурация источников ─────────────────────────────
def test_discovery_urls_are_nonempty():
    for key, cfg in DISCOVERY_SOURCES.items():
        assert cfg["url"].startswith("https://"), key
        assert cfg["name"], key
        assert cfg["version"], key


def test_known_empty_merchant_is_flagged():
    """Merchant v1: discovery есть, но resources пуст — это должно быть
    задокументировано в конфиге, а не молчаливо давать 0."""
    assert DISCOVERY_SOURCES["merchant"].get("known_empty") is True


def test_gsc_points_at_searchconsole_not_webmasters():
    """Регрессия: webmasters/v3 отдаёт HTTP 404. Живой документ —
    searchconsole:v1."""
    assert "searchconsole" in DISCOVERY_SOURCES["gsc"]["url"]


# ── Тест 6: схема БД (если БД уже создана) ────────────────────
@pytest.mark.skipif(
    not (PROJECT_ROOT / "data" / "wiki.db").exists(),
    reason="БД не создана: python scripts/init_db.py",
)
def test_db_has_new_schema():
    conn = sqlite3.connect(PROJECT_ROOT / "data" / "wiki.db")
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(api_endpoints)")}
        assert "resource" in cols, "нет колонки resource — нужна миграция v2"
        assert "method_name" in cols
    finally:
        conn.close()


@pytest.mark.skipif(
    not (PROJECT_ROOT / "data" / "wiki.db").exists(),
    reason="БД не создана",
)
def test_db_has_no_legacy_rows():
    """После clean-legacy строк с resource='' быть не должно."""
    conn = sqlite3.connect(PROJECT_ROOT / "data" / "wiki.db")
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM api_endpoints WHERE resource=''"
        ).fetchone()[0]
        assert n == 0, f"осталось {n} строк легаси — запусти wiki_query.py clean-legacy --yes"
    finally:
        conn.close()


def test_stale_threshold_is_two_weeks():
    assert STALE_DAYS == 14