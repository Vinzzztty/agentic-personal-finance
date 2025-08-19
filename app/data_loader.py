import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

from urllib.parse import quote

import pandas as pd


@dataclass
class Transaction:
    """Domain entity representing a single financial transaction."""

    tanggal: Optional[pd.Timestamp]
    deskripsi: str
    total: Optional[float]
    kategori: str
    pembayaran: str

    def to_dict(self) -> dict:
        # Convert to plain dict, formatting timestamp to ISO string for serialization
        data = asdict(self)
        if isinstance(self.tanggal, pd.Timestamp):
            data["tanggal"] = self.tanggal.isoformat()
        return data

    @staticmethod
    def from_values(
        tanggal: Optional[pd.Timestamp],
        deskripsi: str,
        total: Optional[float],
        kategori: str,
        pembayaran: str,
    ) -> "Transaction":
        return Transaction(
            tanggal=tanggal,
            deskripsi=deskripsi or "",
            total=total if total is not None else None,
            kategori=kategori or "",
            pembayaran=pembayaran or "",
        )


def _extract_google_sheet_id(google_sheets_url: str) -> str:
    """Extract the Google Sheet ID from a full Sheets URL.

    Supports URLs like:
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>/view
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheets_url)
    if not match:
        raise ValueError("Invalid Google Sheets URL. Could not find sheet ID.")
    return match.group(1)


def _build_csv_export_url(sheet_id: str, sheet_name: str) -> str:
    """Build a public CSV export URL for a specific sheet by name.

    Note: The spreadsheet must be publicly accessible (Anyone with the link can view)
    for this to work without authentication.
    """
    encoded_sheet_name = quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"


def load_transactions_from_csv_url(url: str, sheet_name: str) -> pd.DataFrame:
    """Load transactions from a public Google Sheet into a DataFrame.

    Args:
        url: A full Google Sheets URL (the generic share/view link is fine).
        sheet_name: The name of the worksheet/tab to load (case-sensitive).

    Returns:
        pandas.DataFrame with the sheet's contents.
    """
    sheet_id = _extract_google_sheet_id(url)
    csv_url = _build_csv_export_url(sheet_id, sheet_name)

    df = pd.read_csv(csv_url)
    # print(df.head()) # Debug use
    return df


def preprocess_transactions(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess raw Google Sheet export into a clean transactions table.

    Expected raw format (from the provided sheet):
    - Header row appears on row 1 with columns like: [None, 'Semua Transaksi', 'Deskripsi', None, 'Kategori', 'Pembayaran', None]
    - Actual data rows start after that, with date in the second column, description in third, amount in fourth, etc.

    Output schema:
    - columns: ['tanggal', 'deskripsi', 'total', 'kategori', 'pembayaran']
    - types:   [datetime64[ns], str, float, str, str]
    """
    if raw_df.empty:
        return raw_df

    df = raw_df.copy()

    # Find the header row by locating the row that contains 'Deskripsi' and 'Kategori'
    header_row_idx = None
    for idx, row in df.iterrows():
        values = row.astype(str).str.strip().tolist()
        if "Deskripsi" in values and "Kategori" in values and "Pembayaran" in values:
            header_row_idx = idx
            break

    if header_row_idx is None:
        # Fallback: assume the first row is the header-like row from the sample
        header_row_idx = 0

    # DO NOT overwrite columns. Use header row to discover positions, then slice by position.
    header_values = df.iloc[header_row_idx].astype(str).str.strip().tolist()

    # Build index lookups from the header row
    def find_idx_in_header(*labels: str) -> int | None:
        for i, v in enumerate(header_values):
            if v in labels:
                return i
        return None

    idx_deskripsi = find_idx_in_header("Deskripsi", "Description")
    idx_kategori = find_idx_in_header("Kategori", "Category")
    idx_pembayaran = find_idx_in_header("Pembayaran", "Payment", "Metode")

    # Prefer original named column 'Semua Transaksi' for date
    idx_tanggal = None
    for i, c in enumerate(df.columns):
        if isinstance(c, str) and c.strip() == "Semua Transaksi":
            idx_tanggal = i
            break

    # Fallback: infer the date column by parse-ability just below header row
    if idx_tanggal is None:
        body_probe = df.iloc[header_row_idx + 1 : header_row_idx + 15]
        best_idx, best_parsed = None, -1
        for i in range(len(df.columns)):
            series = body_probe.iloc[:, i].astype(str)
            parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)
            num_parsed = parsed.notna().sum()
            if num_parsed > best_parsed:
                best_parsed, best_idx = num_parsed, i
        idx_tanggal = best_idx

    # Detect amount column by 'Rp ' presence in sample rows (exclude already taken indices)
    taken_indices = {i for i in [idx_deskripsi, idx_kategori, idx_pembayaran, idx_tanggal] if i is not None}
    idx_total = None
    body_sample = df.iloc[header_row_idx + 1 : header_row_idx + 30]
    for i in range(len(df.columns)):
        if i in taken_indices:
            continue
        sample_vals = body_sample.iloc[:, i].astype(str).head(10).tolist()
        if any(v.strip().startswith("Rp ") for v in sample_vals):
            idx_total = i
            break

    # Slice data rows only
    body = df.iloc[header_row_idx + 1 :].reset_index(drop=True)

    # Build a clean DataFrame with available columns
    cleaned = pd.DataFrame()

    def parse_dates(series: pd.Series) -> pd.Series:
        # Try US-style first (e.g., 8/17/2025), then day-first
        s1 = pd.to_datetime(series, errors="coerce", dayfirst=False)
        needs_retry = s1.isna() & series.astype(str).str.contains(r"/", regex=True)
        if needs_retry.any():
            s2 = pd.to_datetime(series[needs_retry], errors="coerce", dayfirst=True)
            s1.loc[needs_retry] = s2
        return s1

    if idx_tanggal is not None:
        cleaned["tanggal"] = parse_dates(body.iloc[:, idx_tanggal].astype(str).str.strip())
    else:
        cleaned["tanggal"] = pd.NaT

    if idx_deskripsi is not None:
        cleaned["deskripsi"] = body.iloc[:, idx_deskripsi].astype(str).str.strip()
    else:
        cleaned["deskripsi"] = ""

    if idx_total is not None:
        total_series = body.iloc[:, idx_total].astype(str)
        total_series = total_series.str.replace(r"[^0-9-]", "", regex=True).replace("", pd.NA)
        cleaned["total"] = pd.to_numeric(total_series, errors="coerce")
    else:
        cleaned["total"] = pd.NA

    if idx_kategori is not None:
        cleaned["kategori"] = body.iloc[:, idx_kategori].astype(str).str.strip()
    else:
        cleaned["kategori"] = ""

    if idx_pembayaran is not None:
        cleaned["pembayaran"] = body.iloc[:, idx_pembayaran].astype(str).str.strip()
    else:
        cleaned["pembayaran"] = ""

    # Drop rows that are fully empty across key fields
    cleaned = cleaned.dropna(how="all", subset=["tanggal", "deskripsi", "total"]).reset_index(drop=True)

    # print(cleaned.head()) # Debug use

    return cleaned


# ---------- Converters between DataFrame and Transaction objects ----------

def dataframe_to_transactions(cleaned_df: pd.DataFrame) -> List[Transaction]:
    """Convert a cleaned transactions DataFrame to a list of Transaction objects.

    Expects the schema produced by preprocess_transactions:
    ['tanggal', 'deskripsi', 'total', 'kategori', 'pembayaran']
    """
    required_columns = {"tanggal", "deskripsi", "total", "kategori", "pembayaran"}
    missing = required_columns - set(cleaned_df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

    transactions: List[Transaction] = []
    for _, row in cleaned_df.iterrows():
        tanggal_val: Optional[pd.Timestamp]
        total_val: Optional[float]

        tanggal_val = row["tanggal"] if not pd.isna(row["tanggal"]) else None
        total_val = float(row["total"]) if pd.notna(row["total"]) else None

        transactions.append(
            Transaction.from_values(
                tanggal=tanggal_val,
                deskripsi=str(row["deskripsi"]).strip(),
                total=total_val,
                kategori=str(row["kategori"]).strip(),
                pembayaran=str(row["pembayaran"]).strip(),
            )
        )

    return transactions


def transactions_to_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """Convert a list of Transaction objects to a DataFrame with the standard schema."""
    if not transactions:
        return pd.DataFrame(columns=["tanggal", "deskripsi", "total", "kategori", "pembayaran"])  # type: ignore[call-arg]

    data = [
        {
            "tanggal": t.tanggal,
            "deskripsi": t.deskripsi,
            "total": t.total,
            "kategori": t.kategori,
            "pembayaran": t.pembayaran,
        }
        for t in transactions
    ]
    return pd.DataFrame(data)


def load_transactions(url: str, sheet_name: str) -> List[Transaction]:
    """High-level convenience: fetch, preprocess, and parse as Transaction objects."""
    raw = load_transactions_from_csv_url(url, sheet_name)
    cleaned = preprocess_transactions(raw)
    return dataframe_to_transactions(cleaned)

