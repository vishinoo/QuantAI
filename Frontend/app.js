/**
 * app.js — QuantAI Main Application Controller
 *
 * Responsibilities:
 *  - Listen for auth state (show login vs app)
 *  - Populate watchlist + portfolio from backend
 *  - Handle all user interactions (search, add/remove, AI chat)
 *  - Render stock analysis results from the backend
 *  - Drive Chart.js charts
 *
 * This file replaces all inline <script> that was previously in the HTML.
 */

import { onAuth, getUserProfile } from "./auth.js";
import {
  analyzeStock,
  getWatchlist,  addToWatchlist,  removeFromWatchlist,
  getPortfolio,  addToPortfolio,  removeFromPortfolio, savePortfolio,
  askAI,
  runSimulation,
} from "./api.js";

/* ─────────────────────────────────────────
   STATE
───────────────────────────────────────── */
let state = {
  currentSymbol: null,
  watchlist:     [],    // [{ symbol, name, price, change, up }]
  portfolio:     [],    // [{ symbol, weight }]
  analysisCache: {},    // { AAPL: { ...data } }
  priceChart:    null,
};

/* ─────────────────────────────────────────
   ENTRY POINT  (called from index.html module script)
───────────────────────────────────────── */
export function initApp() {
  onAuth(handleAuthChange);
  bindStaticEvents();
}

/* ─────────────────────────────────────────
   AUTH STATE
───────────────────────────────────────── */
function handleAuthChange(user) {
  if (user) {
    showApp(user);
  } else {
    showLoginScreen();
  }
}

function showLoginScreen() {
  document.getElementById("login-screen").classList.remove("hidden");
  document.getElementById("app").classList.add("hidden");
}

async function showApp(user) {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");

  // Populate user avatar + name
  const profile = getUserProfile();
  if (profile) {
    const avatarEl = document.getElementById("user-avatar");
    const nameEl   = document.getElementById("user-name");
    if (profile.photoURL) avatarEl.src = profile.photoURL;
    nameEl.textContent = profile.name || profile.email;
  }

  await loadUserData();
}

/* ─────────────────────────────────────────
   LOAD PERSISTED DATA FROM BACKEND
───────────────────────────────────────── */
async function loadUserData() {
  try {
    const [watchlist, portfolio] = await Promise.all([
      getWatchlist(),
      getPortfolio(),
    ]);
    state.watchlist = watchlist;
    state.portfolio = portfolio;
  } catch (err) {
    console.warn("Could not load user data from backend, using defaults:", err);
    // Seed defaults for first-time users
    state.watchlist = [
      { symbol: "AAPL", name: "Apple Inc.",       price: "196.45", change: "+1.24%", up: true  },
      { symbol: "MSFT", name: "Microsoft Corp.",   price: "414.28", change: "+0.87%", up: true  },
      { symbol: "NVDA", name: "NVIDIA Corp.",      price: "875.39", change: "−0.43%", up: false },
      { symbol: "TSLA", name: "Tesla Inc.",        price: "248.11", change: "+2.15%", up: true  },
    ];
    state.portfolio = [{ symbol: "AAPL", weight: 60 }, { symbol: "MSFT", weight: 40 }];
  }

  renderWatchlist();
  renderPortfolio();
}

/* ─────────────────────────────────────────
   EVENT BINDINGS
───────────────────────────────────────── */
function bindStaticEvents() {
  // Search
  document.getElementById("analyze-btn").addEventListener("click", onAnalyzeClick);
  document.getElementById("search-input").addEventListener("keydown", e => {
    if (e.key === "Enter") onAnalyzeClick();
  });

  // Watchlist add
  document.getElementById("wl-add-btn").addEventListener("click", onAddWatchlist);
  document.getElementById("wl-input").addEventListener("keydown", e => {
    if (e.key === "Enter") onAddWatchlist();
  });

  // Portfolio add
  document.getElementById("port-add-btn").addEventListener("click", onAddPortfolio);

  // AI chat
  document.getElementById("ai-send-btn").addEventListener("click", onSendAI);
  document.getElementById("ai-input").addEventListener("keydown", e => {
    if (e.key === "Enter") onSendAI();
  });

  // Quick-pick chips in empty state
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const sym = chip.dataset.sym;
      document.getElementById("search-input").value = sym;
      onAnalyzeClick();
    });
  });
}

/* ─────────────────────────────────────────
   SEARCH / ANALYZE
───────────────────────────────────────── */
async function onAnalyzeClick() {
  const raw = document.getElementById("search-input").value.trim().toUpperCase();
  if (!raw) return;
  await loadStock(raw);
}

async function loadStock(symbol) {
  state.currentSymbol = symbol;
  renderWatchlist(); // highlight active

  // Ensure it's in watchlist
  if (!state.watchlist.find(s => s.symbol === symbol)) {
    try {
      const info = await addToWatchlist(symbol);
      state.watchlist.unshift(info);
      renderWatchlist();
    } catch {
      state.watchlist.unshift({ symbol, name: symbol + " Corp.", price: "—", change: "—", up: true });
      renderWatchlist();
    }
  }

  showMainLoading(symbol);

  // Use cache if available
  if (state.analysisCache[symbol]) {
    renderStockPanel(state.analysisCache[symbol]);
    return;
  }

  try {
    const data = await analyzeStock(symbol);
    state.analysisCache[symbol] = data;
    renderStockPanel(data);
  } catch (err) {
    showMainError(symbol, err.message);
  }
}

/* ─────────────────────────────────────────
   WATCHLIST HANDLERS
───────────────────────────────────────── */
async function onAddWatchlist() {
  const inp = document.getElementById("wl-input");
  const sym = inp.value.trim().toUpperCase();
  if (!sym || state.watchlist.find(s => s.symbol === sym)) return;
  inp.value = "";

  // Optimistic add
  const optimistic = { symbol: sym, name: sym + " Corp.", price: "…", change: "…", up: true };
  state.watchlist.unshift(optimistic);
  renderWatchlist();

  try {
    const info = await addToWatchlist(sym);
    // Replace optimistic entry with real data
    state.watchlist = state.watchlist.map(s => s.symbol === sym ? info : s);
  } catch (err) {
    console.warn("Add to watchlist failed:", err);
  }
  renderWatchlist();
}

async function onRemoveWatchlist(symbol) {
  state.watchlist = state.watchlist.filter(s => s.symbol !== symbol);
  if (state.currentSymbol === symbol) {
    state.currentSymbol = null;
    showEmptyState();
  }
  renderWatchlist();
  try { await removeFromWatchlist(symbol); } catch { /* silent */ }
}

/* ─────────────────────────────────────────
   PORTFOLIO HANDLERS
───────────────────────────────────────── */
async function onAddPortfolio() {
  const sym = document.getElementById("port-sym").value.trim().toUpperCase();
  const wt  = parseInt(document.getElementById("port-wt").value) || 10;
  if (!sym) return;

  document.getElementById("port-sym").value = "";
  document.getElementById("port-wt").value  = "";

  const existing = state.portfolio.findIndex(p => p.symbol === sym);
  if (existing >= 0) {
    state.portfolio[existing].weight = wt;
  } else {
    state.portfolio.push({ symbol: sym, weight: wt });
  }
  renderPortfolio();
  try { await addToPortfolio(sym, wt); } catch { /* silent */ }
}

async function onRemovePortfolio(symbol) {
  state.portfolio = state.portfolio.filter(p => p.symbol !== symbol);
  renderPortfolio();
  try { await removeFromPortfolio(symbol); } catch { /* silent */ }
}

// Called from the "Add to Portfolio" button inside the stock panel
window.addCurrentToPortfolio = async function(symbol) {
  const existing = state.portfolio.find(p => p.symbol === symbol);
  if (!existing) {
    state.portfolio.push({ symbol, weight: 10 });
    renderPortfolio();
    try { await addToPortfolio(symbol, 10); } catch { /* silent */ }
  }
};

// Called from "Re-run Simulation"
window.rerunSimulation = async function(symbol) {
  delete state.analysisCache[symbol];
  await loadStock(symbol);
};

/* ─────────────────────────────────────────
   AI CHAT
───────────────────────────────────────── */
async function onSendAI() {
  const inp = document.getElementById("ai-input");
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = "";

  appendChatMessage(msg, "user-msg");
  const loadEl = appendChatMessage("Thinking…", "ai loading");

  try {
    const { reply } = await askAI(msg, state.currentSymbol, state.portfolio);
    loadEl.textContent = reply;
    loadEl.classList.remove("loading");
  } catch {
    loadEl.textContent = "Unable to connect to AI. Check your API configuration.";
  }
}

function appendChatMessage(text, cls = "ai") {
  const box = document.getElementById("chat-box");
  const el  = document.createElement("div");
  el.className = `chat-msg ${cls}`;
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

/* ─────────────────────────────────────────
   RENDER — WATCHLIST
───────────────────────────────────────── */
function renderWatchlist() {
  document.getElementById("wl-list").innerHTML = state.watchlist.map(s => `
    <div class="wl-card${state.currentSymbol === s.symbol ? " active" : ""}"
         onclick="window._loadStock('${s.symbol}')">
      <div class="wl-card-top">
        <div>
          <div class="wl-sym">${s.symbol}</div>
          <div class="wl-name">${s.name}</div>
        </div>
        <button class="wl-rmv" onclick="event.stopPropagation();window._rmWL('${s.symbol}')">✕</button>
      </div>
      <div class="wl-bottom">
        <span class="wl-price">$${s.price}</span>
        <span class="badge ${s.up ? "pos" : "neg"}">${s.change}</span>
      </div>
    </div>`).join("");
}

/* ─────────────────────────────────────────
   RENDER — PORTFOLIO
───────────────────────────────────────── */
function renderPortfolio() {
  const total = state.portfolio.reduce((a, p) => a + p.weight, 0);
  document.getElementById("port-list").innerHTML = state.portfolio.map(p => `
    <div class="port-item">
      <span class="port-sym">${p.symbol}</span>
      <div class="port-bar-bg">
        <div class="port-bar-fill" style="width:${Math.round((p.weight / Math.max(total, 100)) * 100)}%"></div>
      </div>
      <span class="port-wt">${p.weight}%</span>
      <button class="port-rm" onclick="window._rmPort('${p.symbol}')">✕</button>
    </div>`).join("");
}

/* ─────────────────────────────────────────
   RENDER — MAIN PANEL STATES
───────────────────────────────────────── */
function showEmptyState() {
  document.getElementById("empty-state").classList.remove("hidden");
  document.getElementById("stock-content").classList.add("hidden");
}

function showMainLoading(symbol) {
  document.getElementById("empty-state").classList.add("hidden");
  const content = document.getElementById("stock-content");
  content.classList.remove("hidden");
  content.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      Running factor analysis for <strong style="margin-left:4px">${symbol}</strong>…
    </div>`;
}

function showMainError(symbol, message) {
  document.getElementById("stock-content").innerHTML = `
    <div class="card" style="color:var(--neg)">
      <strong>${symbol}</strong> — Analysis failed: ${message}
      <br><button class="btn" style="margin-top:12px" onclick="window._loadStock('${symbol}')">Retry</button>
    </div>`;
}

/* ─────────────────────────────────────────
   RENDER — STOCK ANALYSIS PANEL
   Expects the data shape returned by /api/analyze:
   {
     symbol, name, price, change, up,
     scores: { momentum, quality, value, risk, composite, label },
     fundamentals: { pe, roe, profit_margin, revenue_growth },
     simulation: { bear, base, bull, var_95, upside },
     insights: { summary, risk, positioning, behavioral }
   }
───────────────────────────────────────── */
function renderStockPanel(data) {
  const { symbol, name, price, change, up, scores, fundamentals: f, simulation: sim, insights } = data;
  const w   = scores.composite;
  const cls = w >= 80 ? "acc" : w >= 60 ? "pos" : w < 40 ? "neg" : "neu";

  const factorColor = { Momentum: "#1a3a6b", Quality: "#5c1a6b", Value: "#7a5c1a", Risk: "#1a6b3c" };
  const valueColor  = (v, pos) => parseFloat(v) >= 0 ? (pos || "var(--pos)") : "var(--neg)";

  const insightItems = [
    { tag: "Summary",     body: insights.summary,     cls: "acc"   },
    { tag: "Risk",        body: insights.risk,        cls: w < 40 ? "neg" : w > 70 ? "pos" : "amber" },
    { tag: "Positioning", body: insights.positioning, cls: "ink3"  },
    { tag: "Behavioral",  body: insights.behavioral,  cls: "ink3"  },
  ];

  const content = document.getElementById("stock-content");
  content.classList.remove("hidden");
  document.getElementById("empty-state").classList.add("hidden");

  content.innerHTML = `
    <!-- Header card -->
    <div class="card">
      <div class="stock-header">
        <div>
          <div class="stock-sym">${symbol}</div>
          <div class="stock-name">${name}</div>
        </div>
        <div>
          <div class="stock-price">$${price}</div>
          <div class="stock-chg ${up ? "pos" : "neg"}">${change} today</div>
        </div>
      </div>
      <div class="rule"></div>
      <div class="score-wrap">
        <div class="score-circle" style="border-color:${scoreColor(w)}">
          <div class="score-num" style="color:${scoreColor(w)}">${w}</div>
          <div class="score-sub">Score</div>
        </div>
        <div style="flex:1">
          <div class="badge-row">
            <span class="badge ${cls}">${scores.label}</span>
            <span class="badge-desc">Weighted composite signal</span>
          </div>
          <div class="factors">
            ${["Momentum","Quality","Value","Risk"].map(n => `
              <div class="factor-row">
                <span class="factor-name">${n}</span>
                <div class="factor-track">
                  <div class="factor-fill" style="width:${scores[n.toLowerCase()]}%;background:${factorColor[n]}"></div>
                </div>
                <span class="factor-val">${scores[n.toLowerCase()]}</span>
              </div>`).join("")}
          </div>
        </div>
      </div>
    </div>

    <!-- Metrics grid -->
    <div class="metrics-grid">
      <div class="metric"><div class="ml">P / E Ratio</div><div class="mv">${f.pe}×</div><div class="ms">Trailing 12m</div></div>
      <div class="metric"><div class="ml">ROE</div><div class="mv">${f.roe}%</div><div class="ms">Return on equity</div></div>
      <div class="metric"><div class="ml">Profit Margin</div><div class="mv">${f.profit_margin}%</div><div class="ms">Net margin</div></div>
      <div class="metric">
        <div class="ml">Revenue Growth</div>
        <div class="mv" style="color:${valueColor(f.revenue_growth)}">${parseFloat(f.revenue_growth) >= 0 ? "+" : ""}${f.revenue_growth}%</div>
        <div class="ms">Year-over-year</div>
      </div>
      <div class="metric"><div class="ml">Bull Upside</div><div class="mv pos">+${sim.upside}%</div><div class="ms">90th percentile</div></div>
      <div class="metric">
        <div class="ml">VaR 95%</div>
        <div class="mv ${parseFloat(sim.var_95) > 20 ? "neg" : "amber"}">${sim.var_95}%</div>
        <div class="ms">1-year downside</div>
      </div>
    </div>

    <!-- Price chart -->
    <div class="card">
      <div class="card-header">
        <span class="heading">Price History &amp; Moving Averages</span>
        <div class="chart-legend">
          <span class="legend-item"><span class="legend-line" style="border-color:#1a3a6b"></span>Price</span>
          <span class="legend-item"><span class="legend-line" style="border-color:#7a5c1a;border-style:dashed"></span>MA 50</span>
          <span class="legend-item"><span class="legend-line" style="border-color:#8b1a1a;border-style:dashed"></span>MA 200</span>
        </div>
      </div>
      <div style="position:relative;height:180px"><canvas id="price-chart"></canvas></div>
    </div>

    <!-- Simulation + distribution -->
    <div class="sim-grid">
      <div class="card">
        <span class="label" style="margin-bottom:0">Monte Carlo — 1-Year</span>
        <div class="rule"></div>
        <div class="sim-row"><span class="sim-label">Bull case (90th pctile)</span><span class="sim-val" style="color:var(--pos)">$${sim.bull}</span></div>
        <div class="sim-row"><span class="sim-label">Base case (average)</span>  <span class="sim-val">$${sim.base}</span></div>
        <div class="sim-row"><span class="sim-label">Bear case (10th pctile)</span><span class="sim-val" style="color:var(--neg)">$${sim.bear}</span></div>
        <div class="sim-row"><span class="sim-label">Value at Risk (95%)</span>  <span class="sim-val" style="color:var(--amber)">${sim.var_95}%</span></div>
      </div>
      <div class="card">
        <span class="label" style="margin-bottom:0">Scenario Distribution</span>
        <div class="rule"></div>
        <div style="position:relative;height:120px"><canvas id="dist-chart"></canvas></div>
      </div>
    </div>

    <!-- AI Insights -->
    <div class="card">
      <div class="card-header" style="margin-bottom:4px">
        <span class="heading">AI Strategic Insights</span>
        <span style="font-size:10px;color:var(--pos)">● Live</span>
      </div>
      ${insightItems.map(i => `
        <div class="insight">
          <div class="insight-tag" style="color:var(--${i.cls})">${i.tag}</div>
          <div class="insight-body">${i.body}</div>
        </div>`).join("")}
    </div>

    <!-- Actions -->
    <div class="action-row">
      <button class="btn primary" onclick="window.addCurrentToPortfolio('${symbol}')">+ Add to Portfolio</button>
      <button class="btn"         onclick="window.rerunSimulation('${symbol}')">↻ Re-run Simulation</button>
    </div>
  `;

  // Draw charts after DOM updates
  requestAnimationFrame(() => {
    drawPriceChart(data.chart_data || generateFallbackChartData(parseFloat(price)));
    drawDistChart(sim);
  });
}

/* ─────────────────────────────────────────
   CHARTS
───────────────────────────────────────── */
function drawPriceChart(data) {
  if (state.priceChart) state.priceChart.destroy();
  const ctx = document.getElementById("price-chart");
  if (!ctx) return;

  state.priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        { label: "Price", data: data.prices, borderColor: "#1a3a6b", borderWidth: 1.5, pointRadius: 0, fill: true, backgroundColor: "rgba(26,58,107,0.05)", tension: 0.3 },
        { label: "MA 50",  data: data.ma50,   borderColor: "#7a5c1a", borderWidth: 1, pointRadius: 0, borderDash: [4,4], tension: 0.3 },
        { label: "MA 200", data: data.ma200,  borderColor: "#8b1a1a", borderWidth: 1, pointRadius: 0, borderDash: [6,3], tension: 0.3 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { mode: "index", intersect: false, backgroundColor: "#fff", titleColor: "#8a8578", bodyColor: "#1a1916", borderColor: "#e5e1da", borderWidth: 1, padding: 10 },
      },
      scales: {
        x: { display: false },
        y: { grid: { color: "rgba(229,225,218,0.8)" }, ticks: { color: "#8a8578", font: { family: "IBM Plex Mono", size: 10 } }, border: { display: false } },
      },
    },
  });
}

function drawDistChart(sim) {
  const ctx = document.getElementById("dist-chart");
  if (!ctx) return;

  const bear = parseFloat(sim.bear), base = parseFloat(sim.base), bull = parseFloat(sim.bull);
  const rng  = bull - bear;
  const vals = [bear, bear+rng*0.15, bear+rng*0.35, base, base+rng*0.2, base+rng*0.4, bull].map(v => parseFloat(v.toFixed(2)));

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["P10","P20","P40","Base","P60","P80","P90"],
      datasets: [{
        data: vals,
        backgroundColor: vals.map(v => v < base ? "rgba(139,26,26,0.2)" : "rgba(26,107,60,0.2)"),
        borderColor:     vals.map(v => v < base ? "rgba(139,26,26,0.6)" : "rgba(26,107,60,0.6)"),
        borderWidth: 1, borderRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#fff", bodyColor: "#1a1916", borderColor: "#e5e1da", borderWidth: 1 } },
      scales: {
        x: { ticks: { color: "#8a8578", font: { family: "IBM Plex Mono", size: 10 } }, grid: { display: false }, border: { display: false } },
        y: { display: false },
      },
    },
  });
}

/* Generate client-side chart data when backend doesn't return it */
function generateFallbackChartData(price) {
  const n = 252;
  const labels = [], prices = [], ma50 = [], ma200 = [], hist = [];
  let p = price * (0.78 + Math.random() * 0.15);

  for (let i = 0; i < n; i++) {
    labels.push(new Date(Date.now() - (n - i) * 86400000).toLocaleDateString("en", { month: "short", day: "numeric" }));
    p *= (1 + (Math.random() - 0.48) * 0.025);
    hist.push(p);
  }
  hist[hist.length - 1] = price;

  for (let i = 0; i < n; i++) {
    prices.push(parseFloat(hist[i].toFixed(2)));
    ma50.push(i >= 49  ? parseFloat((hist.slice(i-49,  i+1).reduce((a,v)=>a+v,0) / 50 ).toFixed(2)) : null);
    ma200.push(i >= 199 ? parseFloat((hist.slice(i-199, i+1).reduce((a,v)=>a+v,0) / 200).toFixed(2)) : null);
  }
  return { labels, prices, ma50, ma200 };
}

/* ─────────────────────────────────────────
   HELPERS
───────────────────────────────────────── */
function scoreColor(w) {
  return w >= 60 ? "var(--pos)" : w < 40 ? "var(--neg)" : "var(--amber)";
}

// Expose functions referenced by inline onclick attributes
window._loadStock = symbol => loadStock(symbol);
window._rmWL      = symbol => onRemoveWatchlist(symbol);
window._rmPort    = symbol => onRemovePortfolio(symbol);
