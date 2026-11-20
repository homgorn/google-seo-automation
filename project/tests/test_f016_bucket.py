#!/usr/bin/env python3
"""tests/test_f016_bucket.py — F016: GSC Bucket System Design (doc + feature)."""

import json
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


def test_f016_feature_entry():
    data = json.loads((PROJECT_ROOT / "feature_list.json").read_text(encoding="utf-8"))
    f016 = [x for x in data if x["id"] == "F016"]
    assert f016, "F016 missing from feature_list.json"
    assert len(f016[0]["steps"]) >= 7


def test_f016_design_doc_exists():
    assert (PROJECT_ROOT / "docs" / "gsc" / "gsc_bucket_design.md").exists()
    text = (PROJECT_ROOT / "docs" / "gsc" / "gsc_bucket_design.md").read_text(encoding="utf-8")
    for s in ("GSS_PENDING", "GSC_READY", "DEPLOYING", "CLOUDFLARE_WAIT", "GSC_FULL_DEPLOY"):
        assert s in text


def test_f016_related_docs_exist():
    assert (PROJECT_ROOT / "docs" / "gsc" / "gsc_declaration.md").exists()
    assert (PROJECT_ROOT / "docs" / "gsc" / "check-in").is_dir()
