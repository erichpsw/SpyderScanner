
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import textwrap
import io

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

            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
            st.write("✅ Columns after cleanup:", list(df.columns))

            df['symbol'] = df['symbol'].astype(str).str.upper().str.strip()

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
            df['stock_last_numeric'] = pd.to_numeric(df['stock_last'], errors='coerce').fillna(0)

            if scan_type == "Scan Report Small Cap":
                df = df[df['stock_last_numeric'] < 20]
            elif scan_type == "Scan Report Mid Cap":
                df = df[(df['stock_last_numeric'] >= 20) & (df['stock_last_numeric'] <= 100)]
            elif scan_type == "Scan Report Large Cap":
                df = df[df['stock_last_numeric'] > 100]
            elif scan_type == "Scan Report Targeted":
                tickers = [x.strip().upper() for x in tickers_input.split(',')]
                df = df[df['symbol'].isin(tickers)]

            grouped = df.groupby('symbol').agg({'premiumvalue':'sum'}).reset_index()
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False)['symbol'].tolist()

            calls = df[df['call/put'].str.upper() == 'CALL']['premiumvalue'].sum()
            puts = df[df['call/put'].str.upper() == 'PUT']['premiumvalue'].sum()
            overall_bias = "Bullish" if calls >= puts else "Bearish"

            report_text = "OMEN Report - Smart Money Scan Report\n\n"
            report_text += "This report integrates Ben Sturgill's Smart Money Strategies, focusing on Stealth Sweeps, Block Trades, Repeater Alerts, and Institutional Order Flow.\n\n"

            styles = getSampleStyleSheet()
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
            Story = [Paragraph("<b>OMEN Report - Smart Money Scan Report</b>", styles['Title']), Spacer(1, 12)]
            Story.append(Paragraph("This report integrates Ben Sturgill's Smart Money Strategies, focusing on Stealth Sweeps, Block Trades, Repeater Alerts, and Institutional Order Flow.", styles['BodyText']))
            Story.append(Spacer(1, 12))

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]

                stock_price = ticker_data['stock_last_numeric'].dropna().mean()
                if pd.isna(stock_price) or stock_price == 0:
                    stock_price = df[df['symbol'] == ticker]['stock_last_numeric'].dropna().mean()

                mcap = "Small Cap" if stock_price < 20 else "Mid Cap" if stock_price <= 100 else "Large Cap"

                trade_type = "Sweep" if ticker_data['flags'].str.contains("sweep", case=False, na=False).any() else "Block Trade"
                stealth = ", ".join(ticker_data['trade_spread'].dropna().unique()) if not ticker_data['trade_spread'].dropna().empty else "None"
                alerts = ", ".join(ticker_data['alerts'].dropna().unique()) if not ticker_data['alerts'].dropna().empty else "None"

                header = f"{ticker} - {mcap} (${stock_price:.2f})"
                Story.append(Paragraph(f"<b>{header}</b>", styles['Heading2']))
                Story.append(Spacer(1, 8))

                data = [
                    ["Institutional Trade Type:", trade_type],
                    ["Overall Smart Money Sentiment:", overall_bias],
                    ["Stealth Order Flow Indicators:", stealth],
                    ["Smart Money Alerts Triggered:", alerts]
                ]
                table = Table(data, colWidths=[250, 500])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                Story.append(table)
                Story.append(Spacer(1, 12))

                Story.append(Paragraph("<b>🔹 Top Trades Identified:</b>", styles['Heading3']))
                report_text += f"## {header}\n\nInstitutional Trade Type: {trade_type}\nSmart Money Sentiment: {overall_bias}\nStealth Indicators: {stealth}\nAlerts: {alerts}\n\n🔹 Top Trades:\n"

                top_trades = ticker_data.head(3)
                for idx, row in top_trades.iterrows():
                    strike = row['strike']
                    c_or_p = row['call/put']
                    exp = row['expiration_date']
                    spread = row['trade_spread'] if pd.notna(row['trade_spread']) else "Unknown"
                    premium = parse_premium(row['premium'])
                    premium_str = "${:,.2f}M".format(premium/1e6) if premium >= 1e6 else "${:,.0f}K".format(premium/1e3)
                    label = ["🏆", "🔥", "⚡"][idx % 3]

                    trade_line = f"{label} {strike}{c_or_p} – {exp} ({spread}, {premium_str} Premium)"
                    Story.append(Paragraph(trade_line, styles['BodyText']))
                    report_text += trade_line + "\n"

                Story.append(Spacer(1, 12))
                summary = f"<b>📌 Summary:</b> Institutional traders are aggressively positioning in {ticker} with significant block trades or sweeps, signaling strong {overall_bias.lower()} bias."
                Story.append(Paragraph(summary, styles['BodyText']))
                Story.append(Spacer(1, 12))
                report_text += "\n📌 Summary: " + summary + "\n\n"

            Story.append(Paragraph("<b>📈 Final Market Sentiment Verdict:</b>", styles['BodyText']))
            Story.append(Paragraph(f"🔵 Bullish Bias: {overall_bias}", styles['BodyText']))
            Story.append(Spacer(1, 12))

            pdf.build(Story)
            st.text_area("📊 OMEN Smart Money Report", report_text, height=500)

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
