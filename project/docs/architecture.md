# Архитектура проекта: Google SEO Automation

> Документ фиксирует **измеренные** факты о состоянии источников на 2026-10-12.
> Каждое утверждение помечено provenance: `[измерено]`, `[документация]`, `[выведено]`.

---

## 1. Текущее состояние (status)

| Компонент | Состояние | Файлы |
|-----------|-----------|-------|
| Вики-база (SQLite + FTS5) | ✅ работает | `scripts/init_db.py`, `scripts/sync_wiki.py`, `scripts/wiki_query.py` |
| Синхронизация discovery | ✅ работает, 8 источников | `scripts/sync_wiki.py` |
| Агенты (7 ролей) | ✅ описаны | `.opencode/agents/*.md` |
| Тесты | ✅ 16 passed | `tests/test_sync_wiki.py` |
| Интеграции GA4/GTM/GSC/Ads/Bing | ❌ не начаты | F003–F007 |
| OpenChamber-синхронизация | ❌ не начата | F009 |
| Эмбеддинги/семантический поиск | ❌ не начат | F002 (частично) |

---

## 2. Измеренная таблица источников `[измерено 2026-10-12]`

Проверено двумя независимыми способами: проба URL скриптом-зондом и фактический прогон `sync_wiki.py --full`.

| Источник | Рабочий discovery URL | Эндпоинтов | rev |
|---------|----------------------|-----------|-----|
| Google Analytics Data v1beta | `analyticsdata.googleapis.com/$discovery/rest?version=v1beta` | 11 | 20261007 |
| Google Analytics Admin v1alpha | `analyticsadmin.googleapis.com/$discovery/rest?version=v1alpha` | **166** | 20261007 |
| Google Tag Manager v2 | `tagmanager.googleapis.com/$discovery/rest?version=v2` | **106** | 20261007 |
| Google Search Console v1 | `searchconsole.googleapis.com/$discovery/rest?version=v1` | 11 | 20261010 |
| Google Indexing v3 | `indexing.googleapis.com/$discovery/rest?version=v3` | 2 | 20261007 |
| PageSpeed Insights v5 | `www.googleapis.com/discovery/v1/apis/pagespeedonline/v5/rest` | 1 | 20261007 |
| Business Profile (Business Info) v1 | `mybusinessbusinessinformation.googleapis.com/$discovery/rest?version=v1` | 15 | 20261007 |
| Google Merchant v1 | `merchantapi.googleapis.com/$discovery/rest?version=v1` | **0** | 20261006 |
| **ИТОГО** | | **312** | |

### 2.1 Неработающие URL `[измерено]`

| URL | Ответ | Вердикт |
|-----|-------|---------|
| `www.googleapis.com/discovery/v1/apis/webmasters/v3/rest` | 404 | ✗ не существует |
| `www.googleapis.com/webmasters/v3/$discovery/rest` | 404 | ✗ не существует |
| `mybusiness.googleapis.com/$discovery/rest?version=v4` | 404 | ✗ v4 недоступен через discovery |
| `www.googleapis.com/pagespeedonline/v5/$discovery/rest` | 404 | ✗ только через общий каталог |

### 2.2 Merchant API — отдельная проблема `[измерено]`

Discovery-документ существует (revision 20261006), но:
- `resources` = **пустой объект**
- `schemas` содержит только `ProductChange` и `ProductStatusChangeMessage`
- методов ноль

**Вывод `[выведено]`:** Google не публикует discovery для Merchant API v1. Поэтому
автоматический захват методов оттуда невозможен. Варианты для F010 (Merchant):
1. Proto-файлы из `github.com/googleapis/googleapis` (`google/shopping/merchant/v1/*.proto`) — надёжно, но нужен protobuf-парсер;
2. HTML-парсинг `developers.google.com/merchant/api/reference/rest` — хрупко;
3. Ручная выгрузка из документации с ревью.

Рекомендация: вариант 1. Зафиксировано как `known_empty: True` в конфиге и защищено тестом `test_known_empty_merchant_is_flagged`.

---

## 3. Ключевая особенность Google API: path-шаблоны `[измерено]`

Google описывает маршруты **шаблонами**, а не конкретными путями.

Пример — 35 разных методов GA4 Admin имеют **одинаковый** path `v1alpha/{+name}`:
`properties.get`, `properties.keyEvents.get`, `properties.audiences.get`,
`accounts.dataStreams.patch`, `properties.bigQueryLinks.delete` …

Различить их можно только по `resource`.

### Следствие для схемы БД

```sql
-- ❌ БЫЛО (схлопывало 312 методов в 162, терялось 150)
UNIQUE(doc_id, method, path)

-- ✅ СТАЛО
UNIQUE(doc_id, resource, method_name)
```

Конкретный маршрут получается подстановкой: `v1alpha/{+name}` + `properties/{propertyId}/keyEvents/{keyEventId}`.

Миграция идемпотентная: `scripts/init_db.py::migrate_to_v2`. Данные `api_endpoints` —
производный кэш, он целиком восстанавливается из discovery, поэтому пересоздание
таблицы не приводит к потере информации.

Проверка: `python scripts/wiki_query.py collisions --source ga4_admin`

---

## 4. Слои системы

```
┌─────────────────────────────────────────────────────────────┐
│  L4. Потребление: агенты, OpenChamber-сессии, CLI (wiki_query)│
├─────────────────────────────────────────────────────────────┤
│  L3. Автоматизации: GA4, GTM, GSC, Ads, Bing, AEO  [F003–F008]│
├─────────────────────────────────────────────────────────────┤
│  L2. Знание: SQLite (docs/endpoints/schemas/guides) + FTS5   │
│               + changelog + freshness            [F001,F002] │
├─────────────────────────────────────────────────────────────┤
│  L1. Источники: Google Discovery, локальные wiki/*.md        │
└─────────────────────────────────────────────────────────────┘
```

**Правило зависимостей:** L3 может читать L2, но никогда не ходит в сеть напрямую
за документацией. Все сетевые обращения к документации — только через `sync_wiki.py`.
Это даёт: одну точку отказа, один журнал изменений, один счётчик свежести.

---

## 5. Контур качества

| Гейт | Кто | Что проверяет | Как запустить |
|------|-----|---------------|---------------|
| 1. Юнит | `runner` | чистая логика, регрессии | `pytest tests/ -q` |
| 2. Сеть | `runner` | источники живы, счётчики сошлись | `sync_wiki.py --full` + сверка с таблицей §2 |
| 3. Верификация | `verifier` | фича работает end-to-end, шаги из feature_list | вручную по `steps` |
| 4. Ревью | `critic` | слепые зоны, premise, blast radius | 2–3 агента параллельно |

`passes: true` в `feature_list.json` проставляет **только** `verifier`.

---

## 6. Известные риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Google сменит discovery-схему | Низкая | Высокое | `revision` в БД; алерт при смене; тесты на структуру |
| Merchant API не покрыт автоматически | **Факт** | Среднее | proto-источник (F010) |
| Квота API исчерпана | Средняя | Среднее | `sync_runs` логирует; считать днём, а не в реальном времени |
| Rate limit при bi-weekly sync | Низкая | Низкое | `time.sleep(0.4)` между источниками |
| Вики устарела | Средняя | Высокое | `--check-freshness` + cron раз в 14 дней |
| Windows cp1252 ломает вывод | **Было, исправлено** | Низкое | `reconfigure(encoding="utf-8")` в каждом скрипте |

---

## 7. Что НЕ измерено (честно)

- **GA4 Data API Admin v1beta** vs v1alpha — использована v1alpha (166 методов). v1beta может содержать больше.
- **Google Ads API v18** — **нет discovery-документа** в стандартном виде; GAQL и ресурсы берутся из proto и документации. Не покрыто автоматическим захватом. Аналог проблемы Merchant.
- **Bing Ads API v13** — SOAP + миграция на REST; discovery отсутствует. Требует отдельного подхода.
- **BigQuery GA4 export** — схема задокументирована в вики вручную, автоматический захват схемы не реализован.

Эти три пункта — кандидаты на отдельные задачи (F010a/b/c).