# Astro + Cloudflare 2026 Best Practices — F014

> Grounding: Astro Docs (astro-docs MCP, Nov 2026). Код: `scripts/f014_astro_cloudflare.py`.

## Деплой (2026)

Cloudflare рекомендует **Workers** для новых проектов; Pages — legacy.
```jsonc
// wrangler.jsonc
{
  "name": "my-astro-app",
  "compatibility_date": "2026-11-01",   // день деплоя
  "assets": { "directory": "./dist", "not_found_handling": "404-page" },
  "observability": { "enabled": true }
}
```
- Static: без adapter. On-demand: `npx astro add cloudflare` → `@astrojs/cloudflare`.
- Деплой: `npx astro build && npx wrangler deploy`.

## Кэш (Cache Provider API, astro@7)

```js
import cloudflare from '@astrojs/cloudflare';
import { cacheCloudflare } from '@astrojs/cloudflare/cache';
export default defineConfig({
  adapter: cloudflare(),
  cache: { provider: cacheCloudflare() },   // → Cloudflare-CDN-Cache-Control + Cache-Tag
});
```
- Хешированные ассеты (`_astro/*`) → длинный кэш. `public/_headers`:
  ```
  /_astro/*
    Cache-Control: public, max-age=31536000, immutable
  ```

## Images

- `imageService: 'cloudflare-binding'` (дефолт `@astrojs/cloudflare@14`).
- `<img>`: `width`/`height` (против CLS) + `loading="lazy"` (вне above-the-fold).

## Redirects / 404 / Troubleshooting

- `public/_redirects` или `redirects` в astro.config.
- `not_found_handling: '404-page'` для кастомной 404 на Workers.
- Hydration mismatch → выключить Auto Minify в Cloudflare.

## Команды

```bash
python scripts/f014_astro_cloudflare.py --action best_practices --project-dir ./site
python scripts/f014_astro_cloudflare.py --action wrangler --write   # генерация (ALLOW_MUTATIONS=1)
```
Отчёт: `docs/reports/f014-astro-cf-YYYYMMDD.md`.

## Ссылки
- https://docs.astro.build/en/guides/deploy/cloudflare/
- https://docs.astro.build/en/guides/integrations-guide/cloudflare/
- https://docs.astro.build/en/guides/caching/