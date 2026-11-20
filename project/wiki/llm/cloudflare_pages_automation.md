# scripts/cloudflare_pages_automation.py — F012: CF Pages worker (VERDICT engine)

Alternative to `cloudflare_pages_gsc.py` / `cloudflare_deploy_hook.py`: cloudflare-first verifier worker.
Source of truth: `feature_list.json` F012, tests `tests/test_f012_f013_f015.py`.

## Steps (7) — EXTRACT по `feature_list.json` F012
- S01-S05: верификация деплоя через GSC API (`_get_gsc_service()` → BLOCKED без auth), результат `return 0/1/2`
- Все GSC мутации (none в этом файле — read-only, тестовый инструмент)
- Tests: help/--step/--deployed-url проверяются через subprocess.

## Verdict semantics (common.py)
exit codes 0 (pass) / 1 (fail) / 2 (blocked). `check_mutation_allowed()` — dry-run default.

## Связи
- [cloudflare_pages_gsc.md](cloudflare_pages_gsc.md), [cloudflare_deploy_hook.md](cloudflare_deploy_hook.md), [README.md](README.md)
