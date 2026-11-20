# GSC Declaration — интеграция с Google Search Console (F010)

Автоматизированная интеграция с GSC: sitemap, URL inspection, Indexing API, статусы, check-in.

## Статусы (grep STATUS journal)

- `docs/gsc/gsc_status_reports/gsc-journal-*.csv` — journal статусов, структура:
  `doc_id (sitetoken|status_report|usage_report|gsc_change_log), doc_type (json|tok),
  field_changed (page_urls|timestamps_start|timestamps_end), new_value, deploy_url,
  detected_at, timestamps_start, timestamps_end`

## Check-in (деплой → статус)

- `docs/gsc/check-in/README.md`, `discovery-guide.md`

## API (прямой клиент — googleapiclient + OAuth по умолчанию профиля пользователя)

- `urls:inspect` — INDEX_GSC_READY / INDEX_HEADER_COUNTED / PASS
- `sitemaps.list` / `urlNotifications.metadata`
- `Indexing API urlNotifications:publish` (URL_UPDATED / URL_DELETED) — мутация, dry-run default

## Keywords
- GSC declaration, sitemap, URL inspection, Indexing API, gsc_status_reports, check-in, sitetoken
