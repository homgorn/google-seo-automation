# LLM-Подсистема (wiki/llm/) — Google SEO Automation

Структура: документация всех LLM-скриптов, вики фич (F001–F015), связи между артефактами,
семантический граф знаний: `project/data/llm_knowledge.db` (SQLite: entities, ontology, triples).
Основной слой знаний — `project/wiki/` (индексы: `wiki/index.md`, `wiki/index.json`, генерируются `scripts/wiki_index.py`).

## Обновления версий (2026-11-19)

| Файл | Статус | Что описано |
|------|--------|-------------|
| `cloudflare_pages_gsc.py` | in_progress | F012: sitemaps.submit, Indexing API (urls.publish URL_UPDATED), GSC URL inspection, deploy-hook действия |
| `cloudflare_deploy_hook.py` | in_progress | F012-01: verify_deploy, url_inspection, gsc_discover, dump_to_db |
| `cloudflare_pages_automation.py` | in_progress | F012: VERDICT-based worker (S01–S05), шаги deploy-hook → GSC |
| `f015_chromex.py` | in_progress | F015: `remote` (PSI v5 реальные метрики), `analyze` (Lighthouse), thresholds LCP/CLS/FCP/INP/TTFB, ретраи на 429 |
| `append_new_features.py` | in_progress | F012–F015 в feature_list.json |
| `enrich_feature_list.py` | passing_stub | Stub for enrichment of new features |

## Все вики-фичи (feature_list.json)

Всего: **14 фич**. Автоматизация (prio 1) → Cloudflare-first
(`docs/cloudflare-pages-gsc.md`), GSC через прямой API v3.

### F012 — Cloudflare Pages Deploy Automation (prio 1) ✅ (structural, auth-blocked)
**Скрипт:** [cloudflare_pages_gsc.py](cloudflare_pages_gsc.md) · [cloudflare_deploy_hook.py](cloudflare_deploy_hook.md)
**Шаги (7):** sitemaps.submit → Indexing API → urls.inspect → sitemaps.get → results → GSC verify → quota audit.
Мутации: **dry-run по умолчанию** (`ALLOW_MUTATIONS`), тесты: `tests/test_f012_f013_f015.py` (зелёные, 14+).

### F013 — SEO Acceleration Pack (prio 1) 🔶
**Шаги (12):** Robots.txt, AI crawler allow/deny (GPTBot/PerplexityBot/ClaudeBot/LLaMABot), structured data (OG+JSON-LD), sitemap interlinks, CWV telemetry, PageSpeed alerts, E-E-A-T блоки, meta tags, image alt audit, interlink report.
**Скрипты/файлы:** `project/docs/architecture.md` (WIP) · `project/docs/runbooks/` · `project/reference/`

### F014 — Astro + Cloudflare 2026 Best Practices (prio 2)
**Не реализована.**

### F015 — Chrome UX + CWV Monitoring (prio 2) ✅
**Скрипт:** [f015_chromex.py](f015_chromex.py)
**Шаги (8):** PSI metrics → thresholds → reports `docs/reports/f015-*.md`.
Thresholds (Stability Index): **LCP < 2500ms, CLS < 0.1** (+FCP 2000ms, INP 200ms, TTFB 1800ms).
Отчёты: `docs/reports/f015-psi-*.md` (PSI), `docs/reports/f015-*.md` (Lighthouse).

### F010–F011 — Testing framework, Runbooks (prio 2)
Реализованы: `verify_feature.py` (verification engine), runbooks `docs/runbooks/`.

### F001–F009 — Original layer
GA4, GTM, GSC, Google Ads, Bing Ads, AEO, Wiki, OS, Recovery, OpenChamber. (Auth: GCP sa)

## LLM Knowledge DB (data/llm_knowledge.db)

| Entity | Rows | Что |
|--------|------|-----|
| features | 14 | F001–F015 + метрики F013/F015 (CWV thresholds) |
| scripts | 14 | Пути, статус, мутации |
| thresholds | 5 | LCP/CLS/FCP/INP/TTFB + semantic |

Семантический граф (`data/llm_knowledge.db`): сущности — features/scripts/docs/APIs + онтология
(depends_on, affects, mutates, implements, tests_for, monitored_by). Триплеты: `links` и `triples`.

## Поиск по знаниям

```bash
python -m sqlite3 data/llm_knowledge.db "SELECT * FROM triples WHERE subject='feature:F015';"
python scripts/wiki_query.py --query "CWV thresholds"
```
