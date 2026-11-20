# GSC Discover — как проверять (F010)

## GSC Discover semantics — почему требуется сравнение

GSC Discover показывает, как быстро URL попал в Discover feed — до тех пор,
как он не будет индексирован через Indexing API/deploy. Deploy → check должен
использовать **URL Inspection и status-change comparisons**, а не lock-in indexing API.

## Верификация (стандартный шаблон — `verify_feature.py --feature F010`)

1. `S01: gsc_automation.py --step S01 --site-url https://example.com/` → PASS/BLOCKED(GSC_SITE_URL).
2. `S05b: urls.inspect — indexStatus == INDEX_GSC_READY` (GSC API).
3. `S05: Indexing API — POST https://indexing.googleapis.com/v3/urlNotifications:publish` (мутация).
4. GSC_DISCOVER_VERIFY — верифайер по статусам GSC, покрытие (3 основные страницы).
5. GSC Discover status check — status-change comparison, сравнение timestamps
   (timestamps_start ≤ timestamp ≤ timestamps_end).

## Триплеты для F010

- `doc_id: sitetoken, doc_type: tok`
- `doc_id: status_report, doc_type: json`
- `doc_id: usage_report, doc_type: json`
- `doc_id: gsc_change_log, doc_type: json`

## Keywords
- F010, GSC discover, timestamps_start, timestamps_end, INDEX_GSC_READY, deployment, discover, status comparison
