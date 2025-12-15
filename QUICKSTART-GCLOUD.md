# 🚀 Quick Start: Deploy to Google Cloud Run

Complete setup in **15 minutes** with **$0 cost**.

## Prerequisites

- Google Account (Gmail)
- GitHub Account
- Terminal/Command Line

## Step-by-Step Setup

### 1️⃣ Install Google Cloud CLI

**macOS:**
```bash
brew install google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

### 2️⃣ Run Automated Setup Script

```bash
./setup-gcloud.sh
```

This script will:
- ✅ Create Google Cloud project
- ✅ Enable required APIs
- ✅ Set up service account
- ✅ Generate authentication key
- ✅ Guide you through database setup
- ✅ Collect API keys

**Follow the prompts!** It will ask for:
- Project ID (choose something like `ai-travel-planner-yourname`)
- Database URL (from Supabase - we'll help you get it)
- API keys (Groq & Tavily - free signups)

### 3️⃣ Get Free Database (Supabase)

While script is running:

1. Open: https://supabase.com
2. Sign up (free)
3. Click "New project"
4. Choose a name, password, region
5. Wait ~2 minutes for setup
6. Go to: **Settings** → **Database**
7. Find **Connection string** (URI mode)
8. Copy it (looks like: `postgresql://postgres.[ref]:[password]@...`)
9. Paste when script asks for DATABASE_URL

### 4️⃣ Get API Keys (Both Free)

**Groq (AI/LLM):**
1. Go to: https://console.groq.com
2. Sign up
3. Create API key
4. Copy the key (starts with `gsk_`)

**Tavily (Web Search):**
1. Go to: https://tavily.com
2. Sign up
3. Get API key from dashboard
4. Copy the key (starts with `tvly-`)

### 5️⃣ Configure GitHub Secrets

After script finishes, go to:
https://github.com/Jfor12/ai-travel-planner/settings/secrets/actions

Click **"New repository secret"** for each:

| Secret Name | Where to Find |
|-------------|---------------|
| `GCP_PROJECT_ID` | Script shows it (your project ID) |
| `GCP_SA_KEY` | Run `cat key.json` and copy ALL text |
| `DATABASE_URL` | Your Supabase connection string |
| `GROQ_API_KEY` | From console.groq.com |
| `TAVILY_API_KEY` | From tavily.com |

**For GCP_SA_KEY:**
```bash
# View the key file
cat key.json

# Copy EVERYTHING from { to } including all the text
# Paste into GitHub secret (no modifications)
```

### 6️⃣ Deploy!

```bash
git add .
git commit -m "Deploy to Google Cloud Run"
git push origin main
```

Watch deployment at: https://github.com/Jfor12/ai-travel-planner/actions

Takes ~3-5 minutes for first deploy.

### 7️⃣ Get Your Backend URL

After deployment succeeds:

```bash
gcloud run services describe ai-travel-planner \
  --region us-central1 \
  --format='value(status.url)'
```

Copy the URL (looks like: `https://ai-travel-planner-xxx-uc.a.run.app`)

### 8️⃣ Update Frontend

Edit `index.html` and update the API URL:

```javascript
// Find this section (around line 400)
const API_URL = window.location.hostname.includes('codespaces')
    ? 'http://localhost:8000'
    : window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://YOUR-CLOUD-RUN-URL-HERE';  // ← UPDATE THIS
```

Replace with your Cloud Run URL (without trailing slash).

### 9️⃣ Push Frontend Update

```bash
git add index.html
git commit -m "Update API URL to Google Cloud Run"
git push origin main
```

### 🎉 Done!

Your app is live at:
- Frontend: https://jfor12.github.io/ai-travel-planner
- Backend: Your Cloud Run URL

## 🛡️ Set Up Billing Alert (Important!)

1. Go to: https://console.cloud.google.com/billing/budgets
2. Create budget
3. Set amount: **$5 or $10**
4. Set alerts: **50%, 90%, 100%**
5. Save

**Your app stays free** - this is just a safety net!

## 📊 What You Just Created

- ✅ **Backend**: Google Cloud Run (2M free requests/month)
- ✅ **Database**: Supabase (500MB free)
- ✅ **Frontend**: GitHub Pages (unlimited free)
- ✅ **CI/CD**: GitHub Actions (auto-deploy)
- ✅ **Monitoring**: Google Cloud logs

**Monthly Cost: $0** 💰

## 🐛 Troubleshooting

**Script fails at "Creating project":**
```bash
# Project ID might be taken, try a different one
./setup-gcloud.sh  # Run again with new ID
```

**"Billing account required":**
```bash
# Link billing at: https://console.cloud.google.com/billing
# Don't worry - free tier won't charge
```

**GitHub Action fails:**
```bash
# Verify all 5 secrets are set correctly
# Check: https://github.com/Jfor12/ai-travel-planner/settings/secrets/actions
```

**Can't find Cloud Run URL:**
```bash
gcloud run services list --region us-central1
```

## 📚 More Help

- Full guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Billing safety: [DEPLOYMENT.md#cost-estimates--protection](DEPLOYMENT.md#cost-estimates--protection)
- Verification: `./verify-gcp-setup.sh`

---

**Questions?** Check the [main README](README.md) or [DEPLOYMENT.md](DEPLOYMENT.md)
