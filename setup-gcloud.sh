#!/bin/bash
# Google Cloud Run Setup Script
# Run this to set up your project from scratch

set -e

echo "🚀 AI Travel Planner - Google Cloud Run Setup"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Step 1: Checking prerequisites..."
echo ""

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✅ gcloud CLI installed${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ git not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ git installed${NC}"

echo ""
echo "=============================================="
echo "📝 Step 2: Project Configuration"
echo "=============================================="
echo ""

# Get project details
read -p "Enter your desired project ID (e.g., ai-travel-planner-jfor12): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Project ID cannot be empty${NC}"
    exit 1
fi

echo ""
echo "Your project ID: $PROJECT_ID"
echo ""

# Login to gcloud
echo "🔐 Logging in to Google Cloud..."
gcloud auth login

echo ""
echo "=============================================="
echo "🏗️  Step 3: Creating Google Cloud Project"
echo "=============================================="
echo ""

# Create project
echo "Creating project: $PROJECT_ID..."
gcloud projects create $PROJECT_ID --name="AI Travel Planner" || {
    echo -e "${YELLOW}⚠️  Project might already exist. Continuing...${NC}"
}

# Set active project
gcloud config set project $PROJECT_ID

# Link billing account (required for Cloud Run)
echo ""
echo "🔗 Linking billing account..."
echo "Go to: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "Link a billing account (won't charge within free tier)"
echo ""
read -p "Press Enter after linking billing account..."

echo ""
echo "=============================================="
echo "⚙️  Step 4: Enabling Google Cloud APIs"
echo "=============================================="
echo ""

echo "Enabling required APIs (takes ~2 minutes)..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable compute.googleapis.com

echo -e "${GREEN}✅ APIs enabled${NC}"

echo ""
echo "=============================================="
echo "📦 Step 5: Creating Artifact Registry"
echo "=============================================="
echo ""

echo "Creating Docker repository..."
gcloud artifacts repositories create ai-travel-planner \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for AI Travel Planner" || {
    echo -e "${YELLOW}⚠️  Repository might already exist. Continuing...${NC}"
}

echo -e "${GREEN}✅ Artifact Registry created${NC}"

echo ""
echo "=============================================="
echo "🔑 Step 6: Creating Service Account"
echo "=============================================="
echo ""

SERVICE_ACCOUNT_NAME="github-actions"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating service account: $SERVICE_ACCOUNT_EMAIL..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="GitHub Actions Deployer" || {
    echo -e "${YELLOW}⚠️  Service account might already exist. Continuing...${NC}"
}

echo ""
echo "Granting permissions..."

# Grant Cloud Run Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.admin"

# Grant Service Account User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Grant Artifact Registry Writer
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Grant Storage Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/storage.admin"

echo -e "${GREEN}✅ Permissions granted${NC}"

echo ""
echo "=============================================="
echo "🔐 Step 7: Generating Service Account Key"
echo "=============================================="
echo ""

KEY_FILE="key.json"

echo "Generating key file: $KEY_FILE..."
gcloud iam service-accounts keys create $KEY_FILE \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

echo -e "${GREEN}✅ Key file created: $KEY_FILE${NC}"

echo ""
echo "=============================================="
echo "💾 Step 8: Database Setup (FREE)"
echo "=============================================="
echo ""

echo "For a 100% FREE setup, use Supabase PostgreSQL:"
echo ""
echo "1. Go to: https://supabase.com"
echo "2. Sign up (free)"
echo "3. Create new project"
echo "4. Go to: Settings → Database"
echo "5. Copy the 'Connection string' (URI format)"
echo ""
echo "It looks like:"
echo "postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
echo ""
read -p "Paste your DATABASE_URL here: " DATABASE_URL

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}DATABASE_URL cannot be empty${NC}"
    exit 1
fi

echo ""
echo "=============================================="
echo "🤖 Step 9: API Keys"
echo "=============================================="
echo ""

echo "You need these API keys (all have free tiers):"
echo ""

echo "Groq API Key (LLM):"
echo "1. Go to: https://console.groq.com"
echo "2. Sign up and create API key"
echo ""
read -p "Paste your GROQ_API_KEY: " GROQ_API_KEY

echo ""
echo "Tavily API Key (Search):"
echo "1. Go to: https://tavily.com"
echo "2. Sign up and create API key"
echo ""
read -p "Paste your TAVILY_API_KEY (or press Enter to skip): " TAVILY_API_KEY

if [ -z "$TAVILY_API_KEY" ]; then
    TAVILY_API_KEY="none"
fi

echo ""
echo "=============================================="
echo "🔧 Step 10: GitHub Secrets Configuration"
echo "=============================================="
echo ""

echo "Now we'll set up GitHub secrets for automatic deployment."
echo ""
echo "Go to: https://github.com/Jfor12/ai-travel-planner/settings/secrets/actions"
echo ""
echo "Click 'New repository secret' and add these 5 secrets:"
echo ""

echo -e "${YELLOW}Secret 1: GCP_PROJECT_ID${NC}"
echo "Value: $PROJECT_ID"
echo ""

echo -e "${YELLOW}Secret 2: GCP_SA_KEY${NC}"
echo "Value: Copy ENTIRE contents of key.json file"
echo "Run: cat $KEY_FILE"
echo "Copy everything from { to }"
echo ""

echo -e "${YELLOW}Secret 3: DATABASE_URL${NC}"
echo "Value: $DATABASE_URL"
echo ""

echo -e "${YELLOW}Secret 4: GROQ_API_KEY${NC}"
echo "Value: $GROQ_API_KEY"
echo ""

echo -e "${YELLOW}Secret 5: TAVILY_API_KEY${NC}"
echo "Value: $TAVILY_API_KEY"
echo ""

echo "⚠️  IMPORTANT: Don't commit key.json to git!"
echo ""

# Create .gitignore entry
if ! grep -q "key.json" .gitignore 2>/dev/null; then
    echo "key.json" >> .gitignore
    echo -e "${GREEN}✅ Added key.json to .gitignore${NC}"
fi

echo ""
read -p "Press Enter after adding all 5 secrets to GitHub..."

echo ""
echo "=============================================="
echo "🎉 Setup Complete!"
echo "=============================================="
echo ""

echo "Summary of what was created:"
echo "  ✅ Google Cloud Project: $PROJECT_ID"
echo "  ✅ Artifact Registry repository"
echo "  ✅ Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "  ✅ Service Account Key: $KEY_FILE"
echo "  ✅ Required APIs enabled"
echo ""

echo "Next steps:"
echo "1. Make sure all 5 GitHub secrets are set"
echo "2. Push to main branch:"
echo ""
echo "   git add ."
echo "   git commit -m 'Deploy to Google Cloud Run'"
echo "   git push origin main"
echo ""
echo "3. Watch deployment at:"
echo "   https://github.com/Jfor12/ai-travel-planner/actions"
echo ""
echo "4. After deployment, get your service URL:"
echo "   gcloud run services describe ai-travel-planner --region us-central1 --format='value(status.url)'"
echo ""
echo "5. Update index.html with your Cloud Run URL"
echo ""

echo "📊 Set up billing alert (RECOMMENDED):"
echo "   https://console.cloud.google.com/billing/budgets?project=$PROJECT_ID"
echo "   Create budget: \$5-10 with 50%, 90%, 100% alerts"
echo ""

echo "💰 Expected cost: \$0/month (free tier)"
echo ""

echo "Need help? Check DEPLOYMENT.md"
echo ""
