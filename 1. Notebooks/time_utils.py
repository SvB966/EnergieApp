"""
time_utils.py
-------------
Date/time helpers shared by energy notebooks.

• Pure functions only, zero I/O.
• Single public constant: DATETIME_FORMAT.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from frequency_utils import get_freq_seconds

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
DATETIME_FORMAT: str = "%d/%m/%Y %H:%M"

# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #
def parse_user_datetime(
    dt_str: str,
    fmt: str = DATETIME_FORMAT,
) -> Optional[datetime]:
    """Convert a user-supplied string to `datetime` (or `None` on failure)."""
    try:
        return datetime.strptime(dt_str, fmt)
    except ValueError:
        logger.error("Invalid date/time: %s (expected %s)", dt_str, fmt)
        return None


def round_datetime_to_freq(
    ts: datetime,
    freq_key: str,
    *,
    is_start: bool = True,
) -> datetime:
    """
    Round *ts* to the bucket border of *freq_key*.

    Parameters
    ----------
    ts         : datetime to round
    freq_key   : key from `frequency_utils`
    is_start   : True ⇒ round **down**, False ⇒ round **up**
    """
    seconds = get_freq_seconds(freq_key)
    if seconds <= 0:
        return ts  # unknown frequency → leave untouched
    offset = ts.timestamp() % seconds
    if offset == 0:
        return ts
    delta = timedelta(seconds=offset if is_start else seconds - offset)
    return ts - delta if is_start else ts + delta


__all__ = ["DATETIME_FORMAT", "parse_user_datetime", "round_datetime_to_freq"]
