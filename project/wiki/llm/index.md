# wiki/llm/ — LLM Wiki вики

## Страницы

| Страница | Тема |
|----------|------|
| [README.md](README.md) | Статус фич: F012 ✅, F013 🔶, F015 ✅, описания модулей |
| [cloudflare_pages_gsc.md](cloudflare_pages_gsc.md) | F012: `cloudflare_pages_gsc.py` — субтитры (steps, verdict, мутации) |
| [cloudflare_deploy_hook.md](cloudflare_deploy_hook.md) | F012-01: `cloudflare_deploy_hook.py` — actions, exit-codes |
| [cloudflare_pages_automation.md](cloudflare_pages_automation.md) | F012 worker (EXTRACT по feature_list) |
| [f015_chromex.md](f015_chromex.md) | F015: `f015_chromex.py` — remote (PSI) / analyze (Lighthouse), thresholds |
| [f014_astro_cloudflare.md](f014_astro_cloudflare.md) | F014: `f014_astro_cloudflare.py` — Astro+Cloudflare 2026 (wrangler, cache, images, redirects) |
| [append_new_features.md](append_new_features.md) | F012–F015: `append_new_features.py` — добавление фич |
| [research/webdev-cwv-thresholds.md](research/webdev-cwv-thresholds.md) | web.dev: INP/CLS/FCP пороги + definitions |

## Семантический граф

- БД: `project/data/llm_knowledge.db` (SQLite: entities, ontology, triples, edges)
- Запросы: `python scripts/query_llm_graph.py --subject feature:F015` (или --predicate/--query)
- Обновление: `python scripts/build_llm_knowledge.py`

## Ресёрч (фетчи)

| Файл | Источник | Что |
|------|----------|-----|
| [research/webdev-cwv-thresholds.md](research/webdev-cwv-thresholds.md) | web.dev | INP/CLS thresholds + definitions (fetch 2026-11-19) |
