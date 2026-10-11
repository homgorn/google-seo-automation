#!/usr/bin/env bash
# init.sh - Google SEO Automation Project Environment Setup
# Run this first in every new session to start the dev environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Google SEO Automation - Environment Initialization${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Check required tools
check_tool() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found: $(command -v "$1")"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 NOT FOUND - $2"
        return 1
    fi
}

echo -e "${YELLOW}Checking required tools...${NC}"
MISSING_TOOLS=0

check_tool "python3" "Install Python 3.10+" || ((MISSING_TOOLS++))
check_tool "node" "Install Node.js 20+" || ((MISSING_TOOLS++))
check_tool "npm" "Install npm" || ((MISSING_TOOLS++))
check_tool "git" "Install Git" || ((MISSING_TOOLS++))
check_tool "sqlite3" "Install SQLite3" || ((MISSING_TOOLS++))

# Check for Hyper CLI (optional but recommended)
if command -v hyperai &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} hyperai found: $(command -v hyperai)"
else
    echo -e "  ${YELLOW}⚠${NC} hyperai NOT FOUND - Install from https://app.hyperfx.ai/mcp (recommended for API access)"
fi

# Check for OpenChamber CLI
if command -v opencode &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} opencode found: $(command -v opencode)"
else
    echo -e "  ${YELLOW}⚠${NC} opencode NOT FOUND - OpenChamber integration will be limited"
fi

echo ""

# 2. Check Python dependencies
echo -e "${YELLOW}Checking Python environment...${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "  ${BLUE}→${NC} Installing/updating Python dependencies..."
    pip3 install -q -r requirements.txt 2>/dev/null || {
        echo -e "  ${RED}✗${NC} Failed to install requirements"
        ((MISSING_TOOLS++))
    }
    echo -e "  ${GREEN}✓${NC} Python dependencies ready"
else
    echo -e "  ${YELLOW}⚠${NC} No requirements.txt found - creating minimal..."
    cat > requirements.txt << 'EOF'
# Core
requests>=2.31.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
google-api-python-client>=2.100.0
google-cloud-bigquery>=3.11.0

# Data processing
pandas>=2.1.0
numpy>=1.24.0

# Vector search / embeddings
sentence-transformers>=2.2.0
chromadb>=0.4.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0

# Async
aiohttp>=3.9.0
asyncio-throttle>=1.0.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0.1
tqdm>=4.66.0
rich>=13.0.0
tenacity>=8.2.0
EOF
    pip3 install -q -r requirements.txt 2>/dev/null || ((MISSING_TOOLS++))
    echo -e "  ${GREEN}✓${NC} Python dependencies installed"
fi

# 3. Check Node dependencies
echo -e "${YELLOW}Checking Node environment...${NC}"
if [ -f "package.json" ]; then
    echo -e "  ${BLUE}→${NC} Installing/updating Node dependencies..."
    npm ci --silent 2>/dev/null || npm install --silent 2>/dev/null || {
        echo -e "  ${RED}✗${NC} Failed to install Node dependencies"
        ((MISSING_TOOLS++))
    }
    echo -e "  ${GREEN}✓${NC} Node dependencies ready"
else
    echo -e "  ${YELLOW}⚠${NC} No package.json found - creating minimal..."
    cat > package.json << 'EOF'
{
  "name": "google-seo-automation",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "jest",
    "lint": "eslint .",
    "build": "tsc"
  },
  "dependencies": {
    "googleapis": "^133.0.0",
    "@google-cloud/bigquery": "^7.3.0",
    "openchamber-sdk": "^1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "jest": "^29.7.0",
    "eslint": "^8.56.0"
  }
}
EOF
    npm install --silent 2>/dev/null || ((MISSING_TOOLS++))
    echo -e "  ${GREEN}✓${NC} Node dependencies installed"
fi

# 4. Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
if [ ! -f "data/wiki.db" ]; then
    echo -e "  ${BLUE}→${NC} Creating wiki database schema..."
    python3 scripts/init_db.py 2>/dev/null || {
        echo -e "  ${YELLOW}⚠${NC} init_db.py not found - will create on first run"
    }
else
    echo -e "  ${GREEN}✓${NC} Wiki database exists"
fi

# 5. Check environment variables
echo -e "${YELLOW}Checking environment configuration...${NC}"
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} .env file found"
    # Source it to check required vars
    set -a
    source "$ENV_FILE"
    set +a
else
    echo -e "  ${YELLOW}⚠${NC} .env file not found - creating template..."
    cat > "$ENV_FILE" << 'EOF'
# Google Cloud / APIs
GOOGLE_CLOUD_PROJECT_ID=
GOOGLE_APPLICATION_CREDENTIALS=
GA4_PROPERTY_ID=
GTM_ACCOUNT_ID=
GTM_CONTAINER_ID=
GSC_SITE_URL=

# OAuth 2.0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
GOOGLE_ADS_CUSTOMER_ID=

# Microsoft Advertising (Bing Ads)
MS_ADS_DEVELOPER_TOKEN=
MS_ADS_CLIENT_ID=
MS_ADS_CLIENT_SECRET=
MS_ADS_REFRESH_TOKEN=
MS_ADS_CUSTOMER_ID=
MS_ADS_ACCOUNT_ID=

# Hyper MCP (if using)
HYPER_API_KEY=
HYPER_WORKSPACE_ID=

# OpenChamber
OPENCHAMBER_API_KEY=
OPENCHAMBER_PROJECT_ID=

# Vector DB / Embeddings
OPENAI_API_KEY=
# OR use local embeddings (sentence-transformers)
USE_LOCAL_EMBEDDINGS=true

# Database
DATABASE_URL=sqlite:///data/wiki.db

# Scheduling
WIKI_REFRESH_CRON="0 2 */14 * *"  # Bi-weekly at 2 AM
DAILY_REPORT_CRON="0 6 * * *"      # Daily at 6 AM
EOF
    echo -e "  ${BLUE}→${NC} Created .env template - PLEASE FILL IN YOUR CREDENTIALS"
fi

# Check critical env vars
CRITICAL_VARS=("GOOGLE_CLOUD_PROJECT_ID" "GA4_PROPERTY_ID")
for var in "${CRITICAL_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo -e "  ${YELLOW}⚠${NC} $var not set - some features will be limited"
    else
        echo -e "  ${GREEN}✓${NC} $var configured"
    fi
done

# 6. Verify API access (quick check)
echo -e "${YELLOW}Verifying API access...${NC}"
python3 -c "
import os
from google.auth import default
try:
    credentials, project = default()
    print(f'  ✓ Google Auth: Project={project}')
except Exception as e:
    print(f'  ⚠ Google Auth: {e}')
" 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} Google Auth not configured"

# 7. Show project status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Project Status${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

if [ -f "feature_list.json" ]; then
    FEATURE_COUNT=$(python3 -c "import json; print(len(json.load(open('feature_list.json'))))")
    PASSED_COUNT=$(python3 -c "import json; print(sum(1 for f in json.load(open('feature_list.json')) if f.get('passes')))")
    echo -e "  Features: ${GREEN}$PASSED_COUNT${NC}/${FEATURE_COUNT} passed"
fi

if [ -f "progress.md" ]; then
    echo -e "  ${GREEN}✓${NC} progress.md exists"
else
    echo -e "  ${YELLOW}⚠${NC} progress.md not found - will create on first run"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

if [ $MISSING_TOOLS -gt 0 ]; then
    echo -e "${RED}Environment has $MISSING_TOOLS missing dependencies${NC}"
    echo -e "${YELLOW}Please install missing tools and re-run init.sh${NC}"
    exit 1
else
    echo -e "${GREEN}Environment ready!${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  1. Fill in .env with your credentials"
    echo -e "  2. Run: python3 scripts/sync_wiki.py --full (initial wiki population)"
    echo -e "  3. Start OpenChamber session: opencode session create"
    echo -e "  4. Begin with F001: explorer for API documentation research"
fi