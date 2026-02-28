"""
kite-market-data: read instruments from Postgres; fetch LTP from Kite (exchange:tradingsymbol); write to Redis.
Runs on a timer (e.g. every 1–5 min). Uses same Kite token from Postgres.
"""
import logging
import os
import time

from kiteconnect import KiteConnect

from db import get_eq_index_instrument_tokens, get_kite_token
from redis_cache import get_redis, set_ltp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

INTERVAL_SEC = int(os.environ.get("MARKET_DATA_INTERVAL", "60"))
BATCH_SIZE = 250  # Kite LTP accepts up to 250 per request


def run_ltp_cycle():
    token = get_kite_token()
    if not token:
        logger.warning("No valid Kite session. Skip LTP cycle.")
        return
    kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY", ""))
    kite.set_access_token(token)
    r = get_redis()
    instruments = get_eq_index_instrument_tokens(limit=1000)
    if not instruments:
        logger.warning("No instruments in DB. Run stocks-refdata or /refresh_sd first.")
        return
    # Kite ltp() accepts list of "EXCHANGE:SYMBOL"; max 250 per request
    keys = [f"{x['exchange']}:{x['tradingsymbol']}" for x in instruments]
    key_to_info = {f"{x['exchange']}:{x['tradingsymbol']}": x for x in instruments}
    total = 0
    for i in range(0, len(keys), BATCH_SIZE):
        batch = keys[i : i + BATCH_SIZE]
        try:
            quotes = kite.ltp(batch)
        except Exception as e:
            logger.exception("Kite LTP batch failed: %s", e)
            continue
        for k, data in quotes.items():
            ltp = data.get("last_price")
            if ltp is None:
                continue
            info = key_to_info.get(k, {})
            set_ltp(
                r,
                info.get("instrument_token", 0),
                ltp,
                info.get("exchange"),
                info.get("tradingsymbol"),
            )
            total += 1
    logger.info("LTP updated for %d instruments", total)


def main():
    logger.info("kite-market-data: interval=%ds", INTERVAL_SEC)
    while True:
        run_ltp_cycle()
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
