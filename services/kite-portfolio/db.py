"""Postgres: kite_session and portfolio_snapshots."""
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

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


def get_latest_session():
    """Return latest kite session row if not expired, else None."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, access_token, expires_at, created_at
                FROM kite_session ORDER BY id DESC LIMIT 1
                """
            )
            row = cur.fetchone()
    if not row:
        return None
    expires_at = row["expires_at"]
    if isinstance(expires_at, datetime) and expires_at <= datetime.utcnow():
        return None
    return dict(row)


def save_session(access_token: str, valid_hours: int = 24):
    with get_conn() as conn:
        with conn.cursor() as cur:
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=valid_hours)
            cur.execute(
                """
                INSERT INTO kite_session (access_token, expires_at, created_at)
                VALUES (%s, %s, %s)
                """,
                (access_token, expires_at, now),
            )


def save_portfolio_snapshot(rows: list, snapshot_id: str = None):
    """rows: list of dicts with tradingsymbol, type, quantity, average_price, last_price, pnl, pnl_percent, etc."""
    sid = snapshot_id or str(uuid.uuid4())
    now = datetime.utcnow()
    with get_conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO portfolio_snapshots
                    (snapshot_id, snapshot_at, tradingsymbol, type, quantity, average_price,
                     last_price, pnl, pnl_percent, invested, exchange, instrument_token)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        sid,
                        now,
                        r.get("tradingsymbol"),
                        r.get("type", "HOLDING"),
                        r.get("quantity", 0),
                        r.get("average_price", 0),
                        r.get("last_price", 0),
                        r.get("pnl"),
                        r.get("pnl_percent"),
                        r.get("invested"),
                        r.get("exchange"),
                        r.get("instrument_token"),
                    ),
                )
    return sid


def upsert_instruments(rows: list):
    """Upsert instruments (symbol, exchange, instrument_token, segment, instrument_type, name, bse_token, nse_token)."""
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
