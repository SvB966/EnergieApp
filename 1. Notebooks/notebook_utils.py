"""
notebook_utils.py
Shared helpers voor de twee energie-notebooks.

Kernpunten
----------
* Eén bron voor alle datum-parsing, DB-calls, aggregatie, (her)sampling en export
  zodat notebooks zelf slechts UI-logica bevatten.
* TTL-caches beperken DB-load: 5 min voor min/max-periodes, pivot-sets en type-IDs.
* Functies zijn stateless; een SQLAlchemy-engine kan worden geïnjecteerd óf
  lazy worden aangemaakt via `db_connection.get_engine()`.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Set

import numpy as np
import pandas as pd
from caching import TTLCache
from db_connection import get_engine
from frequency_utils import (
    get_freq_minutes,
    get_freq_seconds,
    get_pandas_freq,
    detect_auto_frequency,
    resample_dataframe,
)
from mappings import group_typeid_mapping
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Basis-configuratie
# --------------------------------------------------------------------------- #

DATETIME_FORMAT = "%d/%m/%Y %H:%M"
MAX_ROWS = 8_000

# proces-brede, thread-safe caches
_min_max_cache   = TTLCache(ttl=300)
_full_data_cache = TTLCache(ttl=300)
_typeid_cache    = TTLCache(ttl=300)

# --------------------------------------------------------------------------- #
# Datum-helpers
# --------------------------------------------------------------------------- #

def parse_user_datetime(
    dt_str: str,
    fmt: str = DATETIME_FORMAT
) -> Optional[datetime]:
    """Converteer een user-input naar `datetime` of `None` bij fout."""
    try:
        return datetime.strptime(dt_str, fmt)
    except ValueError:
        logger.error("Ongeldige datum/tijd: %s (verwacht formaat %s)", dt_str, fmt)
        return None


def round_datetime_to_freq(
    ts: datetime,
    freq_key: str,
    *,
    is_start: bool = True
) -> datetime:
    """
    Rond `ts` af op de bucket-grens van `freq_key`.
    * is_start=True  ⇒ afronden naar beneden
    * is_start=False ⇒ afronden naar boven
    """
    seconds = get_freq_seconds(freq_key)
    if seconds <= 0:
        return ts                          # onbekende freq
    offset = ts.timestamp() % seconds
    if offset == 0:
        return ts
    delta = timedelta(seconds=offset if is_start else seconds - offset)
    return ts - delta if is_start else ts + delta


# --------------------------------------------------------------------------- #
# Database-helpers
# --------------------------------------------------------------------------- #

def _ensure_engine(engine: Engine | None = None) -> Engine:
    return engine or get_engine()


def fetch_typeids_for_ean(
    ean_value: str,
    *,
    search_method: str = "transferpoint",
    engine: Engine | None = None
) -> Set[int]:
    """
    Haal alle `TypeId`s op die horen bij een ingevoerd EAN/ID.

    Parameters
    ----------
    ean_value      : str
    search_method  : transferpoint | objectid | registerid | registratorid
    """
    engine = _ensure_engine(engine)
    cache_key = (ean_value, search_method)
    cached = _typeid_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        if search_method == "transferpoint":
            sql = """
                SELECT DISTINCT r.TypeId
                FROM TBL_Register r
                JOIN TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
                WHERE cp.EAN_ConnectionPoint = ?
                   OR cp.TransferPointID IN (
                       SELECT ID FROM TBL_ConnectionPoint
                       WHERE EAN_ConnectionPoint = ?
                   )
            """
            params = (ean_value, ean_value)

        elif search_method == "objectid":
            sql = """
                SELECT DISTINCT r.TypeId
                FROM TBL_Register r
                JOIN TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
                WHERE cp.ObjectId = (
                    SELECT TOP 1 cp2.ObjectId
                    FROM TBL_ConnectionPoint cp2
                    WHERE cp2.EAN_ConnectionPoint = ?
                )
            """
            params = (ean_value,)

        elif search_method == "registerid":
            sql = "SELECT DISTINCT TypeId FROM dbo.TBL_Register WHERE ID = ?"
            params = (int(ean_value),)

        elif search_method == "registratorid":
            sql = "SELECT DISTINCT TypeId FROM dbo.TBL_Register WHERE RegistratorID = ?"
            params = (int(ean_value),)

        else:
            raise ValueError(f"Onbekende search_method '{search_method}'")

        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params)

        result: Set[int] = set(df["TypeId"].unique()) if not df.empty else set()

    except Exception as exc:
        logger.exception("fetch_typeids_for_ean error: %s", exc)
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
    """Roep *usp_GetMinMaxPeriodForEAN* aan en cache het resultaat."""
    engine = _ensure_engine(engine)
    cache_key = (
        ean_value, allowed_typeids_str, start_date, end_date, search_method
    )
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
            )
        if df.empty or pd.isnull(df.iloc[0, 0]):
            result = (None, None)
        else:
            result = (df["MinUTCPeriod"].iloc[0], df["MaxUTCPeriod"].iloc[0])

    except Exception as exc:
        logger.exception("fetch_min_max_period error: %s", exc)
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
    """Roept *usp_GetConnectionDataFull* aan en cachet het pivot-resultaat."""
    engine = _ensure_engine(engine)
    cache_key = (
        ean_value, allowed_typeids_str, start_date, end_date,
        interval_minutes, include_status, search_method
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

    except Exception as exc:
        logger.exception("fetch_full_data error: %s", exc)
        result = None

    _full_data_cache.set(cache_key, result)
    return result


# --------------------------------------------------------------------------- #
# Aggregatie-helpers
# --------------------------------------------------------------------------- #

_registerid_pattern = re.compile(r"\((\d+)\)")

def _map_registerids_to_typeids(
    df: pd.DataFrame,
    *,
    engine: Engine
) -> dict[int, int]:
    """Geef mapping RegisterID → TypeId op basis van kolomnamen '(123)'."""
    reg_ids: Set[int] = {
        int(m.group(1))
        for col in df.columns
        for m in [_registerid_pattern.search(col)]
        if m and col.lower() not in {"utcperiod", "utc period"}
    }
    if not reg_ids:
        return {}

    sql = f"""
        SELECT ID, TypeId
        FROM dbo.TBL_Register
        WHERE ID IN ({','.join(map(str, reg_ids))})
    """
    with engine.connect() as conn:
        mapping_df = pd.read_sql_query(sql, conn)
    return dict(zip(mapping_df["ID"], mapping_df["TypeId"]))


def group_columns_by_typeid(
    df: pd.DataFrame,
    *,
    group_mapping: dict[str, List[int]] | None = None,
    include_status: bool = False,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """
    Zet full-pivot DF om naar totale consumptie (en optioneel status)
    per virtuele **groep**.
    """
    engine = _ensure_engine(engine)
    group_mapping = group_mapping or group_typeid_mapping

    if "utcperiod" not in df.columns:
        raise ValueError("DataFrame mist 'utcperiod' kolom")

    regid_to_typeid = _map_registerids_to_typeids(df, engine=engine)
    out = {"utcperiod": pd.to_datetime(df["utcperiod"])}
    df_n = df.copy()

    for grp, tid_list in group_mapping.items():
        cons_cols, status_cols = [], []
        for col in df_n.columns:
            m = _registerid_pattern.search(col)
            if not m:
                continue
            reg_id = int(m.group(1))
            if regid_to_typeid.get(reg_id) in tid_list:
                (status_cols if "(status)" in col.lower() else cons_cols).append(col)

        out[f"{grp} Total"] = (
            df_n[cons_cols].sum(axis=1, numeric_only=True)
            if cons_cols else 0
        )

        if include_status:
            def _agg_status(row):
                if any(row[status_cols] == "P"):
                    return "P"
                if any(row[status_cols] == "T"):
                    return "T"
                return ""
            out[f"{grp} Status"] = (
                df_n.apply(_agg_status, axis=1) if status_cols else ""
            )

    return pd.DataFrame(out)


# --------------------------------------------------------------------------- #
# Dataset-bouw  (FIX 2025-05-23)
# --------------------------------------------------------------------------- #

def build_dataset(
    ean_val: str,
    chosen_groups: List[str],
    start_date: datetime,
    end_date: datetime,
    freq_val: str,
    aggregate: bool,
    *,
    include_status_raw: bool = False,
    search_method: str = "transferpoint",
    engine: Engine | None = None,
) -> Optional[pd.DataFrame]:
    """
    High-level ETL: haalt SP-data op, groepeert/resamplet en levert een
    analyse-klare DataFrame met **altijd** de kolom 'UTC Period'.
    """
    engine = _ensure_engine(engine)

    # ── 1. TypeIDs bepalen ──────────────────────────────────────────────────
    typeids = [tid for grp in chosen_groups
                     for tid in group_typeid_mapping.get(grp, [])]
    if not typeids:
        logger.warning("build_dataset: geen TypeIDs voor groepen %s", chosen_groups)
        return None
    allowed_typeids = ",".join(map(str, sorted(set(typeids))))

    # ── 2. Bestaat er data? ─────────────────────────────────────────────────
    min_p, _ = fetch_min_max_period(
        ean_val, allowed_typeids, start_date, end_date,
        search_method, engine=engine
    )
    if min_p is None:
        logger.info("build_dataset: geen data in opgegeven periode.")
        return None

    # ── 3. SP-data ophalen ──────────────────────────────────────────────────
    interval_minutes = (
        get_freq_minutes(freq_val)
        if freq_val.lower() != "auto" else 5
    )
    df_full = fetch_full_data(
        ean_val, allowed_typeids,
        start_date, end_date,
        interval_minutes=interval_minutes,
        include_status=include_status_raw and not aggregate,
        search_method=search_method,
        engine=engine,
    )
    if df_full is None or df_full.empty:
        logger.info("build_dataset: SP gaf geen data.")
        return None

    df_filtered = df_full.loc[
        (df_full["utcperiod"] >= start_date) &
        (df_full["utcperiod"] <= end_date)
    ].copy()
    if df_filtered.empty:
        return None

    # ── 4. Kolomselectie / groepering ──────────────────────────────────────
    if aggregate:
        df_interest = group_columns_by_typeid(
            df_filtered,
            include_status=include_status_raw,
            engine=engine,
            group_mapping={g: group_typeid_mapping[g] for g in chosen_groups},
        )
    else:
        df_interest = df_filtered.copy()
        regid_to_typeid = _map_registerids_to_typeids(df_interest, engine=engine)
        allowed_typeids_set = {tid for g in chosen_groups
                                      for tid in group_typeid_mapping[g]}
        keep_cols = [
            col for col in df_interest.columns
            if col.lower() == "utcperiod"
            or (
                (m := _registerid_pattern.search(col))
                and regid_to_typeid.get(int(m.group(1))) in allowed_typeids_set
            )
        ]
        df_interest = df_interest[keep_cols]

    if df_interest.empty:
        return None

    # ── 5. Resample – statuskolommen behouden ------------------------------ 
    df_interest.set_index(
        pd.to_datetime(df_interest["utcperiod"]), inplace=True
    )
    df_interest.drop(columns=["utcperiod"], inplace=True)

    if freq_val.lower() == "auto":
        freq_val = detect_auto_frequency(df_interest.index.sort_values())
    pandas_freq = get_pandas_freq(freq_val) or freq_val

    status_cols  = [c for c in df_interest.columns if "(status)" in c.lower()]
    numeric_cols = [c for c in df_interest.columns if c not in status_cols]

    def _agg_status(series: pd.Series) -> str:
        if (series == "P").any():
            return "P"
        if (series == "T").any():
            return "T"
        return ""

    agg_map = {c: "sum" for c in numeric_cols}
    agg_map.update({c: _agg_status for c in status_cols})

    df_resampled = df_interest.resample(pandas_freq).agg(agg_map).reset_index()

    # ── 5a. Zorg **altijd** voor kolom 'UTC Period' ------------------------
    time_col_candidates = {"index", "utcperiod", df_resampled.columns[0]}
    for cand in time_col_candidates:
        if cand in df_resampled.columns:
            df_resampled.rename(columns={cand: "UTC Period"}, inplace=True)
            break

    # ── 6. Kolomvolgorde netjes ────────────────────────────────────────────
    cols = df_resampled.columns.tolist()
    if "UTC Period" in cols:
        cols.insert(0, cols.pop(cols.index("UTC Period")))
        df_resampled = df_resampled[cols]

    return df_resampled


# --------------------------------------------------------------------------- #
# Export-helpers
# --------------------------------------------------------------------------- #

def export_dataset_to_csv(df: pd.DataFrame, filename: str) -> bool:
    """Sla DF op als CSV met nette datumstring in 'UTC Period'."""
    if df is None or df.empty:
        logger.warning("export_dataset_to_csv: lege DF.")
        return False
    df_exp = df.copy()
    if "UTC Period" in df_exp.columns:
        df_exp["UTC Period"] = (
            pd.to_datetime(df_exp["UTC Period"], errors="coerce")
              .dt.strftime("%Y-%m-%d %H:%M:%S")
        )
    try:
        df_exp.to_csv(filename, index=False)
        logger.info("CSV geëxporteerd: %s", filename)
        return True
    except Exception as exc:
        logger.exception("CSV-export fout: %s", exc)
        return False


def export_dataset_to_excel(
    df: pd.DataFrame,
    filename: str,
    *,
    excel_format: bool = False,
    include_status: bool = False,
) -> bool:
    """Schrijf DF naar XLSX en pas optioneel conditionele opmaak toe."""
    if df is None or df.empty:
        logger.warning("export_dataset_to_excel: lege DF.")
        return False

    try:
        from xlsxwriter.utility import xl_col_to_name

        with pd.ExcelWriter(
            filename,
            engine="xlsxwriter",
            datetime_format="yyyy-mm-dd hh:mm:ss",
        ) as writer:
            df.to_excel(writer, index=False, sheet_name="Dataset")
            wb = writer.book
            ws = writer.sheets["Dataset"]

            # headers & randen
            hdr_fmt = wb.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "fg_color": "#F2F2F2", "border": 1, "font_name": "Arial",
                "font_size": 10,
            })
            data_fmt = wb.add_format({
                "border": 1, "align": "center", "valign": "vcenter",
                "font_name": "Arial", "font_size": 10,
            })
            for c_idx, col in enumerate(df.columns):
                ws.write(0, c_idx, col, hdr_fmt)
                width = 25 if col.lower() == "utc period" else max(15, len(col) + 2)
                ws.set_column(c_idx, c_idx, width, data_fmt)

            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)

            # optionele kleuring
            if excel_format:
                p_fmt = wb.add_format({"bg_color": "#FFFFAF"})
                t_fmt = wb.add_format({"bg_color": "#FFDB69"})
                ok_fmt = wb.add_format({"bg_color": "#CCFFCC"})

                for c_idx, col in enumerate(df.columns):
                    low = col.lower()
                    rng = (1, c_idx, len(df), c_idx)

                    if "status" in low:
                        ws.conditional_format(*rng, {
                            "type": "cell", "criteria": "==", "value": '"P"', "format": p_fmt
                        })
                        ws.conditional_format(*rng, {
                            "type": "cell", "criteria": "==", "value": '"T"', "format": t_fmt
                        })
                        ws.conditional_format(*rng, {
                            "type": "cell", "criteria": "==", "value": '""',  "format": ok_fmt
                        })
                    elif "consumption" in low and include_status:
                        status_col = col.replace("(consumption)", "(status)")
                        if status_col in df.columns:
                            s_idx = df.columns.get_loc(status_col)
                            s_letter = xl_col_to_name(s_idx)
                            ws.conditional_format(*rng, {
                                "type": "formula",
                                "criteria": f'=${s_letter}$2="P"',
                                "format": p_fmt,
                            })
                                # P
                            ws.conditional_format(*rng, {
                                "type": "formula",
                                "criteria": f'=${s_letter}$2="T"',
                                "format": t_fmt,
                            })
                                # T
                            ws.conditional_format(*rng, {
                                "type": "formula",
                                "criteria": f'=${s_letter}$2=""',
                                "format": ok_fmt,
                            })

        logger.info("Excel geëxporteerd: %s", filename)
        return True

    except Exception as exc:
        logger.exception("Excel-export fout: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# Inzichten
# --------------------------------------------------------------------------- #

def get_insights_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maak per status-kolom een mini-rapport: aantal P/T + eerste/laatste datum.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    status_cols = [c for c in df.columns if "status" in c.lower()]
    if not status_cols:
        return pd.DataFrame()

    time_col = next(
        (c for c in ("UTC Period", "utcperiod") if c in df.columns), None
    )
    rows = []
    for col in status_cols:
        for stat in ("P", "T"):
            mask = df[col] == stat
            if not mask.any():
                continue
            dates = (
                pd.to_datetime(df.loc[mask, time_col], errors="coerce")
                if time_col else pd.Series(dtype="datetime64[ns]")
            )
            rows.append({
                "Kanaal": col,
                "Status": stat,
                "Count": mask.sum(),
                "Van datum": dates.min() if not dates.empty else None,
                "Tot datum": dates.max() if not dates.empty else None,
            })

    ins = pd.DataFrame(rows)
    return ins.set_index(["Kanaal", "Status"]) if not ins.empty else ins


def generate_insights_html(df: pd.DataFrame) -> str:
    """HTML-wrapper rond `get_insights_df` voor notebook-weergave."""
    ins_df = get_insights_df(df)
    return ins_df.to_html(classes="dataframe", border=0) if not ins_df.empty else "Geen inzichten beschikbaar."


# --------------------------------------------------------------------------- #
# __all__
# --------------------------------------------------------------------------- #

__all__ = [
    "DATETIME_FORMAT",
    "MAX_ROWS",
    "parse_user_datetime",
    "round_datetime_to_freq",
    "fetch_typeids_for_ean",
    "fetch_min_max_period",
    "fetch_full_data",
    "group_columns_by_typeid",
    "build_dataset",
    "export_dataset_to_csv",
    "export_dataset_to_excel",
    "get_insights_df",
    "generate_insights_html",
]
