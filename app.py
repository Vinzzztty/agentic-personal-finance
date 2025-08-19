from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from app.data_loader import load_transactions_from_csv_url, preprocess_transactions
from app.charts import (
    pie_by_kategori,
    pie_by_pembayaran,
    timeseries_daily_total,
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
    st.subheader("Your Data Transactions")
    st.dataframe(df, use_container_width=True)

    st.subheader("Visualizations")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Pie by Kategori**")
        st.altair_chart(pie_by_kategori(df), use_container_width=True)
    with c2:
        st.markdown("**Pie by Pembayaran**")
        st.altair_chart(pie_by_pembayaran(df), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Daily Total (Line)**")
        st.altair_chart(timeseries_daily_total(df), use_container_width=True)
    with c4:
        st.markdown("**Monthly Total (Bar)**")
        st.altair_chart(timeseries_monthly_total(df), use_container_width=True)

    st.markdown("**Top Kategori (Bar)**")
    st.altair_chart(bar_top_categories(df), use_container_width=True)

    # ------------------------- Chat with temporary memory -------------------------
    st.subheader("Chat (temporary memory)")
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = start_session(df)

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
        st.chat_message("user").markdown(prompt)
        answer = ask_with_memory(session, prompt)
        st.chat_message("assistant").markdown(answer)



if __name__ == "__main__":
    main()