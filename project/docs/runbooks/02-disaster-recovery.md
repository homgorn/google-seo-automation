# Runbook 2: Disaster Recovery

## Purpose
Recover from data loss, corruption, or service outage.

## Scenario 1: Database corruption (wiki.db)

### Symptoms
- `sqlite3 data/wiki.db` returns "database disk image is malformed"
- `wiki_query.py stats` crashes

### Recovery
```bash
# 1. Delete corrupted DB (it's a cache, fully regenerable)
rm data/wiki.db

# 2. Recreate schema
python scripts/init_db.py

# 3. Repopulate from discovery
python scripts/sync_wiki.py --full

# 4. Verify
python scripts/wiki_query.py stats
python scripts/sync_wiki.py --check-freshness
```

**Time to recover:** ~2-3 minutes (network-dependent)
**Data loss:** None (DB is derived from sources)

## Scenario 2: Lost .env / credentials

### Symptoms
- All API calls return 401/403
- `init.sh` reports missing env vars

### Recovery
```bash
# 1. Restore from backup
cp .env.backup .env

# 2. If no backup, recreate from template
cp .env.example .env
# Fill in values manually

# 3. Test
python scripts/sync_wiki.py --check-freshness
```

## Scenario 3: Git history corruption

### Symptoms
- `git status` shows unexpected changes
- `git log` shows wrong commits

### Recovery
```bash
# 1. Fetch from remote
git fetch origin
git reset --hard origin/master

# 2. Re-run tests
python -m pytest tests/ -q

# 3. Re-sync wiki
python scripts/sync_wiki.py --full
```

## Scenario 4: API quota exhaustion

### Symptoms
- `sync_wiki.py` returns HTTP 429
- `sync_runs` shows status="failed"

### Recovery
```bash
# 1. Check which source failed
sqlite3 data/wiki.db "SELECT source, status, errors FROM sync_runs ORDER BY id DESC LIMIT 5"

# 2. Wait for quota reset (Google: 24h for daily quotas)
# 3. Retry with longer delay
python scripts/sync_wiki.py --full  # already has time.sleep(0.4) between sources

# 4. If persistent, reduce sources
python scripts/sync_wiki.py --source ga4_data --source gtm  # only critical sources
```

## Scenario 5: Python environment broken

### Symptoms
- `python` not found or wrong version
- `pip install` fails

### Recovery
```bash
# 1. Recreate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify
python scripts/init_db.py
python scripts/sync_wiki.py --check-freshness
```

## Verification
- [ ] DB recreated from sources (312 endpoints)
- [ ] All non-blocked features PASS
- [ ] `.env` restored with valid credentials
- [ ] Git history clean
- [ ] No data loss
