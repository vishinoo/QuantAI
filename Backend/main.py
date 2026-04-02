"""
main.py — QuantAI FastAPI Server
=================================
Entry point.  Start with:
    uvicorn main:app --reload --port 8000

All routes are defined here; logic lives in models.py,
persistence in database.py, and token verification in auth.py.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from models import (
    analyze_stock_full,
    get_stock_info,
    run_portfolio_impact,
    run_monte_carlo,
    generate_ai_insight,
    ask_ai_question,
)
from database import (
    get_user_watchlist, add_to_watchlist, remove_from_watchlist,
    get_user_portfolio, upsert_portfolio_item, remove_portfolio_item,
    log_user_decision, get_user_performance,
)
from auth import verify_token, UserClaims

# ──────────────────────────────────────────
#  App + CORS
# ──────────────────────────────────────────
app = FastAPI(title="QuantAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourapp.com"],  # update for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────
#  Request / Response Models (Pydantic)
# ──────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol: str

class PortfolioItem(BaseModel):
    symbol: str
    weight: float          # percentage, e.g. 60.0

class PortfolioSaveRequest(BaseModel):
    items: list[PortfolioItem]

class PortfolioImpactRequest(BaseModel):
    portfolio: dict[str, float]   # { "AAPL": 0.6, "MSFT": 0.4 }
    candidate: str

class ChatRequest(BaseModel):
    message: str
    symbol: Optional[str] = None
    portfolio: Optional[list[dict]] = None

class SimulateRequest(BaseModel):
    symbol: str
    days: int = 252
    simulations: int = 1000

class DecisionRequest(BaseModel):
    symbol: str
    action: str            # "buy" | "sell"
    price: float

class WatchlistAddRequest(BaseModel):
    symbol: str

# ──────────────────────────────────────────
#  HEALTH CHECK
# ──────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

# ──────────────────────────────────────────
#  STOCK ANALYSIS
# ──────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, user: UserClaims = Depends(verify_token)):
    """
    Full factor analysis pipeline:
    features → factor scores → portfolio weighting → simulation → AI insights
    Returns everything the frontend needs to render a stock page.
    """
    try:
        result = analyze_stock_full(req.symbol.upper())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{symbol}")
async def stock_info(symbol: str, user: UserClaims = Depends(verify_token)):
    """Lightweight fundamental info for a ticker (used when adding to watchlist)."""
    try:
        return get_stock_info(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────
#  SIMULATION
# ──────────────────────────────────────────

@app.post("/api/simulate")
async def simulate(req: SimulateRequest, user: UserClaims = Depends(verify_token)):
    """Standalone Monte Carlo simulation."""
    try:
        return run_monte_carlo(req.symbol.upper(), req.days, req.simulations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────
#  PORTFOLIO
# ──────────────────────────────────────────

@app.get("/api/portfolio")
async def portfolio_get(user: UserClaims = Depends(verify_token)):
    """Return the user's saved portfolio."""
    return get_user_portfolio(user.uid)


@app.put("/api/portfolio")
async def portfolio_save(req: PortfolioSaveRequest, user: UserClaims = Depends(verify_token)):
    """Overwrite the user's entire portfolio."""
    for item in req.items:
        upsert_portfolio_item(user.uid, item.symbol.upper(), item.weight)
    return {"status": "saved"}


@app.post("/api/portfolio/add")
async def portfolio_add(item: PortfolioItem, user: UserClaims = Depends(verify_token)):
    """Add or update a single position."""
    upsert_portfolio_item(user.uid, item.symbol.upper(), item.weight)
    return {"status": "added"}


@app.delete("/api/portfolio/{symbol}")
async def portfolio_remove(symbol: str, user: UserClaims = Depends(verify_token)):
    """Remove a position from the portfolio."""
    remove_portfolio_item(user.uid, symbol.upper())
    return {"status": "removed"}


@app.post("/api/portfolio/impact")
async def portfolio_impact(req: PortfolioImpactRequest, user: UserClaims = Depends(verify_token)):
    """
    Compute the impact of adding a candidate stock to the portfolio.
    Returns delta_return, delta_vol, sector info.
    """
    try:
        return run_portfolio_impact(req.portfolio, req.candidate.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────
#  WATCHLIST
# ──────────────────────────────────────────

@app.get("/api/watchlist")
async def watchlist_get(user: UserClaims = Depends(verify_token)):
    """Return the user's saved watchlist with current price data."""
    return get_user_watchlist(user.uid)


@app.post("/api/watchlist")
async def watchlist_add(req: WatchlistAddRequest, user: UserClaims = Depends(verify_token)):
    """Add a ticker to the watchlist; returns enriched stock info."""
    try:
        info = get_stock_info(req.symbol.upper())
        add_to_watchlist(user.uid, req.symbol.upper())
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/watchlist/{symbol}")
async def watchlist_remove(symbol: str, user: UserClaims = Depends(verify_token)):
    """Remove a ticker from the watchlist."""
    remove_from_watchlist(user.uid, symbol.upper())
    return {"status": "removed"}

# ──────────────────────────────────────────
#  AI CHAT
# ──────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest, user: UserClaims = Depends(verify_token)):
    """Send a message to the AI assistant with optional stock + portfolio context."""
    try:
        reply = ask_ai_question(req.message, req.symbol, req.portfolio or [])
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────
#  PERFORMANCE TRACKING
# ──────────────────────────────────────────

@app.post("/api/decisions")
async def log_decision(req: DecisionRequest, user: UserClaims = Depends(verify_token)):
    """Record a buy/sell decision for prediction-vs-reality tracking."""
    log_user_decision(user.uid, req.symbol, req.action, req.price)
    return {"status": "logged"}


@app.get("/api/performance")
async def performance(user: UserClaims = Depends(verify_token)):
    """Return model vs user performance metrics."""
    return get_user_performance(user.uid)
