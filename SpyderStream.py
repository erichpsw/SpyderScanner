
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

st.set_page_config(page_title="OMEN Smart Money Scanner", layout="centered")
st.title("🚀 OMEN Smart Money Scanner")

uploaded_file = st.file_uploader("📤 Upload your SpyderScanner CSV or Excel file", type=["csv", "xls", "xlsx"])

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

            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
            df['symbol'] = df['symbol'].astype(str).str.upper().str.strip()

            df['stock_last'] = pd.to_numeric(
                df['stock_last']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip(),
                errors='coerce'
            )

            def parse_premium(val):
                try:
                    val = str(val).replace('$', '').replace(',', '').strip().lower()
                    if 'k' in val:
                        val = val.replace('k', 'e3')
                    if 'm' in val:
                        val = val.replace('m', 'e6')
                    return float(eval(val))
                except:
                    return 0

            df['premiumvalue'] = df['premium'].apply(parse_premium)

            if scan_type == "Scan Report Small Cap":
                df = df[df['stock_last'] < 20]
            elif scan_type == "Scan Report Mid Cap":
                df = df[(df['stock_last'] >= 20) & (df['stock_last'] <= 100)]
            elif scan_type == "Scan Report Large Cap":
                df = df[df['stock_last'] > 100]
            elif scan_type == "Scan Report Targeted":
                tickers = [x.strip().upper() for x in tickers_input.split(',')]
                df = df[df['symbol'].isin(tickers)]

            grouped = df.groupby('symbol').agg({'premiumvalue':'sum'}).reset_index()
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False).head(3)['symbol'].tolist()

            calls = df[df['call/put'].str.upper() == 'CALL']['premiumvalue'].sum()
            puts = df[df['call/put'].str.upper() == 'PUT']['premiumvalue'].sum()
            overall_bias = "Bullish" if calls >= puts else "Bearish"

            header_block = (
                "OMENReport - Smart Money Scan Report\n\n"
                "This report integrates Ben Sturgill’s Smart Money Strategies, focusing on Stealth Sweeps, Block Trades, Repeater Alerts, "
                "and Institutional Order Flow. The trades included have been ranked using a proprietary scoring system that balances "
                "institutional premium size, Smart Money Alerts, same-day trade flow, multi-strike positioning, and multi-expiration setups.\n\n"
                "⸻\n\n"
                "🚀 Top 3 Tickers with High-Probability Trades\n\n"
            )

            report_text = header_block

            styles = getSampleStyleSheet()
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
            Story = [Paragraph("<b>OMENReport - Smart Money Scan Report</b>", styles['Title']), Spacer(1, 12)]
            Story.append(Paragraph(
                "This report integrates Ben Sturgill’s Smart Money Strategies, focusing on Stealth Sweeps, Block Trades, Repeater Alerts, "
                "and Institutional Order Flow. The trades included have been ranked using a proprietary scoring system that balances "
                "institutional premium size, Smart Money Alerts, same-day trade flow, multi-strike positioning, and multi-expiration setups.",
                styles['BodyText']))
            Story.append(Spacer(1, 12))
            Story.append(Paragraph("<b>🚀 Top 3 Tickers with High-Probability Trades</b>", styles['Heading2']))
            Story.append(Spacer(1, 12))

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]

                try:
                    stock_price = ticker_data['stock_last'].dropna().iloc[0]
                except:
                    stock_price = 0

                mcap = "Small Cap" if stock_price < 20 else "Mid Cap" if stock_price <= 100 else "Large Cap"

                trade_type = "Sweep" if ticker_data['flags'].str.contains("sweep", case=False, na=False).any() else "Block Trade"
                stealth = ", ".join(ticker_data['trade_spread'].dropna().unique()) if not ticker_data['trade_spread'].dropna().empty else "None"
                alerts = ", ".join(ticker_data['alerts'].dropna().unique()) if not ticker_data['alerts'].dropna().empty else "None"

                header = f"{ticker} - {mcap} (${stock_price:.2f})"
                Story.append(Paragraph(f"<b>{header}</b>", styles['Heading2']))
                Story.append(Spacer(1, 8))

                report_text += f"## {header}\n"
                report_text += f"Institutional Trade Type: {trade_type}\nSmart Money Sentiment: {overall_bias}\nStealth Indicators: {stealth}\nAlerts: {alerts}\n\n🔹 Top Trades:\n"

                stealth_keywords = ["above ask", "askish", "at ask", "at bid", "hidden"]
                filtered = ticker_data.copy()
                filtered['stealth_flag'] = filtered['trade_spread'].str.lower().apply(lambda x: any(k in str(x) for k in stealth_keywords))
                filtered['alert_flag'] = filtered['alerts'].notnull()

                filtered = filtered.sort_values(by=['stealth_flag', 'alert_flag', 'premiumvalue'], ascending=[False, False, False])
                top_trades = filtered.head(3)

                for idx, row in top_trades.iterrows():
                    label = ["🏆", "🔥", "⚡"][idx % 3]

                    strike = row['strike']
                    c_or_p = row['call/put']
                    exp = row['expiration_date']
                    spread = row['trade_spread'] if pd.notna(row['trade_spread']) else "Unknown"
                    premium = parse_premium(row['premium'])
                    premium_str = "${:,.2f}M".format(premium/1e6) if premium >= 1e6 else "${:,.0f}K".format(premium/1e3)

                    trade_line = f"{label} {strike} {c_or_p} – {exp} ({spread}, {premium_str} Premium)"
                    Story.append(Paragraph(trade_line, styles['BodyText']))
                    report_text += trade_line + "\n"

                Story.append(Spacer(1, 12))
                summary_text = f"📌 Summary: Institutional traders are aggressively positioning in {ticker} with significant block trades or sweeps, signaling strong {overall_bias.lower()} bias."
                Story.append(Paragraph(summary_text, styles['BodyText']))
                Story.append(Spacer(1, 12))
                report_text += "\n" + summary_text + "\n\n"

            Story.append(Paragraph("<b>📈 Final Market Sentiment Verdict:</b>", styles['BodyText']))
            Story.append(Paragraph(f"🔵 Bullish Bias: {overall_bias}", styles['BodyText']))
            Story.append(Spacer(1, 12))

            pdf.build(Story)
            st.text_area("📊 OMEN Smart Money Report", report_text, height=600)

            st.download_button(
                label="📥 Download OMENReport as PDF",
                data=buffer.getvalue(),
                file_name="OMENReport.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error reading file: {e}")

else:
    st.info("⬆️ Upload a CSV or Excel file to begin.")
