# Google SEO Automation

Автоматизация Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads и AI-ответов (AI Overviews / AEO) поверх **внутренней вики-базы**,
которая сама обновляется из официальных машиночитаемых источников Google.

> Статус: инфраструктура знаний работает. Интеграции GA4/GTM/GSC/Ads — в очереди.

---

## Что уже работает

- **312 эндпоинтов** из 7 Google Discovery-документов, автоматически
- **Полнотекстовый поиск** по вики (SQLite FTS5), без внешних зависимостей
- **Детект изменений** по SHA256 + журнал `change_log`
- **Проверка свежести** с порогом 14 дней
- **16 тестов**, закрывающих 4 реально найденных бага
- **7 агентов** с явными контрактами ввода-вывода

## Быстрый старт

```bash
cd project

# 1. Проверить окружение и установить зависимости
./init.sh

# 2. Создать/обновить схему БД (идемпотентно, с миграциями)
python scripts/init_db.py

# 3. Забрать свежую документацию из Google
python scripts/sync_wiki.py --full

# 4. Проверить, что всё актуально
python scripts/sync_wiki.py --check-freshness
```

> `sync_wiki.py` и `wiki_query.py` работают **на стандартной библиотеке Python 3.10+**.
> `pip install` не требуется, чтобы читать вики. Остальные зависимости — для
> будущих интеграций (см. `requirements.txt`).

## Использование вики

```bash
python scripts/wiki_query.py stats                      # сводка
python scripts/wiki_query.py endpoints --source gtm     # эндпоинты источника
python scripts/wiki_query.py search "workspace tag"     # полнотекстовый поиск
python scripts/wiki_query.py endpoint workspaces.tags.create
python scripts/wiki_query.py collisions --source ga4_admin  # где совпадают шаблоны
python scripts/wiki_query.py changes --limit 10         # что менялось
```

## Источники

| Источник | Эндпоинтов |
|---------|-----------|
| Google Analytics Admin API v1alpha | 166 |
| Google Tag Manager API v2 | 106 |
| Google Business Profile API v1 | 15 |
| Google Analytics Data API v1beta | 11 |
| Google Search Console API v1 | 11 |
| Google Indexing API v3 | 2 |
| PageSpeed Insights API v5 | 1 |
| **Итого** | **312** |

Полный разбор, включая неработающие URL и пробелы покрытия —
[`docs/architecture.md`](docs/architecture.md).

## Расписание

```bash
# Вики — раз в 14 дней
0 2 */14 * *  python scripts/sync_wiki.py --full

# Свежесть — ежедневно (чтобы узнать о просрочке сразу)
0 3 * * *     python scripts/sync_wiki.py --check-freshness
```

## Структура

```
project/
├── wiki/                  markdown-источник знаний (коммитится)
├── data/wiki.db           SQLite: docs, endpoints, changelog, FTS5 (не коммитится)
├── scripts/
│   ├── init_db.py         схема + идемпотентные миграции
│   ├── sync_wiki.py       забор discovery + ингест markdown + freshness
│   └── wiki_query.py      CLI-поиск по вики
├── tests/                 регрессионные тесты
├── docs/architecture.md   измеренные факты, риски, пробелы
├── .opencode/agents/      7 агентов
├── feature_list.json      11 фич, ни одна не passes без verifier
├── AGENTS.md              маршрутизация по агентам
└── init.sh                проверка окружения
```

## Агенты

| Агент | Роль | Модель |
|-------|------|--------|
| `explorer` | read-only разведка | дешёвая |
| `runner` | шумные команды, только сводка | дешёвая |
| `verifier` | **обязателен** перед `passes: true` | дешёвая |
| `critic` | адверсариальное ревью | сильная |
| `migrator` | массовые механические правки | дешёвая |
| `implementer` | реализация одной фичи | сильная |
| `orchestrator` | OpenChamber-сессии и расписание | дешёвая |

## Безопасность

- `.env` в `.gitignore`, шаблон — `.env.example`
- Секреты только из окружения, никогда не в коде и не в логах
- Операции с мутациями по умолчанию dry-run (`ALLOW_MUTATIONS=0`)
- Бюджеты Google Ads — в микросах, с лимитом `ADS_MAX_MUTATION_MICROS`
- БД в `.gitignore` — это кэш, он пересоздаётся из источников

## Лицензия

MIT