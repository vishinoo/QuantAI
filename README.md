# QuantAI — Decision Engine for Equity Investing

QuantAI is a quant-driven equity intelligence platform designed to turn fragmented financial data into structured, actionable decisions. Instead of presenting isolated metrics, the system aggregates momentum, value, quality, and risk factors into a unified scoring model, contextualizes them with price behavior and historical trends, and evaluates how each stock impacts a user’s portfolio in real time.

The platform also incorporates probabilistic modeling through Monte Carlo simulations and an AI-driven insight layer that translates outputs into clear reasoning around risk, positioning, and potential outcomes.

---

## 🧠 Core Idea

Most investing tools optimize for **information density**.  
QuantAI is built to optimize for **decision quality**.

Search a stock → instantly understand:
- Should I buy this?
- Why?
- What are the risks?
- How does it affect my portfolio?

---

## ⚙️ Features

### 📊 Factor-Based Scoring
- Momentum, Value, Quality, Risk
- Normalized scoring system (0–100)
- Weighted composite signal (Buy / Sell / Neutral)

### 📈 Price Context & Trends
- Historical price chart
- Moving averages (MA50, MA200)
- Trend visualization

### 📦 Portfolio Engine
- Add/remove positions
- Real-time portfolio impact:
  - Expected return change
  - Volatility shift
  - Exposure insights

### 🎲 Monte Carlo Simulation + AI Insights
- Probabilistic price projections
- Bull / Base / Bear scenarios
- Value-at-Risk (VaR)
- AI-generated strategic insights explaining:
  - Risk
  - Positioning
  - Behavioral patterns

### 🧾 Watchlist System
- Track multiple stocks
- Quick access to analysis

---

## 🏗️ Tech Stack

**Frontend**
- HTML / CSS / JavaScript
- Chart.js for visualization

**Backend (Prototype)**
- Python
- yfinance for market + fundamental data
- Pandas for data processing

---

## 🚧 Current State (Prototype)

This project is intentionally built as a **functional prototype**, not a fully deployed production app.

The original vision includes:
- Google authentication
- Persistent user portfolios
- Real-time AI-powered insights
- Cloud-hosted backend

However, these features were **intentionally deferred** to:
- Avoid paying for APIs (e.g., Firebase, AI services)
- Validate the core product idea first
- Focus on the decision engine rather than infrastructure

---

## 🎯 Goal

To build a **retail quant terminal** that:
- Reduces noise
- Improves decision-making
- Connects analysis directly to portfolio impact

---

## 📌 Future Improvements

- Full backend API (FastAPI)
- User authentication (Firebase / OAuth)
- Database for persistent portfolios
- Live data pipelines (Polygon / institutional-grade APIs)
- Advanced backtesting engine
- Custom factor weighting + strategy builder

---

## ⚠️ Disclaimer

This tool is for educational and experimental purposes only.  
It is not financial advice.

---

## 👤 Author

Built to explore how structured systems can improve decision-making in financial markets.
