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

# ✅ Targeted Scan Input Box
tickers = None
if scan_type == "Scan Report Targeted":
    tickers = st.text_input("Enter tickers separated by commas (e.g., NVDA, TSLA, AAPL):")
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

            # ✅ Sweep Priority + Block/Multi with Stealth and Premium Filter
            sweep_stealth = df[
                (df['flags'].str.contains('sweep', case=False, na=False)) &
                (df['trade_spread'].isin(['Above Ask', 'Askish', 'At Ask']))
            ]

            block_multi_stealth = df[
                (df['flags'].str.contains('block|multi', case=False, na=False)) &
                (df['premiumvalue'] >= 1_000_000) &
                (df['trade_spread'].isin(['Above Ask', 'Askish', 'At Ask']))
            ]

            df = pd.concat([sweep_stealth, block_multi_stealth]).drop_duplicates()

            # ✅ OI Filter — Opening Sweep Flag
            df['OpeningSweepFlag'] = df.apply(
                lambda row: row['trade_size'] > row['open_interest']
                if pd.notnull(row['trade_size']) and pd.notnull(row['open_interest']) else False,
                axis=1
            )
            # ✅ Stealth Prioritization
            stealth_weight = {'Above Ask': 1, 'Askish': 2, 'At Bid': 3, 'Bidish': 4}
            df['stealth_rank'] = df['trade_spread'].map(stealth_weight).fillna(99)
            df['priority_score'] = (df['stealth_rank'] * 1_000_000) + df['premiumvalue']
            df = df.sort_values(by='priority_score', ascending=False)

            stealth_groups = (
                df.groupby(['symbol', 'strike', 'expiration_date', 'call/put', 'trade_spread'])
                .agg({'premiumvalue': 'sum'})
                .reset_index()
            )
            stealth_groups['stealth_rank'] = stealth_groups['trade_spread'].map(stealth_weight).fillna(99)
            stealth_groups = stealth_groups.sort_values(
                by=['symbol', 'stealth_rank', 'premiumvalue'],
                ascending=[True, True, False]
            )

            filtered_stealth = (
                stealth_groups.groupby(['symbol'])
                .first()
                .reset_index()
            )
            stealth_dict = filtered_stealth.groupby('symbol')['trade_spread'].apply(lambda x: ', '.join(x)).to_dict()

            # ✅ Smart Money Alerts
            df['DonkeyKong'] = df['premiumvalue'] >= 1_000_000
            repeater_group = df.groupby(['symbol', 'strike', 'expiration_date', 'call/put']).size().reset_index(name='count')
            repeater_hits = repeater_group[repeater_group['count'] >= 2]
            df['RepeaterFlag'] = df.apply(
                lambda row: ((repeater_hits['symbol'] == row['symbol']) &
                             (repeater_hits['strike'] == row['strike']) &
                             (repeater_hits['expiration_date'] == row['expiration_date']) &
                             (repeater_hits['call/put'] == row['call/put'])).any(),
                axis=1
            )
            df['AllTheThings'] = (
                df['DonkeyKong'] &
                (df['trade_spread'].isin(['Above Ask', 'Askish'])) &
                (df['RepeaterFlag'])
            )

            # ✅ Cap Filters
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
                if tickers:
                    tickers_list = [ticker.strip().upper() for ticker in tickers.split(",")]
                    df = df[df['symbol'].isin(tickers_list)]
                else:
                    st.warning("⚠️ Please enter at least one ticker for Targeted Scan.")
                    st.stop()
            grouped = df.groupby('symbol').agg({'premiumvalue': 'sum'}).reset_index()
            top_n = 5 if scan_type == "Scan Report Long Term" else 3
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False).head(top_n)['symbol'].tolist()

            styles = getSampleStyleSheet()
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            Story = []

            Story.append(Paragraph("<b>OMENReport - Smart Money Scan Report</b>", styles['Title']))
            Story.append(Paragraph(f"<b>Filter: {scan_type}</b>", styles['Heading2']))
            Story.append(Spacer(1, 12))

            report_text = f"OMENReport - Smart Money Scan Report\nFilter: {scan_type}\n\n"

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]
                stock_price = ticker_data['stock_last'].dropna().iloc[0] if not ticker_data['stock_last'].dropna().empty else 0
                mcap = "Small Cap" if stock_price < 20 else "Mid Cap" if stock_price <= 100 else "Large Cap"
                trade_type = "Sweep" if ticker_data['flags'].str.contains("sweep", case=False, na=False).any() else "Block Trade"
                stealth = stealth_dict.get(ticker, 'None')
                opening_sweep = "✅" if ticker_data['OpeningSweepFlag'].any() else "❌"

                Story.append(Paragraph(f"<b>{ticker} - {mcap} (${stock_price:.2f})</b>", styles['Heading2']))
                Story.append(Spacer(1, 8))
                Story.append(Paragraph(f"Institutional Trade Type: {trade_type}", styles['BodyText']))
                Story.append(Paragraph(f"Opening Sweep: {opening_sweep}", styles['BodyText']))
                Story.append(Paragraph(f"Stealth Indicators: {stealth}", styles['BodyText']))

                call_count = ticker_data[ticker_data['call/put'].str.lower() == 'call'].shape[0]
                put_count = ticker_data[ticker_data['call/put'].str.lower() == 'put'].shape[0]
                sentiment = "Bullish" if (call_count * 1.10) > put_count else "Bearish" if (put_count * 1.10) > call_count else "Neutral"
                Story.append(Paragraph(f"Overall Smart Money Sentiment: {sentiment}", styles['BodyText']))

                alerts = 'DonkeyKong' if ticker_data['DonkeyKong'].any() else \
                         'All the Things' if ticker_data['AllTheThings'].any() else \
                         'Repeater' if ticker_data['RepeaterFlag'].any() else 'None'
                Story.append(Paragraph(f"Smart Money Alerts Triggered: {alerts}", styles['BodyText']))
                Story.append(Spacer(1, 8))

                report_text += f"## {ticker} - {mcap} (${stock_price:.2f})\n"
                report_text += f"Institutional Trade Type: {trade_type}\n"
                report_text += f"Opening Sweep: {opening_sweep}\n"
                report_text += f"Stealth Indicators: {stealth}\n"
                report_text += f"Overall Smart Money Sentiment: {sentiment}\n"
                report_text += f"Smart Money Alerts Triggered: {alerts}\n\n"

                filtered = ticker_data.sort_values(by=['priority_score'], ascending=False).head(3)
                for idx, row in filtered.iterrows():
                    label = ["🏆", "🔥", "⚡"][idx % 3]
                    strike = row['strike']
                    c_or_p = row['call/put']
                    exp = row['expiration_date']
                    spread = row['trade_spread'] if pd.notna(row['trade_spread']) else "Unknown"
                    premium = parse_premium(row['premium'])
                    premium_str = "${:,.2f}M".format(premium / 1e6) if premium >= 1e6 else "${:,.0f}K".format(premium / 1e3)
                    opening_flag = " [Opening Sweep]" if row['OpeningSweepFlag'] else ""
                    trade_line = f"{label} {strike} {c_or_p} – {exp} ({spread}, {premium_str} Premium){opening_flag}"
                    Story.append(Paragraph(trade_line, styles['BodyText']))
                    report_text += trade_line + "\n"

                summary_text = (
                    f"📌 Summary: Institutional traders are aggressively positioning in {ticker} with "
                    f"significant {trade_type.lower()} trades. This setup signals strong {sentiment.lower()} bias."
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
