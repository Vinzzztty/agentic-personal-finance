from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from app.data_loader import load_transactions_from_csv_url, preprocess_transactions
from app.charts import (
    pie_by_kategori,
    pie_by_pembayaran,
    timeseries_daily_total,
    timeseries_weekly_total,
    timeseries_monthly_total,
    bar_top_categories,
)
from app.llm import llm_available, start_session, ask_with_memory, ChatSession
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


def main():
    st.set_page_config(page_title="Personal Finance", layout="wide")
    st.title("Personal AI Assistant")

    csv_url = os.getenv("SPREADSHEET_URL")
    sheet_name = os.getenv("SHEET_NAME")

    @st.cache_data(show_spinner=False)
    def _cached_load(url: str, sheet: str):
        return load_transactions_from_csv_url(url, sheet)

    raw_df = _cached_load(csv_url.strip(), sheet_name.strip())
    df = preprocess_transactions(raw_df)
    if "tanggal" in df.columns:
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")

    # ------------------------- Filters -------------------------
    st.subheader("Filters")

    valid_dates = df["tanggal"].dropna()
    min_date = valid_dates.min()
    max_date = valid_dates.max()
    default_start = min_date.date() if not pd.isna(min_date) else None
    default_end = max_date.date() if not pd.isna(max_date) else None

    all_kategori = sorted(df["kategori"].dropna().unique().tolist()) if "kategori" in df.columns else []
    all_pembayaran = sorted(df["pembayaran"].dropna().unique().tolist()) if "pembayaran" in df.columns else []

    # Session state defaults
    if "f_date_range" not in st.session_state:
        st.session_state.f_date_range = (default_start, default_end) if default_start and default_end else None
    if "f_kategori" not in st.session_state:
        st.session_state.f_kategori = all_kategori
    if "f_pembayaran" not in st.session_state:
        st.session_state.f_pembayaran = all_pembayaran
    if "f_top_n" not in st.session_state:
        st.session_state.f_top_n = 8
    if "f_granularity" not in st.session_state:
        st.session_state.f_granularity = "Weekly"
    if "f_preset" not in st.session_state:
        st.session_state.f_preset = "All time"

    # Preset options and helper
    presets = ["All time", "Last 30 days", "This month", "Last month", "YTD", "Custom"]

    def preset_range(option: str):
        if not (default_start and default_end):
            return None
        # Use data max date as reference for consistency with dataset
        ref = default_end
        if option == "All time":
            return (default_start, default_end)
        if option == "Last 30 days":
            start = pd.to_datetime(ref) - pd.Timedelta(days=29)
            return (start.date(), ref)
        if option == "This month":
            start = pd.Timestamp(ref.replace(day=1))
            return (start.date(), ref)
        if option == "Last month":
            first_this = pd.Timestamp(ref.replace(day=1))
            last_month_end = first_this - pd.Timedelta(days=1)
            last_month_start = pd.Timestamp(last_month_end.replace(day=1))
            return (last_month_start.date(), last_month_end.date())
        if option == "YTD":
            start = pd.Timestamp(ref.replace(month=1, day=1))
            return (start.date(), ref)
        return None

    # Row 1: preset, date range, granularity (horizontal), reset
    r1c1, r1c2, r1c3, r1c4 = st.columns([2, 3, 2, 1])
    with r1c1:
        chosen_preset = st.selectbox("Preset", options=presets, index=presets.index(st.session_state.f_preset), key="f_preset")
        if chosen_preset != "Custom":
            pr = preset_range(chosen_preset)
            if pr:
                st.session_state.f_date_range = pr
    with r1c2:
        if default_start and default_end:
            date_range = st.date_input(
                "Date range",
                value=st.session_state.f_date_range,
                min_value=default_start,
                max_value=default_end,
                key="f_date_range",
            )
        else:
            date_range = st.date_input("Date range", key="f_date_range")
    with r1c3:
        granularity = st.radio("Timeseries", ["Daily", "Weekly", "Monthly"], index=["Daily","Weekly","Monthly"].index(st.session_state.f_granularity), horizontal=True, key="f_granularity")
    with r1c4:
        if st.button("Reset", use_container_width=True):
            st.session_state.f_preset = "All time"
            st.session_state.f_date_range = (default_start, default_end) if default_start and default_end else None
            st.session_state.f_kategori = all_kategori
            st.session_state.f_pembayaran = all_pembayaran
            st.session_state.f_top_n = 8
            st.session_state.f_granularity = "Weekly"

    # Counts for informative labels
    kategori_counts = df["kategori"].value_counts(dropna=False) if "kategori" in df.columns else pd.Series(dtype=int)
    pembayaran_counts = df["pembayaran"].value_counts(dropna=False) if "pembayaran" in df.columns else pd.Series(dtype=int)
    kategori_label = lambda v: f"{v} ({int(kategori_counts.get(v, 0))})"
    pembayaran_label = lambda v: f"{v} ({int(pembayaran_counts.get(v, 0))})"

    # Row 2: kategori, pembayaran, topN + summary
    r2c1, r2c2, r2c3, r2c4 = st.columns([3, 3, 2, 2])
    with r2c1:
        kcol1, kcol2 = st.columns([1, 1])
        with kcol1:
            if st.button("Select all", key="btn_kat_all"):
                st.session_state.f_kategori = all_kategori
        with kcol2:
            if st.button("Clear", key="btn_kat_clear"):
                st.session_state.f_kategori = []
        selected_kategori = st.multiselect(
            "Kategori",
            options=all_kategori,
            default=st.session_state.f_kategori,
            format_func=kategori_label,
            key="f_kategori",
        )
    with r2c2:
        pcol1, pcol2 = st.columns([1, 1])
        with pcol1:
            if st.button("Select all", key="btn_pay_all"):
                st.session_state.f_pembayaran = all_pembayaran
        with pcol2:
            if st.button("Clear", key="btn_pay_clear"):
                st.session_state.f_pembayaran = []
        selected_pembayaran = st.multiselect(
            "Pembayaran",
            options=all_pembayaran,
            default=st.session_state.f_pembayaran,
            format_func=pembayaran_label,
            key="f_pembayaran",
        )
    with r2c3:
        top_n = st.slider("Top N", min_value=3, max_value=20, value=st.session_state.f_top_n, key="f_top_n")
    with r2c4:
        # Active filter summary
        if isinstance(st.session_state.f_date_range, (list, tuple)) and len(st.session_state.f_date_range) == 2:
            dr_start, dr_end = st.session_state.f_date_range
            dr_text = f"{dr_start} → {dr_end}"
        else:
            dr_text = "All dates"
        st.caption(
            f"Filters: {dr_text} | {len(st.session_state.f_kategori)} kategori | {len(st.session_state.f_pembayaran)} pembayaran | Top {st.session_state.f_top_n} | {st.session_state.f_granularity}"
        )

    # ------------------------- Apply Filters -------------------------
    filtered = df.copy()
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2 and date_range[0] and date_range[1]:
        start_ts = pd.to_datetime(date_range[0])
        end_ts = pd.to_datetime(date_range[1])
        filtered = filtered[(filtered["tanggal"].notna()) & (filtered["tanggal"].between(start_ts, end_ts))]

    if selected_kategori and "kategori" in filtered.columns:
        filtered = filtered[filtered["kategori"].isin(selected_kategori)]

    if selected_pembayaran and "pembayaran" in filtered.columns:
        filtered = filtered[filtered["pembayaran"].isin(selected_pembayaran)]

    # ------------------------- KPI Summary -------------------------
    st.subheader("Overview")
    k1, k2, k3, k4 = st.columns(4)
    total_spend = float(filtered["total"].sum()) if "total" in filtered.columns else 0.0
    num_tx = int(len(filtered))
    avg_tx = (total_spend / num_tx) if num_tx > 0 else 0.0
    if filtered["tanggal"].notna().any():
        coverage_days = int((filtered["tanggal"].max() - filtered["tanggal"].min()).days) + 1
    else:
        coverage_days = 0
    k1.metric("Total Spend", f"Rp {total_spend:,.0f}")
    k2.metric("Transactions", f"{num_tx:,}x")
    k3.metric("Avg / Transaction", f"Rp {avg_tx:,.0f}")
    k4.metric("Coverage (days)", f"{coverage_days:,} hari")

    # ------------------------- Visualizations -------------------------
    st.subheader("Charts")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Spending Over Time**")
        if granularity == "Daily":
            st.altair_chart(timeseries_daily_total(filtered), use_container_width=True)
        elif granularity == "Weekly":
            st.altair_chart(timeseries_weekly_total(filtered), use_container_width=True)
        else:
            st.altair_chart(timeseries_monthly_total(filtered), use_container_width=True)
    with c2:
        st.markdown("**Top Categories (Bar)**")
        st.altair_chart(bar_top_categories(filtered, top_n=top_n), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Pie by Category**")
        st.altair_chart(pie_by_kategori(filtered, top_n=top_n), use_container_width=True)
    with c4:
        st.markdown("**Pie by Payment Method**")
        st.altair_chart(pie_by_pembayaran(filtered, top_n=top_n), use_container_width=True)

    # ------------------------- Insights -------------------------
    st.subheader("Insights")
    
    if filtered.empty:
        st.info("No data available for the current filters.")
    else:
        # Create tabs for different insight categories
        insight_tab1, insight_tab2, insight_tab3, insight_tab4 = st.tabs(["📊 Overview", "📈 Trends", "💳 Categories", "💰 Recommendations"])
        
        with insight_tab1:
            # Basic insights
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Key Metrics**")
                if "total" in filtered.columns:
                    total_spend = filtered["total"].sum()
                    avg_daily = filtered.groupby(filtered["tanggal"].dt.date)["total"].sum().mean() if filtered["tanggal"].notna().any() else 0
                    st.metric("Total Spending", f"Rp {total_spend:,.0f}")
                    st.metric("Average Daily Spend", f"Rp {avg_daily:,.0f}")
                    
                    if "tanggal" in filtered.columns and filtered["tanggal"].notna().any():
                        date_range = filtered["tanggal"].max() - filtered["tanggal"].min()
                        st.metric("Data Coverage", f"{date_range.days + 1} days")
                
                if "kategori" in filtered.columns:
                    unique_categories = filtered["kategori"].nunique()
                    st.metric("Categories Used", f"{unique_categories}")
            
            with col2:
                st.markdown("**Top Performers**")
                if "kategori" in filtered.columns and "total" in filtered.columns:
                    top_category = filtered.groupby("kategori")["total"].sum().sort_values(ascending=False).head(1)
                    if not top_category.empty:
                        st.metric("Top Category", f"{top_category.index[0]}", f"Rp {top_category.iloc[0]:,.0f}")
                
                if "pembayaran" in filtered.columns and "total" in filtered.columns:
                    top_payment = filtered.groupby("pembayaran")["total"].sum().sort_values(ascending=False).head(1)
                    if not top_payment.empty:
                        st.metric("Top Payment Method", f"{top_payment.index[0]}", f"Rp {top_payment.iloc[0]:,.0f}")
        
        with insight_tab2:
            # Trend analysis
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Spending Trends**")
                if "tanggal" in filtered.columns and "total" in filtered.columns:
                    temp = filtered.copy()
                    temp = temp[temp["tanggal"].notna()]
                    
                    if granularity == "Daily":
                        period_series = temp.groupby("tanggal")["total"].sum()
                    elif granularity == "Weekly":
                        period_series = temp.set_index("tanggal").resample("W")["total"].sum()
                    else:
                        month_idx = temp["tanggal"].dt.to_period("M").dt.to_timestamp()
                        period_series = temp.assign(month=month_idx).groupby("month")["total"].sum()
                    
                    if not period_series.empty:
                        peak_when = period_series.idxmax()
                        peak_value = period_series.max()
                        low_when = period_series.idxmin()
                        low_value = period_series.min()
                        
                        label = "week" if granularity == "Weekly" else ("month" if granularity == "Monthly" else "day")
                        st.metric(f"Peak {label.title()}", f"{peak_when.date()}", f"Rp {peak_value:,.0f}")
                        st.metric(f"Lowest {label.title()}", f"{low_when.date()}", f"Rp {low_value:,.0f}")
                        
                        # Trend direction
                        if len(period_series) > 1:
                            first_half = period_series.head(len(period_series)//2).mean()
                            second_half = period_series.tail(len(period_series)//2).mean()
                            trend = "↗️ Increasing" if second_half > first_half else "↘️ Decreasing" if second_half < first_half else "→ Stable"
                            st.metric("Trend Direction", trend)
            
            with col2:
                st.markdown("**Patterns**")
                if "tanggal" in filtered.columns and "total" in filtered.columns:
                    temp = filtered.copy()
                    temp = temp[temp["tanggal"].notna()]
                    
                    # Day of week analysis
                    temp["day_of_week"] = temp["tanggal"].dt.day_name()
                    day_spending = temp.groupby("day_of_week")["total"].sum().sort_values(ascending=False)
                    if not day_spending.empty:
                        st.metric("Highest Spending Day", f"{day_spending.index[0]}", f"Rp {day_spending.iloc[0]:,.0f}")
                    
                    # Month analysis
                    temp["month"] = temp["tanggal"].dt.month_name()
                    month_spending = temp.groupby("month")["total"].sum().sort_values(ascending=False)
                    if not month_spending.empty:
                        st.metric("Highest Spending Month", f"{month_spending.index[0]}", f"Rp {month_spending.iloc[0]:,.0f}")
        
        with insight_tab3:
            # Category analysis
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Category Breakdown**")
                if "kategori" in filtered.columns and "total" in filtered.columns:
                    cat_analysis = filtered.groupby("kategori").agg({
                        "total": ["sum", "count", "mean"],
                        "tanggal": "nunique"
                    }).round(2)
                    cat_analysis.columns = ["Total Spend", "Transaction Count", "Average Amount", "Active Days"]
                    cat_analysis = cat_analysis.sort_values("Total Spend", ascending=False)
                    
                    if not cat_analysis.empty:
                        st.dataframe(cat_analysis.head(10), use_container_width=True)
                        
                        # Category efficiency
                        if len(cat_analysis) > 1:
                            most_efficient = cat_analysis.loc[cat_analysis["Average Amount"].idxmax()]
                            st.metric("Highest Avg Transaction", f"Rp {most_efficient['Average Amount']:,.0f}", 
                                    f"{most_efficient.name}")
            
            with col2:
                st.markdown("**Payment Analysis**")
                if "pembayaran" in filtered.columns and "total" in filtered.columns:
                    pay_analysis = filtered.groupby("pembayaran").agg({
                        "total": ["sum", "count", "mean"],
                        "tanggal": "nunique"
                    }).round(2)
                    pay_analysis.columns = ["Total Spend", "Transaction Count", "Average Amount", "Active Days"]
                    pay_analysis = pay_analysis.sort_values("Total Spend", ascending=False)
                    
                    if not pay_analysis.empty:
                        st.dataframe(pay_analysis, use_container_width=True)
                        
                        # Payment preference
                        if len(pay_analysis) > 1:
                            most_used = pay_analysis.loc[pay_analysis["Transaction Count"].idxmax()]
                            st.metric("Most Used Method", f"{most_used.name}", f"{most_used['Transaction Count']} transactions")
        
        with insight_tab4:
            # Recommendations and insights
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Smart Insights**")
                insights_list = []
                
                if "total" in filtered.columns and "tanggal" in filtered.columns:
                    # Spending frequency
                    if filtered["tanggal"].notna().any():
                        date_range = filtered["tanggal"].max() - filtered["tanggal"].min()
                        avg_frequency = len(filtered) / (date_range.days + 1)
                        if avg_frequency > 2:
                            insights_list.append("🔄 High transaction frequency - consider batch purchases")
                        elif avg_frequency < 0.5:
                            insights_list.append("📅 Low transaction frequency - good spending control")
                    
                    # Category balance
                    if "kategori" in filtered.columns:
                        cat_spending = filtered.groupby("kategori")["total"].sum()
                        if len(cat_spending) > 1:
                            top_cat_ratio = cat_spending.max() / cat_spending.sum()
                            if top_cat_ratio > 0.5:
                                insights_list.append("⚖️ Spending heavily concentrated in one category")
                            elif top_cat_ratio < 0.2:
                                insights_list.append("🎯 Well-balanced spending across categories")
                
                if "pembayaran" in filtered.columns:
                    # Payment method diversity
                    payment_methods = filtered["pembayaran"].nunique()
                    if payment_methods == 1:
                        insights_list.append("💳 Using single payment method - consider diversifying")
                    elif payment_methods > 3:
                        insights_list.append("💳 Good payment method diversity")
                
                if insights_list:
                    for insight in insights_list:
                        st.markdown(f"- {insight}")
                else:
                    st.info("No specific insights available for current data.")
            
            with col2:
                st.markdown("**Recommendations**")
                recommendations = []
                
                if "kategori" in filtered.columns and "total" in filtered.columns:
                    # Category recommendations
                    cat_spending = filtered.groupby("kategori")["total"].sum().sort_values(ascending=False)
                    if not cat_spending.empty:
                        top_category = cat_spending.index[0]
                        top_amount = cat_spending.iloc[0]
                        total_spend = cat_spending.sum()
                        
                        if top_amount / total_spend > 0.4:
                            recommendations.append(f"💰 Consider reducing spending in {top_category}")
                        
                        # Find potential savings
                        if len(cat_spending) > 1:
                            second_cat = cat_spending.iloc[1]
                            if top_amount > second_cat * 2:
                                recommendations.append(f"📊 {top_category} spending is significantly higher than other categories")
                
                if "tanggal" in filtered.columns and "total" in filtered.columns:
                    # Time-based recommendations
                    temp = filtered.copy()
                    temp = temp[temp["tanggal"].notna()]
                    if len(temp) > 1:
                        daily_spending = temp.groupby(temp["tanggal"].dt.date)["total"].sum()
                        if daily_spending.std() > daily_spending.mean() * 0.5:
                            recommendations.append("📅 High spending variability - consider setting daily budgets")
                
                if recommendations:
                    for rec in recommendations:
                        st.markdown(f"- {rec}")
                else:
                    st.info("No specific recommendations at this time.")

    # ------------------------- Data & Download -------------------------
    with st.expander("View filtered data"):
        st.dataframe(filtered, use_container_width=True)
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="transactions_filtered.csv", mime="text/csv")

    # ------------------------- Chat with temporary memory -------------------------
    st.subheader("Chat (temporary memory)")
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = start_session(filtered)
    else:
        # Update session with filtered data when filters change
        st.session_state.chat_session = start_session(filtered)

    session: ChatSession = st.session_state.chat_session

    # Show history
    for msg in session.messages:
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])  # type: ignore[arg-type]
        elif msg["role"] == "assistant":
            st.chat_message("assistant").markdown(msg["content"])  # type: ignore[arg-type]

    if not llm_available():
        st.info("Ollama belum terpasang/berjalan. Install dan jalankan Ollama untuk menggunakan chat.")

    prompt = st.chat_input("Tanyakan tentang datamu...")
    if prompt:
        # Display user message
        st.chat_message("user").markdown(prompt)
        
        # Create a placeholder for the assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Show loading indicator
            with st.spinner("🤔 AI sedang menganalisis data..."):
                # Initialize response accumulator
                full_response = ""
                
                def stream_callback(content: str, is_complete: bool = False):
                    """Callback function for streaming updates"""
                    nonlocal full_response
                    if not is_complete:
                        full_response += content
                        # Update the placeholder with accumulated content
                        message_placeholder.markdown(full_response + "▌")
                    else:
                        # Final update without cursor
                        message_placeholder.markdown(full_response)
                
                try:
                    # Use streaming if available, fallback to regular if not
                    from app.llm import ask_with_memory_streaming
                    answer = ask_with_memory_streaming(session, prompt, stream_callback)
                except ImportError:
                    # Fallback to non-streaming
                    from app.llm import ask_with_memory
                    answer = ask_with_memory(session, prompt)
                    message_placeholder.markdown(answer)


if __name__ == "__main__":
    main()