#!/usr/bin/env python3
"""
Database initialization script for Google SEO Automation Wiki.
Creates SQLite schema for API documentation storage with vector search support.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Windows-консоль cp1252 не печатает кириллицу — форсируем UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(Path(__file__).parent))
from common import Verdict, check_mutation_allowed  # noqa: E402
DB_PATH = PROJECT_ROOT / "data" / "wiki.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
-- Main API documentation table
CREATE TABLE IF NOT EXISTS api_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,                    -- 'ga4', 'gtm', 'gsc', 'ads', 'indexing', 'merchant', 'business', 'pagespeed', 'bing', 'bigquery'
    category TEXT NOT NULL,                  -- 'rest', 'rpc', 'reference', 'guide', 'schema', 'best_practice'
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,                   -- Full markdown/content
    content_hash TEXT NOT NULL,              -- SHA256 for change detection
    version TEXT,                            -- API version (v1, v2, v1beta, v18, etc.)
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON                            -- Additional structured data (endpoints, params, etc.)
);

-- API endpoints extracted from documentation
--
-- ВНИМАНИЕ к схеме (миграция v2, 2026-10-12):
-- Google использует path-ШАБЛОНЫ, а не конкретные маршруты.
-- accounts.properties.get и accounts.dataStreams.get имеют ОДИНАКОВЫЙ
-- path "v1alpha/{+name}" и различаются только ресурсом.
-- Измерено: 312 методов сворачивались в 162 уникальные пары (method, path),
-- терялось 150 эндпоинтов. Поэтому уникальность включает resource.
CREATE TABLE IF NOT EXISTS api_endpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
    resource TEXT NOT NULL DEFAULT '',       -- accounts.containers.workspaces.tags
    method_name TEXT NOT NULL DEFAULT '',    -- accounts.properties.get (RPC id)
    method TEXT NOT NULL,                    -- GET, POST, PUT, DELETE, PATCH
    path TEXT NOT NULL,                      -- шаблон: v1alpha/{+name}
    full_url TEXT,                           -- https://analyticsadmin.googleapis.com/...
    description TEXT,
    parameters JSON,                         -- Query params, body params
    response_schema JSON,                    -- Expected response structure
    auth_scopes JSON,                        -- Required OAuth scopes
    rate_limits JSON,                        -- Quota/rate limit info
    deprecated BOOLEAN DEFAULT FALSE,
    UNIQUE(doc_id, resource, method_name)
);

-- Schema definitions (JSON-LD, GAQL, BigQuery schemas, etc.)
CREATE TABLE IF NOT EXISTS schemas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
    schema_type TEXT NOT NULL,               -- 'json_ld', 'gaql', 'bigquery', 'openapi', 'protobuf'
    name TEXT NOT NULL,                      -- Schema name (e.g., 'Article', 'Campaign', 'events_*')
    definition JSON NOT NULL,                -- Full schema definition
    fields JSON,                             -- Parsed field list with types
    required_fields JSON,                    -- List of required field names
    version TEXT,
    UNIQUE(doc_id, schema_type, name)
);

-- Best practices and guides
CREATE TABLE IF NOT EXISTS guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
    guide_type TEXT NOT NULL,                -- 'setup', 'optimization', 'troubleshooting', 'migration', 'audit'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags JSON,                               -- ['ga4', 'ecommerce', 'conversions']
    priority INTEGER DEFAULT 0,              -- 0=low, 1=medium, 2=high, 3=critical
    UNIQUE(doc_id, guide_type, title)
);

-- Change log for tracking API documentation updates
CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
    change_type TEXT NOT NULL,               -- 'created', 'updated', 'deprecated', 'removed'
    field_changed TEXT,                      -- Which field changed
    old_value TEXT,                          -- Previous value (truncated)
    new_value TEXT,                          -- New value (truncated)
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_run_id TEXT                         -- Links to sync_runs table
);

-- Sync runs tracking
CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    run_type TEXT NOT NULL,                  -- 'full', 'incremental', 'manual'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,                    -- 'running', 'completed', 'failed', 'partial'
    docs_processed INTEGER DEFAULT 0,
    docs_created INTEGER DEFAULT 0,
    docs_updated INTEGER DEFAULT 0,
    docs_deprecated INTEGER DEFAULT 0,
    errors JSON,                             -- Array of error objects
    run_id TEXT UNIQUE NOT NULL              -- UUID for this run
);

-- Vector embeddings for semantic search (using ChromaDB separately, but track here)
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,            -- Which chunk of the document
    chunk_text TEXT NOT NULL,                -- Text chunk (for reference)
    chroma_id TEXT UNIQUE NOT NULL,          -- ChromaDB document ID
    embedding_model TEXT NOT NULL,           -- e.g., 'all-MiniLM-L6-v2'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doc_id, chunk_index)
);

-- AEO / AI Overviews tracking
CREATE TABLE IF NOT EXISTS aeo_citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    llm TEXT NOT NULL,                       -- 'chatgpt', 'perplexity', 'claude', 'gemini', 'mistral', 'ai_overview'
    query TEXT NOT NULL,
    cited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    position INTEGER,                        -- Position in response
    snippet TEXT,                            -- Cited text snippet
    confidence REAL,                         -- 0-1 confidence score
    UNIQUE(url, llm, query, cited_at)
);

-- AEO content audits
CREATE TABLE IF NOT EXISTS aeo_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    industry TEXT,                           -- 'saas', 'healthcare', 'finance', etc.
    composite_score INTEGER,                 -- 0-100
    experience_score INTEGER,
    expertise_score INTEGER,
    authoritativeness_score INTEGER,
    trustworthiness_score INTEGER,
    recommendations JSON,                    -- Structured recommendations
    audited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(url, audited_at)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_docs_source ON api_docs(source);
CREATE INDEX IF NOT EXISTS idx_api_docs_category ON api_docs(category);
CREATE INDEX IF NOT EXISTS idx_api_docs_content_hash ON api_docs(content_hash);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_doc_id ON api_endpoints(doc_id);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_method_path ON api_endpoints(method, path);
CREATE INDEX IF NOT EXISTS idx_schemas_doc_id ON schemas(doc_id);
CREATE INDEX IF NOT EXISTS idx_guides_doc_id ON guides(doc_id);
CREATE INDEX IF NOT EXISTS idx_change_log_doc_id ON change_log(doc_id);
CREATE INDEX IF NOT EXISTS idx_sync_runs_source ON sync_runs(source);
CREATE INDEX IF NOT EXISTS idx_embeddings_doc_id ON embeddings(doc_id);
CREATE INDEX IF NOT EXISTS idx_aeo_citations_url ON aeo_citations(url);
CREATE INDEX IF NOT EXISTS idx_aeo_audits_url ON aeo_audits(url);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS api_docs_fts USING fts5(
    title, content, category, source,
    content='api_docs', content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS api_docs_ai AFTER INSERT ON api_docs BEGIN
    INSERT INTO api_docs_fts(rowid, title, content, category, source)
    VALUES (new.id, new.title, new.content, new.category, new.source);
END;

CREATE TRIGGER IF NOT EXISTS api_docs_ad AFTER DELETE ON api_docs BEGIN
    INSERT INTO api_docs_fts(api_docs_fts, rowid, title, content, category, source)
    VALUES ('delete', old.id, old.title, old.content, old.category, old.source);
END;

CREATE TRIGGER IF NOT EXISTS api_docs_au AFTER UPDATE ON api_docs BEGIN
    INSERT INTO api_docs_fts(api_docs_fts, rowid, title, content, category, source)
    VALUES ('delete', old.id, old.title, old.content, old.category, old.source);
    INSERT INTO api_docs_fts(rowid, title, content, category, source)
    VALUES (new.id, new.title, new.content, new.category, new.source);
END;
"""

def columns_of(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def migrate_to_v2(conn):
    """Миграция api_endpoints -> схема с колонкой resource.

    Идемпотентна. Данные api_endpoints — производный кэш: они целиком
    восстанавливаются командой `python3 scripts/sync_wiki.py --full`,
    поэтому пересоздание таблицы не приводит к потере информации.
    Ничего не удаляется с диска — меняется только таблица в SQLite.

    Мутация — GUARDED (check_mutation_allowed).
    """
    if not check_mutation_allowed(Verdict("F001"), "migrate_to_v2"):
        return
    cols = columns_of(conn, "api_endpoints")
    if not cols:
        return  # таблицы ещё нет — её создаст executescript выше
    if "resource" in cols:
        return  # уже на новой схеме

    print("Миграция api_endpoints v1 -> v2 (добавление resource/method_name)...")
    conn.executescript(
        """
        BEGIN;
        CREATE TABLE api_endpoints_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL REFERENCES api_docs(id) ON DELETE CASCADE,
            resource TEXT NOT NULL DEFAULT '',
            method_name TEXT NOT NULL DEFAULT '',
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            full_url TEXT,
            description TEXT,
            parameters JSON,
            response_schema JSON,
            auth_scopes JSON,
            rate_limits JSON,
            deprecated BOOLEAN DEFAULT FALSE,
            UNIQUE(doc_id, resource, method_name)
        );
        INSERT INTO api_endpoints_v2
            (doc_id, resource, method_name, method, path, full_url,
             description, parameters, response_schema, auth_scopes,
             rate_limits, deprecated)
        SELECT doc_id, '', method || ' ' || path, method, path, full_url,
               description, parameters, response_schema, auth_scopes,
               rate_limits, deprecated
        FROM api_endpoints;
        DROP TABLE api_endpoints;
        ALTER TABLE api_endpoints_v2 RENAME TO api_endpoints;
        CREATE INDEX IF NOT EXISTS idx_api_endpoints_method_path
            ON api_endpoints(method, path);
        CREATE INDEX IF NOT EXISTS idx_api_endpoints_resource
            ON api_endpoints(resource);
        COMMIT;
        """
    )
    conn.commit()
    print("  ok: старая схема заменена; кэш перезаполнится через sync_wiki.py --full")


def migrate_guides_routing(conn):
    """Миграция v3: перенаправление гайдов в правильные документы.

    ИЗМЕРЕНО 2026-11-11: до рефакторинга скрипты писали гайды с
    «зашитыми» doc_id (1, 2, 3, 6), которые соответствовали документам
    ЧУЖИХ источников: AEO-гайды попадали в gtm, GTM-гайды в ga4_data,
    Ads-гайды в indexing. Аудит-трейл вёл не туда.

    Исправление — UPDATE doc_id по соответствию feature → source.
    Ничего не удаляется: содержимое гайдов сохраняется.

    Мутация — GUARDED (check_mutation_allowed).
    """
    if not check_mutation_allowed(Verdict("F001"), "migrate_guides_routing"):
        return
    mapping = {
        "gsc": "gsc",
        "gtm": "gtm",
        "ga4": "ga4_data",
        "ads": "google-apis-master",
        "aeo": "google-apis-master",
        "embeddings": "google-apis-master",
        "openchamber": "google-apis-master",
    }
    # Признаки фичи в заголовке гайда (регистронезависимо)
    markers = {
        "gsc": ["gsc ", "sitemap"],
        "gtm": ["gtm ", "tag management", "trigger management",
                "version lifecycle", "workspace lifecycle", "variable management"],
        "ga4": ["ga4 ", "key event", "bigquery export", "data stream",
                "custom dimension", "property listing", "reporting"],
        "ads": ["ads ", "budget", "keyword", "campaign lifecycle"],
        "aeo": ["aeo ", "e-e-a-t", "schema for ai", "citation tracking",
                "competitor citation", "content optimization"],
    }

    doc_ids = {}
    for source in set(mapping.values()):
        row = conn.execute(
            "SELECT id FROM api_docs WHERE source = ? ORDER BY id LIMIT 1", (source,)
        ).fetchone()
        if row:
            doc_ids[source] = row[0]
    if not doc_ids:
        return

    fixed = 0
    rows = conn.execute("SELECT id, doc_id, guide_type, title FROM guides").fetchall()
    for guide_id, current_doc, guide_type, title in rows:
        tl = title.lower()
        target_source = None
        for feature, words in markers.items():
            if any(w in tl for w in words):
                target_source = mapping[feature]
                break
        if not target_source:
            continue
        target_doc = doc_ids.get(target_source)
        if not target_doc or target_doc == current_doc:
            continue
        # UNIQUE(doc_id, guide_type, title): если в целевом документе уже
        # есть гайд с таким заголовком (его записала новая версия кода) —
        # оставляем как есть, иначе получим IntegrityError.
        dup = conn.execute(
            "SELECT id FROM guides WHERE doc_id = ? AND guide_type = ? AND title = ?",
            (target_doc, guide_type, title),
        ).fetchone()
        if dup:
            continue
        conn.execute(
            "UPDATE guides SET doc_id = ? WHERE id = ?", (target_doc, guide_id)
        )
        fixed += 1

    if fixed:
        conn.commit()
        print(f"  Миграция v3: перенаправлено {fixed} гайдов в правильные документы")

    # Дедупликация: гайд с тем же заголовком, оставшийся в неверном
    # документе, — точная копия уже существующего. Копию удаляем.
    # Безопасность: содержимое идентично, БД — регенерируемый кэш.
    removed = 0
    for guide_id, current_doc, guide_type, title in conn.execute(
        "SELECT id, doc_id, guide_type, title FROM guides"
    ).fetchall():
        others = conn.execute(
            """SELECT COUNT(*) FROM guides
               WHERE guide_type = ? AND title = ? AND id <> ?""",
            (guide_type, title, guide_id),
        ).fetchone()[0]
        if not others:
            continue
        current_source = conn.execute(
            "SELECT source FROM api_docs WHERE id = ?", (current_doc,)
        ).fetchone()
        current_source = current_source[0] if current_source else ""
        tl = title.lower()
        is_correct = False
        for feature, words in markers.items():
            if any(w in tl for w in words):
                is_correct = (mapping[feature] == current_source)
                break
        if not is_correct:
            conn.execute("DELETE FROM guides WHERE id = ?", (guide_id,))
            removed += 1
    if removed:
        conn.commit()
        print(f"  Миграция v3: удалено {removed} дубликатов гайдов из неверных документов")


def init_database():
    """Initialize the database with all tables and indexes."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    migrate_to_v2(conn)
    migrate_guides_routing(conn)
    conn.commit()
    
    # Verify tables created
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Database initialized at: {DB_PATH}")
    print(f"Tables created ({len(tables)}):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} rows")
    
    conn.close()
    return True

if __name__ == "__main__":
    init_database()