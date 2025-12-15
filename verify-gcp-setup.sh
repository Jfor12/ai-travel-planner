#!/bin/bash
# verify-gcp-setup.sh
# Quick verification script for Google Cloud deployment setup

set -e

echo "🔍 Verifying Google Cloud Run deployment setup..."
echo ""

# Check if key.json exists
if [ -f "key.json" ]; then
    echo "✅ key.json file found"
    
    # Validate JSON format
    if python3 -c "import json; json.load(open('key.json'))" 2>/dev/null; then
        echo "✅ key.json is valid JSON"
        
        # Check required fields
        PROJECT_ID=$(python3 -c "import json; print(json.load(open('key.json')).get('project_id', ''))")
        SERVICE_ACCOUNT=$(python3 -c "import json; print(json.load(open('key.json')).get('client_email', ''))")
        
        if [ -n "$PROJECT_ID" ]; then
            echo "✅ Project ID: $PROJECT_ID"
        else
            echo "❌ Project ID not found in key.json"
        fi
        
        if [ -n "$SERVICE_ACCOUNT" ]; then
            echo "✅ Service Account: $SERVICE_ACCOUNT"
        else
            echo "❌ Service account email not found in key.json"
        fi
    else
        echo "❌ key.json is not valid JSON format"
        exit 1
    fi
else
    echo "⚠️  key.json not found (needed for GitHub secret)"
    echo "   Run: gcloud iam service-accounts keys create key.json --iam-account=SERVICE_ACCOUNT_EMAIL"
fi

echo ""
echo "📋 GitHub Secrets Checklist:"
echo ""
echo "Go to: https://github.com/Jfor12/ai-travel-planner/settings/secrets/actions"
echo ""
echo "Required secrets:"
echo "  ☐ GCP_PROJECT_ID      = $PROJECT_ID"
echo "  ☐ GCP_SA_KEY          = (paste entire key.json contents)"
echo "  ☐ DATABASE_URL        = postgresql://..."
echo "  ☐ GROQ_API_KEY        = gsk_..."
echo "  ☐ TAVILY_API_KEY      = tvly-..."
echo ""

# Check if gcloud is installed
if command -v gcloud &> /dev/null; then
    echo "✅ gcloud CLI installed"
    
    # Get current project
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "not-set")
    echo "   Current project: $CURRENT_PROJECT"
    
    # Check if APIs are enabled
    echo ""
    echo "🔌 Checking required APIs..."
    
    if gcloud services list --enabled --filter="name:run.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "run.googleapis.com"; then
        echo "✅ Cloud Run API enabled"
    else
        echo "❌ Cloud Run API not enabled"
        echo "   Run: gcloud services enable run.googleapis.com"
    fi
    
    if gcloud services list --enabled --filter="name:artifactregistry.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "artifactregistry.googleapis.com"; then
        echo "✅ Artifact Registry API enabled"
    else
        echo "❌ Artifact Registry API not enabled"
        echo "   Run: gcloud services enable artifactregistry.googleapis.com"
    fi
else
    echo "⚠️  gcloud CLI not installed"
    echo "   Install: https://cloud.google.com/sdk/docs/install"
fi

echo ""
echo "📦 Checking Docker setup..."
if command -v docker &> /dev/null; then
    echo "✅ Docker installed"
    if docker ps &> /dev/null; then
        echo "✅ Docker daemon running"
    else
        echo "⚠️  Docker daemon not running"
    fi
else
    echo "⚠️  Docker not installed"
fi

echo ""
echo "✨ Setup verification complete!"
echo ""
echo "Next steps:"
echo "1. Copy key.json contents to GitHub secret GCP_SA_KEY"
echo "2. Add other required secrets to GitHub"
echo "3. Push to main branch to trigger deployment"
echo ""
echo "View deployment guide: DEPLOYMENT.md"
