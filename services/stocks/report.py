"""Build portfolio CSV from holdings/positions (Kite data only; no yfinance in-service)."""
from kite.CsvWriter import CsvWriter


def no_decimal(value):
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        return str(value)


def details_from_kite(csv_writer, holdings_or_positions, data_type, symbols=None):
    if symbols is None:
        symbols = []
    csv_writer.AddHeaders(["Type", "Invested", "P&L", "BuyPrice", "LTP"])
    csv_writer.AddHeaderAfter("P&L", "P&L Percent")
    for item in holdings_or_positions:
        symbol = item["tradingsymbol"]
        csv_writer.AddRow(symbol)
        symbols.append(symbol)
        csv_writer.AddValue(symbol, "Type", data_type)
        avg_price = item["average_price"]
        qty = item["quantity"]
        pnl = item.get("pnl", 0)
        invested = avg_price * qty
        csv_writer.AddValue(symbol, "Invested", no_decimal(invested))
        csv_writer.AddValue(symbol, "P&L", no_decimal(pnl))
        csv_writer.AddValue(symbol, "BuyPrice", no_decimal(avg_price))
        csv_writer.AddValue(symbol, "LTP", no_decimal(item["last_price"]))
        pnl_percent = pnl / invested * 100 if invested != 0 else 0
        csv_writer.AddValue(symbol, "P&L Percent", no_decimal(pnl_percent))


def build_watchlist_csv(holdings, positions_net) -> str:
    """Returns CSV string (no file)."""
    csv_writer = CsvWriter()
    symbols = []
    details_from_kite(csv_writer, holdings, "HOLDING", symbols)
    details_from_kite(csv_writer, positions_net or [], "POSITION", symbols)
    return csv_writer.df.to_csv(index=False)
