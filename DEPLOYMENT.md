# Railway Deployment Guide

## Files Added/Updated

1. **requirements.txt** - Added all dependencies including `gunicorn`
2. **runtime.txt** - Specifies Python 3.13
3. **build.sh** - Installs Playwright browsers
4. **Procfile** - Already configured with `web: gunicorn app:app`

## Railway Configuration

### 1. Environment Variables
Add these in Railway dashboard:
- `OPENAI_API_KEY` - Your OpenAI API key
- `PORT` - Railway sets this automatically
- `FLASK_DEBUG` - Set to `0` for production

### 2. Build Command
In Railway settings, set the build command to:
```bash
pip install -r requirements.txt && bash build.sh
```

### 3. Start Command
Railway should auto-detect the Procfile, but if needed:
```bash
gunicorn app:app
```

### 4. Important Notes
- **Playwright**: The build script installs Chromium browser needed for PDF generation
- **Static Files**: Make sure the `static/fonts` directory is included in deployment
- **Data Directory**: Ensure `data/lessons.json` is accessible

## Frontend (Vercel) Configuration

Update your frontend API calls to point to your Railway backend URL:
- Replace `http://localhost:5000` with your Railway URL
- Example: `https://your-app.railway.app`

## Troubleshooting

If Playwright fails:
- Railway might need additional system dependencies
- Consider using a Docker deployment for better control
- Alternative: Use a different PDF generation library that doesn't require browsers
