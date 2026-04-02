# QuantAI — Full-Stack Stock Analysis Platform

Factor analysis · Monte Carlo simulation · AI insights · Google login

---

## Project Structure

```
quantai/
├── frontend/
│   ├── index.html     ← UI shell with login screen + app
│   ├── styles.css     ← All styling (clean professional theme)
│   ├── app.js         ← Main controller: auth, rendering, events
│   ├── api.js         ← All backend fetch calls, isolated
│   └── auth.js        ← Firebase Google login + token management
│
└── backend/
    ├── main.py        ← FastAPI routes
    ├── models.py      ← Analysis engine (refactored from stock1.py)
    ├── database.py    ← SQLite persistence (watchlist, portfolio, decisions)
    ├── auth.py        ← Firebase token verification
    └── requirements.txt
```

---

## Setup

### 1. Firebase (Authentication)

1. Go to [firebase.google.com](https://console.firebase.google.com) → Create project
2. Authentication → Sign-in method → Enable **Google**
3. Add your domain to **Authorised domains** (e.g. `localhost`)
4. Project settings → Your apps → Add web app → copy the **firebaseConfig**
5. Paste it into `frontend/auth.js` where marked
6. Project settings → Service accounts → **Generate new private key**
7. Save as `backend/service-account.json`

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Point Firebase at your service account
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# Start the server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend

No build step needed for local development:

```bash
cd frontend

# Serve with any static server, e.g.:
npx serve .
# or
python -m http.server 5173
```

Open `http://localhost:5173`.

> **Important:** The frontend uses ES Modules (`import`/`export`), so you must
> serve it over HTTP — opening `index.html` directly as a file won't work.

---

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | backend | Your Anthropic API key |
| `GOOGLE_APPLICATION_CREDENTIALS` | backend | Path to Firebase service account JSON |
| `FIREBASE_SERVICE_ACCOUNT` | backend | Alternative: JSON string (for prod/CI) |
| `QUANTAI_DB` | backend | SQLite path (default: `quantai.db`) |
| `QUANTAI_API_URL` | frontend (window global) | Backend URL (default: `http://localhost:8000`) |

---

## API Reference

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/analyze` | Full factor analysis for a symbol |
| `GET`  | `/api/stock/:sym` | Lightweight price + fundamentals |
| `POST` | `/api/simulate` | Monte Carlo simulation |
| `GET`  | `/api/portfolio` | Get user's portfolio |
| `POST` | `/api/portfolio/add` | Add/update a position |
| `DELETE` | `/api/portfolio/:sym` | Remove a position |
| `POST` | `/api/portfolio/impact` | Portfolio impact analysis |
| `GET`  | `/api/watchlist` | Get user's watchlist |
| `POST` | `/api/watchlist` | Add to watchlist |
| `DELETE` | `/api/watchlist/:sym` | Remove from watchlist |
| `POST` | `/api/chat` | AI assistant query |
| `POST` | `/api/decisions` | Log a buy/sell decision |
| `GET`  | `/api/performance` | Model vs user metrics |

All routes require `Authorization: Bearer <firebase-token>`.

---

## Migrating to Production

- **Database:** Swap SQLite in `database.py` for PostgreSQL via `asyncpg` or Supabase
- **Hosting frontend:** Netlify, Vercel, or Firebase Hosting (static)
- **Hosting backend:** Railway, Render, or Google Cloud Run
- **CORS:** Update `allow_origins` in `main.py` with your production domain
