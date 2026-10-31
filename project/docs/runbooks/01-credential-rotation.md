# Runbook 1: Credential Rotation

## Purpose
Rotate Google Cloud OAuth / service account credentials without downtime.

## Prerequisites
- Access to Google Cloud Console (IAM & Admin → Service Accounts)
- Access to `.env` file (or secret manager)
- Backup of current `.env` file

## Steps

### Step 1: Create new service account key
1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Select the service account used by this project
3. Go to "Keys" tab → "Add Key" → "Create new key" → JSON
4. Download the new key file
5. Save as `secrets/service-account-new.json`

### Step 2: Update .env
```bash
cp .env .env.backup
# Update GOOGLE_APPLICATION_CREDENTIALS to point to new key
sed -i 's|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account-new.json|' .env
```

### Step 3: Test new credentials
```bash
python scripts/sync_wiki.py --check-freshness
# Should connect without auth errors
```

### Step 4: Verify all APIs
```bash
python scripts/verify_feature.py --all
# All non-blocked features should PASS
```

### Step 5: Clean up
```bash
# Remove old key file
rm secrets/service-account-old.json
# Update git (if key was committed — it shouldn't be)
git rm --cached secrets/service-account-old.json
```

## Rollback
If new credentials fail:
```bash
cp .env.backup .env
# Restore old key file
python scripts/sync_wiki.py --check-freshness
```

## Frequency
Every 90 days (Google recommends quarterly rotation).

## Verification
- [ ] New key file exists and is valid JSON
- [ ] `.env` updated with new path
- [ ] `sync_wiki.py --check-freshness` passes
- [ ] `verify_feature.py --all` passes (non-blocked features)
- [ ] Old key removed from filesystem
