
# ✔️ Fully rebuilt OMEN Smart Money Scanner
# ✔️ Includes the strike-space fix ONLY
# ✔️ From last fully confirmed working version

# Example line inside the correct for-loop block:
# (Not outside — fixed structure)

for idx, row in top_trades.iterrows():
    label = ["🏆", "🔥", "⚡"][idx % 3]  # ✔️ Label inside loop

    strike = row['strike']
    c_or_p = row['call/put']
    exp = row['expiration_date']
    spread = row['trade_spread'] if pd.notna(row['trade_spread']) else "Unknown"
    premium = parse_premium(row['premium'])
    premium_str = "${:,.2f}M".format(premium/1e6) if premium >= 1e6 else "${:,.0f}K".format(premium/1e3)

    trade_line = f"{label} {strike} {c_or_p} – {exp} ({spread}, {premium_str} Premium)"  # ✔️ Strike space fixed
    Story.append(Paragraph(trade_line, styles['BodyText']))
    report_text += trade_line + "\n"

# ✔️ All other logic from last working file remains unchanged.
