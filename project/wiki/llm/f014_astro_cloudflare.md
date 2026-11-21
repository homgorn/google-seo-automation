# scripts/f014_astro_cloudflare.py — F014: Astro + Cloudflare 2026 Best Practices

Source: Astro Docs MCP (Nov 2026), `docs/cloudflare-astro-2026.md`, tests `tests/test_f014_astro.py`.

## CLI
```
f014_astro_cloudflare.py --action wrangler|cache|images|redirects|best_practices --project-dir ./site [--write]
```

## Actions
- `wrangler` — валидация/генерация wrangler.jsonc (assets.directory=./dist, compatibility_date, not_found_handling=404-page). Без файла → BLOCKED; `--write` генерирует (гард ALLOW_MUTATIONS).
- `cache` — cache provider (cacheCloudflare → Cloudflare-CDN-Cache-Control) + public/_headers `/_astro/* immutable`.
- `images` — imageService cloudflare-binding; img width/height (CLS) + loading=lazy; WARN если dims нет.
- `redirects` — public/_redirects или configured redirects.
- `best_practices` — полный аудит → `docs/reports/f014-astro-cf-YYYYMMDD.md` (overall PASS/FAIL/BLOCKED).

## Grounding (Astro Docs)
- Workers рекомендован (Pages legacy); `wrangler.jsonc` + `npx wrangler deploy`.
- Cache Provider API astro@7: `cacheCloudflare()` → Cloudflare-CDN-Cache-Control + Cache-Tag.
- Хешированные ассеты `_astro/*` → immutable; `not_found_handling: '404-page'`.
- Auto Minify выключить при hydration mismatch.

## Тесты
`tests/test_f014_astro.py` (8): helpers, wrangler missing→BLOCKED, valid→PASS, images missing dims→WARN, best_practices report.

## Связи
- [README.md](README.md), `docs/cloudflare-astro-2026.md`, [f013](f015_chromex.md)