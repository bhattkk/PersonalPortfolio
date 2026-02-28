-- Portfolio app schema: instruments, fundamentals, kite_session, portfolio_snapshots

CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(64) NOT NULL,
    exchange VARCHAR(16) NOT NULL,
    instrument_token BIGINT NOT NULL,
    segment VARCHAR(32),
    instrument_type VARCHAR(16),
    name VARCHAR(255),
    bse_token VARCHAR(32),
    nse_token VARCHAR(32),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, exchange)
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_exchange ON instruments(exchange);
CREATE INDEX IF NOT EXISTS idx_instruments_type ON instruments(instrument_type);

CREATE TABLE IF NOT EXISTS fundamentals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(64) NOT NULL UNIQUE,
    market_cap NUMERIC,
    pe NUMERIC,
    pb NUMERIC,
    week_52_high NUMERIC,
    week_52_low NUMERIC,
    source VARCHAR(32) DEFAULT 'yfinance',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kite_session (
    id SERIAL PRIMARY KEY,
    access_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Single row or latest-wins: application uses ORDER BY id DESC LIMIT 1
CREATE INDEX IF NOT EXISTS idx_kite_session_expires ON kite_session(expires_at);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_id UUID NOT NULL DEFAULT gen_random_uuid(),
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tradingsymbol VARCHAR(64) NOT NULL,
    type VARCHAR(16) NOT NULL,  -- 'HOLDING' or 'POSITION'
    quantity INTEGER NOT NULL,
    average_price NUMERIC NOT NULL,
    last_price NUMERIC NOT NULL,
    pnl NUMERIC,
    pnl_percent NUMERIC,
    invested NUMERIC,
    exchange VARCHAR(16),
    instrument_token BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_at ON portfolio_snapshots(snapshot_at);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_symbol ON portfolio_snapshots(tradingsymbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_snapshot_id ON portfolio_snapshots(snapshot_id);
