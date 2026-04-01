"""
stocks service: subscribe to telegram:commands; handle login, watchlist, refresh_sd.
Session in Postgres; outbound via Redis stream; token reply via Redis reply_context.
"""
import logging
import os
import threading

from app_logging import setup_logging
from kiteconnect import KiteConnect

from db import get_latest_session, save_session, save_portfolio_snapshot, upsert_instruments
from redis_client import (
    push_login_url,
    push_text,
    push_portfolio_report,
    wait_for_token_reply,
    subscribe_commands,
)
from report import build_watchlist_csv

setup_logging("stocks")
logger = logging.getLogger(__name__)

API_KEY = os.environ.get("KITE_API_KEY", "")
API_SECRET = os.environ.get("KITE_API_SECRET", "")
CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))


def get_kite():
    return KiteConnect(api_key=API_KEY)


def ensure_token(kite: KiteConnect) -> bool:
    """Set access token from Postgres if valid. Return True if valid."""
    row = get_latest_session()
    if not row:
        return False
    try:
        kite.set_access_token(row["access_token"])
        kite.profile()
        return True
    except Exception as e:
        logger.warning("Session invalid: %s", e)
        return False


def handle_login():
    kite = get_kite()
    if ensure_token(kite):
        push_text(CHAT_ID, "✔ Already logged in. Token still valid.")
        return
    url = kite.login_url()
    context_id = push_login_url(CHAT_ID, url)
    token = wait_for_token_reply(context_id)
    if not token:
        push_text(CHAT_ID, "❌ Login timed out. Please try /login again.")
        return
    try:
        data = kite.generate_session(token, api_secret=API_SECRET)
        save_session(data["access_token"])
        kite.set_access_token(data["access_token"])
        push_text(CHAT_ID, "✔ Token saved. You are logged in.")
    except Exception as e:
        logger.exception("generate_session failed: %s", e)
        push_text(CHAT_ID, f"❌ Login failed: {e}")


def holding_to_row(h, row_type="HOLDING"):
    qty = h.get("quantity", 0) or 0
    avg = h.get("average_price", 0) or 0
    last = h.get("last_price", 0) or 0
    pnl = h.get("pnl") or 0
    invested = avg * qty if qty else 0
    pnl_pct = (pnl / invested * 100) if invested else 0
    return {
        "tradingsymbol": h.get("tradingsymbol"),
        "type": row_type,
        "quantity": qty,
        "average_price": avg,
        "last_price": last,
        "pnl": pnl,
        "pnl_percent": pnl_pct,
        "invested": invested,
        "exchange": h.get("exchange"),
        "instrument_token": h.get("instrument_token"),
    }


def handle_watchlist():
    kite = get_kite()
    if not ensure_token(kite):
        push_text(CHAT_ID, "❌ Token invalid or expired. Please /login again.")
        return
    try:
        holdings = kite.holdings()
        positions = kite.positions()
        net = positions.get("net") or []
        rows = [holding_to_row(h, "HOLDING") for h in holdings]
        rows += [holding_to_row(p, "POSITION") for p in net]
        save_portfolio_snapshot(rows)
        csv_content = build_watchlist_csv(holdings, net)
        push_portfolio_report(CHAT_ID, csv_content, "portfolio_report.csv")
        push_text(CHAT_ID, "✔ Watchlist refreshed.")
    except Exception as e:
        logger.exception("Watchlist failed: %s", e)
        push_text(CHAT_ID, f"❌ Watchlist failed: {e}")


def handle_refresh_sd():
    kite = get_kite()
    if not ensure_token(kite):
        push_text(CHAT_ID, "❌ Token invalid or expired. Please /login first.")
        return
    try:
        instrument_rows = []
        for exchange in ["NSE", "BSE"]:
            for instr in kite.instruments(exchange=exchange):
                if instr.get("instrument_type") not in ("EQ", "INDEX"):
                    continue
                symbol = instr.get("tradingsymbol")
                instrument_rows.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "instrument_token": instr.get("instrument_token"),
                    "segment": instr.get("segment"),
                    "instrument_type": instr.get("instrument_type"),
                    "name": instr.get("name"),
                    "bse_token": str(instr.get("exchange_token", "")) if exchange == "BSE" else None,
                    "nse_token": str(instr.get("exchange_token", "")) if exchange == "NSE" else None,
                })
        upsert_instruments(instrument_rows)
        push_text(CHAT_ID, f"✔ Fetched {len(instrument_rows)} instruments (EQ+INDEX). Static data refreshed.")
    except Exception as e:
        logger.exception("Refresh SD failed: %s", e)
        push_text(CHAT_ID, f"❌ Refresh failed: {e}")


def on_command(cmd: str):
    logger.info("Command received: %s", cmd)
    if cmd == "login":
        handle_login()
    elif cmd == "watchlist":
        handle_watchlist()
    elif cmd == "refresh_sd":
        handle_refresh_sd()
    else:
        logger.warning("Unknown command: %s", cmd)


def main():
    if not API_KEY or not API_SECRET or not CHAT_ID:
        logger.error("Set KITE_API_KEY, KITE_API_SECRET, TELEGRAM_CHAT_ID")
        raise SystemExit(1)
    logger.info("stocks: subscribing to telegram:commands")
    subscribe_commands(on_command)


if __name__ == "__main__":
    main()
