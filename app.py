import streamlit as st
import yfinance as yf
import pandas as pd
import json
import requests
import os

# ============================================
# CONFIGURATION
# ============================================
st.set_page_config(page_title="Nivesha", page_icon="logo.png", layout="wide")
WATCHLIST_FILE = "my_watchlist.json"
AV_KEY = "V8TXR4IBIMTJCFNB"
AV_URL = "https://www.alphavantage.co/query"
# ============================================
# WATCHLIST MANAGEMENT
# ============================================
def load_watchlist():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r") as f: 
                return json.load(f)
    except:
        pass # If file is broken, just start fresh
    return []

def save_watchlist(wl):
    try:
        with open(WATCHLIST_FILE, "w") as f: 
            json.dump(wl, f)
    except:
        pass # Ignores the error when running on the internet

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# ============================================
# BACKEND: ALL 13 RATIOS
# ============================================
def get_data_av(sym):
    try:
        inc_resp = requests.get(AV_URL, params={"function": "INCOME_STATEMENT", "symbol": sym, "apikey": AV_KEY}).json()
        if "Note" in inc_resp: return "RATE_LIMIT"
        inc = inc_resp.get("annualReports", [])
        bs = requests.get(AV_URL, params={"function": "BALANCE_SHEET", "symbol": sym, "apikey": AV_KEY}).json().get("annualReports", [])
        cf = requests.get(AV_URL, params={"function": "CASH_FLOW", "symbol": sym, "apikey": AV_KEY}).json().get("annualReports", [])
        info_av = requests.get(AV_URL, params={"function": "OVERVIEW", "symbol": sym, "apikey": AV_KEY}).json()
        quote = requests.get(AV_URL, params={"function": "GLOBAL_QUOTE", "symbol": sym, "apikey": AV_KEY}).json().get("Global Quote", {})
        if len(inc) < 2 or len(bs) < 2: return None
        col1, col2 = "Year1", "Year2"
        d_inc = {"Total Revenue": [float(inc[0].get("totalRevenue", 0) or 0)], "Cost Of Revenue": [float(inc[0].get("costofGoodsAndServicesSold", 0) or 0)], "Net Income": [float(inc[0].get("netIncome", 0) or 0)]}
        d_bs = {"Total Current Assets": [float(bs[0].get("totalCurrentAssets", 0) or 0)], "Total Current Liabilities": [float(bs[0].get("totalCurrentLiabilities", 0) or 0)], "Inventory": [float(bs[0].get("inventory", 0) or 0)], "Cash And Cash Equivalents": [float(bs[0].get("cashAndCashEquivalentsAtCarryingValue", 0) or 0)], "Short Term Debt": [float(bs[0].get("shortTermDebt", 0) or 0)], "Long Term Debt": [float(bs[0].get("longTermDebt", 0) or 0)], "Stockholders Equity": [float(bs[0].get("totalShareholderEquity", 0) or 0)], "Total Assets": [float(bs[0].get("totalAssets", 0) or 0)]}
        d_cf = {"Operating Cash Flow": [float(cf[0].get("operatingCashflow", 0) or 0)]}
        df_inc = pd.DataFrame(d_inc, index=[col1]).T
        df_bs = pd.DataFrame(d_bs, index=[col1]).T
        df_cf = pd.DataFrame(d_cf, index=[col1]).T
        df_bs[col2] = [float(bs[1].get("totalCurrentAssets", 0) or 0), float(bs[1].get("totalCurrentLiabilities", 0) or 0), float(bs[1].get("inventory", 0) or 0), 0, 0, 0, float(bs[1].get("totalShareholderEquity", 0) or 0), float(bs[1].get("totalAssets", 0) or 0)]
        df_inc[col2] = ["", "", ""]
        info = {"shortName": info_av.get("Name", sym), "sector": info_av.get("Sector", "Unknown"), "currentPrice": float(quote.get("05. price", 0)) if quote.get("05. price") else None, "sharesOutstanding": float(info_av.get("SharesOutstanding", 0)) if info_av.get("SharesOutstanding") else None, "marketCap": float(info_av.get("MarketCapitalization", 0)) if info_av.get("MarketCapitalization") else None}
        return {"inc": df_inc, "bs": df_bs, "cf": df_cf, "info": info}
    except Exception as e: 
        return str(e) # This will now show us the exact error message

@st.cache_data(ttl=3600)
def get_data(symbol):
    try:
        t = yf.Ticker(symbol)
        return {"inc": t.income_stmt, "bs": t.balance_sheet, "cf": t.cash_flow, "info": t.info}
    except:
        av_data = get_data_av(symbol)
        if av_data == "RATE_LIMIT":
            st.warning("🛑 Daily limit reached! You used your 5 free checks for today. They reset at midnight US Eastern Time.")
            st.stop()
        if isinstance(av_data, str): # If it's a string, it's an error message!
            st.error(f"Debug Error: {av_data}")
            st.stop()
        if not av_data:
            st.error("Could not find data for this stock.")
            st.stop()
        return av_data

def sget(df, idx, col):
    try:
        if idx in df.index and col in df.columns:
            v = df.loc[idx, col]
            # Fix Yahoo Finance glitch: force it to pick the first valid number if it sends messy data
            if isinstance(v, pd.Series):
                v = v.dropna().iloc[0]
            return float(v) if pd.notna(v) else None
    except: 
        pass
    return None

def calc_all_13_ratios(sym):
    d = get_data(sym)
    if len(d["inc"].columns) < 2: return None, d["info"]
    
    info = d["info"]
    col, pcol = d["inc"].columns[0], d["inc"].columns[1]
    
    # --- BALANCE SHEET ---
    tca = sget(d["bs"], "Total Current Assets", col) or sget(d["bs"], "Total current assets", col) or sget(d["bs"], "Current Assets", col)
    tcl = sget(d["bs"], "Total Current Liabilities", col) or sget(d["bs"], "Total current liabilities", col) or sget(d["bs"], "Current Liabilities", col)
    inv = sget(d["bs"], "Inventory", col) or sget(d["bs"], "Inventories", col) or 0
    cash = sget(d["bs"], "Cash And Cash Equivalents", col) or sget(d["bs"], "Cash", col) or sget(d["bs"], "Cash and cash equivalents", col)
    td = (sget(d["bs"], "Short Term Debt", col) or 0) + (sget(d["bs"], "Long Term Debt", col) or 0)
    te = sget(d["bs"], "Stockholders Equity", col) or sget(d["bs"], "Common Stock Equity", col) or sget(d["bs"], "Stockholders' Equity", col)
    ta = sget(d["bs"], "Total Assets", col) or sget(d["bs"], "Total assets", col)
    pta = sget(d["bs"], "Total Assets", pcol) or sget(d["bs"], "Total assets", pcol)
    
    # --- INCOME STATEMENT ---
    rev = sget(d["inc"], "Total Revenue", col) or sget(d["inc"], "Revenue", col)
    cogs = sget(d["inc"], "Cost Of Revenue", col) or sget(d["inc"], "Cost Of Goods Sold", col) or sget(d["inc"], "Cost of Revenue", col)
    ni = sget(d["inc"], "Net Income", col) or sget(d["inc"], "Net Income Common Stockholders", col) or sget(d["inc"], "Net income", col)
    
    # --- CASH FLOW ---
    ocf = sget(d["cf"], "Operating Cash Flow", col) or sget(d["cf"], "Cash Flow From Continuing Operating Activities", col)
    
    # --- AVERAGES ---
    p_inv = sget(d["bs"], "Inventory", pcol) or sget(d["bs"], "Inventories", pcol) or 0
    avg_inv = (inv + p_inv) / 2
    avg_ta = ((ta or 0) + (pta or 0)) / 2
    
    # --- MARKET DATA ---
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding")
    if not shares and price and info.get("marketCap"): shares = info["marketCap"] / price
    
    r = {}
    if tca and tcl and tcl != 0: r["Current Ratio"] = tca/tcl
    if tca and tcl and tcl != 0: r["Quick Ratio"] = (tca - inv)/tcl
    if cash and tcl and tcl != 0: r["Cash Ratio"] = cash/tcl
    if td and te and te != 0: r["Debt/Equity"] = td/te
    if cogs and avg_inv and avg_inv != 0: r["Inventory Turnover"] = cogs/avg_inv
    if "Inventory Turnover" in r and r["Inventory Turnover"] != 0: r["Days Inventory"] = 365/r["Inventory Turnover"]
    if rev and avg_ta and avg_ta != 0: r["Assets Turnover"] = rev/avg_ta
    if ni and te and te != 0: r["ROE"] = (ni/te)*100
    if ni and rev and rev != 0: r["Net Margin"] = (ni/rev)*100
    if price and ni and shares and (ni/shares) != 0: r["P/E Ratio"] = price/(ni/shares)
    if price and ocf and shares and (ocf/shares) != 0: r["P/CF Ratio"] = price/(ocf/shares)
    if price and rev and shares and (rev/shares) != 0: r["P/S Ratio"] = price/(rev/shares)
    if price and te and shares and (te/shares) != 0: r["P/BV Ratio"] = price/(te/shares)
    
    return r, info

def get_simple_verdicts(ratios):
    if not ratios: return {}
    v = {}
    
    safety_score = 0
    if ratios.get("Current Ratio", 0) >= 1.5: safety_score += 25
    elif ratios.get("Current Ratio", 0) >= 1: safety_score += 10
    if ratios.get("Quick Ratio", 0) >= 1: safety_score += 25
    elif ratios.get("Quick Ratio", 0) >= 0.5: safety_score += 10
    if ratios.get("Cash Ratio", 0) >= 0.5: safety_score += 25
    elif ratios.get("Cash Ratio", 0) >= 0.2: safety_score += 10
    if ratios.get("Debt/Equity", 100) <= 0.5: safety_score += 25
    elif ratios.get("Debt/Equity", 100) <= 1.5: safety_score += 10
    
    if safety_score >= 70: v["safety"] = ("🛡️", "Very Safe", "Strong financial fortress. Easily pays short-term bills and has low debt.")
    elif safety_score >= 40: v["safety"] = ("🟡", "Normal Risk", "Financial health is okay. Can pay bills, but keep an eye on debt levels.")
    else: v["safety"] = ("⚠️", "Risky", "Warning: Low cash or high debt. Might struggle if the economy turns bad.")

    profit_score = 0
    if ratios.get("ROE", 0) >= 15: profit_score += 35
    elif ratios.get("ROE", 0) >= 5: profit_score += 15
    if ratios.get("Net Margin", 0) >= 15: profit_score += 35
    elif ratios.get("Net Margin", 0) >= 5: profit_score += 15
    elif ratios.get("Net Margin", 0) >= 0: profit_score += 5
    if ratios.get("Assets Turnover", 0) >= 0.5: profit_score += 30
    elif ratios.get("Assets Turnover", 0) >= 0.25: profit_score += 15
    
    if profit_score >= 70: v["profit"] = ("💰", "Highly Profitable", "Excellent! Very efficient at turning sales into actual cash profit.")
    elif profit_score >= 40: v["profit"] = ("👍", "Making Money", "Solidly profitable, though not an absolute superstar yet.")
    else: v["profit"] = ("📉", "Struggling", "Having trouble making money. Might be growing fast on purpose, or just struggling.")

    value_score = 0
    pe, ps, pbv = ratios.get("P/E Ratio", 100), ratios.get("P/S Ratio", 100), ratios.get("P/BV Ratio", 100)
    pcf = ratios.get("P/CF Ratio", 100)
    
    if 0 < pe <= 15: value_score += 25
    elif 15 < pe <= 25: value_score += 15
    elif pe > 40: value_score -= 5
    if 0 < pcf <= 15: value_score += 25
    elif 15 < pcf <= 25: value_score += 15
    elif pcf > 40: value_score -= 5
    if ps <= 1.5: value_score += 25
    elif 1.5 < ps <= 3: value_score += 15
    elif ps > 7: value_score -= 5
    if pbv <= 1.5: value_score += 25
    elif 1.5 < pbv <= 3: value_score += 15
    elif pbv > 6: value_score -= 5

    if value_score >= 70: v["value"] = ("🎁", "Great Value", "Bargain! Stock price is low compared to profits and assets.")
    elif value_score >= 30: v["value"] = ("💲", "Fair Price", "Reasonable price. Not a steal, but not a rip-off either.")
    else: v["value"] = ("🚀", "Expensive", "Paying a premium. Investors expect massive growth. If it slows, price could drop.")

    v["total_score"] = max(0, min(100, int((safety_score + profit_score + value_score) / 3)))
    return v

# ============================================
# UI DISPLAY FUNCTION (NO HTML, 100% SAFE)
# ============================================
def display_stock_card(symbol):
    ratios, info = calc_all_13_ratios(symbol)
    if not ratios:
        st.error(f"Could not find data for {symbol}. Did you type the ticker correctly?")
        return
    
    verdicts = get_simple_verdicts(ratios)
    score = verdicts["total_score"]
    name = info.get("shortName", symbol)
    sector = info.get("sector", "Unknown Sector")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    
    # Header: Name and Price side-by-side
    col_name, col_price = st.columns([3, 1])
    with col_name:
        st.subheader(f"{name}")
        st.caption(f"Sector: {sector}")
    with col_price:
        if price:
            st.metric(label="Current Price", value=f"${price:.2f}")
        else:
            st.metric(label="Current Price", value="N/A")
    
    # The Big Score
    if score >= 75: st.metric(label="Investment Health Score", value=f"🟢 {score}/100")
    elif score >= 50: st.metric(label="Investment Health Score", value=f"🔵 {score}/100")
    elif score >= 25: st.metric(label="Investment Health Score", value=f"🟡 {score}/100")
    else: st.metric(label="Investment Health Score", value=f"🔴 {score}/100")
    
    st.markdown("---")
    
    # The 3 Simple Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        s_emoji, s_verdict, s_text = verdicts["safety"]
        if "Very" in s_verdict: st.success(f"**{s_emoji} SAFETY**\n\n### {s_verdict}\n{s_text}")
        elif "Normal" in s_verdict: st.warning(f"**{s_emoji} SAFETY**\n\n### {s_verdict}\n{s_text}")
        else: st.error(f"**{s_emoji} SAFETY**\n\n### {s_verdict}\n{s_text}")
        
    with col2:
        p_emoji, p_verdict, p_text = verdicts["profit"]
        if "Highly" in p_verdict: st.success(f"**{p_emoji} PROFITABILITY**\n\n### {p_verdict}\n{p_text}")
        elif "Making" in p_verdict: st.warning(f"**{p_emoji} PROFITABILITY**\n\n### {p_verdict}\n{p_text}")
        else: st.error(f"**{p_emoji} PROFITABILITY**\n\n### {p_verdict}\n{p_text}")
        
    with col3:
        v_emoji, v_verdict, v_text = verdicts["value"]
        if "Great" in v_verdict: st.success(f"**{v_emoji} PRICE VALUE**\n\n### {v_verdict}\n{v_text}")
        elif "Fair" in v_verdict: st.warning(f"**{v_emoji} PRICE VALUE**\n\n### {v_verdict}\n{v_text}")
        else: st.error(f"**{v_emoji} PRICE VALUE**\n\n### {v_verdict}\n{v_text}")

# ============================================
# MAIN APP UI
# ============================================
def main():
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image("logo.png", width=180)
    with col_title:
        st.markdown("<h1 style='color: #0a3d6b; margin-top: 25px;'>Nivesha</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #a0a0a0;'>Is it a good investment? Let's find out in plain English.</p>", unsafe_allow_html=True)
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("⭐ My Watchlist")
        with st.form("add_watchlist_form", clear_on_submit=True):
            new_ticker = st.text_input("Add Ticker", placeholder="e.g. TSLA")
            submitted = st.form_submit_button("➕ Add to List")
            if submitted and new_ticker:
                clean_ticker = new_ticker.strip().upper()
                if clean_ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(clean_ticker)
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Added {clean_ticker}!")
                else:
                    st.warning(f"{clean_ticker} is already in your list.")
        st.markdown("---")
        if not st.session_state.watchlist:
            st.info("Your list is empty.")
        else:
            for tick in st.session_state.watchlist:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"🔍 {tick}", key=f"wl_{tick}", use_container_width=True):
                        st.session_state.active_ticker = tick
                with col2:
                    if st.button("❌", key=f"del_{tick}"):
                        st.session_state.watchlist.remove(tick)
                        save_watchlist(st.session_state.watchlist)
                        st.rerun()
            if st.button("🗑️ Clear Entire List"):
                st.session_state.watchlist = []
                save_watchlist(st.session_state.watchlist)
                st.rerun()

    # Tabs
    tab_single, tab_vs = st.tabs(["🔍 Single Stock Check", "⚔️ Versus Mode"])
    
    if "active_ticker" not in st.session_state:
        st.session_state.active_ticker = "AAPL"

    with tab_single:
        symbol_input = st.text_input("Enter Stock Ticker", value=st.session_state.active_ticker, key="single_input")
        if st.button("Check Stock", type="primary", key="single_btn"):
            display_stock_card(symbol_input.strip().upper())
            
            with st.expander("📈 View Stock Price History (Past 2 Years)"):
                try:
                    hist = yf.Ticker(symbol_input.strip().upper()).history(period="2y")
                    st.line_chart(hist["Close"], height=300)
                except: 
                    st.warning("Could not load price history.")
            
            with st.expander("🤓 Geek Mode: View exact 13 financial ratios"):
                ratios, _ = calc_all_13_ratios(symbol_input.strip().upper())
                if ratios:
                    # Your personalized explanations and optimal ranges
                    guides = {
                        "Current Ratio": "Should be between 1.5 and 2.0, indicating financial health.",
                        "Quick Ratio": "Should be ≥ 1.0, ensuring short-term solvency.",
                        "Cash Ratio": "Should be between 0.5 and 1, indicating a safe level.",
                        "Debt/Equity": "Should be < 0.5, meaning it relies more on own capital than debt.",
                        "Inventory Turnover": "Should be > 2 and < 9, indicating good turnover.",
                        "Days Inventory": "The lower the better for liquidity and turnover.",
                        "Assets Turnover": "> 1.2x is strong for mature companies. < 0.8x reflects inefficiency.",
                        "ROE": "< 10% Low | 10-15% Acceptable | > 15% Excellent efficiency.",
                        "Net Margin": "< 5% Risky | 10% Healthy | > 20% Highly Profitable.",
                        "P/E Ratio": "0-10 Undervalued (or trap) | 10-20 Ideal | 20+ Overvalued/Growth.",
                        "P/CF Ratio": "< 10 Undervalued | 10-15 Healthy | > 20 Overvalued.",
                        "P/S Ratio": "< 1.0 Very attractive | < 2.0 Healthy.",
                        "P/BV Ratio": "< 1 Below book value | 1-3 Standard | > 5 High (tech/intangibles)."
                    }
                    
                    # Create the table
                    ratio_df = pd.DataFrame.from_dict(ratios, orient='index', columns=['Value'])
                    ratio_df.index.name = "Ratio"
                    ratio_df['Unit'] = ratio_df.index.map(lambda x: "%" if x in ["ROE", "Net Margin"] else "x")
                    ratio_df['What You Want To See'] = ratio_df.index.map(guides)
                    st.dataframe(ratio_df, use_container_width=True)

    with tab_vs:
        st.markdown("### Which stock is better? Let them fight. 🥊")
        col_a, col_b = st.columns(2)
        with col_a: fighter_a = st.text_input("Stock A", value="AAPL", key="vs_a")
        with col_b: fighter_b = st.text_input("Stock B", value="MSFT", key="vs_b")
            
        if st.button("⚔️ FIGHT!", type="primary", key="vs_btn"):
            c1, c2 = st.columns(2)
            
            with c1:
                score_a = None
                try:
                    ratios_a, _ = calc_all_13_ratios(fighter_a.strip().upper())
                    if ratios_a: score_a = get_simple_verdicts(ratios_a)["total_score"]
                except: pass
            
            with c2:
                score_b = None
                try:
                    ratios_b, _ = calc_all_13_ratios(fighter_b.strip().upper())
                    if ratios_b: score_b = get_simple_verdicts(ratios_b)["total_score"]
                except: pass
            
            if score_a is not None and score_b is not None:
                if score_a > score_b: winner_text = f"🏆 {fighter_a.strip().upper()} wins by {score_a - score_b} points!"
                elif score_b > score_a: winner_text = f"🏆 {fighter_b.strip().upper()} wins by {score_b - score_a} points!"
                else: winner_text = "🤝 It's a perfect tie!"
                st.success(winner_text)
                st.divider()
                
                col_left, col_right = st.columns(2)
                with col_left: display_stock_card(fighter_a.strip().upper())
                with col_right: display_stock_card(fighter_b.strip().upper())
            else:
                st.error("Could not analyze one or both stocks.")

if __name__ == "__main__":
    main()
