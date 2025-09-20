from kiteconnect import KiteConnect
from messaging.telegram_bot import TelegramBot
import json, sys, time, os, csv, datetime as dt

API_KEY    = os.environ.get("KITE_API_KEY")
API_SECRET  = os.environ.get("KITE_API_SECRET")
SESSION_F  = "kite_session.json"
OUT_CSV    = "portfolio_" + dt.date.today().isoformat() + ".csv"

class KiteWrapper:
    def __init__(self, bot):
        self.bot = bot
        bot.register_callback("/watchlist", lambda msg: self.refresh_watchlist())
        bot.register_callback('/token', lambda msg: self.access_token(msg.split()[-1]))
 
    def login_once(self):
        """Run this once in the morning to generate a session token."""
        self.kite = KiteConnect(api_key=API_KEY)
        print("Login URL:", kite.login_url())
        self.bot.send_message("Please visit the above URL and authorize the app. Then paste the 'request_token' parameter from the redirected URL here.")
        
    def access_token(self, request_token):
        data = self.kite.generate_session(request_token, api_secret=API_SECRET)
        with open(SESSION_F, "w") as f:
            json.dump({"access_token": data["access_token"]}, f)
        print("✔ token saved for today.")

    def load_token():
        with open(SESSION_F) as f:
            return json.load(f)["access_token"]

    def refresh_watchlist(self):
        kite = KiteConnect(api_key=API_KEY)
        try:
            kite.set_access_token(self.load_token())
            # Quick light call to verify session
            kite.profile()
        except Exception as e:
            self.bot.send_message("⚠️ Failed to authenticate with saved token. Please run /token <request_token> again.")

        holdings  = kite.holdings()
        positions = kite.positions()

        # write a compact CSV
        with open(OUT_CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Type","Symbol","Qty","AvgPrice","LTP","P&L"])
            for h in holdings:
                w.writerow(["HOLDING", h["tradingsymbol"], h["quantity"], h["average_price"], h["last_price"], h.get("pnl", "")])
            for p in positions.get("net", []):
                w.writerow(["POSITION", p["tradingsymbol"], p["quantity"], p["average_price"], p["last_price"], p.get("pnl","")])
        print("Saved", OUT_CSV)
        self.bot.send_message("✔ Portfolio refreshed. Sending CSV...")
        self.bot.send_csv(OUT_CSV)
        self.bot.send_message("Use /refresh to refresh portfolio anytime.")
