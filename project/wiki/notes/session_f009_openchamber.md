# OpenChamber Session Template — Chunk C: F009 OpenChamber Sync

## Feature
F009 — Bi-directional wiki ↔ OpenChamber session synchronization

## Context
Script: `scripts/openchamber_sync.py`
Directions: `wiki_to_oc` (push findings) | `oc_to_wiki` (pull decisions) | `status` (read)
Notes dir: `wiki/notes/`

## Verifier Checklist

- [ ] `python scripts/openchamber_sync.py --status` → PASS (таблица источников + свежесть)
- [ ] `python scripts/openchamber_sync.py --direction wiki_to_oc` → PASS (не падает)
- [ ] `python scripts/openchamber_sync.py --direction oc_to_wiki` → PASS (создаёт/обновляет `wiki/notes/sync_oc_to_wiki.md`)
- [ ] `wiki/notes/session_f005_gsc.md` и `session_f002_embeddings.md` существуют
- [ ] Нет блокеров на стороне OpenChamber (API ключ или проект ID)

## Dependencies
- `OPENCHAMBER_API_KEY` или `.env` с ключом
- `openchamber_sync.py` — UTF-8 исправлен (`reconfigure`)

## Artifacts
- `scripts/openchamber_sync.py`
- `wiki/notes/session_f005_gsc.md`
- `wiki/notes/session_f002_embeddings.md`
- `wiki/notes/sync_oc_to_wiki.md` (генерируется при `--direction oc_to_wiki`)
