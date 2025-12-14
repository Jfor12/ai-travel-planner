# WordPress/Elementor Integration Guide

## Quick Integration (2 minutes)

### Option A: WordPress Custom HTML Block (Easiest)

1. **Edit your WordPress page**
2. **Add a "Custom HTML" block**
3. **Paste this code:**

```html
<iframe 
  src="https://your-api-domain.com/index.html" 
  style="width:100%; min-height: 900px; border: none; border-radius: 8px;"
  allow="geolocation"
  title="AI Travel Planner"
></iframe>
```

4. **Replace** `https://your-api-domain.com` with your actual domain
5. **Publish!**

### Option B: Elementor Custom Widget

1. **Edit page with Elementor**
2. **Search for "HTML" widget**
3. **Add HTML widget**
4. **Paste the iframe code above**
5. **Adjust height in Elementor controls**
6. **Save & Publish**

### Option C: Link to Standalone App (Simplest)

1. **Add a button to your WordPress page**
2. **Link to:** `https://your-api-domain.com/index.html`
3. **Set to open in new tab**

## Deployment Steps

### Step 1: Deploy the Backend API

Choose one:

**A) Google Cloud Run (Recommended)**
```bash
# Install gcloud CLI first

# Create a new service
gcloud run deploy travel-planner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars \
    GROQ_API_KEY=your_groq_key,\
    TAVILY_API_KEY=your_tavily_key

# You'll get a URL like: https://travel-planner-xxxxx-uc.a.run.app
```

**B) Railway.app**
1. Push code to GitHub
2. Connect GitHub to Railway.app
3. Add environment variables
4. Deploy (automatic on push)

**C) Heroku**
1. Install Heroku CLI
2. Run: `heroku create your-app-name`
3. Set environment variables
4. Push to deploy

**D) DigitalOcean**
1. Create account
2. Create new App
3. Connect GitHub repo
4. Set environment variables
5. Deploy

### Step 2: Get Your API URL

After deployment, you'll get a URL like:
```
https://travel-planner-xxxxx.herokuapp.com
```

### Step 3: Update the Frontend

Edit `index.html` and change:
```javascript
const API_URL = 'http://localhost:8000';  // Line 480 (approx)
```

To:
```javascript
const API_URL = 'https://your-deployed-api.com';
```

### Step 4: Deploy Frontend

**Option A: GitHub Pages**
1. Upload `index.html` to GitHub
2. Enable Pages in repo settings
3. URL: `https://yourusername.github.io/repo-name/index.html`

**Option B: Same Server as API**
```bash
# Add to your server's public folder
cp index.html /var/www/html/
```

**Option C: Your Web Host**
1. FTP/SFTP the file
2. Make it public
3. Get the URL

## Environment Variables

The backend needs these in production:

```
GROQ_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
MAPBOX_API_KEY=pk-... (optional)
DATABASE_URL=postgres://... (optional)
```

**Set them in your hosting platform's dashboard**, not in `.env` files.

## Security Notes

### ✅ Do
- Use HTTPS only
- Keep API keys in environment variables
- Use strong database credentials
- Enable CORS only for your domain

### ❌ Don't
- Commit `.env` files to Git
- Expose API keys in JavaScript
- Use plain HTTP in production
- Allow CORS from `*`

## Update CORS for Your Domain

Edit `api.py` and add your domain:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com",           # Add your domain
    "https://www.yourdomain.com",       # And www version
    "https://your-api-domain.com",      # If hosting separately
]
```

## Troubleshooting

### "CORS Error: blocked by browser"

**Problem:** Frontend domain doesn't match API CORS settings

**Solution:**
1. Edit `api.py`
2. Add your domain to `CORS_ORIGINS`
3. Redeploy

### "API Connection Failed"

**Problem:** Frontend can't reach backend

**Check:**
```bash
curl https://your-api.com/health
```

Should return:
```json
{"status": "healthy", "has_groq_key": true, ...}
```

### Map not showing

**Problem:** Leaflet CSS not loading

**Solution:** Make sure you have internet connection (Leaflet loads from CDN)

### "Missing API Keys"

**Error message:** "API keys not configured"

**Solution:**
1. Verify environment variables set correctly
2. Restart the app
3. Check you're using correct key names:
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`

## Advanced: Custom Styling

Want to match your WordPress theme?

Edit the `<style>` section in `index.html`:

```css
/* Change primary color */
body {
    background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
}

button {
    background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
}
```

## Advanced: Use Your Own Domain

If you have WordPress on `example.com`:

1. Deploy API to subdomain: `api.example.com`
2. Deploy HTML to: `example.com/travel-planner/`
3. Update API_URL in HTML

This way everything is under your brand!

## Performance Tips

### Caching
Add caching headers to API responses:

```python
from fastapi.responses import JSONResponse

@app.post("/api/generate-intel")
async def generate_travel_intel(request: TravelRequest):
    # ... existing code ...
    
    return JSONResponse(
        content=response,
        headers={
            "Cache-Control": "public, max-age=3600"  # 1 hour cache
        }
    )
```

### Rate Limiting
Prevent abuse:

```bash
pip install slowapi
```

Then add to `api.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/generate-intel")
@limiter.limit("5/minute")
async def generate_travel_intel(request: TravelRequest):
    # ...
```

## Example: Full WordPress Integration

**In WordPress page editor:**

1. Add Elementor section
2. Add two columns
3. **Left column:**
   - Heading: "Plan Your Trip"
   - Description text
   - Button linking to app

4. **Right column:**
   - HTML widget with iframe

**HTML Code:**
```html
<div style="padding: 20px; background: #f8f9fa; border-radius: 8px;">
  <h3>AI Travel Planner</h3>
  <p>Get instant travel guides powered by AI</p>
  <iframe 
    src="https://api.yourdomain.com/index.html" 
    style="width:100%; min-height: 900px; border: none; border-radius: 8px;"
    title="Travel Planner"
  ></iframe>
</div>
```

## Support

- **Questions?** Check the API docs at `/docs`
- **Need help?** Review `QUICKSTART.md`
- **Debugging?** Check browser console (F12)

---

**Ready to launch?** Start with Step 1! 🚀
