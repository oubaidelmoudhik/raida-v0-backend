# Render Deployment Guide

## Files Added/Updated

1. **requirements.txt** – Includes all dependencies (`gunicorn`, `openai`, `python-pptx`, `Jinja2`, `python-dotenv`, etc.)
2. **runtime.txt** – Specifies Python 3.13 (optional for Render, but kept for clarity)
3. **build.sh** – Installs Playwright browsers needed for PDF generation
4. **Procfile** – `web: gunicorn app:app` (used by Render when not using a Dockerfile)
5. **render.yaml** – Render service definition (added in the backend folder)

## Render Configuration

### 1. Create `render.yaml`
Create a file named `render.yaml` in the backend directory with the following content:

```yaml
services:
  - type: web
    name: raida-backend
    env: python
    buildCommand: pip install -r requirements.txt && bash build.sh
    startCommand: gunicorn app:app
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: FLASK_DEBUG
        sync: false
```

Render will automatically provide the `PORT` environment variable; you do not need to set it manually.

### 2. Environment Variables
Add the following variables in the Render dashboard for the service:
- `OPENAI_API_KEY` – Your OpenAI API key
- `FLASK_DEBUG` – Set to `0` for production (optional)

### 3. Build & Deploy
Render will run the `buildCommand` defined in `render.yaml` which installs dependencies and the Playwright browsers. After the build completes, it will execute the `startCommand` (`gunicorn app:app`).

### 4. Static & Data Files
Ensure the following directories are included in the repository so Render can serve them:
- `static/fonts` – Contains the Cairo font files used for Arabic PDFs
- `data/lessons.json` – Lesson metadata accessed by the API

### 5. Frontend (Vercel) Adjustments
Update your Vercel frontend to point to the Render backend URL:
- Replace any occurrence of `http://localhost:5000` with `https://<your-render-service>.onrender.com`

## Important Notes
- **Playwright**: The `build.sh` script installs Chromium, which Render’s build environment supports.
- **Procfile**: Render can use the Procfile if you prefer not to use `render.yaml`; the start command remains `gunicorn app:app`.
- **Testing Locally**: Run `gunicorn app:app` locally to verify the production entry point before deploying.

---

All previous Railway‑specific sections have been removed. This guide now focuses solely on deploying the backend to Render.
