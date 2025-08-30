from kiteconnect import KiteConnect
import json
import os

API_KEY     = os.environ.get("KITE_API_KEY")
API_SECRET  = os.environ.get("KITE_API_SECRET")
gs_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
SESSION_F   = "kite_session.json"

kite = KiteConnect(api_key=API_KEY)
print("Login URL:", kite.login_url())
request_token = input("Paste request_token: ").strip()
data = kite.generate_session(request_token, api_secret=API_SECRET)
with open(SESSION_F, "w") as f:
    json.dump({"access_token": data["access_token"]}, f)
print("✔ token saved for today.")
