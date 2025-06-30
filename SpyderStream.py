
# ✔️ OMEN Smart Money Scanner with Long Term Filter and AI Toggle

import streamlit as st
import pandas as pd
import openai
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import datetime

# Configure OpenAI
openai.api_key = "YOUR_OPENAI_API_KEY"

def generate_openai_summary(ticker, trade_type, sentiment, stealth, alerts, top_trades):
    try:
        trades_text = "; ".join(
            [f"{row['strike']} {row['call/put']} – {row['expiration_date']} "
             f"({row['trade_spread']}, ${row['premiumvalue']:,.0f} Premium)"
             for _, row in top_trades.iterrows()]
        )

        prompt = (
            f"You are an expert financial analyst. Write a concise institutional-grade summary "
            f"for the options activity on {ticker}. "
            f"The institutional trade type is {trade_type}. Overall smart money sentiment is {sentiment}. "
            f"Stealth indicators include {stealth}. Alerts triggered include {alerts}. "
            f"Top trades include: {trades_text}. "
            f"Explain what this suggests about institutional positioning or sentiment. Keep it to 2-3 sentences."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )

        summary = response['choices'][0]['message']['content'].strip()
        return summary

    except Exception as e:
        return f"(AI Summary unavailable due to error: {e})"

# Streamlit UI
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

ai_option = st.selectbox(
    "Select Summary Type:",
    ["Standard Summary (Non-AI)", "AI Summary (OpenAI GPT-3.5)"]
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

            grouped = df.groupby('symbol').agg({'premiumvalue': 'sum'}).reset_index()
            top_tickers = grouped.sort_values(by='premiumvalue', ascending=False).head(3)['symbol'].tolist()

            styles = getSampleStyleSheet()
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            Story = []

            for ticker in top_tickers:
                ticker_data = df[df['symbol'] == ticker]

                stock_price = ticker_data['stock_last'].dropna().iloc[0] if not ticker_data['stock_last'].dropna().empty else 0
                mcap = "Small Cap" if stock_price < 20 else "Mid Cap" if stock_price <= 100 else "Large Cap"

                trade_type = "Sweep" if ticker_data['flags'].str.contains("sweep", case=False, na=False).any() else "Block Trade"
                stealth = ", ".join(ticker_data['trade_spread'].dropna().unique()) or "None"
                alerts = ", ".join(ticker_data['alerts'].dropna().unique()) or "None"

                Story.append(Paragraph(f"<b>{ticker} - {mcap} (${stock_price:.2f})</b>", styles['Heading2']))
                Story.append(Spacer(1, 8))

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

                if ai_option == "AI Summary (OpenAI GPT-3.5)":
                    ai_summary = generate_openai_summary(
                        ticker, trade_type, "Bullish", stealth, alerts, filtered
                    )
                    summary_text = f"📌 AI Summary: {ai_summary}"
                else:
                    summary_text = (
                        f"📌 Summary: Institutional traders are aggressively positioning in {ticker} with "
                        f"significant {trade_type.lower()} trades, including stealth indicators such as "
                        f"{stealth} and alerts like {alerts}. This setup signals strong bullish bias."
                    )

                Story.append(Paragraph(summary_text, styles['BodyText']))
                Story.append(Spacer(1, 12))

            pdf.build(Story)

            st.download_button(
                label="📥 Download OMENReport as PDF",
                data=buffer.getvalue(),
                file_name="OMENReport.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
