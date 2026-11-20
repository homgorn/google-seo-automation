# GSC Bucket System Design — F016

Дизайн системы переходов страниц через GSC-бакеты (bucket lifecycle).

## Модель состояний (bucket states)

Каждая страница проходит через стадии, отражённые в `gsc_automation.gsc_urls_inspect().indexStatus`:

```
GSS_PENDING    ──(pages в CMS/sitemap, до GSC)──▶
GSC_READY      ──(urls.inspect == INDEX_GSC_READY, sitemaps.submit)──▶
DEPLOYING      ──(verify_deploy: sites.get deployed=True)──▶
CLOUDFLARE_WAIT ──(verify_gsc_discover: sites.get + sitemaps.get + INDEX_GSC_READY)──▶
GSC_FULL_DEPLOY ──(полное прохождение, уведомление пользователя)──▶ DONE
```

## Buckets и регистрация (deploy-time buckets)

```
deploy(url, pages, site_url, users) →
  1. discover_and_submit(url, pages) — GSC submit (sitemap + Indexing API)
  2. deploy_discovery_requeue(url, users) — регистрация deploy в GSC (wait + edge retry)
```

## Переходы (создание задач в очереди Cloudflare Queue — edge sync)

```
resolve_bucket_transition(bucket, users) → {bucket, reason, wait_seconds}
```

- `GSS_PENDING → GSC_READY`: через `gsc_automation.gsc_urls_inspect()` (INDEX_GSC_READY), запись в journal: `doc_id: sitetoken`, `status_transition: GSS_PENDING→GSC_READY`
- `GSC_READY → DEPLOYING`: `verify_deploy(url, site_url)` (sites.get deployed=True), journal `status_transition: GSC_READY→DEPLOYING`
- `DEPLOYING → CLOUDFLARE_WAIT`: `verify_gsc_discover(site_url)` — sites.get + sitemaps.get + INDEX_GSC_READY, journal `status_transition: DEPLOYING→CLOUDFLARE_WAIT`
- `CLOUDFLARE_WAIT → GSC_FULL_DEPLOY`: `GSC_FULL_DEPLOY_NOTIFY(url, site_url, users)` — email с всеми страницами + timeline (через SMTP)

## Проверки переходов

- `wait_for_deployment_ready(url, site_url, users)` — ожидание до INDEX_GSC_READY, опрос discover (wait + edge retry)
- `requeue_transition(bucket, users)` — перепроверка через GSC API, переходы через Cloudflare Queue (edge retry)
- `verify_gsc_discover(site_url)` — INDEX_GSC_READY на ключевых страницах (deployment)
- `check_valid_error_status(site_url, url)` — `gsc_automation.gsc_urls_inspect()` → {verified, indexStatus, ...}

## Квоты и переходы (GSS iterations → GSC-ready)

- `wait_for_quota_available(urls, quota_used, deadline)` — GSC_DISCOVER_VERIFY bucket (bucket=CLOUDFLARE_WAIT, quota на DISCOVER_VERIFY 200/день) — опрос url.inspect, квота, wait 10-15 мин, edge retry
- Export: `get_deployment_gsc_errors(site_url, bucket, users)` — GSC URL statuses export (из `gsc_automation`)

## Компоненты

- `gsc_automation.py` — GSC API (sites.list, sitemaps.list, urls.inspect) — уже существует
- `cloudflare_pages_gsc.py` — GSC submit + Indexing on deploy — уже существует
- `gsc_bucket.py` (TBD) — машина переходов: Cloudflare Queue

## Связи

- [`gsc_automation.py`](../../scripts/gsc_automation.py) — GSC API
- [`cloudflare_pages_gsc.py`](../../scripts/cloudflare_pages_gsc.py) — GSC submit on deploy
- [F010 GSC journal](gsc_declaration.md) — переходы через journal

## Keywords
- F016, GSC bucket, bucket states, GSS iterations, GSC-ready, deployment, Cloudflare wait, GSC full deploy, notification, state machine, transitions, deploy lifecycle, edge sync.
