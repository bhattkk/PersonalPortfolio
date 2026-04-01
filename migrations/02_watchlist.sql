-- User watchlist: symbols of interest (updated by app / jobs)

CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    last_price NUMERIC,
    instrument_token BIGINT NOT NULL UNIQUE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist(symbol);
