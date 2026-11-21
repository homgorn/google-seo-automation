#!/usr/bin/env python3
"""tests/test_f013_sitemap.py — F013: sitemap interlinks + deploy_submit (steps 5,9,12)."""

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


def test_f013_sitemap_blocked_when_missing(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f013_seo_acceleration import Verdict, action_sitemap
    v = Verdict("F013")
    ok = action_sitemap(v, tmp_path)
    assert ok is False
    assert v.blocked == 1


def test_f013_sitemap_valid_with_lastmod(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f013_seo_acceleration import Verdict, action_sitemap
    pub = tmp_path / "public"
    pub.mkdir()
    (pub / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset>'
        '<url><loc>https://x.com/</loc><lastmod>2026-11-21</lastmod></url>'
        '<url><loc>https://x.com/a</loc><lastmod>2026-11-20</lastmod></url>'
        '</urlset>', encoding="utf-8")
    v = Verdict("F013")
    ok = action_sitemap(v, tmp_path)
    assert ok is True
    assert v.passed >= 1


def test_f013_sitemap_missing_lastmod_warns(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f013_seo_acceleration import Verdict, action_sitemap
    pub = tmp_path / "public"
    pub.mkdir()
    (pub / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset>'
        '<url><loc>https://x.com/</loc></url>'
        '<url><loc>https://x.com/a</loc><lastmod>2026-11-20</lastmod></url>'
        '</urlset>', encoding="utf-8")
    v = Verdict("F013")
    ok = action_sitemap(v, tmp_path)
    assert ok is False  # missing lastmod → не PASS
    assert any(s["status"] == "WARN" for s in v.steps)


def test_f013_sitemap_index_passes(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from f013_seo_acceleration import Verdict, action_sitemap
    pub = tmp_path / "public"
    pub.mkdir()
    (pub / "sitemap.xml").write_text(
        '<sitemapindex><sitemap><loc>https://x.com/s1.xml</loc></sitemap></sitemapindex>',
        encoding="utf-8")
    v = Verdict("F013")
    ok = action_sitemap(v, tmp_path)
    assert ok is True


def test_f013_deploy_submit_dry_run_blocks():
    sys.path.insert(0, str(SCRIPTS))
    from f013_seo_acceleration import Verdict, action_deploy_submit
    import f013_seo_acceleration as f
    old = f.mutations_allowed
    f.mutations_allowed = lambda: False
    try:
        v = Verdict("F013")
        ok = action_deploy_submit(v, "https://example.com/")
        assert ok is False
        assert v.blocked == 1  # dry-run BLOCKED
    finally:
        f.mutations_allowed = old


def test_f013_help_lists_sitemap_and_deploy():
    code, out = run("f013_seo_acceleration.py", "--help")
    assert code == 0
    assert "sitemap" in out
    assert "deploy_submit" in out