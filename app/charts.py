from __future__ import annotations

import pandas as pd
import altair as alt


def pie_chart(df: pd.DataFrame, category_col: str, value_col: str, top_n: int = 8) -> alt.Chart:
    agg = (
        df.groupby(category_col, dropna=False)[value_col]
        .sum(numeric_only=True)
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    chart = (
        alt.Chart(agg)
        .mark_arc()
        .encode(
            theta=alt.Theta(field=value_col, type="quantitative"),
            color=alt.Color(field=category_col, type="nominal"),
            tooltip=[category_col, value_col],
        )
    )
    return chart


def pie_by_kategori(df: pd.DataFrame, top_n: int = 8) -> alt.Chart:
    safe = df.copy()
    safe = safe[(safe["total"].notna()) & (safe["kategori"].astype(str).str.len() > 0)]
    return pie_chart(safe, category_col="kategori", value_col="total", top_n=top_n)


def pie_by_pembayaran(df: pd.DataFrame, top_n: int = 8) -> alt.Chart:
    safe = df.copy()
    safe = safe[(safe["total"].notna()) & (safe["pembayaran"].astype(str).str.len() > 0)]
    return pie_chart(safe, category_col="pembayaran", value_col="total", top_n=top_n)


def timeseries_daily_total(df: pd.DataFrame) -> alt.Chart:
    safe = df.copy()
    if "tanggal" in safe.columns:
        safe["tanggal"] = pd.to_datetime(safe["tanggal"], errors="coerce")
    safe = safe[safe["tanggal"].notna() & safe["total"].notna()]
    daily = safe.groupby("tanggal", as_index=False)["total"].sum(numeric_only=True)
    chart = (
        alt.Chart(daily)
        .mark_line(point=True)
        .encode(
            x=alt.X("tanggal:T", title="Tanggal"),
            y=alt.Y("total:Q", title="Total"),
            tooltip=["tanggal:T", "total:Q"],
        )
    )
    return chart


def timeseries_monthly_total(df: pd.DataFrame) -> alt.Chart:
    safe = df.copy()
    if "tanggal" in safe.columns:
        safe["tanggal"] = pd.to_datetime(safe["tanggal"], errors="coerce")
    safe = safe[safe["tanggal"].notna() & safe["total"].notna()]
    safe["month"] = safe["tanggal"].dt.to_period("M").dt.to_timestamp()
    monthly = safe.groupby("month", as_index=False)["total"].sum(numeric_only=True)
    chart = (
        alt.Chart(monthly)
        .mark_bar()
        .encode(
            x=alt.X("month:T", title="Bulan"),
            y=alt.Y("total:Q", title="Total"),
            tooltip=["month:T", "total:Q"],
        )
    )
    return chart


def bar_top_categories(df: pd.DataFrame, top_n: int = 10) -> alt.Chart:
    safe = df.copy()
    safe = safe[safe["total"].notna()]
    agg = (
        safe.groupby("kategori", dropna=False)["total"].sum(numeric_only=True).sort_values(ascending=False).head(top_n)
    ).reset_index()
    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("total:Q", title="Total"),
            y=alt.Y("kategori:N", sort="-x", title="Kategori"),
            tooltip=["kategori", "total"],
        )
    )
    return chart

