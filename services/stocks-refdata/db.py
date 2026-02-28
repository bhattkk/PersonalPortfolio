"""Postgres: read kite_session; write instruments and fundamentals."""
import os
from contextlib import contextmanager
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

POSTGRES_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://portfolio:portfolio@localhost:5432/portfolio",
)


@contextmanager
def get_conn():
    conn = psycopg2.connect(POSTGRES_URL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_latest_kite_token():
    """Return access_token if session exists and not expired."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT access_token, expires_at FROM kite_session ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
    if not row:
        return None
    exp = row["expires_at"]
    if exp and isinstance(exp, datetime) and exp <= datetime.utcnow():
        return None
    return row["access_token"]


def upsert_instruments(rows: list):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO instruments (symbol, exchange, instrument_token, segment, instrument_type, name, bse_token, nse_token, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (symbol, exchange) DO UPDATE SET
                    instrument_token = EXCLUDED.instrument_token,
                    segment = EXCLUDED.segment,
                    instrument_type = EXCLUDED.instrument_type,
                    name = EXCLUDED.name,
                    bse_token = EXCLUDED.bse_token,
                    nse_token = EXCLUDED.nse_token,
                    updated_at = NOW()
                    """,
                    (
                        r.get("symbol"),
                        r.get("exchange"),
                        r.get("instrument_token"),
                        r.get("segment"),
                        r.get("instrument_type"),
                        r.get("name"),
                        r.get("bse_token"),
                        r.get("nse_token"),
                    ),
                )


def upsert_fundamental(symbol: str, market_cap=None, pe=None, pb=None, week_52_high=None, week_52_low=None, source="yfinance"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fundamentals (symbol, market_cap, pe, pb, week_52_high, week_52_low, source, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                market_cap = EXCLUDED.market_cap,
                pe = EXCLUDED.pe,
                pb = EXCLUDED.pb,
                week_52_high = EXCLUDED.week_52_high,
                week_52_low = EXCLUDED.week_52_low,
                source = EXCLUDED.source,
                updated_at = NOW()
                """,
                (symbol, market_cap, pe, pb, week_52_high, week_52_low, source),
            )
