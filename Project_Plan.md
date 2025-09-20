# Personal Portfolio Analysis Project

This project integrates **Zerodha Kite API**, **quantitative research tools**, and **Telegram bot reports** to analyze a personal stock portfolio with both technical and fundamental insights.

---

## 📌 Project Goals
1. Fetch real-time portfolio and watchlist data from **Kite API**.
2. Apply **custom technical and fundamental analysis**.
3. Generate **signals, scans, and risk metrics**.
4. Deliver daily/weekly **portfolio reports to Telegram bot** (on-demand or scheduled).

---

## 🔄 High-Level Workflow
1. **Data Ingestion**
   - Use Kite Connect API to fetch:
     - Current portfolio holdings
     - Watchlist instruments
     - Historical OHLC data (for backtesting)

2. **Feature Engineering**
   - Technical indicators: Moving Averages, RSI, MACD, Bollinger Bands
   - Fundamental factors: P/E, PEG, ROE, Debt/Equity (via external APIs like Alpha Vantage, Yahoo Finance, or Perplexity Finance if available)
   - Derived signals: Momentum scores, Risk-adjusted returns, Sector comparisons

3. **Strategy Layer**
   - Apply custom screening criteria
   - Combine **technical signals + fundamental scores**
   - Rank instruments for buy/sell/hold

4. **Output & Alerts**
   - Generate reports in **Markdown / table format**
   - Send via **Telegram bot**:
     - **On-demand query**: request latest analysis by messaging bot
     - **Scheduled alerts**: daily/weekly summary at fixed times

---

## 🛠 Tools & Libraries
- **Data APIs**: Zerodha Kite Connect, Yahoo Finance, Alpha Vantage, Perplexity Finance (if API available)
- **Quant Research**:
  - [Microsoft Qlib](https://github.com/microsoft/qlib) → quantitative research & model training
  - TA-Lib / pandas-ta → technical indicators
  - Scikit-learn / PyTorch / TensorFlow → ML models for alpha factors
- **Messaging & Reports**:
  - Telegram Bot API (`python-telegram-bot`)
  - Cron / APScheduler for scheduled jobs
  - Pandas DataFrames for tabular outputs

---

## 📚 Related Research & Projects
- **Microsoft Qlib**: AI-oriented quantitative investment platform
- **Fama-French Factors**: Combining fundamental + technical factors
- **Quantopian (archived)**: Algorithmic trading research platform
- **Backtrader**: Python library for strategy backtesting
- **Deep Reinforcement Learning for Stock Trading** (papers using RL + technical signals)

---

## 🚀 Suggested Phased Implementation

### Phase 1 – Basic Data Pipeline
- Fetch portfolio & watchlist from Kite API
- Send raw snapshot to Telegram bot (on request)

### Phase 2 – Technical Analysis
- Compute indicators (RSI, MACD, Moving Averages)
- Add scans based on rules (e.g., RSI < 30 = Oversold)
- Send results as a formatted table to Telegram

### Phase 3 – Fundamental Integration
- Pull company fundamentals (P/E, PEG, EPS growth)
- Combine with technical scores for ranking
- Push integrated signals to Telegram

### Phase 4 – Advanced Research
- Experiment with Qlib for factor models
- Train ML models on historical data
- Backtest strategies
- Extend Telegram bot to support commands like `/report`, `/signal`, `/compare INFY TCS`

---

# Project Folder Structure – Portfolio Analyzer

This document describes the suggested skeleton for the portfolio analyzer project.

---

## Root Level
- **README.md** → High-level description of the project
- **requirements.txt** → List of dependencies (`pykiteconnect`, `redis`, `python-telegram-bot`, `pandas-ta`, `qlib`, etc.)
- **config.yaml** → Central config file for API keys, Redis settings, Telegram token
- **main.py** → Entry point for running the app (scheduler, CLI triggers)

---

## `src/` – Core Source Code

### `data/`
- `kite_api.py` → Fetch portfolio, positions, and historical OHLC data using Kite API
- `fundamentals.py` → Pull stock fundamentals (e.g., from Yahoo/Alpha Vantage)
- `storage.py` → Store/retrieve data in Redis or another DB

### `analysis/`
- `technicals.py` → Compute RSI, MACD, Bollinger Bands, Moving Averages
- `fundamentals.py` → Score stocks based on P/E, PEG, growth, etc.
- `qlib_runner.py` → Integrate Microsoft Qlib for strategy backtesting
- `signals.py` → Generate final buy/sell/hold signals by combining analysis

### `bots/`
- `telegram_bot.py` → Telegram bot setup, command handlers (`/report`, `/addstock`)
- `reports.py` → Format and send reports to Telegram (Markdown tables, alerts)

### `utils/`
- `logger.py` → Centralized logging
- `scheduler.py` → APScheduler or cron integration for scheduled reports
- `formatter.py` → Convert pandas DataFrames to Markdown/Telegram messages

---

## `tests/`
- `test_data.py` → Test data fetching & storage
- `test_analysis.py` → Test technical/fundamental analysis
- `test_bots.py` → Test Telegram bot interactions
- `test_end2end.py` → End-to-end test for pipeline (data → analysis → report)

---

## `notebooks/`
- `indicators.ipynb` → Research and visualization of technical indicators
- `qlib_backtest.ipynb` → Experiments with Qlib backtesting and ML strategies

---

## ✅ Benefits of this Structure
- **Modular** → Each layer (data, analysis, bot) is independent
- **Extensible** → Easy to add new strategies, APIs, or output channels
- **Testable** → Clear separation enables unit and end-to-end testing
- **Research-friendly** → `notebooks/` allows fast prototyping before moving code into `src/`

