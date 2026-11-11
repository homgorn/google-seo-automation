# ROADMAP — Google SEO Automation

> Living document. Обновляется при закрытии чанка.
> Текущая стадия: **v0.1.0 — инфраструктура знаний готова, интеграции заблокированы на credentials**

---

## Стадии проекта

| Стадия | Статус | Содержимое | Дата |
|--------|--------|------------|------|
| **S0. Spec** | ✅ | SPEC-001, ADR-001..004, feature_list с acceptance criteria | 2026-11-11 |
| **S1. Knowledge base** | ✅ | Вики, 312 эндпоинтов, FTS5, граф знаний, индексы | 2026-10-12 |
| **S2. Tooling** | ✅ | 7 скриптов + common.py, 116 тестов, verify_feature | 2026-11-11 |
| **S3. Code review** | ✅ | 3 независимых ревью, 12 дефектов закрыты | 2026-11-11 |
| **S4. Live integrations** | ⏸ | GA4/GTM/GSC/Ads/Bing — нужен `.env` | — |
| **S5. Production hardening** | 🔲 | Мониторинг, алерты, cost caps, DR-тест | — |
| **S6. Release** | 🔲 | Теги, releases, Pages | — |

---

## Ближайшие шаги (по приоритету)

### Блокер 1 — credentials (нужно от владельца)

| # | Что нужно | Разблокирует |
|---|-----------|---------------|
| 1 | `GOOGLE_APPLICATION_CREDENTIALS` **или** `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` | F003 GA4 |
| 2 | `GSC_SITE_URL` | F005 GSC |
| 3 | `GOOGLE_ADS_DEVELOPER_TOKEN` + `GOOGLE_ADS_CUSTOMER_ID` | F006 Ads |

> Оба auth-метода GA4 поддержаны: `--auth-method service_account` и
> `--auth-method oauth`. Выбор — за владельцем.

### Блокер 2 — решения по покрытию

| # | Вопрос | Рекомендация |
|---|--------|--------------|
| 4 | Merchant API: proto-файлы или ручной markdown? | Proto из `googleapis` — надёжнее, требует protobuf-парсер |
| 5 | Bing Ads v13: SOAP или REST? | REST (SOAP уходит с 2026-10-01) |
| 6 | AEO: нужны ли реальные LLM-вызовы для трекинга цитат? | Да, но через API-ключи Anthropic/OpenAI |

---

## Следующие 3 чанка (после разблокировки)

### Чанк G — F003 GA4: живые вызовы
- [ ] `properties.list` по аккаунту
- [ ] `runReport` с реальными метриками/измерениями
- [ ] Создание custom dimension + key event
- [ ] BigQuery export: проверка связи `analytics_{id}`
- [ ] Тесты с моками HTTP

### Чанк H — F005 GSC: живые вызовы
- [ ] `searchanalytics.query` за 30 дней (с учётом лага 2-3 дня)
- [ ] `sitemaps.submit` + проверка статуса
- [ ] `urls:inspect` для 10 ключевых URL
- [ ] Indexing API: publish с учётом квоты 200/день
- [ ] Дашборд + алерты на падение индексации

### Чанк I — F006 Ads: живые вызовы
- [ ] GAQL: отчёт по кампаниям
- [ ] Поисковые запросы → negative keywords (с dry-run по умолчанию)
- [ ] Создание бюджета → кампании (PAUSED) → ad group → ad
- [ ] Верификация GAQL перед активацией
- [ ] Cost cap через `ADS_MAX_MUTATION_MICROS`

---

## Долгосрочно (S5-S6)

| Пункт | Описание | Приоритет |
|-------|----------|-----------|
| Мониторинг квот | Отслеживание API quota, алерт при >80% | High |
| Cost monitoring | BigQuery + API + Ads — бюджетные алерты | High |
| DR-тест | Регулярная проверка восстановления из `wiki.db` | Medium |
| Retention policy | Сколько хранить `aeo_citations`, `change_log` | Medium |
| IAM least-privilege | Отдельный service account на фичу | Medium |
| Dependency audit | `pip-audit` в CI | Medium |
| Semantic embeddings | Реальные эмбеддинги вместо FTS5 | Low |
| Merchant proto parser | Захват методов из proto | Low |
| Bing Ads REST | Полная поддержка REST API | Low |

---

## Известные пробелы покрытия (не скрыты)

| Пробел | Причина | Обходной путь |
|--------|---------|---------------|
| Merchant API — 0 эндпоинтов | Google не публикует discovery-методы | Proto-файлы |
| Bing Ads v13 — нет discovery | SOAP → REST миграция | Ручная спецификация |
| Google Ads v18 — нет discovery | GAQL только из документации | Словарь полей вручную |
| Embeddings — только FTS5 | chromadb не установлен | `USE_LOCAL_EMBEDDINGS=true` + установка |
| Feature steps не покрыты (5 из 39) | Часть шагов требуют живых API | Планируется в чанках G-I |

---

## Правила ведения

1. Чанк закрыт → строка в `docs/progress.md` + обновление этой таблицы
2. Фича `passes: true` выставляет **только** verifier
3. Каждое решение, меняющее архитектуру → ADR
4. Каждый новый скрипт → тест в `tests/`
5. Пробел покрытия либо закрывается, либо фиксируется здесь
