"""Redis: read instrument list (optional from refdata); write LTP."""
import os

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REFDATA_INSTRUMENTS_KEY = "refdata:instruments"
LTP_KEY_PREFIX = "market:ltp:"
LTP_TTL = 300  # 5 min


def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def get_symbols_from_redis(r) -> list:
    """If stocks-refdata has run, symbols are in refdata:instruments (newline-sep)."""
    raw = r.get(REFDATA_INSTRUMENTS_KEY)
    if not raw:
        return []
    return [s.strip() for s in raw.split("\n") if s.strip()]


def set_ltp(r, instrument_token: int, ltp: float, exchange: str = None, tradingsymbol: str = None):
    key = f"{LTP_KEY_PREFIX}{instrument_token}"
    r.setex(key, LTP_TTL, str(ltp))
    if exchange and tradingsymbol:
        key2 = f"{LTP_KEY_PREFIX}{exchange}:{tradingsymbol}"
        r.setex(key2, LTP_TTL, str(ltp))
