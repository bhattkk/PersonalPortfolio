from kiteconnect import KiteConnect
import json, sys, time, os, csv, datetime as dt

API_KEY    = os.environ.get("KITE_API_KEY")
SESSION_F  = "kite_session.json"
OUT_CSV    = "portfolio_" + dt.date.today().isoformat() + ".csv"

def load_token():
    with open(SESSION_F) as f:
        return json.load(f)["access_token"]

def main():
    kite = KiteConnect(api_key=API_KEY)
    try:
        kite.set_access_token(load_token())
        # Quick light call to verify session
        kite.profile()
    except Exception as e:
        print("No valid session. Run login_once.py this morning. Error:", e)
        sys.exit(1)

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

if __name__ == "__main__":
    main()
