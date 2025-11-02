from kiteconnect import KiteConnect
from messaging.telegram_bot import TelegramBot
from kite.CsvWriter import CsvWriter
import json, sys, time, os, csv, datetime as dt
import logging
import yfinance as yf
import glob
import pandas as pd
from datetime import datetime

API_KEY    = os.environ.get("KITE_API_KEY")
API_SECRET  = os.environ.get("KITE_API_SECRET")
SESSION_F  = "kite_session.json"
OUT_CSV    = "portfolio_report.csv"

def no_decimal(value):
    try:
        # Try converting to float, then int
        return str(int(float(value)))
    except (ValueError, TypeError):
        # If not a number, keep as string
        return str(value)
    
def get_yfticker(symbol):
    yfticker = yf.Ticker(symbol)
    if not logging.info or yfticker.info.get("regularMarketPrice") is None:
        print(f"{symbol} is invalid or not listed on Yahoo Finance")
        return None
    return yfticker

def details_from_yfinance(csv_writer, symbols):
    for symbol in symbols:
        try:
            yfticker = get_yfticker(symbol+".NS")

            # if contains -SM, and ticker not found then try removing -SM
            if yfticker is None:
                if "-SM" in symbol:
                    yfticker = get_yfticker(symbol.replace("-SM", "")+".NS")
            
            if yfticker is None:
                # try getting BSE_TOKEN from kite_instruments.csv
                with open("kite_instruments.csv", "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["Symbol"] == symbol:
                            bse_token = row.get("BSE_TOKEN", "")
                            if bse_token:
                                print(f"Found BSE_TOKEN {bse_token} for {symbol}")
                                yfticker = get_yfticker(f"{bse_token}.BO")
                            break

            if yfticker is None:
                print(f"❌ Skipping {symbol} as no valid ticker found on yfinance.")
                continue

            info = yfticker.info
            print(f"Fetched data for {symbol} from yfinance.")
            #csv_writer.AddHeaders(["MarketCap","PE","PB","52WeekHigh","DiffFrom52WH","52WeekLow", "DiffFrom52WL"])
            market_cap = info.get("marketCap", "")
            # Market Cap in crores
            if market_cap != "":
                market_cap = int(market_cap) / 1e7
            csv_writer.AddValue(symbol, "MarketCap", no_decimal(market_cap))
            csv_writer.AddValue(symbol, "PE", no_decimal(info.get("trailingPE", "")))
            csv_writer.AddValue(symbol, "PB", no_decimal(info.get("priceToBook", "")))
            csv_writer.AddValue(symbol, "52WeekHigh", no_decimal(info.get("fiftyTwoWeekHigh", "")))
            
            diffFrom52WH = ""
            if info.get("fiftyTwoWeekHigh", "") and info.get("regularMarketPrice", ""):
                diffFrom52WH = (info["regularMarketPrice"] - info["fiftyTwoWeekHigh"]) / info["fiftyTwoWeekHigh"] * 100
            csv_writer.AddValue(symbol, "DiffFrom52WH (%)", no_decimal(diffFrom52WH))

            csv_writer.AddValue(symbol, "52WeekLow", no_decimal(info.get("fiftyTwoWeekLow", "")))
            
            diffFrom52WL = ""
            if info.get("fiftyTwoWeekLow", "") and info.get("regularMarketPrice", ""):
                diffFrom52WL = (info["regularMarketPrice"] - info["fiftyTwoWeekLow"]) / info["fiftyTwoWeekLow"] * 100
            csv_writer.AddValue(symbol, "DiffFrom52WL (%)", no_decimal(diffFrom52WL))

        except Exception as e:
            print(f"❌ Failed to fetch data for {symbol} from yfinance: {e}")

def cagr_from_the_tradebook(csv_writer, holdings):
    # --- Read and combine tradebooks ---
    files = glob.glob("tradebook*.csv")
    dfs = [pd.read_csv(f) for f in files]
    trades = pd.concat(dfs, ignore_index=True)
    # --- Clean and prepare ---
    trades['trade_date'] = pd.to_datetime(trades['trade_date'])
    trades['trade_type'] = trades['trade_type'].str.lower()
    
    # if  symbol column contains '-', keep only part before '-'
    trades['symbol'] = trades['symbol'].apply(lambda x: x.split('-')[0] if '-' in x else x)
    # Combine by date, symbol, and trade_type
    # per day quantity needs to be added and price averaged
    agg = (
        trades.groupby(['symbol', 'trade_date', 'trade_type'])
        .agg({'quantity': 'sum', 'price': 'mean'})
        .reset_index()
        .sort_values(['symbol', 'trade_date'])
    )
    today = datetime.now()

    for holding in holdings:
        symbol = holding['tradingsymbol']
        qty = holding['quantity']
        ltp = holding['last_price']
        if qty <= 0:
            continue

        # Remove if anything after char '-' in symbol
        symbol_temp = symbol
        if '-' in symbol:
            symbol_temp = symbol.split('-')[0]

        # Filter trades for this symbol
        sym_trades = agg[agg['symbol'].str.contains(symbol_temp)].copy()

        if sym_trades.empty:
            continue

        # Sort by date descending
        sym_trades = sym_trades.sort_values('trade_date', ascending=False)

        remaining_qty = qty
        used_buys = [] # to store (quantity, average_price, date)
        for _, row in sym_trades.iterrows():
            if remaining_qty <= 0:
                break
            if row['trade_type'] != 'buy':
                continue

            trade_qty = row['quantity']
            trade_price = row['price']
            trade_date = row['trade_date']

            print (f"Processing {symbol}: trade_date={trade_date.date()}, trade_type={row['trade_type']}, trade_qty={trade_qty}, trade_price={trade_price}")

            if trade_qty <= remaining_qty:
                used_buys.append((trade_qty, trade_price, trade_date))
                remaining_qty -= trade_qty
            else:
                used_buys.append((remaining_qty, trade_price, trade_date))
                remaining_qty = 0

        if not used_buys:
                continue

        # --- Compute weighted CAGR ---
        total_qty = sum(qty for qty, _, _ in used_buys)
        cagr_parts = []
        for qty, price, date in used_buys:
            years = max((today - date).days / 365, 1/365)
            cagr = ((ltp / price) ** (1 / years) - 1) * 100
            cagr_parts.append((qty, cagr))

        weighted_cagr = sum(qty * cagr for qty, cagr in cagr_parts) / total_qty
        holding_period_num = int(sum((today - d).days for _, _, d in used_buys) / len(used_buys))
        if holding_period_num < 100:
            holding_period = f"{holding_period_num} days"
        else:
            holding_period = f"{holding_period_num // 30} months"

        # buy dates like 23 Oct 2023, 15 Jan 2024 sorted and unique
        buy_dates = []
        
        # Assuming used_buys is a list of tuples (_, _, datetime_object)
        buy_dates = sorted([d for _, _, d in used_buys])
        buy_dates = [d.strftime("%d %b %Y") for d in buy_dates]
        buy_dates = ", ".join(buy_dates)


        csv_writer.AddValue(symbol, "Buy Dates", buy_dates)
        csv_writer.AddValue(symbol, "Holding Period", holding_period)
        csv_writer.AddValue(symbol, "CAGR (%)", no_decimal(round(weighted_cagr, 2)))
        

class KiteWrapper:
    def __init__(self, bot):
        self.logger = logging.getLogger(__name__)
        self.bot = bot
        self.logger.info("KiteWrapper initialized.")
        bot.register_callback("refresh_sd", self.refresh_static_data)
        bot.register_callback("watchlist", self.refresh_watchlist)
        bot.register_callback('token', self.access_token)
        bot.register_callback('login', self.login_once)
        self.kite = KiteConnect(api_key=API_KEY)
 
    def login_once(self):
        """Run this once in the morning to generate a session token."""
        print("Login URL:", self.kite.login_url())
        return self.kite.login_url()
        
    def access_token(self, request_token):
        data = self.kite.generate_session(request_token, api_secret=API_SECRET)
        with open(SESSION_F, "w") as f:
            json.dump({"access_token": data["access_token"]}, f)
        print("✔ token saved for today: ", data["access_token"])
        self.kite.set_access_token(data["access_token"])

    def load_token():
        with open(SESSION_F) as f:
            return json.load(f)["access_token"]
    
    def validate_token(self):
        try:
            with open(SESSION_F) as f:
                data = json.load(f)
                access_token = data.get("access_token", "")
                if not access_token:
                    raise ValueError("Access token not found in session file.")
                self.kite.set_access_token(access_token)
                profile = self.kite.profile()
                print("✔ Token valid. User:", profile.get("user_name", "Unknown"))
                return True
        except Exception as e:
            print("❌ Token validation failed:", str(e))
            return False

    async def refresh_static_data(self):
        validate_token = self.validate_token()
        if not validate_token:
            await self.bot.send_message("❌ Token invalid or expired. Please /login again.")
            return False
        
        csv_writer = CsvWriter()
        csv_writer.AddHeaders(["InstrumentToken","Name","BSE_TOKEN","NSE_TOKEN","Segment","InstrumentType"])

        for exchange in ["NSE","BSE"]:
            instruments = self.kite.instruments(exchange=exchange)
            for instr in instruments:
                symbol = instr["tradingsymbol"]
                instType = instr["instrument_type"]
                instToken = instr["instrument_token"]
                exchangeToken = instr["exchange_token"]
                segment = instr["segment"]
                name = instr["name"]
                if instType not in ["EQ","MF"]:
                    continue
                csv_writer.AddRow(symbol)
                csv_writer.AddValue(symbol, "Name", name)
                csv_writer.AddValue(symbol, "InstrumentType", instType)
                csv_writer.AddValue(symbol, "Segment", segment)
                csv_writer.AddValue(symbol, "InstrumentToken", str(instToken))
                csv_writer.AddValue(symbol, f"{exchange}_TOKEN", str(exchangeToken))

        # delete old file if exists
        if os.path.exists("kite_instruments.csv"):
            os.remove("kite_instruments.csv")
            print("✔ Old file deleted: kite_instruments.csv")
        csv_writer.DumpCsv("kite_instruments.csv")
        print(f"Static instrument data saved: kite_instruments.csv")
               
        await self.bot.send_message(f"✔ Fetched {len(instruments)} instruments from Kite.")
        return True

    async def refresh_watchlist(self):
        validate_token = self.validate_token()
        if not validate_token:
            await self.bot.send_message("❌ Token invalid or expired. Please /login again for latest.")
            if os.path.exists(OUT_CSV):
                await self.bot.send_csv(OUT_CSV)

        holdings  = self.kite.holdings()
        positions = self.kite.positions()

        csv_writer = CsvWriter()
        self.prepare_watchlist(holdings, positions, csv_writer)
        csv_writer.DumpCsv(OUT_CSV)

        print(f"Latest Portfolio report generated: {OUT_CSV}")
        await self.bot.send_csv(OUT_CSV)
        return True
    

    def prepare_watchlist(self, holdings, positions, csv_writer):
        symbols = []
        self.details_from_kite(csv_writer, holdings, "HOLDING", symbols)
        self.details_from_kite(csv_writer, positions.get("net", []), "POSITION", symbols)
        details_from_yfinance(csv_writer, symbols)
        cagr_from_the_tradebook(csv_writer, holdings)

    def details_from_kite(self, csv_writer, holdingsorPositions, data_type, symbols=[]):
        csv_writer.AddHeaders(["Type","Invested","P&L", "BuyPrice","LTP"])
        Pnl_Percent_header = "P&L Percent"
        csv_writer.AddHeaderAfter("P&L", Pnl_Percent_header)
        for item in holdingsorPositions:
            symbol = item["tradingsymbol"]
            csv_writer.AddRow(symbol)
            symbols.append(symbol)
            csv_writer.AddValue(symbol, "Type", data_type)
            avg_price = item["average_price"]
            qty = item["quantity"]
            pnl = item.get("pnl", 0)

            csv_writer.AddValue(symbol, "Invested", no_decimal(avg_price * qty))
            csv_writer.AddValue(symbol, "P&L", no_decimal(pnl))
            csv_writer.AddValue(symbol, "BuyPrice", no_decimal(avg_price))
            csv_writer.AddValue(symbol, "LTP", no_decimal(item["last_price"]))
            
            pnl_percent = pnl / (avg_price * qty) * 100 if avg_price * qty != 0 else 0
            csv_writer.AddValue(symbol, Pnl_Percent_header, no_decimal(pnl_percent))


