# scripts/append_new_features.py — F012–F015: Добавление фич в feature_list.json

Source of truth: `feature_list.json` (F001–F015), `docs/progress.md`, `docs/cloudflare-pages-gsc.md`.

## Steps
1. Вставка новых фич в `feature_list.json`: F012, F013, F015 (reset+append)
2. Полные шаги (7/12/8) — расширены вручную согласно `feature_list.json`
3. Enrichment: `ACCEPTANCE/DEPENDS_ON/BLOCKED_BY/TEST_REFS/SCRIPTS/SPECS` из `enrich_feature_list.py`
4. Генерация `docs/reports/` и тестов

## Notes
- Запуск: `python scripts/append_new_features.py` (из корня проекта)
- `sys.path.insert(0, "scripts")` — чтобы импортировать `enrich_feature_list.py`
- F014 — **не добавлена** (была только в памяти владельца, не в репозитории)
- Совпадения F012/F013 steps: существующие шаги — не удалять без подтверждения пользователя

## Связи
- [README.md](README.md), `feature_list.json`, `docs/progress.md`
