#!/usr/bin/env python3
"""tests/test_f014_astro.py — F014: Astro + Cloudflare 2026 Best Practices."""

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


def test_f014_module_exists():
    assert (SCRIPTS / "f014_astro_cloudflare.py").exists()


def test_f014_help():
    code, out = run("f014_astro_cloudflare.py", "--help")
    assert code == 0
    for a in ("wrangler", "cache", "images", "redirects", "best_practices"):
        assert a in out


def test_f014_helpers_importable():
    sys.path.insert(0, str(SCRIPTS))
    from f014_astro_cloudflare import (
        Verdict, _wrangler_template, _headers_template,
        action_wrangler, action_cache, action_images, action_redirects,
    )
    w = json.loads(_wrangler_template())
    assert w["assets"]["directory"] == "./dist"
    assert "compatibility_date" in w
    assert w["assets"]["not_found_handling"] == "404-page"
    h = _headers_template()
    assert "/_astro/*" in h and "immutable" in h


def test_f014_wrangler_missing_blocks(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f014_astro_cloudflare import Verdict, action_wrangler
    v = Verdict("F014")
    action_wrangler(v, tmp_path, write=False)
    assert v.blocked == 1  # нет wrangler → BLOCKED


def test_f014_wrangler_valid_passes(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f014_astro_cloudflare import Verdict, action_wrangler
    (tmp_path / "wrangler.jsonc").write_text(
        '{"assets":{"directory":"./dist","not_found_handling":"404-page"},"compatibility_date":"2026-11-01"}',
        encoding="utf-8")
    v = Verdict("F014")
    action_wrangler(v, tmp_path, write=False)
    assert v.passed == 1


def test_f014_images_detects_missing_dims(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f014_astro_cloudflare import Verdict, action_images
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<img src="/a.png" alt="x">', encoding="utf-8")
    v = Verdict("F014")
    action_images(v, tmp_path)
    # img без width/height → WARN (не PASS)
    assert any(s["status"] == "WARN" for s in v.steps)


def test_f014_best_practices_report(tmp_path):
    code, out = run("f014_astro_cloudflare.py", "--action", "best_practices",
                    "--project-dir", str(tmp_path))
    assert code in (0, 1, 2), out
    reports = list((PROJECT_ROOT / "docs" / "reports").glob("f014-astro-cf-*.md"))
    assert reports, "no f014 report generated"


def test_f014_in_verify_feature():
    code, out = run("verify_feature.py", "--feature", "F014")
    assert "F014" in out