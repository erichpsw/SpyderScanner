
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re

# ============================================
# 🔑 API Keys Setup (Optional - Not used yet)
# ============================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")
GOOGLE_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# ============================================
# 🚀 Streamlit App Config
# ============================================
st.set_page_config(page_title="OMENReport - Spider Scanner", layout="centered")
st.title("🚀 OMENReport - Spider Options Scanner")

# ============================================
# 📥 File Upload Section
# ============================================
uploaded_file = st.file_uploader("📤 Upload Spider Scanner CSV or Excel", type=["csv", "xls", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_')
            .str.replace('-', '_')
        )

        st.subheader("✅ Columns after cleanup:")
        st.write(df.columns.tolist())

        # ============================================
        # 🔧 Premium Parsing
        def parse_premium(val):
            try:
                val = str(val).replace('$','').replace(',','').strip().lower()
                if 'k' in val:
                    val = val.replace('k','e3')
                if 'm' in val:
                    val = val.replace('m','e6')
                return float(eval(val))
            except:
                return 0

        df['premiumvalue'] = df['premium'].apply(parse_premium)

        # ============================================
        # 🔍 Sentiment Parsing
        def get_sentiment(spread):
            if pd.isna(spread):
                return 'Neutral'
            spread = str(spread).lower()
            if 'above ask' in spread:
                return 'Aggressive Bullish'
            if 'ask' in spread:
                return 'Bullish'
            if 'bidish' in spread:
                return 'Bearish'
            if 'at bid' in spread:
                return 'Aggressive Bearish'
            return 'Neutral'

        df['sentiment'] = df['trade_spread'].apply(get_sentiment)

        # ============================================
        # 🕵️ Stealth and Trade Type
        df['stealth'] = df['alerts'].apply(lambda x: '✅ High Stealth' if pd.notna(x) else '❌ None')
        df['trade_type'] = df['flags'].fillna('Unknown')

        # ============================================
        # 🏷️ Strike Expiry Label
        df['strikeexpiry'] = df['strike'].astype(str) + ' ' + df['call/put'].astype(str) + ' – ' + df['expiration_date'].astype(str)

        # ============================================
        # 🔢 Clean Numeric Columns
        def clean_numeric_column(col):
            col = col.astype(str).str.replace(',','', regex=False).replace('nan','0', regex=False)
            return pd.to_numeric(col, errors='coerce').fillna(0)

        df['trade_size_numeric'] = clean_numeric_column(df['trade_size'])
        df['open_interest_numeric'] = clean_numeric_column(df['open_interest'])

        # ============================================
        # 📊 Strategy Flags
        df['sweep'] = df['flags'].fillna('').apply(lambda x: 'Sweep' in x)
        df['above_ask'] = df['trade_spread'].fillna('').apply(lambda x: 'Above Ask' in x)
        df['vol_gt_oi'] = df['trade_size_numeric'] > df['open_interest_numeric']
        df['repeater'] = df['alerts'].fillna('').apply(lambda x: 'Repeater' in x)
        df['odd_lot'] = df['trade_size_numeric'].apply(lambda x: x > 0 and x % 100 != 0)

        df['expiration_date_datetime'] = pd.to_datetime(df['expiration_date'], errors='coerce')
        current_date = pd.Timestamp.now()
        df['short_dated'] = (df['expiration_date_datetime'] - current_date).dt.days < 30
        df['short_dated'] = df['short_dated'].fillna(False)

        # ============================================
        # 🚦 Unusual Flow Criteria
        large_premium_threshold = df['premiumvalue'].quantile(0.95)
        df['isunusual'] = (
            (df['premiumvalue'] > large_premium_threshold) |
            (df['vol_gt_oi']) |
            ((df['sweep'] | df['repeater']) & df['above_ask'])
        )

        # ============================================
        # 🏆 Scoring System
        def calculate_score(row):
            score = 0
            if row['sentiment'] in ['Aggressive Bullish', 'Aggressive Bearish']:
                score += 5
            elif row['sentiment'] in ['Bullish', 'Bearish']:
                score += 3
            else:
                score += 1
            if row['stealth'] == '✅ High Stealth':
                score += 4
            else:
                score += 1
            if row['isunusual']:
                score += 5
            else:
                score += 1
            return score

        df['score'] = df.apply(calculate_score, axis=1)

        # ============================================
        # 📄 OMENReport Generation
        if st.button("⚙️ Run OMENReport"):
            st.subheader("📄 OMENReport Results")

            report_text = ""
            tickers = df['symbol'].unique()

            for ticker in tickers:
                ticker_data = df[df['symbol'] == ticker]
                total_premium = ticker_data['premiumvalue'].sum()
                trade_count = len(ticker_data)
                max_premium = ticker_data['premiumvalue'].max()

                report_text += f"---\nTicker: {ticker}\n"
                report_text += f"Total Premium: ${total_premium:,.2f}\n"
                report_text += f"Max Premium: ${max_premium:,.2f}\n"
                report_text += f"Trade Count: {trade_count}\n"
                report_text += "Insight: Example insight goes here.\n"

            report_text += "\n---\nGenerated with OMENReport Scanner\n"

            st.text_area("📊 OMENReport Output", report_text, height=500)

            st.download_button(
                label="📥 Download OMENReport",
                data=report_text,
                file_name="OMENReport.txt",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")

else:
    st.info("⬆️ Upload a CSV or Excel file to begin.")
