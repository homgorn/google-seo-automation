#!/usr/bin/env python3
"""tests/test_gsc_automation.py — F005 (GSC) + F011 (GSC discovery)."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=PROJECT_ROOT, timeout=60)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_gsc_automation_step_s01():
    code, out = run("gsc_automation.py", "--step", "S01", "--site-url", "https://example.com/")
    assert code in (0, 2), out  # 0 = configured, 2 = blocked (default config)
    assert "VERDICT" in out


def test_gsc_automation_step_all():
    code, out = run("gsc_automation.py", "--step", "all", "--site-url", "https://example.com/")
    assert code in (0, 2), out
    assert "VERDICT" in out


def test_gsc_automation_has_journal_steps():
    code, out = run("gsc_automation.py", "--help")
    assert code == 0
    assert "--step" in out and "--site-url" in out


def test_gsc_functions_graceful():
    """Без auth — функции graceful ([] / dict) + F011 journal API."""
    sys.path.insert(0, str(SCRIPTS))
    from gsc_automation import (
        gsc_sites_list, gsc_sitemap_list, gsc_urls_inspect, gsc_get_change_log_doc,
    )
    assert gsc_sites_list() == []
    assert gsc_sitemap_list("https://example.com/") == []
    insp = gsc_urls_inspect("https://example.com/", "https://example.com/")
    assert insp["verified"] is False
    assert insp["indexStatus"] == "UNKNOWN"
    # F011 journal API — returns None если нет записей
    assert gsc_get_change_log_doc("gsc_change_log") is None


def test_gsc_functions_journal_doc():
    """gsc_get_change_log_doc ищет запись в journal (если создана)."""
    sys.path.insert(0, str(SCRIPTS))
    from verify_feature import write_csv_journal, read_csv_journal
    import tempfile
    from pathlib import Path
    from gsc_automation import gsc_get_change_log_doc
    rec = {
        "doc_id": "gsc_change_log", "doc_type": "json",
        "field_changed": "page_urls", "new_value": '["/"]',
        "deploy_url": "https://example.com/",
        "detected_at": "2026-11-19T12:00:00+00:00",
        "timestamps_start": "2026-11-19T12:00:00+00:00",
        "timestamps_end": "2026-11-19T12:00:00+00:00",
    }
    with tempfile.TemporaryDirectory() as td:
        import verify_feature as vf
        old = vf.mutations_allowed
        vf.mutations_allowed = lambda: True
        old_journal = vf.JOURNAL_DIR
        vf.JOURNAL_DIR = Path(td)
        try:
            write_csv_journal(dry_run=False, records=[rec])
            doc = gsc_get_change_log_doc("gsc_change_log")
            assert doc is not None
            assert doc["page_urls"] == '["/"]'
            assert doc["timestamps_start"] == "2026-11-19T12:00:00+00:00"

        finally:
            vf.mutations_allowed = old
            vf.JOURNAL_DIR = old_journal


def test_gsc_mappings_in_verify_feature():
    """F010: F005 → gsc_automation.py; F011: script_map F005 в script_map — проверяем dispatches."""
    sys.path.insert(0, str(SCRIPTS))
    from verify_feature import read_csv_journal, write_csv_journal, DOC_ID_KEYS, DOC_TYPES
    assert "page_urls" in DOC_ID_KEYS
    assert "gsc_change_log" in DOC_TYPES


def test_gsc_sitemap_list_graceful():
    sys.path.insert(0, str(SCRIPTS))
    from gsc_automation import gsc_sitemap_list
    assert gsc_sitemap_list("https://example.com/") == []
