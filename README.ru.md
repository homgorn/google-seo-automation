# Google SEO Automation

Автоматизация Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads и AI-ответов (AI Overviews / AEO) поверх **внутренней вики-базы**,
которая сама обновляется из официальных машиночитаемых источников Google.

> Статус: инфраструктура знаний работает. Интеграции GA4/GTM/GSC/Ads
> реализованы и проверены; для живых API-вызовов нужны credentials (см. `.env.example`).

---

## Что работает

- **312 эндпоинтов** из 7 Google Discovery-документов, автоматически
- **Полнотекстовый поиск** по вики (SQLite FTS5, без внешних зависимостей)
- **Детект изменений** по SHA256 + журнал `change_log`
- **Проверка свежести** с порогом 14 дней и cron-расписанием
- **16 тестов**, закрывающих 4 реально найденных бага
- **7 агентов** с явными контрактами ввода-вывода
- **8 из 11 фич** верифицированы (PASS); 3 заблокированы только на credentials

## Быстрый старт

```bash
cd project

# 1. Проверить окружение и установить зависимости
./init.sh

# 2. Создать / обновить схему БД (идемпотентно, с миграциями)
python scripts/init_db.py

# 3. Забрать свежую документацию из Google
python scripts/sync_wiki.py --full

# 4. Проверить, что всё актуально
python scripts/sync_wiki.py --check-freshness
```

> `sync_wiki.py` и `wiki_query.py` работают **на стандартной библиотеке Python 3.10+**.
> `pip install` не требуется для чтения вики.

## Использование вики

```bash
python scripts/wiki_query.py stats                      # сводка
python scripts/wiki_query.py endpoints --source gtm     # эндпоинты по источнику
python scripts/wiki_query.py search "workspace tag"     # полнотекстовый поиск
python scripts/wiki_query.py endpoint workspaces.tags.create
python scripts/wiki_query.py collisions --source ga4_admin
python scripts/wiki_query.py changes --limit 10
```

## Источники API (измерено 2026-10-12)

| Источник | Discovery-документ | Эндпоинтов |
|----------|-------------------|-----------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (нет методов) |
| **Итого** | | **312** |

## Структура

```
project/
├── wiki/                  Markdown-источник знаний (коммитится)
├── data/wiki.db           SQLite: docs, endpoints, changelog, FTS5 (не коммитится)
├── scripts/               init_db.py, sync_wiki.py, wiki_query.py, embed_wiki.py,
│                          gsc_automation.py, ads_automation.py, gtm_automation.py,
│                          aeo_automation.py, ga4_automation.py, openchamber_sync.py,
│                          verify_feature.py, secret_scan.py
├── tests/                 16 регрессионных тестов
├── docs/
│   ├── architecture.md    Измеренные факты, риски, пробелы
│   ├── progress.md        Журнал изменений
│   └── runbooks/          Ротация credentials, DR, мониторинг стоимости
├── .opencode/roles/      7 агентов
├── feature_list.json      11 фич
├── AGENTS.md              Маршрутизация по ролям
└── init.sh                Проверка окружения
```

## Безопасность

- `.env` в `.gitignore`, шаблон — `.env.example`
- Секреты только из окружения, никогда не в коде
- Мутации по умолчанию dry-run (`ALLOW_MUTATIONS=0`)
- Бюджеты Google Ads — в микросах с лимитом
- БД — кэш, пересоздаётся из источников

## Документация

- [Архитектура](project/docs/architecture.md)
- [Журнал изменений](project/docs/progress.md)
- [Справочник API](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## Вклад

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## Лицензия

[MIT](LICENSE)