# dataset_utils.py
# ----------------
# Mid/high-level data processing: grouping, resampling, export & insights.

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from frequency_utils import (
    detect_auto_frequency,
    get_freq_minutes,
    get_pandas_freq,
)
from mappings import group_typeid_mapping
from time_utils import DATETIME_FORMAT
from db_utils import (
    _ensure_engine,
    fetch_full_data,
    fetch_min_max_period,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Mapping deprecated pandas frequency-aliasen naar de nieuwe benamingen
# --------------------------------------------------------------------------- #
_FREQ_ALIAS_MAP: dict[str, str] = {
    "T":  "min",   # minutes
    "H":  "h",     # hours
    "M":  "ME",    # month end
    "A":  "YE",    # year end
}

# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
_registerid_pattern = re.compile(r"\((\d+)\)")

def _map_registerids_to_typeids(df: pd.DataFrame, *, engine: Engine) -> Dict[int, int]:
    """Return {RegisterID → TypeId} voor iedere kolom met een register-id."""
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


def _join_statuses(vals: pd.Series | list[str], sep: str = "/") -> str:
    """
    Combineer alle niet-lege statuswaarden tot één geordende string.

    Voorbeeld:
        ["P", "T", "P", "I"]   →   "I/P/T"
    """
    uniq = {str(v).strip() for v in vals if str(v).strip()}
    return sep.join(sorted(uniq)) if uniq else ""


# --------------------------------------------------------------------------- #
# Public processing functions
# --------------------------------------------------------------------------- #
def group_columns_by_typeid(
    df: pd.DataFrame,
    *,
    group_mapping: Dict[str, List[int]] | None = None,
    include_status: bool = False,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """
    Collapse de volledige pivot uit de stored procedure in groeps-totals.

    Houdt statuskolommen bij wanneer `include_status=True`.
    """
    engine = _ensure_engine(engine)
    group_mapping = group_mapping or group_typeid_mapping

    if "utcperiod" not in df.columns:
        raise ValueError("DataFrame mist kolom 'utcperiod'")

    regid_to_typeid = _map_registerids_to_typeids(df, engine=engine)
    result: dict[str, pd.Series | int] = {"utcperiod": pd.to_datetime(df["utcperiod"])}
    df_n = df.copy()

    for grp, tids in group_mapping.items():
        cons_cols: list[str] = []
        status_cols: list[str] = []
        for col in df_n.columns:
            m = _registerid_pattern.search(col)
            if m:
                reg_id = int(m.group(1))
                if regid_to_typeid.get(reg_id) in tids:
                    if "(status)" in col.lower():
                        status_cols.append(col)
                    else:
                        cons_cols.append(col)

        # Sommeer consumptie
        if cons_cols:
            result[f"{grp} Total"] = df_n[cons_cols].sum(axis=1, numeric_only=True)
        else:
            result[f"{grp} Total"] = 0

        # Combineer statussen
        if include_status:
            if status_cols:
                result[f"{grp} Status"] = df_n.apply(
                    lambda row: _join_statuses(row[status_cols]), axis=1
                )
            else:
                result[f"{grp} Status"] = ""

    return pd.DataFrame(result)


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
    Notebook-level “one-liner”: validate → fetch SP data → group/resample.

    Returned DataFrame bevat altijd **UTC Period** als eerste kolom
    of `None` wanneer geen data matched.
    """
    engine = _ensure_engine(engine)

    # 1. Resolve TypeIds
    typeids = [
        tid
        for grp in chosen_groups
        for tid in group_typeid_mapping.get(grp, [])
    ]
    if not typeids:
        logger.warning("build_dataset: geen TypeIds voor groups %s", chosen_groups)
        return None
    allowed_typeids = ",".join(map(str, sorted(set(typeids))))

    # 2. Quick existence check
    min_p, _ = fetch_min_max_period(
        ean_val,
        allowed_typeids,
        start_date,
        end_date,
        search_method,
        engine=engine,
    )
    if min_p is None:
        logger.info("build_dataset: geen data in requested period.")
        return None

    # 3. Fetch SP data
    interval_minutes = (
        get_freq_minutes(freq_val)
        if freq_val.lower() != "auto"
        else 5
    )
    df_full = fetch_full_data(
        ean_val,
        allowed_typeids,
        start_date,
        end_date,
        interval_minutes=interval_minutes,
        include_status=include_status_raw and not aggregate,
        search_method=search_method,
        engine=engine,
    )
    if df_full is None or df_full.empty:
        logger.info("build_dataset: SP returned no data.")
        return None

    # Filter op opgegeven periode
    df_filtered = df_full.loc[
        (df_full["utcperiod"] >= start_date)
        & (df_full["utcperiod"] <= end_date)
    ].copy()
    if df_filtered.empty:
        return None

    # 4. Kolomweergave: gegroepeerd of raw
    if aggregate:
        df_interest = group_columns_by_typeid(
            df_filtered,
            include_status=include_status_raw,
            engine=engine,
            group_mapping={
                g: group_typeid_mapping[g]
                for g in chosen_groups
            },
        )
    else:
        df_interest = df_filtered.copy()
        regid_to_typeid = _map_registerids_to_typeids(df_interest, engine=engine)
        allowed_set = {
            tid
            for g in chosen_groups
            for tid in group_typeid_mapping[g]
        }
        keep_cols = [
            col
            for col in df_interest.columns
            if col.lower() == "utcperiod"
            or (
                (m := _registerid_pattern.search(col))
                and regid_to_typeid.get(int(m.group(1))) in allowed_set
            )
        ]
        df_interest = df_interest[keep_cols]

    if df_interest.empty:
        return None

    # 5. Resample (status kolommen apart houden)
    df_interest.set_index(
        pd.to_datetime(df_interest["utcperiod"]), inplace=True
    )
    df_interest.drop(columns=["utcperiod"], inplace=True)

    if freq_val.lower() == "auto":
        freq_val = detect_auto_frequency(
            df_interest.index.sort_values()
        )
    pandas_freq = get_pandas_freq(freq_val) or freq_val

    # --- repareer deprecated aliasen vóór resample() ---
    pandas_freq = _FREQ_ALIAS_MAP.get(pandas_freq, pandas_freq)

    status_cols = [
        c for c in df_interest.columns if "(status)" in c.lower()
    ]
    numeric_cols = [
        c for c in df_interest.columns if c not in status_cols
    ]

    agg_map: dict[str, str | callable] = {
        c: "sum" for c in numeric_cols
    }
    # status-colaggregatie met onze helper
    agg_map.update({c: _join_statuses for c in status_cols})

    df_resampled = (
        df_interest
        .resample(pandas_freq)
        .agg(agg_map)
        .reset_index()
    )

    # 5a. Eerste kolom altijd "UTC Period"
    time_col = df_resampled.columns[0]
    df_resampled.rename(
        columns={time_col: "UTC Period"},
        inplace=True
    )
    cols = ["UTC Period"] + [
        c for c in df_resampled.columns if c != "UTC Period"
    ]
    return df_resampled[cols]


# --------------------------------------------------------------------------- #
# Export helpers
# --------------------------------------------------------------------------- #
def export_dataset_to_csv(df: pd.DataFrame, filename: str) -> bool:
    """
    Schrijft de DataFrame weg naar een CSV-bestand.
    Returns True als het gelukt is, anders False.
    """
    if df is None or df.empty:
        logger.warning("export_dataset_to_csv: lege DataFrame")
        return False

    df_exp = df.copy()
    if "UTC Period" in df_exp.columns:
        df_exp["UTC Period"] = (
            pd.to_datetime(df_exp["UTC Period"], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

    try:
        directory = os.path.dirname(filename)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)

        df_exp.to_csv(filename, index=False)
        logger.info("CSV succesvol geëxporteerd naar %s", filename)
        return True

    except Exception as e:
        logger.exception("Fout bij exporteren naar CSV: %s", e)
        return False


def export_dataset_to_excel(
    df: pd.DataFrame,
    filename: str,
    *,
    excel_format: bool = False,
    include_status: bool = False,
) -> bool:
    """
    Save dataframe to XLSX – optional conditional formatting for status columns.
    """
    if df is None or df.empty:
        logger.warning("export_dataset_to_excel: empty dataframe")
        return False

    try:
        from xlsxwriter.utility import xl_col_to_name

        with pd.ExcelWriter(
            filename,
            engine="xlsxwriter",
            datetime_format="yyyy-mm-dd hh:mm:ss",
        ) as writer:
            df.to_excel(writer, index=False, sheet_name="Dataset")
            wb, ws = writer.book, writer.sheets["Dataset"]

            hdr_fmt = wb.add_format({
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "fg_color": "#F2F2F2",
                "border": 1,
                "font_name": "Arial",
                "font_size": 10,
            })
            data_fmt = wb.add_format({
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
                "font_size": 10,
            })

            for c_idx, col in enumerate(df.columns):
                ws.write(0, c_idx, col, hdr_fmt)
                width = 25 if col.lower() == "utc period" else max(15, len(col) + 2)
                ws.set_column(c_idx, c_idx, width, data_fmt)

            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)

            if excel_format:
                p_fmt = wb.add_format({"bg_color": "#FFFFAF"})
                t_fmt = wb.add_format({"bg_color": "#FFDB69"})
                ok_fmt = wb.add_format({"bg_color": "#CCFFCC"})

                for c_idx, col in enumerate(df.columns):
                    low = col.lower()
                    rng = (1, c_idx, len(df), c_idx)

                    if "status" in low:
                        ws.conditional_format(*rng, {
                            "type": "cell",
                            "criteria": "==",
                            "value": '"P"',
                            "format": p_fmt,
                        })
                        ws.conditional_format(*rng, {
                            "type": "cell",
                            "criteria": "==",
                            "value": '"T"',
                            "format": t_fmt,
                        })
                        ws.conditional_format(*rng, {
                            "type": "cell",
                            "criteria": "==",
                            "value": '""',
                            "format": ok_fmt,
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
                            ws.conditional_format(*rng, {
                                "type": "formula",
                                "criteria": f'=${s_letter}$2="T"',
                                "format": t_fmt,
                            })
                            ws.conditional_format(*rng, {
                                "type": "formula",
                                "criteria": f'=${s_letter}$2=""',
                                "format": ok_fmt,
                            })

        logger.info("Excel succesvol geëxporteerd naar %s", filename)
        return True

    except Exception as exc:
        logger.exception("Excel export failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
def get_insights_df(df: pd.DataFrame) -> pd.DataFrame:
    """Maak dynamische status-tellingen, ongeacht welke codes er bestaan."""
    if df is None or df.empty:
        return pd.DataFrame()

    status_cols = [c for c in df.columns if "status" in c.lower()]
    if not status_cols:
        return pd.DataFrame()

    time_col = next(
        (c for c in ("UTC Period", "utcperiod") if c in df.columns),
        None
    )
    rows: list[dict[str, object]] = []

    for col in status_cols:
        # Verzamel DISTINCT statussen in de hele kolom
        all_statuses = {
            s
            for val in df[col].dropna().astype(str)
            for s in map(str.strip, val.split("/"))
            if s
        }

        for stat in sorted(all_statuses):
            mask = df[col].astype(str).str.contains(rf"\b{re.escape(stat)}\b")
            if not mask.any():
                continue

            dates = (
                pd.to_datetime(df.loc[mask, time_col], errors="coerce")
                if time_col else pd.Series(dtype="datetime64[ns]")
            )
            rows.append({
                "Kanaal": col,
                "Status": stat,
                "Count": int(mask.sum()),
                "Van datum": dates.min() if not dates.empty else None,
                "Tot datum": dates.max() if not dates.empty else None,
            })

    ins = pd.DataFrame(rows)
    return ins.set_index(["Kanaal", "Status"]) if not ins.empty else ins


def generate_insights_html(df: pd.DataFrame) -> str:
    """Return insights dataframe as styled HTML snippet for Jupyter."""
    ins_df = get_insights_df(df)
    return (
        ins_df.to_html(classes="dataframe", border=0)
        if not ins_df.empty
        else "Geen inzichten beschikbaar."
    )


__all__ = [
    # grouping & building
    "group_columns_by_typeid",
    "build_dataset",
    # export
    "export_dataset_to_csv",
    "export_dataset_to_excel",
    # insights
    "get_insights_df",
    "generate_insights_html",
]
