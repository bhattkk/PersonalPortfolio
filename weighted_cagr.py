import pandas as pd
import glob
from datetime import datetime

# --- Step 1: Read and combine tradebooks ---
files = glob.glob("tradebook*.csv")
dfs = [pd.read_csv(f) for f in files]
trades = pd.concat(dfs, ignore_index=True)

# --- Step 2: Clean and prepare ---
trades['trade_date'] = pd.to_datetime(trades['trade_date'])
trades['trade_type'] = trades['trade_type'].str.lower()

# if  symbol column contains '-', keep only part before '-'
trades['symbol'] = trades['symbol'].apply(lambda x: x.split('-')[0] if '-' in x else x)

# Combine by date, symbol, and trade_type
agg = (
    trades.groupby(['symbol', 'trade_date', 'trade_type'])
    .agg({'quantity': 'sum', 'price': 'mean'})
    .reset_index()
    .sort_values(['symbol', 'trade_date'])
)

# --- Step 3: Current holdings ---
# Replace this dict with your actual data
current_holdings = {
    'AADHARHFC': {'qty': 240, 'ltp': 509},
    'ABB': {'qty': 20, 'ltp': 5220},
    'BBOX': {'qty': 200, 'ltp': 530},
}

today = datetime.now()
results = []

for symbol, info in current_holdings.items():
    qty_held = info['qty']
    ltp = info['ltp']

    if qty_held <= 0:
        continue

    # Remove if anything after char '-' in symbol
    if '-' in symbol:
        symbol = symbol.split('-')[0]

    # Filter trades for this symbol
    sym_trades = agg[agg['symbol'].str.contains(symbol)].copy()

    if sym_trades.empty:
        continue

    # --- Net out sells to determine flow ---
    # (We still just traverse in reverse to pick buys for held qty)
    sym_trades = sym_trades.sort_values('trade_date', ascending=False)

    remaining_qty = qty_held
    used_buys = []
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
    weighted_buy_price = sum(qty * price for qty, price, _ in used_buys) / total_qty
    holding_period_num = int(sum((today - d).days for _, _, d in used_buys) / len(used_buys))
    if holding_period_num < 100:
        holding_period = f"{holding_period_num} days"
    else:
        holding_period = f"{holding_period_num // 30} months"

    results.append({
        'symbol': symbol,
        'held_qty': total_qty,
        'ltp': ltp,
        'weighted_buy_price': round(weighted_buy_price, 2),
        'weighted_cagr_%': round(weighted_cagr, 2),
        'buy_dates_used': ', '.join(sorted({d.strftime("%Y-%m-%d") for _, _, d in used_buys})),
        'holding_period': holding_period
    })

# --- Step 4: Final results ---
df_result = pd.DataFrame(results)
print(df_result)
