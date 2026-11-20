# GSC Declaration — F010

Структура документации интеграции с Google Search Console.

- Описание GSC workflow: [`gsc_declaration.md`](gsc_declaration.md)
- Статусы интеграции: [`gsc_status_reports/`](gsc_status_reports/) (grep STATUS journal CSV)
- Check-in: [`check-in/`](check-in/)

**Journal keys** (поддерживаются `verify_feature.read_csv_journal`):
`doc_id, doc_type, field_changed, new_value, deploy_url, detected_at, timestamps_start, timestamps_end`
Допустимые `doc_id`: `sitetoken, status_report, usage_report, gsc_change_log`;
`field_changed`: `page_urls, timestamps_start, timestamps_end`.

`timestamps_start` — когда начинается сравнение временных меток (ISO 8601),
`timestamps_end` — когда заканчивается. `detected_at` ≥ `timestamps_start`.
