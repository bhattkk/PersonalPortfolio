"""
Single job: fetch Kite instruments (EQ+INDEX), yfinance fundamentals; write Postgres + Redis.
Uses Kite token from Postgres (shared with kite-portfolio).
"""
import logging
import os

import redis
import yfinance as yf
from kiteconnect import KiteConnect

from db import get_latest_kite_token, upsert_instruments, upsert_fundamental

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHE_INSTRUMENTS_KEY = "refdata:instruments"
CACHE_FUNDAMENTAL_PREFIX = "refdata:fund:"
CACHE_TTL = 86400 * 2  # 2 days


def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def get_yfticker(symbol_suffix: str):
    t = yf.Ticker(symbol_suffix)
    if t.info.get("regularMarketPrice") is None:
        return None
    return t


def fetch_instruments(kite: KiteConnect) -> list:
    rows = []
    for exchange in ["NSE", "BSE"]:
        for instr in kite.instruments(exchange=exchange):
            if instr.get("instrument_type") not in ("EQ", "INDEX"):
                continue
            rows.append({
                "symbol": instr.get("tradingsymbol"),
                "exchange": exchange,
                "instrument_token": instr.get("instrument_token"),
                "segment": instr.get("segment"),
                "instrument_type": instr.get("instrument_type"),
                "name": instr.get("name"),
                "bse_token": str(instr.get("exchange_token", "")) if exchange == "BSE" else None,
                "nse_token": str(instr.get("exchange_token", "")) if exchange == "NSE" else None,
            })
    return rows


def fetch_fundamentals_for_symbols(symbols: list, r: redis.Redis):
    for symbol in symbols:
        try:
            yfticker = get_yfticker(symbol + ".NS")
            if yfticker is None and "-SM" in symbol:
                yfticker = get_yfticker(symbol.replace("-SM", "") + ".NS")
            if yfticker is None:
                continue
            info = yfticker.info
            market_cap = info.get("marketCap")
            if market_cap:
                market_cap = int(market_cap) / 1e7  # crores
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            w52h = info.get("fiftyTwoWeekHigh")
            w52l = info.get("fiftyTwoWeekLow")
            upsert_fundamental(symbol, market_cap=market_cap, pe=pe, pb=pb, week_52_high=w52h, week_52_low=w52l)
            r.set(
                f"{CACHE_FUNDAMENTAL_PREFIX}{symbol}",
                str({"market_cap": market_cap, "pe": pe, "pb": pb, "week_52_high": w52h, "week_52_low": w52l}),
                ex=CACHE_TTL,
            )
            logger.info("Fundamental: %s", symbol)
        except Exception as e:
            logger.warning("Fundamental %s: %s", symbol, e)


def run_job():
    token = get_latest_kite_token()
    if not token:
        logger.warning("No valid Kite session in Postgres. Run /login via Telegram first.")
        return
    kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY", ""))
    kite.set_access_token(token)
    r = get_redis()

    logger.info("Fetching instruments (EQ+INDEX)...")
    rows = fetch_instruments(kite)
    upsert_instruments(rows)
    # Cache instrument list in Redis (e.g. list of symbols for market-data)
    symbols = list({r["symbol"] for r in rows})
    r.set(CACHE_INSTRUMENTS_KEY, "\n".join(symbols), ex=CACHE_TTL)
    logger.info("Instruments: %d", len(rows))

    logger.info("Fetching fundamentals (yfinance)...")
    fetch_fundamentals_for_symbols(symbols[:500], r)  # limit to avoid rate limit
    logger.info("Refdata job done.")
