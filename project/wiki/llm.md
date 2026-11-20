# LLM Wiki — структурированная вики LLM-субсистемы

Все описания LLM-скриптов, фич (F001–F015), ресёрч-статьи и семантическая БД.

- [`wiki/llm/README.md`](llm/README.md) — главный обзор: статусы фич, описания скриптов
- [`wiki/llm/index.md`](llm/index.md) — индекс: все страницы + ресёрч
- [`wiki/llm/research/webdev-cwv-thresholds.md`](llm/research/webdev-cwv-thresholds.md) — web.dev ресёрч: thresholds + definitions (LCP/CLS/INP/FCP)

## Семантическая БД — `data/llm_knowledge.db`

Таблицы: `entities` (27), `ontology` (26), `triples`, `edges` (10), `feature_metrics` (F013/F015).

```
python scripts/query_llm_graph.py --subject feature:F015
python scripts/query_llm_graph.py --predicate enforces
python scripts/query_llm_graph.py --query "cwv"
```
