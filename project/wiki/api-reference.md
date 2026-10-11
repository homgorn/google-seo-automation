---
title: "Google APIs для SEO, AI Overviews и Автоматизации"
description: "Полная документация всех Google API (GA4, GTM, GSC, Ads, Indexing, Merchant, Business Profile, PageSpeed), Microsoft Advertising API, эндпоинты, схемы, примеры"
category: "api-reference"
source: "google-apis-master"
version: "2026-10-09"
last_fetched: "2026-10-09"
last_updated: "2026-10-09"
status: "current"
---

# Google APIs — Полный справочник для SEO и Автоматизации

> **Обновляется автоматически** каждые 14 дней через `scripts/sync_wiki.py --full`  
> **Последний полный sync:** 2026-10-09 | **Версия документа:** v1.0  
> **Источники:** developers.google.com, Google Search Central, Microsoft Learn, Hyper MCP References

---

## 📋 Быстрая навигация

| Раздел | API / Сервис | Основные эндпоинты |
|-------|---------------|---------------------|
| [GA4](#google-analytics-4-ga4) | Data API v1beta, Admin API v1alpha, Measurement Protocol v2 | `runReport`, `getMetadata`, `runRealtimeReport`, `batchRunReports`, `runPivotReport`, `runFunnelReport`, `checkCompatibility`, `properties.audienceExports`, `properties.recurringAudienceLists` |
| [GTM](#google-tag-manager-gtm) | Tag Manager API v2 | `accounts.get/list/update`, `containers.create/delete/get/update/snippet/combine`, `workspaces.manage`, `tags.manage`, `triggers.manage`, `variables.manage`, `built_in_variables.manage`, `folders.manage`, `environments.manage`, `versions.manage`, `version_headers.manage`, `user_permissions.manage`, `clients.manage`, `templates.manage`, `transformations.manage`, `zones.manage`, `destinations.manage` |
| [GSC](#google-search-console-gsc) | Search Console API v3 (webmasters) | `searchanalytics.query`, `sites.list/get/delete`, `sitemaps.list/get/submit/delete`, `urls.submit` |
| [Ads](#google-ads-api) | Google Ads API v18 | `GoogleAdsService.Search/SearchStream`, `GoogleAdsFieldService`, `CampaignService.mutate`, `AdGroupService.mutate`, `AdService.mutate`, `KeywordService.mutate`, `BiddingStrategyService.mutate`, `ConversionActionService.mutate`, `UserListService.mutate`, `SharedSetService.mutate`, `BudgetService.mutate`, `AssetService.mutate`, `SearchTermsReport` |
| [Indexing](#google-indexing-api) | Indexing API v3 | `urlNotifications:publish`, `urlNotifications/metadata` |
| [Merchant](#google-merchant-center-api) | Merchant API v1 (бывший Content API v2.1, sunset 18.08.2026) | `accounts.{accounts,products,orders,returns,inventory,shipping,dataquality,notifications,quota,conversion_sources}` |
| [Business Profile](#google-business-profile-api) | My Business API v4 (Business Profile) | `accounts.locations.{create,get,list,batchGet,batchGetReviews,delete,patch,transfer}` + `reviews.get/list/reply`, `posts.{create,get,list,delete,patch}` + `media.{create,get,list,delete,upload}` + `questions.{create,list,delete}` + `attributes.list` |
| [PageSpeed](#pagespeed-insights-api) | PageSpeed Insights API v5 | `runpagespeed` |
| [BigQuery](#bigquery-ga4-export) | GA4 → BigQuery (dataset `analytics_<property_id>`, таблицы `events_YYYYMMDD`, `events_intraday_YYYYMMDD`) | SQL: `SELECT event_name, COUNT(DISTINCT user_pseudo_id) ... FROM ... WHERE _TABLE_SUFFIX BETWEEN ...` |
| [Bing Ads](#microsoft-advertising-bing-ads) | Bing Ads API v13 (SOAP + REST transition) | `CampaignManagementService.AddCampaigns/UpdateCampaigns/DeleteCampaigns`, `AdInsightService.GetKeywordCategories`, `BulkService.Upload`, `ReportingService`, `AdLibraryAPI` |

---

## 🔑 Аутентификация и OAuth — Общий паттерн

Применимо ко всем Google APIs (кроме некоторых специальных случаев):

```python
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow

# 1. Service Account (серверные автоматизации)
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/analytics.edit',
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters',
    'https://www.googleapis.com/auth/indexing',
    'https://www.googleapis.com/auth/devstorage.read_write',  # Merchant
    'https://www.googleapis.com/auth/business.manage',        # Business Profile
    'https://www.googleapis.com/auth/userinfo.profile',
]

credentials = service_account.Credentials.from_service_account_file(
    'service-account.json', scopes=SCOPES)

# 2. OAuth Flow (пользовательские действия в OpenChamber)
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
credentials = flow.run_local_server(port=0)
```

---

## 1. Google Analytics 4 (GA4)

### 1.1 Data API v1beta (Основной API для отчётов)

**Базовый URL:** `https://analyticsdata.googleapis.com`
**Discovery:** `https://analyticsdata.googleapis.com/$discovery/rest?version=v1beta`

| Метод | HTTP | Эндпоинт | Описание | Параметры |
|-------|------|----------|----------|-----------|
| `runReport` | POST | `/v1beta/{property=properties/*}:runReport` | Кастомный отчёт (основной для простых запросов) | `property=properties/123`, `start_date`, `end_date`, `metrics=["activeUsers","sessions","conversions","totalRevenue"]`, `dimensions=["sessionDefaultChannelGroup","deviceCategory","date","hour"]` |
| `batchRunReports` | POST | `/v1beta/{property=properties/*}:batchRunReports` | Пакетный запуск нескольких отчётов | `reports[]` (массив запросов) |
| `runPivotReport` | POST | `/v1beta/{property=properties/*}:runPivotReport` | Сводный (pivot) отчёт | `pivot` объект с `rows[]`, `columns[]`, `metrics[]` |
| `batchRunPivotReports` | POST | `/v1beta/{property=properties/*}:batchRunPivotReports` | Пакетный pivot | `reports[]` |
| `getMetadata` | GET | `/v1beta/{name=properties/*}/metadata` | Метаданные всех доступных метрик и измерений | — |
| `checkCompatibility` | POST | `/v1beta/{property=properties/*}:checkCompatibility` | Проверка совместимости метрик/измерений | `dimensions[]`, `metrics[]` |
| `runRealtimeReport` | POST | `/v1beta/{property=properties/*}:runRealtimeReport` | Реал-тайм отчёт (за 30 мин, или 60 для GA360) | `start_date`, `end_date` относительные |
| `properties.audienceExports` | POST | `/v1beta/{property=properties/*}/audienceExports:run` | Экспорт аудитории (GA4 → BigQuery) | `name`, `runTime` |
| `properties.recurringAudienceLists` | POST | `/v1alpha/{parent=properties/*}/recurringAudienceLists` | Повторяющиеся экспорты аудитории | `name`, `schedule` |
| `runFunnelReport` | POST | `/v1alpha/{property=properties/*}:runFunnelReport` | Воронка (funnel exploration) | `funnel` объект с `funnel_steps[]` |
| `chat` | POST | `/v1alpha/{property=properties/*}:chat` | Chat с Analytics Advisor (LLM) | `message` (натуральный язык) |

**Критические правила:**
- **Property ID**: аргумент всегда в формате `properties/<numeric_id>`. Пример: `property_id="properties/123456789"`
- **Диапазон дат включителен с двух сторон**: `start_date="2026-04-01"` + `end_date="2026-04-30"` = 30 дней.
- **Относительные даты**: `start_date="30daysAgo"`, `end_date="yesterday"` (избегать `today` — неполные данные).
- **Сэмплинг**: при >10M событий GA4 автоматически сэмплирует. Для точных данных использовать **BigQuery**.
- **Ratio метрики не суммируются**: `bounceRate`, `engagementRate`, `conversionRate` — это отношения, не суммируемые значения.

**Полезные метрики (camelCase):**
- `activeUsers`, `newUsers`, `totalUsers`, `sessions`, `screenPageViews`
- `bounceRate`, `engagementRate`, `averageSessionDuration`, `userEngagementDuration`
- `eventCount`, `conversions`, `totalRevenue`, `purchaseRevenue`, `transactions`

**Полезные измерения (dimensions):**
- `date`, `hour`, `sessionDefaultChannelGroup`, `sessionSource`, `sessionMedium`, `sessionCampaignName`
- `country`, `city`, `deviceCategory`, `operatingSystem`, `browser`, `landingPage`, `pagePath`
- `eventName` (для event-level анализа)

### 1.2 Admin API v1alpha / v1beta

| Ресурс | Описание |
|--------|----------|
| `accounts` | Список аккаунтов |
| `properties` | Управление свойствами (GA4 properties) |
| `dataStreams` | Потоки данных (Web, iOS, Android) |
| `keyEvents` (конверсии) | `create/update/delete` — ключевые события = конверсии |
| `customDimensions` | Пользовательские измерения (scope: EVENT, USER) |
| `customMetrics` | Пользовательские метрики |

**Пример создания key event (конверсии):**
```
POST /v1beta/properties/123456789/keyEvents
{
  "event_name": "purchase",
  "counting_method": "ONCE_PER_EVENT"
}
```

### 1.3 Measurement Protocol v2

**Эндпоинт:** `https://www.google-analytics.com/mp/collect`  
**Метод:** POST  
**Content-Type:** `application/json`

**Параметры запроса:**
- `api_secret` (обязателен) — из GA4 Admin → Data Stream → Measurement Protocol
- `measurement_id` (обязателен) — G-XXXXXXXXX
- `client_id` — `user_pseudo_id`

**Payload структура:**
```json
{
  "client_id": "user_12345",
  "events": [{
    "name": "page_view",
    "params": {
      "page_title": "GA4 API Reference",
      "page_location": "https://example.com/ga4"
    }
  }],
  "user_location": {
    "city": "San Francisco",
    "region_id": "US-CA",
    "country_id": "US"
  },
  "consent": {
    "ad_storage": "granted",
    "analytics_storage": "granted"
  }
}
```

---

## 2. Google Tag Manager (GTM)

### 2.1 GTM API v2 — Основные ресурсы

**Базовый URL:** `https://tagmanager.googleapis.com`  
**OAuth scopes:**
- `https://www.googleapis.com/auth/tagmanager.manage.accounts`
- `https://www.googleapis.com/auth/tagmanager.edit.containers`
- `https://www.googleapis.com/auth/tagmanager.readonly`
- `https://www.googleapis.com/auth/tagmanager.edit.containers.versions`
- `https://www.googleapis.com/auth/tagmanager.publish`

| Ресурс | Операции | Ключевые параметры |
|--------|-----------|-------------------|
| `v2/accounts` | `get`, `list`, `update` | `path` = `accounts/{account_id}` |
| `v2/accounts.containers` | `create`, `delete`, `get`, `list`, `update`, `snippet`, `combine` | `parent` = `accounts/{account_id}` |
| `v2/accounts.containers.workspaces` | `manage` (create/update/delete) | `workspace_path` |
| `tags` | `manage` (create/update/revert/delete) | `workspace_path`, `tag_id`, `tag_definition={type, ...}` |
| `triggers` | `manage` | `trigger_definition={filter: [...], type}` |
| `variables` | `manage` | `variable_definition={type, ...}` |
| `built_in_variables` | `manage` | `variable_id`, `variable_definition` |
| `folders` | `manage` | `folder_name` |
| `versions` | `manage`, `publish` | `version_name`, `version_description`, `publish_version` |
| `version_headers` | `manage` | `version_path` |
| `environments` | `manage` | `environment_name`, `environment_type` (LIVE, USER, DEV) |
| `clients` | `manage` | `client_definition={type, ...}` |
| `templates` | `manage` | `template_type` |
| `transformations` | `manage` | `transformation_definition` |
| `zones` | `manage` | `zone_path` |
| `destinations` | `manage` | `destination_path` |

**Иерархия ресурсов (обязательна для понимания):**
```
Account (v2/accounts/{account_id})
  └── Container (v2/accounts/{acc}/containers/{container_id})
        ├── Workspace (v2/accounts/{acc}/containers/{c}/workspaces/{w})
        │     ├── Tags (v2/{path}/tags/{tag})
        │     ├── Triggers (v2/{path}/triggers/{trigger})
        │     ├── Variables (v2/{path}/variables/{variable})
        │     ├── Folders
        │     └── BuiltInVariables
        ├── Versions (v2/{path}/versions/{version})
        │     ├── Headers (v2/{path}/versionHeaders)
        └── Environments (v2/{path}/environments/{env})
```

### 2.2 Жизненный цикл GTM изменений

```python
# 1. Создать workspace
workspace = service.account_management().workspaces().manage(
    operation="create",
    account_id="...",
    container_id="...",
    workspace_id="...",
    workspace_path=f"accounts/.../containers/.../workspaces/{ws_id}").execute()

# 2. Добавить tag / trigger / variable
service.tags().manage(
    operation="create",
    workspace_path=f"accounts/.../containers/.../workspaces/{ws_id}",
    tag_definition={
        "name": "GA4 Page View",
        "type": "gaawc",
        "parameter": [{"name": "measurementId", "value": "G-XXXXXXXX"}],
        "firingTriggerId": ["trigger_id"],
        "tagFiringOption": "ONCE_PER_PAGE"
    }
).execute()

# 3. Создать версию
service.versions().manage(
    operation="create",
    workspace_path=f"accounts/.../containers/.../workspaces/{ws_id}",
    version_name="v3.0 - Purchase Tracking",
    version_description="Added purchase event tracking with enhanced ecommerce"
).execute()

# 4. Опубликовать версию (через UI или версию операции)
```

---

## 3. Google Search Console (GSC)

### 3.1 Search Analytics (Основной API для SEO данных)

**Базовый URL:** `https://www.googleapis.com/webmasters/v3`
**OAuth scopes:** `https://www.googleapis.com/auth/webmasters.readonly`, `https://www.googleapis.com/auth/webmasters`

| Метод | HTTP | Эндпоинт | Описание |
|-------|------|----------|----------|
| `searchanalytics.query` | POST | `/sites/{siteUrl}/searchAnalytics/query` | Поиск трафика (clicks, impressions, ctr, position) |
| `sites.list` | GET | `/sites` | Список проверенных сайтов |
| `sites.get` | GET | `/sites/{siteUrl}` | Информация о сайте |
| `sites.delete` | DELETE | `/sites/{siteUrl}` | Удалить сайт |
| `sitemaps.list` | GET | `/sites/{siteUrl}/sitemaps` | Список sitemap |
| `sitemaps.get` | GET | `/sites/{siteUrl}/sitemaps/{feedpath}` | Информация о sitemap |
| `sitemaps.submit` | PUT | `/sites/{siteUrl}/sitemaps/{feedpath}` | Отправить sitemap |
| `sitemaps.delete` | DELETE | `/sites/{siteUrl}/sitemaps/{feedpath}` | Удалить sitemap |

**Параметры query (searchanalytics):**
```json
{
  "startDate": "2026-09-01",
  "endDate": "2026-09-30",
  "dimensions": ["query", "page", "country", "device", "date"],
  "dimensionFilterGroups": [{
    "filters": [{
      "dimension": "query",
      "operator": "contains",
      "expression": "seo"
    }]
  }],
  "aggregationType": "byProperty",
  "rowLimit": 25000,
  "startRow": 0
}
```

**Ограничения:**
- Результаты сортируются по `clicks` (по убыванию). Одинаковые `clicks` — произвольный порядок.
- API не гарантирует возврат всех строк — это ограничение GSC, не ошибка.
- Для запросов с `date` как dimension — дни без данных пропускаются.
- Для определения всех дней с данными — делайте запрос без фильтров, сгруппированный по `date`.
- Для данных >25 000 строк — инкрементируйте `startRow` для следующего запроса.
- Данные GSC имеют 2-3 дня задержки. Не запрашивайте "вчера" и не ожидайте стабильных цифр.

### 3.2 URL Inspection

**Эндпоинт:** `https://searchconsole.googleapis.com/v3/urls:inspect`

```json
{
  "inspectionUrl": "https://example.com/page",
  "siteUrl": "https://example.com/"
}
```

**Ответ:** `inspectionResult` с `indexStatus` (`VERDICT_UNSPECIFIED`, `PASS`, `FAIL`, `PARTIAL`), `pageFetchState`, `lastCrawlTime`, `googleCanonical`, `referringUrls`, `sitemap`.

---

## 4. Google Ads API v18

### 4.1 GAQL (Google Ads Query Language)

**Базовый URL:** `https://googleads.googleapis.com`  
**Service:** `GoogleAdsService.Search` или `.SearchStream`  
**REST endpoint:** `/v18/customers/{customer_id}/googleAds:search` или `searchStream`

**Структура запроса:**
```sql
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  segments.date,
  metrics.impressions,
  metrics.clicks,
  metrics.conversions,
  metrics.cost_micros,
  metrics.conversions_value
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'PAUSED'
ORDER BY metrics.impressions DESC
LIMIT 100
```

**Критические правила GAQL:**
- **BUDGETS В МИКРОСАХ**: `$50/день` = `50_000_000` микрос. Никогда не передавайте доллары напрямую.
- **Всегда начинайте с PAUSED**: Создавайте кампании с `status="PAUSED"`. Активируйте только после явного подтверждения пользователя.
- **Зависимости при создании**: budget → campaign (PAUSED) → targeting → ad_groups → ads/assets → publish (после подтверждения).
- **Никогда не изобретайте URL, бюджеты или location IDs** — получайте из API.
- **Не объединяйте `ad_group_criterion` с `search_term_view`** в одном запросе.
- **Не запрашивайте >5 sub-accounts в одном batch**.
- **Никогда не объединяйте метрики и сегменты несовместимо** — проверяйте `GoogleAdsFieldService`.

**Основные ресурсы для mutation:**
- `Campaign` (`advertising_channel_type`: SEARCH, DISPLAY, PERFORMANCE_MAX, VIDEO, DEMAND_GEN, SHOPPING, MULTI_CHANNEL)
- `CampaignBudget` (всегда в micros, `amount_micros`)
- `AdGroup` (`type`: SEARCH_STANDARD, DISPLAY_STANDARD, SHOPPING, VIDEO, etc.)
- `AdGroupAd` (text: `expanded_text_ad`, responsive: `responsive_search_ad` / `responsive_display_ad`)
- `AdGroupCriterion` (keyword: `positive` / `negative`, `keyword.text`, `keyword.match_type`)
- `ConversionAction` (`counting_type`: `ONCE_PER_EVENT`, `EVERY_CONVERSION`)
- `UserList` (customer match, remarketing)
- `BiddingStrategy`
- `SharedSet`, `SharedCriterion`
- `CampaignAsset` (для PMax: текст + изображения)

---

## 5. Google Indexing API v3

**Сервис:** `indexing.googleapis.com`  
**OAuth scope:** `https://www.googleapis.com/auth/indexing`

| Метод | REST Endpoint | Описание |
|-------|---------------|----------|
| `PublishUrlNotification` | POST `/v3/urlNotifications:publish` | Уведомить Google об обновлении или удалении URL |
| `GetUrlNotificationMetadata` | GET `/v3/urlNotifications/metadata` | Получить статус уведомлений для URL |

**Тело запроса (publish):**
```json
{
  "url": "https://example.com/new-page",
  "type": "URL_UPDATED"
}
```

Для удаления: `"type": "URL_DELETED"`.

**Batch запросы (до 100 URL в одном HTTP):**
```json
[
  {"url": "https://example.com/a", "type": "URL_UPDATED"},
  {"url": "https://example.com/b", "type": "URL_UPDATED"}
]
```

**Квота:** По умолчанию 200 запросов в день (для тестирования). Для продакшена — запросить approval и увеличение квоты.

**Строгое ограничение:** Indexing API предназначен для страниц с `JobPosting` или `BroadcastEvent` (встроенных в `VideoObject`). Для других страниц — использовать Sitemap + robots.txt + естественное сканирование. Google предупреждает: злоупотребление Indexing API (многократные запросы для обычного контента) может привести к отзыву доступа.

---

## 6. Google Merchant Center (Merchant API v1)

> ⚠️ **ВАЖНО:** Content API for Shopping был sunset 18 августа 2026. С 1 сентября 2026 запросы к Content API v2.1 начинают возвращать прогрессивные ошибки. **Мигрируйте на Merchant API v1**.

**Базовый URL:** `https://merchantapi.googleapis.com`  
**Sub-API:** `accounts`, `products`, `promotions`, `inventories`, `reviews`, `notifications`, `dataquality`, `conversion_sources`

**Основные операции:**
- `accounts.productInputs.insert` / `.delete` / `.update`
- `accounts.promotions.insert` / `.get` / `.delete`
- `accounts.reviews.insert` (вставить отзыв для аккаунта)

**Пример вставки продукта (Merchant API):**
```python
from googleapiclient.discovery import build

service = build('merchant', 'v1', credentials=credentials)
service.accounts().productInputs().insert(
    parent=f"accounts/{merchant_id}",
    body={
        "contentLanguage": "en",
        "feedLabel": "US",
        "channel": "ONLINE",
        "offerId": "book123",
        "title": "A Tale of Two Cities",
        "description": "Classic novel",
        "link": "https://shop.com/book",
        "imageLink": "https://shop.com/book.jpg",
        "availability": "in stock",
        "condition": "new",
        "googleProductCategory": "Media > Books",
        "price": {"value": "2.50", "currency": "USD"}
    }
).execute()
```

---

## 7. Google Business Profile (My Business API v4)

**Базовый URL:** `https://mybusiness.googleapis.com`  
**Service endpoint:** `https://mybusinessbusinessinformation.googleapis.com` (v1)  
**OAuth scopes:** `https://www.googleapis.com/auth/business.manage`

**Ресурсы:**

| Ресурс | Методы | Примечания |
|--------|--------|------------|
| `v4/accounts.locations` | `create`, `get`, `list`, `batchGet`, `patch`, `delete`, `transfer`, `batchGetReviews` | Основная сущность «локация» |
| `v4/accounts.locations.reviews` | `list`, `get`, `updateReply`, `deleteReply` | Отзывы клиентов |
| `v4/accounts.locations.posts` | `create`, `get`, `list`, `delete`, `patch` | Посты (контент) |
| `v4/accounts.locations.media` | `create`, `get`, `list`, `delete`, `patch`, `startUpload` | Медиа-файлы |
| `v4/accounts.locations.questions` | `create`, `get`, `list`, `delete` | Вопросы |
| `v4/accounts.locations.questions.answers` | `get`, `list`, `update`, `delete` | Ответы на вопросы |
| `v1/attributes` | `list` | Доступные атрибуты по категории |
| `v1/accounts.locations` (Business Information) | `create`, `get`, `list`, `patch` | Бизнес-информация |

**Проверка локаций:** Локации с >10 экземплярами требуют индивидуальной или bulk-верификации. Правки верифицированных локаций могут проходить проверку на качество.

---

## 8. PageSpeed Insights API v5

**Базовый URL:** `https://www.googleapis.com/pagespeedonline/v5`  
**OAuth scopes:** `https://www.googleapis.com/auth/userinfo.profile`

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `runpagespeed` | GET `/runPagespeed` | Анализ производительности страницы |

**Обязательные параметры запроса:** `url` (полный URL страницы)  
**Опциональные:** `category` (PERFORMANCE, ACCESSIBILITY, BEST_PRACTICES, SEO, PWA), `locale`, `strategy` (DESKTOP / MOBILE)

**Структура ответа:**
```json
{
  "kind": "pagespeedapi#result",
  "id": "https://example.com/",
  "loadingExperience": {
    "metrics": {
      "FIRST_CONTENTFUL_PAINT_MS": {"percentile": 1200, ...},
      "FIRST_INPUT_DELAY_MS": {"percentile": 80, ...},
      "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2300, ...},
      "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 0.05, ...},
      "INTERACTION_TO_NEXT_PAINT": {"percentile": 150, ...}
    },
    "overall_category": "AVERAGE"
  },
  "originLoadingExperience": { ... },
  "analysisUTCTimestamp": "2026-10-09T12:00:00Z",
  "lighthouseResult": {
    "categories": {
      "performance": {"score": 0.85},
      "accessibility": {"score": 0.92},
      "best-practices": {"score": 0.88},
      "seo": {"score": 0.95},
      "pwa": {"score": 0.7}
    }
  }
}
```

**Core Web Vitals пороги:**
- LCP < 2.5s (Good) / 2.5-4.0s (Needs Improvement) / >4.0s (Poor)
- INP < 200ms / 200-500ms / >500ms
- CLS < 0.1 / 0.1-0.25 / >0.25

---

## 9. BigQuery — GA4 Export Schema

**Dataset pattern:** `project_id.analytics_<property_id>`  
**Таблицы:**
- `events_YYYYMMDD` (ежедневный экспорт, обновляется до 3 дней назад для поздних событий)
- `events_intraday_YYYYMMDD` (стриминг, удаляется в конце дня после завершения `events_`)
- `p_ga4_*` (если включен BigQuery Link с трансформированными таблицами)

**Основная схема `events_` (каждая строка = одно событие):**

| Поле | Тип | Описание |
|------|-----|----------|
| `event_date` | STRING | Дата события (`YYYYMMDD`) |
| `event_timestamp` | INTEGER | Unix timestamp (микросекунды) |
| `event_name` | STRING | Имя события (`page_view`, `purchase`, `first_visit`, etc.) |
| `event_params` | RECORD (REPEATED) | Повторяющийся RECORD с `(key, value{string_value, int_value, float_value, double_value})` |
| `user_pseudo_id` | STRING | Псевдо-ID пользователя |
| `user_first_touch_timestamp` | INTEGER | Время первого взаимодействия |
| `traffic_source` | RECORD | Источник трафика (для событий с трафиком) |
| `device` | RECORD | Устройство (category, operating_system, mobile_model_name, etc.) |
| `geo` | RECORD | География (continent, country, region, city, subcontinent) |
| `ecommerce` | RECORD | E-commerce данные (purchase, transaction_id, value, currency, etc.) |

**Пример запроса (подсчёт событий):**
```sql
SELECT
  event_date,
  event_name,
  COUNT(DISTINCT user_pseudo_id) AS unique_users,
  COUNT(*) AS event_count
FROM `project.analytics_123456789.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20260901' AND '20260930'
GROUP BY event_date, event_name
ORDER BY event_date DESC, event_count DESC
```

**Пример запроса (e-commerce):**
```sql
SELECT
  event_date,
  (SELECT COALESCE(value.int_value, value.float_value) FROM UNNEST(event_params) WHERE key = 'transaction_id') AS transaction_id,
  (SELECT COALESCE(value.int_value, value.float_value) FROM UNNEST(event_params) WHERE key = 'value') AS revenue
FROM `project.analytics_123456789.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20260901' AND '20260930'
  AND event_name = 'purchase'
```

---

## 10. Microsoft Advertising (Bing Ads) API v13

> ⚠️ **Миграция:** Microsoft Advertising переходит с SOAP на REST API. С 1 октября 2026 все новые функции и улучшения будут доступны только через REST API. Существующие SOAP-интеграции продолжат работать в течение 6-месячного окна миграции.

### 10.1 SOAP Services (текущая v13)

**Production URL:** `https://campaign.api.bingads.microsoft.com/CampaignManagement/v13`
**Sandbox URL:** `https://campaign.api.bingads.microsoft.com/CampaignManagement/v13` (для sandbox)

**Namespace:** `https://bingads.microsoft.com/CampaignManagement/v13` (в SOAP header)

**Обязательные SOAP headers:**
- `AuthenticationToken` — OAuth access token
- `CustomerAccountId` — ID аккаунта (customer/account)
- `DeveloperToken` — Developer token
- `CustomerId` (header для MCC / partner access)
- `AccountId` (тело запроса для операций с сущностями аккаунта)

| Service | Операции | Описание |
|---------|----------|----------|
| `CampaignManagementService` | `AddCampaigns`, `GetCampaignsByIds`, `UpdateCampaigns`, `DeleteCampaigns`, `AddAdGroups`, `UpdateAdGroups`, `DeleteAdGroups`, `AddAds`, `UpdateAds`, `DeleteAds` | Управление кампаниями, группами объявлений, объявлениями |
| `AdInsightService` | `GetKeywordCategories`, `GetBidSuggestions`, `GetHistoricalMetrics`, `GetHistoricalSearchCount` | Анализ ключевых слов, ставки, метрики |
| `BulkService` | `Download`, `Upload` (bulk file upload/download) | Массовые операции через CSV/XML файлы |
| `ReportingService` | `SubmitGenerateReport` (все отчёты API) | Генерация отчётов (CampaignPerformance, AdPerformance, etc.) |
| `CustomerManagementService` | `GetUser` (получить User с ID), `UpdateCustomer` | Управление пользователями |

**REST API (новое):**
`https://adlibrary.api.bingads.microsoft.com/api/v1/` (Ad Library — публичный инструмент прозрачности)
- `GET /Advertisers` — поиск рекламодателей по имени
- `GET /Advertisers/{AdvertiserId}` — рекламодатель по ID
- `GET /Ads` — объявления по рекламодателю

---

## 📊 AEO (Answer Engine Optimization) — Для AI Overviews и LLM Visibility

### Принципы AEO vs SEO

| Параметр | SEO (традиционный) | AEO (AI-ответы) |
|----------|-------------------|-----------------|
| **Оптимизируем для** | Позиции в поиске (клики) | Цитирования в LLM-ответах |
| **Успех** | Позиция 1-10, органический трафик | Количество цитирований в ChatGPT, Perplexity, Claude, Gemini |
| **Ключевые сигналы** | Backlinks, ключевые слова, скорость | E-E-A-T, structured data, factual density, первоисточники |
| **Обновление** | Недели-месяцы | Дни-недели (LLM training cycles) |

### Как контент попадает в AI Overviews

Google AI Overviews выбирают источники через:
1. **Query fan-out** — множественные связанные запросы через LLM (Gemini)
2. **Retrieval из индекса Google** + Knowledge Graph + Shopping Graph
3. **Re-ranking** — по E-E-A-T, topical authority, clarity, factual density
4. **Цитирование** — ссылки в сгенерированном ответе (часто с фрагментом текста)

**Нет дополнительных технических требований** для AI Overviews. Достаточно:
- Быть проиндексированным в Google (`robots.txt` разрешает сканирование)
- Быть eligible для snippet (`noindex` отсутствует, контент доступен)
- Иметь **structured data**, соответствующее видимому тексту
- Иметь **высокую factual density** (верифицируемые утверждения на 1000 слов)
- Иметь **E-E-A-T сигналы** (автор с биографией, первоисточники, даты публикации/обновления)

### Schema для AI Overviews (из `references/schema-types-guide.md`)

```json
{
  "@context": "https://schema.org",
  "@type": ["Article", "FAQPage"],
  "headline": "How to Optimize for AI Overviews",
  "author": {
    "@type": "Person",
    "name": "Dr. Jane Smith",
    "sameAs": ["https://linkedin.com/in/janesmith", "https://scholar.google.com/citations?user=..."]
  },
  "datePublished": "2026-04-15",
  "dateModified": "2026-09-22",
  "publisher": {
    "@type": "Organization",
    "name": "Your Company",
    "logo": {"@type": "ImageObject", "url": "https://example.com/logo.png"},
    "sameAs": ["https://twitter.com/yourco", "https://github.com/yourco"]
  },
  "mainEntity": {
    "@type": "FAQPage",
    "mainEntity": [
      {"@type": "Question", "name": "What are AI Overviews?", "acceptedAnswer": {"@type": "Answer", "text": "AI Overviews are AI-generated summaries..."}},
      {"@type": "Question", "name": "How do I appear in AI Overviews?", "acceptedAnswer": {"@type": "Answer", "text": "Follow SEO best practices, add structured data..."}}
    ]
  }
}
```

---

## 📁 Структура этого документа в Wiki DB

После запуска `scripts/init_db.py`:

| Таблица | Что хранит | Пример строки |
|--------|-----------|---------------|
| `api_docs` | Полная документация каждого источника | `source='ga4', category='rest', title='Data API v1beta runReport'` |
| `api_endpoints` | Каждый эндпоинт API | `method='POST', path='/v1beta/properties/*:runReport'` |
| `schemas` | JSON-LD, BigQuery, GAQL схемы | `schema_type='json_ld', name='Article', definition={...}` |
| `guides` | Руководства по настройке/оптимизации | `guide_type='setup', title='GA4 Tracking Plan'` |
| `change_log` | История изменений документации | `change_type='updated', field_changed='version', new_value='v1beta'` |
| `sync_runs` | Логи автоматических обновлений | `run_type='full', status='completed', docs_processed=847` |
| `embeddings` | Векторные эмбеддинги для поиска | `chroma_id='api-doc-001-chunk-3'` |
| `aeo_citations` | Цитирования в LLM-ответах | `llm='perplexity', query='how to optimize for AI overviews'` |
| `aeo_audits` | Результаты AEO-аудитов | `composite_score=72, experience_score=80` |

---

## 🔧 Как обновлять этот документ автоматически

```bash
# Полный ресинк всех источников (би-недельно по cron: 0 2 */14 * *)
python3 scripts/sync_wiki.py --full

# Инкрементальный sync (только изменённые документы)
python3 scripts/sync_wiki.py --incremental --sources ga4,gtm,gsc

# Обновление конкретного источника
python3 scripts/sync_wiki.py --source ga4 --category rest

# Проверка свежести
sqlite3 data/wiki.db "SELECT source, MAX(last_updated) FROM api_docs GROUP BY source;"
```

---

## 📚 Связанные навыки (Skills) в проекте

- `seo-research-hyperfx` — SEO-исследования через HyperSEO
- `seo-audit-mia` — Технический SEO-аудит (включая hreflang, canonical, schema)
- `analytics-insights-hyperfx` — GA4, GTM, GSC, BigQuery через Hyper MCP
- `google-ads-hyperfx` — Google Ads через Hyper MCP
- `programmatic-seo-alireza` — Программное SEO в масштабе
- `schema-markup-alireza` — Schema.org реализация
- `site-architecture-alireza` — Архитектура сайта и внутренние ссылки
- `aeo-alireza` — AEO (AI Overviews, LLM citations, E-E-A-T)
- `deep-research-alireza` — Методология глубоких исследований
- `universal-scraping-architect-alireza` — Скрейпинг документации API

---

> Документ сгенерирован автоматически на основе официальной документации Google, Microsoft Learn, и референсов Hyper MCP. Для проверки актуальности запустите `python3 scripts/sync_wiki.py --check-freshness`.
