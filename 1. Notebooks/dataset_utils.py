"""
dataset_utils.py
----------------
Mid/high-level data processing: grouping, resampling, export & insights.

Depends only on:
• time_utils          (date helpers)
• db_utils            (data access)
• frequency_utils     (resolution helpers)
• mappings            (business mapping of TypeIds → logical groups)
"""

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
# Internal helpers
# --------------------------------------------------------------------------- #
_registerid_pattern = re.compile(r"\((\d+)\)")


def _map_registerids_to_typeids(df: pd.DataFrame, *, engine: Engine) -> Dict[int, int]:
    """Return {RegisterID → TypeId} for every register present in the dataframe."""
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
    Collapse the full pivot coming from the stored procedure into **group totals**.

    Keeps status columns where requested.
    """
    engine = _ensure_engine(engine)
    group_mapping = group_mapping or group_typeid_mapping

    if "utcperiod" not in df.columns:
        raise ValueError("DataFrame is missing 'utcperiod' column")

    regid_to_typeid = _map_registerids_to_typeids(df, engine=engine)
    result = {"utcperiod": pd.to_datetime(df["utcperiod"])}
    df_n = df.copy()

    for grp, tids in group_mapping.items():
        cons_cols, status_cols = [], []
        for col in df_n.columns:
            m = _registerid_pattern.search(col)
            if m:
                reg_id = int(m.group(1))
                if regid_to_typeid.get(reg_id) in tids:
                    (status_cols if "(status)" in col.lower() else cons_cols).append(col)

        result[f"{grp} Total"] = df_n[cons_cols].sum(axis=1, numeric_only=True) if cons_cols else 0

        if include_status:
            def _agg_status(row):
                if any(row[status_cols] == "P"):
                    return "P"
                if any(row[status_cols] == "T"):
                    return "T"
                return ""

            result[f"{grp} Status"] = (
                df_n.apply(_agg_status, axis=1) if status_cols else ""
            )

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
    The notebook-level “one-liner”: validate → fetch SP data → group/resample.

    Always returns a dataframe containing **UTC Period** as first column
    or `None` when no data matched.
    """
    engine = _ensure_engine(engine)

    # 1. Resolve TypeIds for selected logical groups
    typeids = [tid for grp in chosen_groups for tid in group_typeid_mapping.get(grp, [])]
    if not typeids:
        logger.warning("build_dataset: no TypeIds found for groups %s", chosen_groups)
        return None
    allowed_typeids = ",".join(map(str, sorted(set(typeids))))

    # 2. Quick existence check (saves a heavy SP call when no data)
    min_p, _ = fetch_min_max_period(
        ean_val,
        allowed_typeids,
        start_date,
        end_date,
        search_method,
        engine=engine,
    )
    if min_p is None:
        logger.info("build_dataset: no data in requested period.")
        return None

    # 3. Fetch data with the correct granularity from the SP
    interval_minutes = get_freq_minutes(freq_val) if freq_val.lower() != "auto" else 5
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

    df_filtered = df_full.loc[
        (df_full["utcperiod"] >= start_date) & (df_full["utcperiod"] <= end_date)
    ].copy()
    if df_filtered.empty:
        return None

    # 4. Column selection / grouping
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
        allowed_set = {tid for g in chosen_groups for tid in group_typeid_mapping[g]}
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

    # 5. Resample (status columns kept separately)
    df_interest.set_index(pd.to_datetime(df_interest["utcperiod"]), inplace=True)
    df_interest.drop(columns=["utcperiod"], inplace=True)

    if freq_val.lower() == "auto":
        freq_val = detect_auto_frequency(df_interest.index.sort_values())
    pandas_freq = get_pandas_freq(freq_val) or freq_val

    status_cols = [c for c in df_interest.columns if "(status)" in c.lower()]
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

    # 5a. Ensure first column is always "UTC Period"
    time_col = df_resampled.columns[0]
    df_resampled.rename(columns={time_col: "UTC Period"}, inplace=True)
    cols = ["UTC Period"] + [c for c in df_resampled.columns if c != "UTC Period"]
    return df_resampled[cols]


# --------------------------------------------------------------------------- #
# Export helpers
# --------------------------------------------------------------------------- #
def export_dataset_to_csv(df: pd.DataFrame, filename: str) -> bool:
    """Write dataframe to CSV, formatting 'UTC Period' nicely."""
    if df is None or df.empty:
        logger.warning("export_dataset_to_csv: empty dataframe")
        return False
    df_exp = df.copy()
    if "UTC Period" in df_exp.columns:
        df_exp["UTC Period"] = (
            pd.to_datetime(df_exp["UTC Period"], errors="coerce")
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )
    try:
        df_exp.to_csv(filename, index=False)
        logger.info("CSV exported: %s", filename)
        return True
    except Exception as exc:  # pragma: no cover
        logger.exception("CSV export failed: %s", exc)
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

            hdr_fmt = wb.add_format(
                {
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "fg_color": "#F2F2F2",
                    "border": 1,
                    "font_name": "Arial",
                    "font_size": 10,
                }
            )
            data_fmt = wb.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "font_name": "Arial",
                    "font_size": 10,
                }
            )

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
                        ws.conditional_format(*rng, {"type": "cell", "criteria": "==", "value": '"P"', "format": p_fmt})
                        ws.conditional_format(*rng, {"type": "cell", "criteria": "==", "value": '"T"', "format": t_fmt})
                        ws.conditional_format(*rng, {"type": "cell", "criteria": "==", "value": '""', "format": ok_fmt})

                    elif "consumption" in low and include_status:
                        status_col = col.replace("(consumption)", "(status)")
                        if status_col in df.columns:
                            s_idx = df.columns.get_loc(status_col)
                            s_letter = xl_col_to_name(s_idx)
                            ws.conditional_format(
                                *rng,
                                {
                                    "type": "formula",
                                    "criteria": f'=${s_letter}$2="P"',
                                    "format": p_fmt,
                                },
                            )
                            ws.conditional_format(
                                *rng,
                                {
                                    "type": "formula",
                                    "criteria": f'=${s_letter}$2="T"',
                                    "format": t_fmt,
                                },
                            )
                            ws.conditional_format(
                                *rng,
                                {
                                    "type": "formula",
                                    "criteria": f'=${s_letter}$2=""',
                                    "format": ok_fmt,
                                },
                            )
        logger.info("Excel exported: %s", filename)
        return True
    except Exception as exc:  # pragma: no cover
        logger.exception("Excel export failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
def get_insights_df(df: pd.DataFrame) -> pd.DataFrame:
    """Simple status report (count P/T, first + last date)."""
    if df is None or df.empty:
        return pd.DataFrame()

    status_cols = [c for c in df.columns if "status" in c.lower()]
    if not status_cols:
        return pd.DataFrame()

    time_col = next((c for c in ("UTC Period", "utcperiod") if c in df.columns), None)
    rows = []
    for col in status_cols:
        for stat in ("P", "T"):
            mask = df[col] == stat
            if not mask.any():
                continue
            dates = pd.to_datetime(df.loc[mask, time_col], errors="coerce") if time_col else pd.Series(dtype="datetime64[ns]")
            rows.append(
                {
                    "Kanaal": col,
                    "Status": stat,
                    "Count": mask.sum(),
                    "Van datum": dates.min() if not dates.empty else None,
                    "Tot datum": dates.max() if not dates.empty else None,
                }
            )

    ins = pd.DataFrame(rows)
    return ins.set_index(["Kanaal", "Status"]) if not ins.empty else ins


def generate_insights_html(df: pd.DataFrame) -> str:
    """Return insights dataframe as styled HTML snippet for Jupyter."""
    ins_df = get_insights_df(df)
    return ins_df.to_html(classes="dataframe", border=0) if not ins_df.empty else "Geen inzichten beschikbaar."


__all__ = [
    "group_columns_by_typeid",
    "build_dataset",
    "export_dataset_to_csv",
    "export_dataset_to_excel",
    "get_insights_df",
    "generate_insights_html",
]
