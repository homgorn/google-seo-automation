# Runbook 3: Cost Monitoring

## Purpose
Monitor and control costs for Google Cloud APIs, BigQuery, and OpenChamber.

## Cost Sources

| Service | Cost Driver | Typical Monthly | Alert Threshold |
|---------|------------|-----------------|-----------------|
| Google Cloud (APIs) | API calls, compute | $0-50 | >$50/day |
| BigQuery | Query bytes processed | $5-50 | >$100/month |
| OpenChamber | Session tokens | $0-20 | >$30/month |
| Google Ads (if used) | Ad spend (separate) | User-defined | User-defined |

## Monitoring Setup

### 1. Google Cloud Billing Alerts
1. Go to Google Cloud Console → Billing → Budgets & Alerts
2. Create budget: $50/month (or user-defined)
3. Set alerts at 50%, 90%, 100%
4. Link to email notification

### 2. BigQuery Cost Controls
```sql
-- Set maximum bytes billed per query
SET @@maximum_bytes_billed = 1000000000;  -- 1 GB limit

-- Check current month usage
SELECT
  SUM(total_bytes_processed) / 1e9 AS gb_processed,
  SUM(total_bytes_processed) / 1e9 * 5 AS estimated_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)
```

### 3. API Quota Monitoring
```bash
# Check daily API usage
python scripts/sync_wiki.py --check-freshness  # Shows last sync age
# If sync fails with 429, quota exhausted
```

### 4. OpenChamber Token Tracking
- Monitor session token usage via OpenChamber dashboard
- Set alerts for >$30/month

## Cost Optimization

### 1. Reduce sync frequency
- Discovery sync: every 14 days (current) — reduce to 30 days if stable
- Freshness check: daily (cheap, no API calls)

### 2. Cache aggressively
- `data/wiki.db` is a cache — don't re-sync unchanged sources
- `content_hash` (SHA256) prevents redundant updates

### 3. BigQuery cost controls
- Use `_TABLE_SUFFIX` to limit date ranges
- Use `LIMIT` in exploratory queries
- Use materialized views for repeated aggregations

### 4. API call batching
- Google Ads: batch up to 5 sub-accounts per request
- Indexing API: batch up to 100 URLs per request

## Verification
- [ ] Billing alerts configured in Google Cloud Console
- [ ] BigQuery maximum_bytes_billed set
- [ ] OpenChamber token alerts configured
- [ ] Cost dashboard reviewed weekly
- [ ] No unexpected cost spikes in last 30 days
