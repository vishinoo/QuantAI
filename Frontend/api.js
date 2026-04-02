/**
 * api.js — QuantAI Frontend API Layer
 *
 * All fetch calls to the Python backend live here.
 * Import individual functions wherever needed.
 * Base URL is read from the environment (set in .env or swap for your prod URL).
 */

const BASE_URL = window.QUANTAI_API_URL || "http://localhost:8000";

/**
 * Helper: attach the Firebase auth token to every request.
 * Imported lazily so auth.js doesn't need to be loaded first.
 */
async function authHeaders() {
  try {
    const { getToken } = await import("./auth.js");
    const token = await getToken();
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  } catch {
    return { "Content-Type": "application/json" };
  }
}

/**
 * Helper: uniform error handling.
 */
async function request(path, options = {}) {
  const headers = await authHeaders();
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/* ─────────────────────────────────────────
   STOCK ANALYSIS
───────────────────────────────────────── */

/**
 * Run full factor analysis + Monte Carlo on a single symbol.
 * Returns { symbol, price, change, scores, simulation, insights }
 */
export async function analyzeStock(symbol) {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ symbol: symbol.toUpperCase() }),
  });
}

/**
 * Fetch brief fundamental data for a symbol (lighter than full analysis).
 */
export async function getStockInfo(symbol) {
  return request(`/api/stock/${symbol.toUpperCase()}`);
}

/* ─────────────────────────────────────────
   PORTFOLIO
───────────────────────────────────────── */

/**
 * Load the authenticated user's saved portfolio.
 * Returns [{ symbol, weight }]
 */
export async function getPortfolio() {
  return request("/api/portfolio");
}

/**
 * Overwrite the user's portfolio with a new allocation list.
 * @param {Array<{symbol: string, weight: number}>} items
 */
export async function savePortfolio(items) {
  return request("/api/portfolio", {
    method: "PUT",
    body: JSON.stringify({ items }),
  });
}

/**
 * Add a single stock to the portfolio (server merges / upserts).
 */
export async function addToPortfolio(symbol, weight) {
  return request("/api/portfolio/add", {
    method: "POST",
    body: JSON.stringify({ symbol: symbol.toUpperCase(), weight }),
  });
}

/**
 * Remove a stock from the portfolio.
 */
export async function removeFromPortfolio(symbol) {
  return request(`/api/portfolio/${symbol.toUpperCase()}`, { method: "DELETE" });
}

/**
 * Run the portfolio engine: compute impact of adding a candidate stock.
 * Returns { delta_return, delta_vol, new_sector, warning }
 */
export async function analyzePortfolioImpact(portfolio, candidateSymbol) {
  return request("/api/portfolio/impact", {
    method: "POST",
    body: JSON.stringify({
      portfolio,                           // { AAPL: 0.6, MSFT: 0.4 }
      candidate: candidateSymbol.toUpperCase(),
    }),
  });
}

/* ─────────────────────────────────────────
   WATCHLIST
───────────────────────────────────────── */

/**
 * Returns the saved watchlist for the authenticated user.
 * Returns [{ symbol, name, price, change, up }]
 */
export async function getWatchlist() {
  return request("/api/watchlist");
}

/**
 * Add a ticker to the watchlist.
 */
export async function addToWatchlist(symbol) {
  return request("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol: symbol.toUpperCase() }),
  });
}

/**
 * Remove a ticker from the watchlist.
 */
export async function removeFromWatchlist(symbol) {
  return request(`/api/watchlist/${symbol.toUpperCase()}`, { method: "DELETE" });
}

/* ─────────────────────────────────────────
   AI CHAT / INSIGHTS
───────────────────────────────────────── */

/**
 * Send a natural-language question to the AI assistant.
 * @param {string} message    User's question
 * @param {string|null} symbol  Active stock context, if any
 * @param {Array} portfolio   Current portfolio for context
 * Returns { reply: string }
 */
export async function askAI(message, symbol = null, portfolio = []) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, symbol, portfolio }),
  });
}

/* ─────────────────────────────────────────
   SIMULATION
───────────────────────────────────────── */

/**
 * Run a standalone Monte Carlo simulation.
 * @param {string} symbol
 * @param {number} days         Default 252 (1 trading year)
 * @param {number} simulations  Default 1000
 */
export async function runSimulation(symbol, days = 252, simulations = 1000) {
  return request("/api/simulate", {
    method: "POST",
    body: JSON.stringify({ symbol: symbol.toUpperCase(), days, simulations }),
  });
}

/* ─────────────────────────────────────────
   PERFORMANCE TRACKING
───────────────────────────────────────── */

/**
 * Log a user decision (buy/sell) for tracking prediction vs reality.
 */
export async function logDecision(symbol, action, price) {
  return request("/api/decisions", {
    method: "POST",
    body: JSON.stringify({ symbol, action, price }),
  });
}

/**
 * Get model vs user performance metrics.
 */
export async function getPerformance() {
  return request("/api/performance");
}
