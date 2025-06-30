
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

        df.columns = df.columns.str.strip()
        st.success("✅ File uploaded and processed successfully.")
        st.subheader("Original Data Preview")
        st.dataframe(df.head())

        if st.button("⚙️ Run OMENReport"):
            st.subheader("📄 OMENReport Results")

            # Example Report Generation
            report_text = ""
            tickers = df["Ticker"].unique()
            for ticker in tickers:
                ticker_data = df[df["Ticker"] == ticker]
                total_premium = ticker_data["Premium"].sum()
                trade_count = len(ticker_data)

                report_text += f"---\nTicker: {ticker}\n"
                report_text += f"Total Premium: ${total_premium:,.2f}\n"
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
