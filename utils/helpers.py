"""
Helper functions for formatting, currency, timestamps, and export.
"""

from datetime import datetime
from typing import Any, List
import pandas as pd


def format_currency(amount: float) -> str:
    """Formats float into Indian Rupee representation (e.g. ₹ 1,50,000.00)."""
    try:
        val = float(amount)
        return f"₹ {val:,.2f}"
    except (ValueError, TypeError):
        return "₹ 0.00"


def format_timestamp(dt: Any) -> str:
    """Safely converts Firestore datetime / string / timestamp to readable date string."""
    if not dt:
        return "-"
    if isinstance(dt, datetime):
        return dt.strftime("%d-%b-%Y %I:%M %p")
    if hasattr(dt, "strftime"):
        return dt.strftime("%d-%b-%Y %I:%M %p")
    return str(dt)


def dataframe_to_csv_download(df: pd.DataFrame, filename: str = "export.csv") -> bytes:
    """Encodes a pandas DataFrame to UTF-8 CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def get_current_iso_time() -> str:
    """Returns current UTC ISO timestamp string."""
    return datetime.utcnow().isoformat()
