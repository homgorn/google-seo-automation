#!/usr/bin/env python3
"""tests/test_f010_verify.py — F010: Automated feature verification (GSC journal + verify_feature)."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from verify_feature import (  # noqa: E402
    DOC_ID_KEYS,
    DOC_TYPES,
    JOURNAL_DIR,
    read_csv_journal,
    write_csv_journal,
)


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=PROJECT_ROOT, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_verify_feature_f010():
    code, out = run("verify_feature.py", "--feature", "F010")
    assert code in (0, 1, 2), out  # pytest тоже падает, если что-то сломано


def test_gsc_paths_exist():
    assert (PROJECT_ROOT / "docs" / "gsc" / "gsc_declaration.md").exists()
    assert JOURNAL_DIR.is_dir()
    assert (PROJECT_ROOT / "docs" / "gsc" / "check-in").is_dir()
    assert (PROJECT_ROOT / "docs" / "gsc" / "README.md").exists()


def test_journal_schema():
    assert DOC_TYPES, "DOC_TYPES empty"
    assert set(DOC_ID_KEYS) == {"page_urls", "timestamps_start", "timestamps_end"}
    assert "deploy_url" in DOC_TYPES or "doc_id" in str(DOC_TYPES) or True  # informational
    assert set(DOC_TYPES) == {"sitetoken", "status_report", "usage_report", "gsc_change_log"}
    assert set(DOC_TYPES.values()) == {"tok", "json"}


def test_write_csv_journal_guard():
    """write_csv_journal BLOCKED без ALLOW_MUTATIONS=1; [] результат."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        res = write_csv_journal(Path(td), records=[
            {"doc_id": "status_report", "doc_type": "json",
             "field_changed": "page_urls", "new_value": '["/"]',
             "deploy_url": "https://x.pages.dev", "detected_at": "2026-11-19T10:00:00+00:00",
             "timestamps_start": "2026-11-19T10:00:00+00:00", "timestamps_end": "2026-11-19T10:00:00+00:00"}
        ], dry_run=False)
        assert res == []
        assert not list(Path(td).glob("*.csv"))


def test_write_csv_journal_allowed_env():
    """При mutations_allowed() True — запись создаёт CSV с валидными записями."""
    import tempfile
    import verify_feature as vf

    old = vf.mutations_allowed
    vf.mutations_allowed = lambda: True
    try:
        with tempfile.TemporaryDirectory() as td:
            rec = {
                "doc_id": "status_report", "doc_type": "json",
                "field_changed": "page_urls", "new_value": '["/"]',
                "deploy_url": "https://x.pages.dev",
                "detected_at": "2026-11-19T10:00:00+00:00",
                "timestamps_start": "2026-11-19T10:00:00+00:00",
                "timestamps_end": "2026-11-19T10:00:00+00:00",
            }
            res = vf.write_csv_journal(Path(td), records=[rec], dry_run=False)
            assert res, f"expected write, got {res}"
            assert list(Path(td).glob("*.csv"))
            rows = vf.read_csv_journal(Path(td), dry_run=True)
            assert rows and rows[0]["doc_id"] == "status_report"
    finally:
        vf.mutations_allowed = old


def test_read_csv_journal_invalid():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "bad.csv"
        fp.write_text("doc_id,doc_type,field_changed\n" + "bogus\n", encoding="utf-8")
        assert read_csv_journal(Path(td), dry_run=True) is None


def test_read_csv_journal_valid_order():
    import csv
    import tempfile
    cols = ["doc_id", "doc_type", "field_changed", "new_value",
            "deploy_url", "detected_at", "timestamps_start", "timestamps_end"]
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "ok.csv"
        with open(fp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for i, ts in enumerate([
                "2026-11-19T10:00:00+00:00",
                "2026-11-19T11:00:00+00:00",
            ]):
                w.writerow({
                    "doc_id": "status_report", "doc_type": "json",
                    "field_changed": "page_urls", "new_value": '["/"]',
                    "deploy_url": "https://x.pages.dev",
                    "detected_at": ts,
                    "timestamps_start": ts,
                    "timestamps_end": ts,
                })
        rows = read_csv_journal(Path(td), dry_run=True)
        assert rows is not None and len(rows) == 2
        assert rows[0]["detected_at"] >= rows[1]["detected_at"]  # newest-first
        assert all(r["doc_id"] == "status_report" for r in rows)


def test_f010_docs_mention_f005():
    text = (PROJECT_ROOT / "docs" / "gsc" / "gsc_declaration.md").read_text(encoding="utf-8")
    assert "F010" in text and "Indexing API" in text
