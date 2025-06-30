
import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from fpdf import FPDF
import textwrap

st.set_page_config(page_title="OMEN Smart Money Scanner", layout="centered")
st.title("🚀 OMEN Smart Money Scanner")

uploaded_file = st.file_uploader("📤 Upload your SpyderScanner CSV or Excel file", type=["csv", "xls", "xlsx"])

scan_type = None
if uploaded_file is not None:
    scan_type = st.selectbox(
        "📊 Select Your Scan Type",
        ["Scan Report - Full Market", "Scan Report Small Cap", "Scan Report Mid Cap", "Scan Report Large Cap", "Scan Report Targeted"]
    )

    tickers_input = ""
    if scan_type == "Scan Report Targeted":
        tickers_input = st.text_input("Enter tickers separated by commas (e.g., HOOD, RKLB)")

    if st.button("⚙️ Run OMEN Smart Money Scan"):
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(' ', '_')
                .str.replace('-', '_')
            )

            df = df.drop(columns=['stock_cnt.', 'option_cnt.', 'option_cnt..1'], errors='ignore')

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
            df['stock_last_numeric'] = pd.to_numeric(df['stock_last'], errors='coerce').fillna(0)

            if scan_type == "Scan Report Small Cap":
                df = df[df['stock_last_numeric'] < 20]
            elif scan_type == "Scan Report Mid Cap":
                df = df[(df['stock_last_numeric'] >= 20) & (df['stock_last_numeric'] <= 100)]
            elif scan_type == "Scan Report Large Cap":
                df = df[df['stock_last_numeric'] > 100]
            elif scan_type == "Scan Report Targeted":
                tickers = [x.strip().upper() for x in tickers_input.split(',')]
                df = df[df['symbol'].str.upper().isin(tickers)]

            grouped = df.groupby('symbol').agg({'premiumvalue':'sum'}).reset_index()
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False).head(3)['symbol'].tolist()

            calls = df[df['call/put'].str.upper() == 'CALL']['premiumvalue'].sum()
            puts = df[df['call/put'].str.upper() == 'PUT']['premiumvalue'].sum()
            overall_bias = "Bullish" if calls >= puts else "Bearish"

            report = "OMEN Report - Smart Money Scan Report\n\n"
            report += "This report integrates Ben Sturgill's Smart Money Strategies, focusing on Stealth Sweeps, Block Trades, Repeater Alerts, and Institutional Order Flow. The trades included have been ranked using a proprietary scoring system that balances institutional premium size, Smart Money Alerts, same-day trade flow, multi-strike positioning, and multi-expiration setups.\n\n"
            report += "🚀 Top 3 Tickers with High-Probability Trades\n\n"

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]

                stock_price = ticker_data['stock_last_numeric'].dropna().mean()
                if pd.isna(stock_price) or stock_price == 0:
                    stock_price = df[df['symbol'] == ticker]['stock_last_numeric'].dropna().mean()

                if stock_price < 20:
                    mcap = "Small Cap"
                elif stock_price <= 100:
                    mcap = "Mid Cap"
                else:
                    mcap = "Large Cap"

                trade_type = "Sweep"
                sentiment = "Bullish" if ticker_data['trade_spread'].str.contains("ask", case=False, na=False).any() else "Bearish"
                stealth = "Above Ask" if ticker_data['trade_spread'].str.contains("above ask", case=False, na=False).any() else "At Bid"
                alerts = ", ".join(ticker_data['alerts'].dropna().unique()) if ticker_data['alerts'].dropna().any() else "None"

                report += f"## {ticker} - {mcap} (${stock_price:.2f})\n\n"
                report += f"Institutional Trade Type: {trade_type}\n"
                report += f"Overall Smart Money Sentiment: {sentiment}\n"
                report += f"Stealth Order Flow Indicators: {stealth}\n"
                report += f"Smart Money Alerts Triggered: {alerts}\n\n"

                report += "🔹 Top Trades Identified:\n\n"
                top_trades = ticker_data.head(3)
                for idx, row in top_trades.iterrows():
                    strike = row['strike']
                    c_or_p = row['call/put']
                    exp = row['expiration_date']
                    label = ["🏆", "🔥", "⚡"][idx % 3]
                    report += f"{label} {strike} {c_or_p} - {exp}\n"

                report += f"\n📌 Summary: Institutional traders are aggressively positioning in {ticker} across multiple strikes and expirations, signaling strong {sentiment.lower()} bias and accumulation/distribution.\n\n"

            report += "📈 Final Market Sentiment Verdict\n"
            report += f"🔵 Bullish Bias: {overall_bias}\n\n"
            report += f"Institutional sentiment based on Smart Money Flow remains {overall_bias.lower()}.\n"
            report += "Key tickers showing aggressive stealth accumulation/distribution.\n"
            report += "Traders should monitor these names for continued strength and potential follow-through.\n"

            st.text_area("📊 OMEN Smart Money Report", report, height=600)

            report = report.replace('’', "'")

            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.set_font("Arial", size=7)  # Smaller font to help wrapping

            wrapped_lines = []
            for line in report.split('\n'):
                wrapped_lines.extend(textwrap.wrap(line, width=90) or [" "])

            for line in wrapped_lines:
                pdf.multi_cell(0, 5, line)

            pdf_output = pdf.output(dest='S').encode('latin1')

            st.download_button(
                label="📥 Download OMENReport as PDF",
                data=pdf_output,
                file_name="OMENReport.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error reading file: {e}")

else:
    st.info("⬆️ Upload a CSV or Excel file to begin.")
