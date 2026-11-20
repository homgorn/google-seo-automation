# scripts/f015_chromex.py — F015: Chrome UX + Core Web Vitals

Source of truth: `feature_list.json` F015 (8 steps), `tests/test_f012_f013_f015.py`,
`wiki/llm/research/webdev-cwv-thresholds.md`.

## CLI
```
f015_chromex.py remote --page <url>... --device mobile   # PSI v5 (прямой API, с ретраями)
f015_chromex.py analyze --page <url>... --budget-ms 30000 # Lighthouse (npx lighthouse)
```

## Steps (8)
1. Chrome UX Report — веб-данные: **[wiki](webdev-cwv-thresholds.md) хорошего порога: LCP, CLS, FCP, INP, TTFB**
2. PSI — `runPagespeed` v5 для каждой страницы → числовые значения (`parse_psi_metrics`: numericValue через `largest-contentful-paint`, `cumulative-layout-shift-semantic` или `cumulative-layout-shift`, `server-response-time`, `interaction-to-next-paint`)
3. Lighthouse — `run_lighthouse` (`npx lighthouse`) для `analyze`
4. Thresholds — `THRESHOLDS`: LCP < 2500, CLS < 0.1, FCP < 2000, INP < 200, TTFB < 1800 (Stability Index; web.dev)
5. Reports — `docs/reports/f015-psi-YYYYMMDD.md` (remote), `docs/reports/f015-YYYYMMDD.md` (analyze)
6. Retry — `run_psi`: retries на 429/5xx (3 попытки, backoff 1.5s × n)
7. Output — `print` реальные числа `LCP=`, `CLS=`, `FCP=`, `INP=`, `TTFB=` — тест парсит через `parse_metric()`
8. Exit codes — 0 = pass, 1 = fail, 2 = blocked (network/Lighthouse unavailable/пустой список)

## Notes
- Нельзя полагаться на строки из логов — все метрики — реальные числа (тесты парсят).
- PSI возвращает `CLS` как `cumulative-layout-shift-semantic` (Lighthouse ≥11.4), фолбэк `cumulative-layout-shift`.
- Web.dev definition (CLS = session window max; "0.1 or less"; INP = 200ms good).

## Тесты
`test_f015_chromex_exit_codes` — `remote --page https://example.com`, парсит `LCP=`/`CLS=`/`TTFB=` из stdout, проверяет пороги (<2500 / <0.1 / <1800).
`test_f015_chromex_uses_psi_api` — URL `googleapis.com/pagespeedonline/v5/runPagespeed`.

## Связи
- [README.md](README.md), `docs/cloudflare-pages-gsc.md`
