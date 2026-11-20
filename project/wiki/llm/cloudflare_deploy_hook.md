# scripts/cloudflare_deploy_hook.py — F012-01: Deploy hook (Cloudflare Pages)

Source of truth: `feature_list.json` F012, tests `tests/test_f012_f013_f015.py`.

## CLI
`--action verify_deploy|url_inspection|gsc_discover|dump_to_db` — all require `--project-id`, `--deployed-url`.

## Steps
- S01 `cmd_verify_deploy`: GSC `sites().get(siteUrl=deployed_url)` → deployed=True (BLOCKED без auth)
- S02 `cmd_url_inspection`: GSC `urls().inspect` для sample_urls (PASS/FAIL, ERROR-изоляция)
- S03 `cmd_gsc_discover`: GSC `sitemaps().get(siteUrl=deployed_url, feedpath="/sitemap.xml")` → lastStatus/lastSubmissionTime
- S04 `cmd_dump_to_db`: INSERT в `change_log` (GUARDED) + `docs/reports/cloudflare-deploy-*.md`

## Notes
- S04 запись в БД — мутация; default BLOCKED без ALLOW_MUTATIONS (гард в `cmd_dump_to_db`).
- GSC через прямой API v3 (googleapis.discovery.build + google.auth.default).
- Тесты: help показывает все actions + флаги; signature --action.

## Связи
- [cloudflare_pages_gsc.md](cloudflare_pages_gsc.md), [README.md](README.md)
- `docs/cloudflare-pages-gsc.md` (развёрнутая документация)
