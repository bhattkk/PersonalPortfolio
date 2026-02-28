"""Read instruments from Postgres (instrument_token for Kite LTP); read kite session."""
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
    finally:
        conn.close()


def get_kite_token():
    """Return access_token if session exists and not expired."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT access_token, expires_at FROM kite_session ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
    if not row:
        return None
    if row["expires_at"] and row["expires_at"] <= datetime.utcnow():
        return None
    return row["access_token"]


def get_eq_index_instrument_tokens(limit=1000):
    """Return list of (instrument_token, exchange, tradingsymbol) for EQ and INDEX."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT instrument_token, exchange, symbol as tradingsymbol
                FROM instruments
                WHERE instrument_type IN ('EQ', 'INDEX')
                ORDER BY exchange, symbol
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
