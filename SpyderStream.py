
import streamlit as st
import pandas as pd
from fpdf import FPDF
import openai
import google.generativeai as genai
from datetime import datetime

# ============================================
# 🔑 API Keys
# ============================================
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# ============================================
# 🚀 Streamlit App
# ============================================
st.set_page_config(page_title="OMENReport - Spider Scanner", layout="centered")
st.title("🚀 OMENReport - Spider Options Scanner")

uploaded_file = st.file_uploader("📤 Upload Spider Scanner CSV or Excel", type=["csv", "xls", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Aggressively clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_')
            .str.replace('-', '_')
        )

        st.success("✅ File uploaded and processed successfully.")
        st.subheader("Original Data Preview")
        st.dataframe(df.head())

        st.write("✅ Columns after cleanup:", df.columns.tolist())

        # Handle ticker column flexibly
        if 'ticker' in df.columns:
            ticker_column = 'ticker'
        elif 'underlying' in df.columns:
            ticker_column = 'underlying'
        else:
            st.error("❌ No ticker or underlying column found in file.")
            st.stop()

        if st.button("⚙️ Run OMENReport"):
            st.subheader("📄 OMENReport Results")

            report_text = ""
            tickers = df[ticker_column].unique()
            for ticker in tickers:
                ticker_data = df[df[ticker_column] == ticker]

                ticker_premium = ticker_data['premium'].sum() if 'premium' in ticker_data.columns else 0
                trade_count = len(ticker_data)

                report_text += f"---\nTicker: {ticker}\n"
                report_text += f"Total Premium: ${ticker_premium:,.2f}\n"
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
