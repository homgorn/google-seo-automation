#!/usr/bin/env python3
"""
f014_astro_cloudflare.py — F014: Astro + Cloudflare 2026 Best Practices.

Статический аудит + генерация конфигов для Astro-проектов, деплоящихся на
Cloudflare (Workers — рекомендованный путь 2026; Pages — legacy).

Grounding: Astro Docs (astro-docs MCP, Nov 2026):
  - Cloudflare Workers: wrangler.jsonc с assets.directory="./dist", compatibility_date
  - On-demand: @astrojs/cloudflare adapter, main="@astrojs/cloudflare/entrypoints/server"
  - Кэш: Cache Provider API (astro@7) — cacheCloudflare() → Cloudflare-CDN-Cache-Control + Cache-Tag
  - Хешированные ассеты Astro → длинный cache по умолчанию
  - _headers / _redirects в public/ (копируются в build output)
  - not_found_handling: "404-page" для кастомной 404
  - Auto Minify выключить при hydration mismatch

Actions (--action):
  wrangler        — валидация/генерация wrangler.jsonc
  cache           — cache provider config + _headers (Cache-Control для ассетов)
  images          — astro.config imageService + width/height/loading=lazy в output
  redirects       — _redirects / configured redirects
  best_practices  — полный аудит (все проверки) → docs/reports/f014-*.md

Usage:
  python scripts/f014_astro_cloudflare.py --action best_practices --project-dir ./site
  python scripts/f014_astro_cloudflare.py --action wrangler --write
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
REPORT_DIR = PROJECT_ROOT / "docs" / "reports"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from common import (  # noqa: E402
    Verdict, check_mutation_allowed, mutations_allowed, log_guide_safe,
)

# Рекомендованная дата совместимости Workers (день деплоя; плейсхолдер — свежий).
DEFAULT_COMPAT_DATE = "2026-11-01"


def _now():
    return datetime.now(timezone.utc)


def _find_config(project_dir: Path) -> Path | None:
    for name in ("astro.config.mjs", "astro.config.ts", "astro.config.js"):
        p = project_dir / name
        if p.exists():
            return p
    return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


# ── wrangler ──────────────────────────────────────────────────
def action_wrangler(verdict: Verdict, project_dir: Path, write=False) -> bool:
    """F014: wrangler.jsonc — assets.directory, compatibility_date, not_found_handling."""
    wrangler = project_dir / "wrangler.jsonc"
    if not wrangler.exists():
        wrangler = project_dir / "wrangler.json"
    cfg_text = _read(wrangler) if wrangler.exists() else ""
    issues = []
    if cfg_text:
        if "assets" not in cfg_text:
            issues.append("нет assets-блока (нужен assets.directory='./dist')")
        if "compatibility_date" not in cfg_text:
            issues.append("нет compatibility_date")
        if "not_found_handling" not in cfg_text and "404" not in cfg_text:
            issues.append("нет not_found_handling='404-page' (кастомная 404)")
        if issues:
            verdict.fail("F014 wrangler.jsonc", "; ".join(issues))
        else:
            verdict.pass_("F014 wrangler.jsonc", f"{wrangler.name}: assets + compatibility_date + not_found_handling OK")
    else:
        # нет wrangler — предлагаем генерацию
        if write and check_mutation_allowed(verdict, "F014 wrangler generate"):
            wrangler = project_dir / "wrangler.jsonc"
            wrangler.write_text(_wrangler_template(), encoding="utf-8")
            verdict.pass_("F014 wrangler.jsonc", f"Сгенерирован {wrangler.name} (assets.directory, compatibility_date, not_found_handling)")
        else:
            verdict.block("F014 wrangler.jsonc", "wrangler.json(c) не найден; запусти --write для генерации (нужен ALLOW_MUTATIONS=1)")
    return verdict.failed == 0


def _wrangler_template() -> str:
    return json.dumps({
        "name": "my-astro-app",
        "compatibility_date": DEFAULT_COMPAT_DATE,
        "assets": {
            "directory": "./dist",
            "not_found_handling": "404-page",
        },
        "observability": {"enabled": True},
    }, indent=2) + "\n"


# ── cache ─────────────────────────────────────────────────────
def action_cache(verdict: Verdict, project_dir: Path) -> bool:
    """F014: Cache Provider API — cacheCloudflare() + _headers для ассетов."""
    config = _find_config(project_dir)
    cfg_text = _read(config) if config else ""
    has_provider = "cacheCloudflare" in cfg_text or "cache:" in cfg_text
    if has_provider:
        verdict.pass_("F014 cache provider", "astro.config использует cache provider (cacheCloudflare/CDN-Cache-Control)")
    else:
        verdict.add("F014 cache provider", "WARN",
                    "нет cache provider — Astro 7 cacheCloudflare() даёт Cloudflare-CDN-Cache-Control + Cache-Tag")

    # _headers: длинный кэш для хешированных ассетов Astro (_astro/*)
    headers = project_dir / "public" / "_headers"
    ht = _read(headers) if headers.exists() else ""
    if "/_astro/*" in ht and "immutable" in ht:
        verdict.pass_("F014 _headers assets", "public/_headers: /_astro/* → immutable (хешированные ассеты)")
    else:
        verdict.add("F014 _headers assets", "WARN",
                    "public/_headers не содержит '/_astro/* Cache-Control immutable' (хешированные ассеты — длинный кэш)")
    return True


def _headers_template() -> str:
    return (
        "# _headers — F014: cache-control для хешированных ассетов Astro\n"
        "/_astro/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "/*.html\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n"
        "/sitemap.xml\n"
        "  Cache-Control: public, max-age=3600\n"
    )


# ── images ────────────────────────────────────────────────────
def action_images(verdict: Verdict, project_dir: Path) -> bool:
    """F014: Astro Images — imageService + width/height/loading=lazy в output."""
    config = _find_config(project_dir)
    cfg_text = _read(config) if config else ""
    if "imageService" in cfg_text or "cloudflare-binding" in cfg_text:
        verdict.pass_("F014 imageService", "astro.config задаёт imageService (cloudflare-binding/compile)")
    else:
        verdict.add("F014 imageService", "WARN",
                    "astro.config не задаёт imageService — дефолт cloudflare-binding (@astrojs/cloudflare@14)")

    # output HTML: img без width/height (CLS) или без loading
    out_dir = project_dir / "dist"
    if not out_dir.exists():
        out_dir = project_dir  # allow raw site dir
    total_img, no_dims, no_lazy = 0, 0, 0
    for html in list(out_dir.rglob("*.html"))[:500]:
        text = _read(html)
        for tag in re.findall(r"<img\b[^>]*>", text):
            total_img += 1
            if not ("width=" in tag and "height=" in tag):
                no_dims += 1
            if "loading=" not in tag and "loading=\"lazy\"" not in tag:
                no_lazy += 1
    if total_img == 0:
        verdict.block("F014 images", "нет <img> в output (нет dist/ или site без картинок)")
    else:
        verdict.add("F014 images", "PASS" if no_dims == 0 else "WARN",
                    f"{total_img} <img>, без width/height: {no_dims}, без loading: {no_lazy} "
                    f"(width/height обязательны против CLS)")
    return no_dims == 0


# ── redirects ─────────────────────────────────────────────────
def action_redirects(verdict: Verdict, project_dir: Path) -> bool:
    """F014: _redirects (Cloudflare) или configured redirects (Astro)."""
    redir = project_dir / "public" / "_redirects"
    config = _find_config(project_dir)
    cfg_text = _read(config) if config else ""
    has = redir.exists() or "redirects" in cfg_text
    if has:
        verdict.pass_("F014 redirects", "configured redirects / public/_redirects присутствуют")
    else:
        verdict.add("F014 redirects", "WARN",
                    "нет public/_redirects и нет redirects в astro.config (для миграций/старых URL)")
    return True


# ── best_practices (full audit) ───────────────────────────────
def action_best_practices(verdict: Verdict, project_dir: Path) -> bool:
    """F014: полный аудит Astro+Cloudflare 2026 → docs/reports/f014-*.md."""
    if not project_dir.exists():
        verdict.block("F014 best practices", f"project dir не найден: {project_dir}")
        return False

    sub = Verdict("F014")
    action_wrangler(sub, project_dir, write=False)
    action_cache(sub, project_dir)
    action_images(sub, project_dir)
    action_redirects(sub, project_dir)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"f014-astro-cf-{_now().strftime('%Y%m%d')}.md"
    lines = [
        f"# F014 — Astro + Cloudflare 2026 Best Practices — {_now().strftime('%Y-%m-%d')}",
        "",
        f"Project dir: `{project_dir}`",
        f"Overall: **{sub.overall}** (PASS={sub.passed}, FAIL={sub.failed}, BLOCKED={sub.blocked})",
        "",
        "## Проверки",
    ]
    for s in sub.steps:
        lines.append(f"- **{s['step']}**: {s['status']} — {s['evidence']}")
    lines += [
        "",
        "## Рекомендации 2026 (Astro Docs)",
        "- Деплой на Cloudflare **Workers** (Pages — legacy); `wrangler.jsonc` + `npx wrangler deploy`",
        "- `cache: { provider: cacheCloudflare() }` → Cloudflare-CDN-Cache-Control + Cache-Tag",
        "- `public/_headers`: `/_astro/* → immutable` (хешированные ассеты)",
        "- `not_found_handling: '404-page'` для кастомной 404",
        "- `imageService: cloudflare-binding` (дефолт @astrojs/cloudflare@14)",
        "- img: width/height (CLS) + loading=lazy (вне above-the-fold)",
        "- Auto Minify выключить при 'Hydration completed but contains mismatches'",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    verdict.pass_("F014 best practices", f"Отчёт: {report.relative_to(PROJECT_ROOT)} — overall={sub.overall}")
    verdict.steps.extend(sub.steps)
    log_guide_safe("f014", "F014 Astro+Cloudflare audit",
                   f"Report: {report.relative_to(PROJECT_ROOT)}, overall={sub.overall}",
                   ["f014", "astro", "cloudflare", "best-practices"])
    return sub.failed == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", choices=[
        "wrangler", "cache", "images", "redirects", "best_practices",
    ], default="best_practices")
    ap.add_argument("--project-dir", default=str(PROJECT_ROOT / "site"),
                    help="Корень Astro-проекта (с astro.config.* / dist/)")
    ap.add_argument("--write", action="store_true",
                    help="Генерировать wrangler.jsonc/_headers (нужен ALLOW_MUTATIONS=1)")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    project_dir = Path(args.project_dir)
    verdict = Verdict("F014")

    if args.action == "wrangler":
        action_wrangler(verdict, project_dir, write=args.write)
    elif args.action == "cache":
        action_cache(verdict, project_dir)
    elif args.action == "images":
        action_images(verdict, project_dir)
    elif args.action == "redirects":
        action_redirects(verdict, project_dir)
    elif args.action == "best_practices":
        action_best_practices(verdict, project_dir)

    print(verdict.summary_str())
    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())