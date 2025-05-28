"""
db_utils.py
-----------
Low-level data-access layer: all **stored-procedure** calls + caches.

Splitting this out means everything that hits the database (and only that)
lives in one place, simplifying mocking and connection-pool control.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Set, Tuple

import pandas as pd
from caching import TTLCache
from sqlalchemy.engine import Engine

from db_connection import get_engine
from time_utils import DATETIME_FORMAT

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Caches (process-wide, thread-safe)
# --------------------------------------------------------------------------- #
_min_max_cache: TTLCache = TTLCache(ttl=300)
_full_data_cache: TTLCache = TTLCache(ttl=300)
_typeid_cache: TTLCache = TTLCache(ttl=300)

# --------------------------------------------------------------------------- #
# Internal
# --------------------------------------------------------------------------- #
def _ensure_engine(engine: Engine | None = None) -> Engine:  # re-exported for tests
    return engine or get_engine()


# --------------------------------------------------------------------------- #
# Public DB functions
# --------------------------------------------------------------------------- #
def fetch_typeids_for_ean(
    ean_value: str,
    *,
    search_method: str = "transferpoint",
    engine: Engine | None = None,
) -> Set[int]:
    """
    Return **all** `TypeId`s linked to a supplied EAN / ID.

    Uses a 5-minute TTL cache to avoid hammering the catalog tables.
    """
    engine = _ensure_engine(engine)
    cache_key = (ean_value, search_method)
    cached = _typeid_cache.get(cache_key)
    if cached is not None:
        return cached

    # ------------------------------------------------------------------- SQL
    if search_method == "transferpoint":
        sql = """
        SELECT DISTINCT r.TypeId
        FROM dbo.TBL_Register r
        JOIN dbo.TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
        WHERE cp.EAN_ConnectionPoint = ?
           OR cp.TransferPointID IN (
                 SELECT ID FROM dbo.TBL_ConnectionPoint
                 WHERE EAN_ConnectionPoint = ?
             )
        """
        params = (ean_value, ean_value)

    elif search_method == "objectid":
        sql = """
        SELECT DISTINCT r.TypeId
        FROM dbo.TBL_Register r
        JOIN dbo.TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
        WHERE cp.ObjectId = (
            SELECT TOP 1 cp2.ObjectId
            FROM dbo.TBL_ConnectionPoint cp2
            WHERE cp2.EAN_ConnectionPoint = ?
        )
        """
        params = (ean_value,)

    elif search_method == "registerid":
        sql, params = "SELECT DISTINCT TypeId FROM dbo.TBL_Register WHERE ID = ?", (int(ean_value),)

    elif search_method == "registratorid":
        sql, params = (
            "SELECT DISTINCT TypeId FROM dbo.TBL_Register WHERE RegistratorID = ?",
            (int(ean_value),),
        )

    else:
        raise ValueError(f"Unknown search_method '{search_method}'")

    # -------------------------------------------------------------- Execute
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
        result: Set[int] = set(df["TypeId"].unique()) if not df.empty else set()
    except Exception as exc:  # pragma: no cover
        logger.exception("fetch_typeids_for_ean failed: %s", exc)
        result = set()

    _typeid_cache.set(cache_key, result)
    return result


def fetch_min_max_period(
    ean_value: str,
    allowed_typeids_str: str,
    start_date: datetime,
    end_date: datetime,
    search_method: str = "transferpoint",
    *,
    engine: Engine | None = None,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Call *usp_GetMinMaxPeriodForEAN*; returns `(min_utcperiod, max_utcperiod)`
    or `(None, None)` when no data found.
    """
    engine = _ensure_engine(engine)
    cache_key = (ean_value, allowed_typeids_str, start_date, end_date, search_method)
    cached = _min_max_cache.get(cache_key)
    if cached is not None:
        return cached

    sql = """
    EXEC dbo.usp_GetMinMaxPeriodForEAN
         @EAN_ConnectionPoint = ?,
         @AllowedTypeIDs      = ?,
         @StartDateStr        = ?,
         @EndDateStr          = ?,
         @SearchMethod        = ?
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                sql,
                conn,
                params=(
                    ean_value,
                    allowed_typeids_str,
                    start_date.strftime(DATETIME_FORMAT),
                    end_date.strftime(DATETIME_FORMAT),
                    search_method,
                ),
                parse_dates=["MinUTCPeriod", "MaxUTCPeriod"],
            )
        result = (
            (df["MinUTCPeriod"].iloc[0], df["MaxUTCPeriod"].iloc[0])
            if not df.empty and pd.notna(df.iloc[0, 0])
            else (None, None)
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("fetch_min_max_period failed: %s", exc)
        result = (None, None)

    _min_max_cache.set(cache_key, result)
    return result


def fetch_full_data(
    ean_value: str,
    allowed_typeids_str: str,
    start_date: datetime,
    end_date: datetime,
    *,
    interval_minutes: int = 5,
    include_status: bool = False,
    search_method: str = "transferpoint",
    engine: Engine | None = None,
) -> Optional[pd.DataFrame]:
    """
    Execute *usp_GetConnectionDataFull* and return the **pivoted** dataframe,
    or `None` if nothing was returned.
    """
    engine = _ensure_engine(engine)
    cache_key = (
        ean_value,
        allowed_typeids_str,
        start_date,
        end_date,
        interval_minutes,
        include_status,
        search_method,
    )
    cached = _full_data_cache.get(cache_key)
    if cached is not None:
        return cached

    sql = """
    EXEC dbo.usp_GetConnectionDataFull
         @EAN_ConnectionPoint = ?,
         @AllowedTypeIDs      = ?,
         @StartDateStr        = ?,
         @EndDateStr          = ?,
         @SearchMethod        = ?,
         @IntervalMinutes     = ?,
         @IncludeStatus       = ?
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                sql,
                conn,
                params=(
                    ean_value,
                    allowed_typeids_str,
                    start_date.strftime(DATETIME_FORMAT),
                    end_date.strftime(DATETIME_FORMAT),
                    search_method,
                    interval_minutes,
                    int(include_status),
                ),
                parse_dates=["utcperiod"],
            )
        result = None if df.empty else df
    except Exception as exc:  # pragma: no cover
        logger.exception("fetch_full_data failed: %s", exc)
        result = None

    _full_data_cache.set(cache_key, result)
    return result


__all__ = [
    "fetch_typeids_for_ean",
    "fetch_min_max_period",
    "fetch_full_data",
    "_ensure_engine",
]
