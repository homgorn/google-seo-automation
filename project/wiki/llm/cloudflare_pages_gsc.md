# scripts/cloudflare_pages_gsc.py — F012: Cloudflare Pages → GSC Decl

Source of truth: `feature_list.json` F012 (7 steps), tests `tests/test_f012_f013_f015.py`.

## Подписи
- CLI: `--step S01..S04|all --deployed-url https://<subdomain>.pages.dev --top-pages ...`

## Steps (7)
1. S01: `verify_deploy_started` — sites.get → deployed=True
2. S02: `verify_sitemap_submit` — `sitemaps().submit(siteUrl=..., feedpath="sitemap.xml")` — мутация, GUARDED
   через `check_mutation_allowed()` (default BLOCKED без ALLOW_MUTATIONS=1)
3. S03: `verify_indexing_top_pages` — Indexing API: `urls().publish({url, type: URL_UPDATED})` (Homepage + 2 key pages)
4. S04: `verify_discover` — семантический verify (sites.get + sitemaps.get)

## Verdict
`Verdict("F012")` (common.py) — per-step PASS/FAIL/BLOCK; exit codes 0/1/2.

## Тесты (structural, no auth)
`tests/test_f012_f013_f015.py` — help text, --step работает, exit in (0,2), mutations_allowed() == False.

## Мутации
Гард: `check_mutation_allowed(verdict, step)` — `mutation_audit.csv`, log via `log_guide_safe`.

## Связи
- [cloudflare_deploy_hook.md](cloudflare_deploy_hook.md) — деплой перед этим скриптом
- [README.md](README.md) — статус: structural, аутентификация: GSS pages budget, auth: GCP sa
- `docs/cloudflare-pages-gsc.md`
