import streamlit as st
import pandas as pd
import datetime
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io


st.set_page_config(page_title="OMEN Smart Money Scanner", layout="centered")
st.title("🚀 OMEN Smart Money Scanner")


uploaded_file = st.file_uploader("📤 Upload your SpyderScanner CSV or Excel file", type=["csv", "xls", "xlsx"])

scan_type = st.selectbox(
    "📊 Select Your Scan Type:",
    [
        "Scan Report - Full Market",
        "Scan Report Small Cap",
        "Scan Report Mid Cap",
        "Scan Report Large Cap",
        "Scan Report Long Term",
        "Scan Report Targeted"
    ]
)


if uploaded_file is not None:
    if st.button("⚙️ Run OMEN Smart Money Scan"):
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
            df['symbol'] = df['symbol'].astype(str).str.upper().str.strip()

            df['stock_last'] = pd.to_numeric(
                df['stock_last'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
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

            today = datetime.datetime.today()

            if scan_type == "Scan Report Small Cap":
                df = df[df['stock_last'] < 20]
            elif scan_type == "Scan Report Mid Cap":
                df = df[(df['stock_last'] >= 20) & (df['stock_last'] <= 100)]
            elif scan_type == "Scan Report Large Cap":
                df = df[df['stock_last'] > 100]
            elif scan_type == "Scan Report Long Term":
                df['expiration_date_parsed'] = pd.to_datetime(df['expiration_date'], errors='coerce')
                df = df[df['expiration_date_parsed'] >= today + pd.Timedelta(days=60)]
            elif scan_type == "Scan Report Targeted":
                tickers = st.text_input("Enter tickers separated by commas (e.g., NVDA, TSLA, AAPL):")
                if tickers:
                    tickers_list = [ticker.strip().upper() for ticker in tickers.split(",")]
                    df = df[df['symbol'].isin(tickers_list)]

            grouped = df.groupby('symbol').agg({'premiumvalue': 'sum'}).reset_index()

            top_n = 5 if scan_type == "Scan Report Long Term" else 3
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False).head(top_n)['symbol'].tolist()

            styles = getSampleStyleSheet()
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            Story = []

            # Header block
            header_block = f"OMENReport - Smart Money Scan Report\nFilter: {scan_type}\n"
            Story.append(Paragraph("<b>OMENReport - Smart Money Scan Report</b>", styles['Title']))
            Story.append(Paragraph(f"<b>Filter: {scan_type}</b>", styles['Heading2']))
            Story.append(Spacer(1, 12))

            report_text = header_block + "\n"

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]

                stock_price = ticker_data['stock_last'].dropna().iloc[0] if not ticker_data['stock_last'].dropna().empty else 0
                mcap = "Small Cap" if stock_price < 20 else "Mid Cap" if stock_price <= 100 else "Large Cap"

                trade_type = "Sweep" if ticker_data['flags'].str.contains("sweep", case=False, na=False).any() else "Block Trade"

                stealth = ", ".join(sorted(set(ticker_data['trade_spread'].dropna()))) or "None"
                alerts = ", ".join(sorted(set(ticker_data['alerts'].dropna()))) or "None"

                Story.append(Paragraph(f"<b>{ticker} - {mcap} (${stock_price:.2f})</b>", styles['Heading2']))
                Story.append(Spacer(1, 8))

                Story.append(Paragraph(f"Institutional Trade Type: {trade_type}", styles['BodyText']))
                Story.append(Paragraph(f"Stealth Order Flow Indicators: {stealth}", styles['BodyText']))
                Story.append(Paragraph(f"Smart Money Alerts Triggered: {alerts}", styles['BodyText']))
                Story.append(Spacer(1, 8))

                report_text += f"\n## {ticker} - {mcap} (${stock_price:.2f})\n"
                report_text += f"Institutional Trade Type: {trade_type}\nStealth Order Flow Indicators: {stealth}\nSmart Money Alerts Triggered: {alerts}\n\n"

                filtered = ticker_data.sort_values(by=['premiumvalue'], ascending=False).head(3)

                for idx, row in filtered.iterrows():
                    label = ["🏆", "🔥", "⚡"][idx % 3]
                    strike = row['strike']
                    c_or_p = row['call/put']
                    exp = row['expiration_date']
                    spread = row['trade_spread'] if pd.notna(row['trade_spread']) else "Unknown"
                    premium = parse_premium(row['premium'])
                    premium_str = "${:,.2f}M".format(premium / 1e6) if premium >= 1e6 else "${:,.0f}K".format(premium / 1e3)

                    trade_line = f"{label} {strike} {c_or_p} – {exp} ({spread}, {premium_str} Premium)"
                    Story.append(Paragraph(trade_line, styles['BodyText']))
                    report_text += trade_line + "\n"

                summary_text = (
                    f"📌 Summary: Institutional traders are aggressively positioning in {ticker} with "
                    f"significant {trade_type.lower()} trades, including stealth indicators such as "
                    f"{stealth} and alerts like {alerts}. This setup signals strong bullish bias."
                )

                Story.append(Paragraph(summary_text, styles['BodyText']))
                Story.append(Spacer(1, 12))
                report_text += "\n" + summary_text + "\n\n"

            pdf.build(Story)

            st.text_area("📊 OMEN Smart Money Report", report_text, height=600)

            st.download_button(
                label="📥 Download OMENReport as PDF",
                data=buffer.getvalue(),
                file_name="OMENReport.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
