# ADR-003: Идентичность эндпоинта = (resource, method_name)

- **Статус:** принято
- **Дата:** 2026-10-12
- **Решает:** как однозначно идентифицировать метод API в БД

## Контекст

Google описывает маршруты **шаблонами**, а не конкретными путями.
Например, в GA4 Admin API 35 разных методов имеют ОДИНАКОВЫЙ path
`v1alpha/{+name}`:

- `properties.get`
- `properties.keyEvents.get`
- `properties.dataStreams.patch`
- `accounts.accessBindings.delete`

Различаются они только по **ресурсу** (`properties.keyEvents` и т.д.).

## Решение

Уникальность эндпоинта = `(doc_id, resource, method_name)`.

```sql
UNIQUE(doc_id, resource, method_name)
```

А не `(doc_id, method, path)`.

## Обоснование

Изначально было `UNIQUE(doc_id, method, path)`. **Измерено 2026-10-12:**
312 методов сворачивались в 162 уникальные пары — **терялось 150 эндпоинтов**
(48%).

Конкретный путь получается подстановкой шаблона:

```
v1alpha/{+name}  +  properties/{propertyId}/keyEvents/{keyEventId}
        ↓
v1alpha/properties/123/keyEvents/456
```

Шаблон без ресурса не является идентификатором метода — это паттерн,
общий для десятков методов.

## Реализация

- `scripts/sync_wiki.py::extract_methods()` — рекурсивный обход дерева
  ресурсов, каждый узел получает полный путь `accounts.containers.workspaces.tags`
- `scripts/init_db.py::migrate_to_v2()` — идемпотентная миграция схемы
- `scripts/wiki_query.py collisions` — показывает шаблоны с несколькими
  ресурсами (диагностика)

## Последствия

**Плюсы**
- Ни один эндпоинт не теряется при синхронизации
- Можно спрашивать «все методы ресурса X»
- `collisions` показывает, где шаблоны разделяются

**Минусы**
- Полный путь ресурса нужно строить рекурсивно (был баг: рекурсия была
  условной, терялось 103 из 106 методов GTM)
- Схема сложнее: нужен `resource` отдельной колонкой

## Связанное

- [ADR-001](ADR-001-sqlite-and-fts5.md)
- `docs/architecture.md` §3 — path-шаблоны Google
