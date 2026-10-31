# OpenChamber Session Template — Chunk B: F002 Embeddings + Semantic Search

## Feature
F002 — Semantic search over internal LLM wiki (ChromaDB + embeddings)

## Context
DB: `data/wiki.db` (FTS5); `scripts/embed_wiki.py`; `data/chroma/` (vector store)
Wiki docs: 9 (см. `wiki_query.py stats`)
Dependencies: `chromadb`, `sentence-transformers` (optional; graceful fallback)

## Verifier Checklist

- [ ] `python scripts/embed_wiki.py --full --dry-run` → PASS (9 документов, 0 ошибок)
- [ ] `python scripts/embed_wiki.py --search "analytics" --limit 3` → находит `ga4_data` или `ga4_admin`
- [ ] Если `chromadb` НЕ установлен → скрипт НЕ падает, выводит `FALLBACK_NO_CHROMA`
- [ ] `data/chroma/` существует (создан или готов к созданию)

## Artifacts
- `scripts/embed_wiki.py`
- `requirements.txt` (chromadb, sentence-transformers добавлены)
- `docs/architecture.md` — раздел о пробелах покрытия
