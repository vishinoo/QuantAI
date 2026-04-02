"""
models.py — QuantAI Analysis Engine
=====================================
Refactored from stock1.py:
  ✅ Returns dicts/JSON instead of printing
  ✅ No side effects
  ✅ Each function is independently callable
  ✅ Anthropic Claude used for AI insight generation

Functions:
  analyze_stock_full()    → main pipeline (called by /api/analyze)
  get_stock_info()        → lightweight fundamentals
  calculate_features()   → momentum, volatility, drawdown
  get_factor_scores()    → 0–100 factor scores
  calculate_weighting()  → composite signal + label
  run_portfolio_impact() → delta return / vol from adding a stock
  run_monte_carlo()      → Monte Carlo simulation
  generate_ai_insight()  → AI narrative for a stock
  ask_ai_question()      → free-form AI chat
"""

import numpy as np
import random
import anthropic
import yfinance as yf

# ──────────────────────────────────────────
#  CLIENT SETUP
# ──────────────────────────────────────────

_anthropic = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ──────────────────────────────────────────
#  MAIN PIPELINE
# ──────────────────────────────────────────

def analyze_stock_full(symbol: str) -> dict:
    """
    Complete analysis pipeline for a single symbol.
    Returns a single dict consumed by the frontend.
    """
    ticker = yf.Ticker(symbol)
    info   = ticker.info or {}

    # Price / basic info
    price  = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    prev   = info.get("previousClose", price)
    change = ((price - prev) / prev * 100) if prev else 0

    # Run analysis modules
    features    = calculate_features(symbol)
    scores      = get_factor_scores(symbol)
    weighting   = calculate_weighting(
        scores["momentum"], scores["quality"], scores["value"], scores["risk"]
    )
    simulation  = run_monte_carlo(symbol)
    fundamentals = {
        "pe":             round(info.get("trailingPE") or 0, 2),
        "roe":            round((info.get("returnOnEquity") or 0) * 100, 2),
        "profit_margin":  round((info.get("profitMargins") or 0) * 100, 2),
        "revenue_growth": round((info.get("revenueGrowth") or 0) * 100, 2),
    }
    insights = generate_ai_insight(symbol, scores, weighting, fundamentals, simulation)
    chart    = build_chart_data(symbol)

    return {
        "symbol":       symbol,
        "name":         info.get("longName", symbol),
        "price":        round(price, 2),
        "change":       f"{'+' if change >= 0 else ''}{change:.2f}%",
        "up":           change >= 0,
        "scores": {
            "momentum":  scores["momentum"],
            "quality":   scores["quality"],
            "value":     scores["value"],
            "risk":      scores["risk"],
            "composite": weighting["final_score"],
            "label":     weighting["label"],
        },
        "fundamentals": fundamentals,
        "simulation":   simulation,
        "insights":     insights,
        "chart_data":   chart,
    }


# ──────────────────────────────────────────
#  LIGHTWEIGHT STOCK INFO
# ──────────────────────────────────────────

def get_stock_info(symbol: str) -> dict:
    """
    Lightweight fetch — used when adding to watchlist.
    Returns symbol, name, price, change, up.
    """
    ticker = yf.Ticker(symbol)
    info   = ticker.info or {}
    price  = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    prev   = info.get("previousClose", price)
    change = ((price - prev) / prev * 100) if prev else 0

    return {
        "symbol": symbol,
        "name":   info.get("longName", symbol + " Corp."),
        "price":  f"{price:.2f}",
        "change": f"{'+' if change >= 0 else ''}{change:.2f}%",
        "up":     change >= 0,
    }


# ──────────────────────────────────────────
#  FEATURE ENGINEERING  (Section 2 from stock1.py)
# ──────────────────────────────────────────

def calculate_features(symbol: str) -> dict | None:
    ticker  = yf.Ticker(symbol)
    history = ticker.history(period="2y")
    if history.empty:
        return None

    df = history[["Close"]].copy()
    df["returns"] = df["Close"].pct_change()

    # Momentum
    return_1m  = df["Close"].pct_change(21).iloc[-1]
    return_3m  = df["Close"].pct_change(63).iloc[-1]
    return_12m = df["Close"].pct_change(252).iloc[-1]

    # Moving averages
    ma50       = df["Close"].rolling(50).mean()
    ma200      = df["Close"].rolling(200).mean()
    ma_signal  = bool(ma50.iloc[-1] > ma200.iloc[-1])

    # Volatility
    volatility = float(df["returns"].std() * np.sqrt(252))

    # Max drawdown
    rolling_max  = df["Close"].cummax()
    drawdown     = (df["Close"] - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())

    return {
        "momentum": {
            "1m":        round(float(return_1m), 4),
            "3m":        round(float(return_3m), 4),
            "12m":       round(float(return_12m), 4),
            "ma_signal": ma_signal,
        },
        "risk": {
            "volatility":    round(volatility, 4),
            "max_drawdown":  round(max_drawdown, 4),
        },
    }


# ──────────────────────────────────────────
#  FACTOR SCORES  (Section 3 from stock1.py)
# ──────────────────────────────────────────

def get_factor_scores(symbol: str) -> dict:
    """
    Returns momentum, value, quality, risk scores (0–100).
    """
    ticker = yf.Ticker(symbol)
    hist   = ticker.history(period="5y")
    info   = ticker.info or {}
    prices = hist["Close"].tolist()

    def stats(data: list) -> tuple[float, float]:
        if len(data) < 2:
            return 0.0, 1.0
        mean = sum(data) / len(data)
        std  = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        return mean, std or 1.0

    # 1. MOMENTUM — 12M return vs 5Y historical 12M returns
    returns_12m = [(prices[i] / prices[i - 252]) - 1 for i in range(252, len(prices))]
    current_12m = (prices[-1] / prices[-252]) - 1 if len(prices) >= 252 else 0
    m_mean, m_std = stats(returns_12m)
    momentum = max(0, min(100, 50 + ((current_12m - m_mean) / m_std) * 15))

    # 2. VALUE — inverse P/E normalised to 10–50 range
    pe    = info.get("trailingPE") or 40
    value = max(0, min(100, (1 - (pe / 50)) * 100))

    # 3. QUALITY — ROE normalised to 0–40% scale
    roe     = info.get("returnOnEquity") or 0
    quality = max(0, min(100, (roe / 0.40) * 100))

    # 4. RISK — inverse volatility score
    chunk = 30
    recent_vols = []
    for i in range(chunk, len(prices), chunk):
        _, v = stats(prices[i - chunk : i])
        recent_vols.append(v)
    _, cur_vol = stats(prices[-chunk:])
    v_mean, v_std = stats(recent_vols)
    risk = max(0, min(100, 50 - ((cur_vol - v_mean) / v_std) * 15))

    return {
        "momentum": round(momentum, 1),
        "value":    round(value, 1),
        "quality":  round(quality, 1),
        "risk":     round(risk, 1),
    }


# ──────────────────────────────────────────
#  PORTFOLIO WEIGHTING  (Section 4 from stock1.py)
# ──────────────────────────────────────────

def calculate_weighting(
    m_score: float, q_score: float, v_score: float, r_score: float
) -> dict:
    """
    Returns composite signal, label, confidence, and factor contributions.
    """
    w_m, w_q, w_v, w_r = 0.35, 0.25, 0.20, 0.20

    m_cont = m_score * w_m
    q_cont = q_score * w_q
    v_cont = v_score * w_v
    r_cont = r_score * w_r
    final  = m_cont + q_cont + v_cont + r_cont

    if   final >= 80: label = "Strong Buy"
    elif final >= 60: label = "Buy"
    elif final >= 40: label = "Neutral"
    else:             label = "Sell"

    scores     = [m_score, q_score, v_score, r_score]
    avg        = sum(scores) / 4
    variance   = sum((s - avg) ** 2 for s in scores) / 4
    confidence = max(0, min(100, 100 - variance ** 0.5))

    return {
        "final_score": round(final, 1),
        "label":       label,
        "confidence":  round(confidence, 1),
        "contributions": {
            "momentum": round(m_cont, 2),
            "quality":  round(q_cont, 2),
            "value":    round(v_cont, 2),
            "risk":     round(r_cont, 2),
        },
    }


# ──────────────────────────────────────────
#  PORTFOLIO IMPACT  (Section 5 from stock1.py)
# ──────────────────────────────────────────

def run_portfolio_impact(portfolio: dict[str, float], candidate: str) -> dict:
    """
    Computes the impact of adding `candidate` at 10% weight.
    portfolio: { "AAPL": 0.6, "MSFT": 0.4 }
    """
    symbols  = list(portfolio.keys()) + [candidate]
    all_data = {}

    for sym in symbols:
        t    = yf.Ticker(sym)
        hist = t.history(period="1y")
        prices  = hist["Close"].tolist()
        returns = [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices))]
        all_data[sym] = {
            "returns":    returns,
            "avg_return": sum(returns) / len(returns) if returns else 0,
            "info":       t.info or {},
        }

    def vol(ret: list) -> float:
        if not ret: return 0.0
        avg = sum(ret) / len(ret)
        return (sum((x - avg) ** 2 for x in ret) / len(ret)) ** 0.5

    # Current metrics
    cur_ret = sum(all_data[s]["avg_return"] * w for s, w in portfolio.items())
    cur_vol = sum(vol(all_data[s]["returns"]) * w for s, w in portfolio.items())

    # New metrics (10% candidate, 90% existing)
    nw  = 0.10
    rw  = 1.0 - nw
    new_ret = all_data[candidate]["avg_return"] * nw + sum(
        all_data[s]["avg_return"] * (w * rw) for s, w in portfolio.items()
    )
    new_vol = vol(all_data[candidate]["returns"]) * nw + sum(
        vol(all_data[s]["returns"]) * (w * rw) for s, w in portfolio.items()
    )

    delta_return = (new_ret - cur_ret) * 252
    delta_vol    = (new_vol - cur_vol) * (252 ** 0.5)

    old_sector = all_data[list(portfolio.keys())[0]]["info"].get("sector", "Unknown")
    new_sector = all_data[candidate]["info"].get("sector", "Unknown")

    return {
        "delta_return":  round(delta_return, 4),
        "delta_vol":     round(delta_vol, 4),
        "new_sector":    new_sector,
        "concentrating": old_sector == new_sector,
        "warning":       f"Increasing concentration in {new_sector}" if old_sector == new_sector
                         else f"Diversifying into {new_sector}",
    }


# ──────────────────────────────────────────
#  MONTE CARLO SIMULATION  (Section 6 from stock1.py)
# ──────────────────────────────────────────

def run_monte_carlo(symbol: str, days: int = 252, simulations: int = 1000) -> dict:
    """
    Returns bear/base/bull price projections and VaR.
    """
    ticker  = yf.Ticker(symbol)
    hist    = ticker.history(period="2y")
    prices  = hist["Close"].tolist()

    returns       = [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices))]
    avg_daily_ret = sum(returns) / len(returns)
    variance      = sum((x - avg_daily_ret) ** 2 for x in returns) / len(returns)
    daily_vol     = variance ** 0.5
    current_price = prices[-1]

    ending_prices = []
    for _ in range(simulations):
        p = current_price
        for _ in range(days):
            p *= (1 + random.gauss(avg_daily_ret, daily_vol))
        ending_prices.append(p)
    ending_prices.sort()

    bear   = ending_prices[int(simulations * 0.10)]
    base   = sum(ending_prices) / simulations
    bull   = ending_prices[int(simulations * 0.90)]
    var_95 = (current_price - ending_prices[int(simulations * 0.05)]) / current_price

    return {
        "current_price": round(current_price, 2),
        "bear":          round(bear,   2),
        "base":          round(base,   2),
        "bull":          round(bull,   2),
        "var_95":        round(var_95 * 100, 2),
        "upside":        round(((bull / current_price) - 1) * 100, 2),
    }


# ──────────────────────────────────────────
#  CHART DATA
# ──────────────────────────────────────────

def build_chart_data(symbol: str) -> dict:
    """
    Returns 1-year price history + MA50 + MA200 for the frontend chart.
    """
    ticker  = yf.Ticker(symbol)
    hist    = ticker.history(period="1y")
    closes  = hist["Close"].tolist()
    dates   = [d.strftime("%b %d") for d in hist.index]

    ma50, ma200 = [], []
    for i in range(len(closes)):
        ma50.append( round(sum(closes[max(0,i-49):i+1]) / min(i+1, 50),  2) if i >= 49  else None)
        ma200.append(round(sum(closes[max(0,i-199):i+1]) / min(i+1, 200), 2) if i >= 199 else None)

    return {
        "labels": dates,
        "prices": [round(p, 2) for p in closes],
        "ma50":   ma50,
        "ma200":  ma200,
    }


# ──────────────────────────────────────────
#  AI INSIGHT GENERATION  (Section 7 from stock1.py)
# ──────────────────────────────────────────

def generate_ai_insight(
    symbol:       str,
    scores:       dict,
    weighting:    dict,
    fundamentals: dict,
    simulation:   dict,
) -> dict:
    """
    Calls Claude to generate structured strategic insights for a stock.
    Returns { summary, risk, positioning, behavioral }
    """
    prompt = f"""You are a quantitative financial analyst. Analyze {symbol}.

Factor scores (0-100): Momentum={scores['momentum']}, Quality={scores['quality']}, Value={scores['value']}, Risk={scores['risk']}.
Composite signal: {weighting['final_score']}/100 → {weighting['label']} (confidence {weighting['confidence']}).

Fundamentals: P/E={fundamentals['pe']}x, ROE={fundamentals['roe']}%, Profit Margin={fundamentals['profit_margin']}%, Revenue Growth={fundamentals['revenue_growth']}%.

Monte Carlo (1Y, 1000 simulations):
  Bull (90th pctile): ${simulation['bull']}
  Base (average):     ${simulation['base']}
  Bear (10th pctile): ${simulation['bear']}
  VaR 95%:           {simulation['var_95']}%
  Upside potential:   {simulation['upside']}%

Return ONLY valid JSON (no markdown, no backticks):
{{
  "summary":     "2 concise sentences covering the overall factor signal and quality of the business",
  "risk":        "1 sentence about downside risk, VaR, and what drives it",
  "positioning": "1 sentence on portfolio sizing and correlation implications",
  "behavioral":  "1 sentence on historical macro or earnings sensitivity patterns"
}}"""

    response = _anthropic.messages.create(
        model      = "claude-opus-4-5",
        max_tokens = 500,
        messages   = [{"role": "user", "content": prompt}],
    )
    import json
    text = response.content[0].text.strip()
    return json.loads(text)


# ──────────────────────────────────────────
#  FREE-FORM AI CHAT
# ──────────────────────────────────────────

def ask_ai_question(message: str, symbol: str | None, portfolio: list[dict]) -> str:
    """
    Answer a natural-language question in the context of a stock and portfolio.
    Returns a plain-text reply (2-3 sentences).
    """
    context_parts = []
    if symbol:
        context_parts.append(f"The user is currently viewing {symbol}.")
    if portfolio:
        port_str = ", ".join(f"{p['symbol']} ({p['weight']}%)" for p in portfolio)
        context_parts.append(f"Their portfolio: {port_str}.")

    context = " ".join(context_parts) or "No specific stock or portfolio context."

    response = _anthropic.messages.create(
        model      = "claude-opus-4-5",
        max_tokens = 300,
        messages   = [{
            "role":    "user",
            "content": (
                f"You are a concise quantitative analyst assistant inside a stock terminal. "
                f"{context} "
                f'User asks: "{message}". '
                f"Reply in 2–3 sentences. Be specific and data-driven."
            ),
        }],
    )
    return response.content[0].text.strip()
