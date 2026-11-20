# GSC Status Reports Journal — F010

Запись статусов интеграции с GSC, поддерживается `verify_feature.read_csv_journal()` / `write_csv_journal()`.

## Schema (journal CSV columns)

| Колонка | Тип | Описание |
|---------|-----|----------|
| doc_id | sitetoken \| status_report \| usage_report \| gsc_change_log | источник данных |
| doc_type | json \| tok | тип документа (поддерживаемый: json, tok) |
| field_changed | page_urls \| timestamps_start \| timestamps_end | что изменилось |
| new_value | string | статус / JSON-строка |
| deploy_url | string | URL деплоя |
| detected_at | ISO 8601 | время обнаружения |
| timestamps_start | ISO 8601 | начало сравнения |
| timestamps_end | ISO 8601 | конец сравнения (detected_at ≥ timestamps_start) |

## Запись (гардировано — mutations_allowed() == False)

```bash
ALLOW_MUTATIONS=1 python -c "from verify_feature import write_csv_journal; write_csv_journal(records=[{'doc_id': 'status_report', ...}], dry_run=False)"
```

Полный шаблон тестов — `tests/test_f010_verify.py`.
