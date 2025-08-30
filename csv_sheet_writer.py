import os
import json
import base64
from typing import Dict, List, Optional, Iterable
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _load_google_creds() -> Credentials:
    """
    Loads service account credentials from one of:
      - GOOGLE_SERVICE_ACCOUNT_JSON (plain JSON)
      - GOOGLE_SERVICE_ACCOUNT_JSON_B64 (base64 JSON)
      - GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_CREDENTIALS_PATH (file path)
    """
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        return Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)

    b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
    if b64:
        data = base64.b64decode(b64).decode("utf-8")
        return Credentials.from_service_account_info(json.loads(data), scopes=SCOPES)

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_CREDENTIALS_PATH")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return Credentials.from_service_account_info(json.load(f), scopes=SCOPES)

    raise KeyError(
        "No Google credentials found. Set one of: "
        "GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SERVICE_ACCOUNT_JSON_B64, "
        "or GOOGLE_APPLICATION_CREDENTIALS/GOOGLE_CREDENTIALS_PATH."
    )


class CsvSheetWriter:
    """
    Google Sheets CSV-like writer.

    - Ensures spreadsheet (sheet_name) exists (creates if missing).
    - Ensures worksheet (worksheet_name) exists (creates if missing).
    - Keeps headers in row 1. Expands headers when new columns appear.
    - Append rows by dict with column names.

    Example:
        writer = CsvSheetWriter("Portfolio", "Holdings")
        writer.add_row({"Date": "2025-08-30", "Stock": "TCS", "Qty": 10, "PE": 32.1})
    """

    def __init__(
        self,
        sheet_name: str,
        worksheet_name: str,
        initial_headers: Optional[Iterable[str]] = None,
        rows: int = 1000,
        cols: int = 26,
    ) -> None:
        self.sheet_name = sheet_name
        self.worksheet_name = worksheet_name
        self.rows = rows
        self.cols = cols

        creds = _load_google_creds()
        self.gc = gspread.authorize(creds)
        self.sh = self._open_or_create_spreadsheet(sheet_name)
        self.ws = self._open_or_create_worksheet(worksheet_name, rows, cols)

        # Initialize headers if provided / missing
        if initial_headers:
            self._ensure_headers(list(initial_headers))

    # ---------- Spreadsheet / Worksheet helpers ----------

    def _open_or_create_spreadsheet(self, name: str):
        try:
            return self.gc.open(name)
        except gspread.SpreadsheetNotFound:
            sh = self.gc.create(name)
            # Optional: share with your primary Google account so you can see it in Drive UI
            # sh.share("youremail@gmail.com", perm_type="user", role="writer")
            return sh

    def _open_or_create_worksheet(self, name: str, rows: int, cols: int):
        try:
            return self.sh.worksheet(name)
        except gspread.WorksheetNotFound:
            return self.sh.add_worksheet(title=name, rows=rows, cols=cols)

    # ---------- Header management ----------

    def _get_headers(self) -> List[str]:
        headers = self.ws.row_values(1)
        # Strip whitespace around header names
        headers = [h.strip() for h in headers if h is not None]
        return headers

    def _set_headers(self, headers: List[str]) -> None:
        if not headers:
            return
        # Write header row starting at A1
        end_col_letter = self._col_letter(len(headers))
        self.ws.update(f"A1:{end_col_letter}1", [headers], value_input_option="USER_ENTERED")

    def _ensure_headers(self, required: List[str]) -> List[str]:
        """
        Make sure headers include at least the ones in `required`.
        Returns the current/updated headers list.
        """
        current = self._get_headers()
        if not current:
            self._set_headers(required)
            return required

        # Add any missing headers at the end
        missing = [h for h in required if h not in current]
        if missing:
            new_headers = current + missing
            self._set_headers(new_headers)
            return new_headers
        return current

    # ---------- Public API ----------

    def add_row(self, row: Dict[str, object]) -> None:
        """
        Append a single row. If the row has new keys (new columns),
        headers are expanded automatically.
        """
        if not row:
            return

        # Ensure headers include all keys of this row
        keys = list(row.keys())
        headers = self._ensure_headers(keys)

        # Map dict to ordered list by headers
        ordered = [row.get(h, "") for h in headers]

        # Append
        self.ws.append_row(ordered, value_input_option="USER_ENTERED")

    def add_rows(self, rows: List[Dict[str, object]]) -> None:
        """
        Append multiple rows efficiently.
        """
        if not rows:
            return

        # Union of all keys across rows to ensure headers cover everything
        all_keys = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    all_keys.append(k)

        headers = self._ensure_headers(all_keys)
        payload = [[r.get(h, "") for h in headers] for r in rows]
        self.ws.append_rows(payload, value_input_option="USER_ENTERED")

    # ---------- Utils ----------

    @staticmethod
    def _col_letter(n: int) -> str:
        """Convert 1-based column index to A1 letter (1 -> A, 27 -> AA)."""
        result = []
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result.append(chr(65 + rem))
        return "".join(reversed(result))


# Optional: tiny CLI for sanity testing
if __name__ == "__main__":
    writer = CsvSheetWriter("Portfolio", "Holdings", initial_headers=["Date", "Stock", "Qty", "PE", "Notes"])
    writer.add_row({"Date": "2025-08-30", "Stock": "TCS", "Qty": 10, "PE": 32.1})
    writer.add_rows([
        {"Date": "2025-08-30", "Stock": "HDFCBANK", "Qty": 25},
        {"Date": "2025-08-30", "Stock": "INFY", "Qty": 15, "Notes": "Long-term"},
    ])
