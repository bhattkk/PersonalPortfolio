import pandas as pd

class CsvWriter:
    def __init__(self):
        # Always keep Symbol as the first column
        self.df = pd.DataFrame(columns=["Symbol"])

    def AddHeader(self, header):
        """Add a single header (column) if it doesn't exist."""
        if header not in self.df.columns:
            self.df[header] = ""

    def AddHeaders(self, header_list):
        """Add multiple headers."""
        for h in header_list:
            self.AddHeader(h)

    def AddHeaderAfter(self, existing_header, new_header):
        """
        Insert a new column immediately after an existing header.
        If existing_header not found, append new_header at the end.
        """
        cols = list(self.df.columns)
        if new_header in cols:
            return  # already exists, no change

        # determine insert position
        if existing_header in cols:
            insert_pos = cols.index(existing_header) + 1
        else:
            insert_pos = len(cols)

        # insert new column at that position
        self.df.insert(insert_pos, new_header, "")

    def AddRow(self, symbol):
        """Add a new row for the symbol if not exists."""
        if symbol not in self.df["Symbol"].values:
            new_row = {col: "" for col in self.df.columns}
            new_row["Symbol"] = symbol
            self.df.loc[len(self.df)] = new_row

    def AddValue(self, symbol, header_name, value):
        """Add or update a value for a given symbol and header."""
        # Ensure column and row exist
        self.AddHeader(header_name)
        self.AddRow(symbol)

        idx = self.df.index[self.df["Symbol"] == symbol][0]
        self.df.at[idx, header_name] = value

    def DumpCsv(self, filename):
        """Write the DataFrame to a CSV file."""
        self.df.to_csv(filename, index=False)
        print(f"Saved: {filename}")

    def LoadCsv(self, filename):
        """Load CSV into the DataFrame."""
        self.df = pd.read_csv(filename, dtype=str).fillna("")
        print(f"Loaded: {filename}")
