# 🚀 Google Cloud Run Deployment Guide

This guide covers deploying the AI Travel Planner backend to Google Cloud Run using Docker containers.

## 📋 Prerequisites

1. **Google Cloud Account** - [Sign up](https://cloud.google.com/free) for free tier ($300 credit)
2. **Google Cloud CLI** - Install [gcloud](https://cloud.google.com/sdk/docs/install)
3. **Docker** - For local testing
4. **GitHub Account** - For automated deployments

## 🎯 Option 1: GitHub Actions (Recommended)

Automated deployment on every push to main branch.

### Step 1: Set Up Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create ai-travel-planner-123 --name="AI Travel Planner"

# Set the project
gcloud config set project ai-travel-planner-123

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### Step 2: Create Artifact Registry

```bash
# Create repository for Docker images
gcloud artifacts repositories create ai-travel-planner \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for AI Travel Planner"
```

### Step 3: Create Service Account

```bash
# Create service account for GitHub Actions
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ai-travel-planner-123 \
  --member="serviceAccount:github-actions@ai-travel-planner-123.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding ai-travel-planner-123 \
  --member="serviceAccount:github-actions@ai-travel-planner-123.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding ai-travel-planner-123 \
  --member="serviceAccount:github-actions@ai-travel-planner-123.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Create and download service account key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@ai-travel-planner-123.iam.gserviceaccount.com
```

### Step 4: Set Up PostgreSQL Database

**Option A: Google Cloud SQL (Managed)**
```bash
# Create PostgreSQL instance
gcloud sql instances create travel-planner-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create travel_planner --instance=travel-planner-db

# Set root password
gcloud sql users set-password postgres \
  --instance=travel-planner-db \
  --password=YOUR_SECURE_PASSWORD

# Get connection string
gcloud sql instances describe travel-planner-db --format="value(connectionName)"
# Use format: postgresql://postgres:PASSWORD@/travel_planner?host=/cloudsql/CONNECTION_NAME
```

**Option B: External Database (Cheaper)**
- Use [Supabase](https://supabase.com) (free tier)
- Use [Neon](https://neon.tech) (free tier)
- Use [ElephantSQL](https://www.elephantsql.com) (free tier)

### Step 5: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets (click "New repository secret" for each):

| Secret Name | Value | Where to Find |
|-------------|-------|---------------|
| `GCP_PROJECT_ID` | `ai-travel-planner-123` | Your project ID |
| `GCP_SA_KEY` | **Entire contents** of `key.json` file | Open key.json and copy ALL text (including `{` and `}`) |
| `DATABASE_URL` | `postgresql://user:pass@host/db` | Database connection string |
| `GROQ_API_KEY` | Your Groq API key | [groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | Your Tavily API key | [tavily.com](https://tavily.com) |

**Important for GCP_SA_KEY:**
```bash
# Copy entire key.json contents
cat key.json
# Copy everything from { to } and paste into GitHub secret
```

**Verify secrets are set:**
- Go to Settings → Secrets and variables → Actions
- You should see all 5 secrets listed (values are hidden)
- If a secret is missing, the workflow will fail

### Step 6: Deploy

```bash
# Push to main branch - deployment happens automatically!
git add .
git commit -m "Deploy to Google Cloud Run"
git push origin main
```

Monitor deployment at: https://github.com/YOUR_USERNAME/ai-travel-planner/actions

### Step 7: Get Your Service URL

```bash
# Get the deployed service URL
gcloud run services describe ai-travel-planner \
  --region=us-central1 \
  --format="value(status.url)"
```

Copy this URL and update `API_URL` in `index.html`.

## 🎯 Option 2: Manual Deployment

For quick one-time deployment without GitHub Actions.

### Deploy Directly

```bash
# Build and deploy in one command
gcloud run deploy ai-travel-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --set-env-vars GROQ_API_KEY="..." \
  --set-env-vars TAVILY_API_KEY="..." \
  --memory 512Mi \
  --cpu 1
```

### Or Use Cloud Build

```bash
# Submit build using cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml

# Set environment variables after deployment
gcloud run services update ai-travel-planner \
  --region us-central1 \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --set-env-vars GROQ_API_KEY="..." \
  --set-env-vars TAVILY_API_KEY="..."
```

## 🔧 Configuration

### Environment Variables

Set via Cloud Run console or CLI:

```bash
gcloud run services update ai-travel-planner \
  --region us-central1 \
  --set-env-vars KEY=VALUE
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `GROQ_API_KEY` - Groq API key for LLM
- `TAVILY_API_KEY` - Tavily search API key (optional)

### Resource Limits

Adjust in `.github/workflows/deploy-gcloud.yml` or via CLI:

```bash
gcloud run services update ai-travel-planner \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2 \
  --max-instances 20 \
  --min-instances 1
```

### Custom Domain

```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
  --service ai-travel-planner \
  --domain api.yourdomain.com \
  --region us-central1
```

## 💰 Cost Estimates

**Google Cloud Run Free Tier (monthly):**
- 2 million requests
- 360,000 GB-seconds memory
- 180,000 vCPU-seconds

**Estimated costs for low traffic:**
- Cloud Run: **$0** (within free tier)
- Cloud SQL (db-f1-micro): **~$7/month**
- Alternative DB (Supabase/Neon): **$0** (free tier)

**Total: $0-7/month** for typical portfolio usage

## 🧪 Testing

Test your deployed service:

```bash
# Health check
curl https://ai-travel-planner-xxx.run.app/health

# Generate guide
curl -X POST https://ai-travel-planner-xxx.run.app/api/generate-intel \
  -H "Content-Type: application/json" \
  -d '{"destination": "Paris", "month": "June"}'
```

## 🔍 Monitoring

View logs:
```bash
gcloud run services logs read ai-travel-planner --region us-central1 --limit 50
```

Or use [Google Cloud Console](https://console.cloud.google.com/run):
- View metrics (requests, latency, errors)
- Check logs in real-time
- Monitor costs

## 🐛 Troubleshooting

### GitHub Actions Authentication Error

**Error:** `must specify exactly one of "workload_identity_provider" or "credentials_json"`

**Solutions:**

1. **Verify GCP_SA_KEY secret is set:**
   ```bash
   # In GitHub: Settings → Secrets and variables → Actions
   # Make sure GCP_SA_KEY exists and contains the full JSON key
   ```

2. **Check key.json format:**
   ```bash
   # Key should be valid JSON starting with {
   cat key.json
   # Should show: {"type": "service_account", "project_id": ...}
   ```

3. **Re-create the secret:**
   - Delete existing GCP_SA_KEY secret
   - Create new secret with name: `GCP_SA_KEY`
   - Paste **entire** contents of key.json (don't add quotes or modify)
   - Save and re-run workflow

4. **Verify from Actions tab:**
   - Go to Actions → Latest workflow run → View logs
   - Check if "Authenticate to Google Cloud" step passes

**Build Fails:**
- Check Dockerfile syntax
- Verify requirements.txt includes all dependencies
- Review build logs in Cloud Build console

**Service Won't Start:**
- Check environment variables are set
- Verify DATABASE_URL is correct
- Review Cloud Run logs: `gcloud run services logs read ai-travel-planner`

**Database Connection Errors:**
- Test database connectivity separately
- Check firewall rules if using Cloud SQL
- Verify connection string format

**CORS Errors:**
- Ensure `api.py` has correct CORS origins
- Add your frontend domain to allowed origins

**Port Binding Issues:**
- Cloud Run automatically sets `PORT` env variable
- Dockerfile should use: `CMD python -m uvicorn api:app --host 0.0.0.0 --port ${PORT}`

## 🔄 Updating Deployment

With GitHub Actions, just push to main:
```bash
git add .
git commit -m "Update feature"
git push origin main
```

Manual update:
```bash
gcloud run deploy ai-travel-planner --source .
```

## 🛡️ Security Best Practices

1. **Never commit secrets** - Use GitHub Secrets or Secret Manager
2. **Rotate API keys** - Change keys periodically
3. **Set up billing alerts** - Prevent unexpected charges
4. **Restrict service account** - Use minimal permissions
5. **Enable authentication** - For production apps (optional)

## 📊 Advantages Over Railway

| Feature | Google Cloud Run | Railway |
|---------|------------------|---------|
| Free Tier | 2M requests/month | $5 credit/month |
| Auto-scaling | 0 to 1000 instances | Limited |
| Cold Start | ~1-2 seconds | Minimal |
| Global CDN | Yes | Limited |
| Logs & Monitoring | Advanced | Basic |
| Cost at Scale | Pay per use | Fixed pricing |

## 🎓 Next Steps

1. ✅ Deploy backend to Cloud Run
2. ✅ Update `index.html` with Cloud Run URL
3. ✅ Test all endpoints
4. 📊 Set up monitoring and alerts
5. 🔒 Configure custom domain (optional)
6. 💰 Set billing alerts ($5-10 threshold)

---

Need help? Check [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
