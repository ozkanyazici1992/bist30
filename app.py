import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# -----------------------------------------------------------------------------
# 1. TASARIM: PROFESYONEL BORSA TEMASI (TRADINGVIEW NAVY)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS: Arka plan artık simsiyah değil, "Derin Lacivert" (Professional Navy)
st.markdown("""
    <style>
    /* Ana Arka Plan: TradingView tarzı koyu lacivert/gri */
    .stApp {
        background-color: #131722;
    }
    
    /* Sidebar (Yan Menü) Rengi: Biraz daha koyu ton */
    [data-testid="stSidebar"] {
        background-color: #0b0e11;
        border-right: 1px solid #2a2e39;
    }
    
    /* Metrik Kartları: Hafif transparan ve modern */
    div[data-testid="stMetric"] {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Yazı Renkleri */
    h1, h2, h3, p, span {
        color: #d1d4dc !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    }
    
    /* Metrik Değerleri Parlak Olsun */
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* Küçük Etiketler */
    div[data-testid="stMetricLabel"] {
        color: #787b86 !important;
    }
    </style>
""", unsafe_allow_html=True)

# BIST 30 Listesi
BIST_TICKERS = {
    "BIST 30 ENDEKSİ": "XU030.IS", "AKBNK": "AKBNK.IS", "ALARK": "ALARK.IS", 
    "ARCLK": "ARCLK.IS", "ASELS": "ASELS.IS", "ASTOR": "ASTOR.IS", 
    "BIMAS": "BIMAS.IS", "BRSAN": "BRSAN.IS", "CANTU": "CANTU.IS", 
    "EKGYO": "EKGYO.IS", "ENKAI": "ENKAI.IS", "EREGL": "EREGL.IS", 
    "FROTO": "FROTO.IS", "GARAN": "GARAN.IS", "GUBRF": "GUBRF.IS", 
    "HEKTS": "HEKTS.IS", "ISCTR": "ISCTR.IS", "KCHOL": "KCHOL.IS", 
    "KONTR": "KONTR.IS", "KOZAL": "KOZAL.IS", "KRDMD": "KRDMD.IS", 
    "ODAS": "ODAS.IS", "OYAKC": "OYAKC.IS", "PETKM": "PETKM.IS", 
    "PGSUS": "PGSUS.IS", "SAHOL": "SAHOL.IS", "SASA": "SASA.IS", 
    "SISE": "SISE.IS", "TCELL": "TCELL.IS", "THYAO": "THYAO.IS", 
    "TOASO": "TOASO.IS", "TUPRS": "TUPRS.IS", "YKBNK": "YKBNK.IS"
}

# -----------------------------------------------------------------------------
# 2. VERİ ÇEKME (RATE LIMIT KORUMALI)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_optimized_data(ticker_symbol):
    """
    Yahoo Finance 'Rate Limit' hatasını aşmak için Retry (Yeniden Deneme) mekanizması.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Threads=False yaptık ki sunucuyu bombalamasın, daha sakin çeksin
            df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False, threads=False)
            
            if df.empty:
                # Veri boşsa hata var demektir, bekleyip tekrar dene
                time.sleep(1)
                continue
                
            # --- VERİ İŞLEME ---
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.reset_index()
            date_col = 'Date' if 'Date' in df.columns else 'Datetime'
            df.rename(columns={date_col: 'Date'}, inplace=True)
            
            # Timezone Fix
            if df['Date'].dt.tz is None:
                 df['Date'] = df['Date'].dt.tz_localize('UTC')
            df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul').dt.tz_localize(None)
            
            df['Month'] = df['Date'].dt.month
            df['Day'] = df['Date'].dt.day
            df['Hour'] = df['Date'].dt.hour
            df['DateOnly'] = df['Date'].dt.date
            
            return df # Başarılı olursa döndür
            
        except Exception as e:
            # Hata alırsak (Rate Limit vb.) 2 saniye bekle ve tekrar dene
            time.sleep(2)
            if attempt == max_retries - 1:
                return None # Son denemede de olmazsa None dön
    return None

def analyze_seasonality(df, target_month, target_day, window=3):
    mask = (
        (df['Month'] == target_month) & 
        (df['Day'] >= target_day - window) & 
        (df['Day'] <= target_day + window)
    )
    subset = df[mask].copy()
    
    if len(subset) < 3: return None

    start_prices = subset.groupby('DateOnly')['Close'].transform('first')
    subset['Pct_Change'] = ((subset['Close'] - start_prices) / start_prices) * 100
    
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 9) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats

# -----------------------------------------------------------------------------
# 3. ARAYÜZ
# -----------------------------------------------------------------------------

with st.sidebar:
    st.title("ProTrade AI")
    st.markdown("---")
    selected_name = st.selectbox("Hisse Senedi", list(BIST_TICKERS.keys()))
    
    st.markdown("### 🗓️ Planlama")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("İşlem Tarihi", value=min_date, min_value=min_date)
    
    st.markdown("---")
    st.caption("Veriler Borsa İstanbul (TRT) saat dilimine ayarlıdır.")

# Main Header
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"<span style='color:#787b86'>Analiz Tarihi: {user_date.strftime('%d %B %Y')}</span>", unsafe_allow_html=True)

# Veri Yükleme ve Hata Yönetimi
ticker_symbol = BIST_TICKERS[selected_name]

# Status Widget
with st.status("Veriler Borsa İstanbul'dan çekiliyor...", expanded=True) as status:
    df = get_optimized_data(ticker_symbol)
    
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        if stats is not None and not stats.empty:
            status.update(label="Analiz Hazır", state="complete", expanded=False)
        else:
            status.update(label="Yetersiz Veri", state="error")
    else:
        # Rate Limit uyarısı
        status.update(label="Bağlantı Hatası (Rate Limit)", state="error")
        st.error("⚠️ Yahoo Finance sunucuları şu an çok yoğun. Lütfen 1 dakika bekleyip sayfayı yenileyin.")

if df is not None and stats is not None and not stats.empty:
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # KPI Kartları
    c1, c2, c3 = st.columns(3)
    c1.metric("📉 Güvenli Alış", f"{int(best_buy)}:00", "Dip Seviye")
    c2.metric("📈 Hedef Satış", f"{int(best_sell)}:00", "Zirve Seviye")
    c3.metric("💰 Beklenen Marj", f"%{potential_profit:.2f}", "Potansiyel")

    # Grafik Alanı
    st.markdown("### ⚡ Gün İçi Simülasyon")
    
    fig = go.Figure()

    # Çizgi Rengi: TradingView Mavisi (#2962FF)
    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines', name='Trend',
        line=dict(color='#2962FF', width=3),
        fill='tozeroy', fillcolor='rgba(41, 98, 255, 0.1)'
    ))

    # Alış (Yeşil)
    fig.add_trace(go.Scatter(
        x=[best_buy], y=[min_val], mode='markers',
        marker=dict(color='#00C853', size=16, line=dict(width=2, color='white')),
        name='AL'
    ))

    # Satış (Kırmızı)
    fig.add_trace(go.Scatter(
        x=[best_sell], y=[max_val], mode='markers',
        marker=dict(color='#D50000', size=16, line=dict(width=2, color='white')),
        name='SAT'
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Saat (09:00 - 18:00)",
            tickvals=[10, 11, 12, 13, 14, 15, 16, 17, 18],
            range=[9.5, 18.5],
            showgrid=False,
            color='#b2b5be'
        ),
        yaxis=dict(
            title="Değişim (%)",
            gridcolor='#2a2e39',
            zerolinecolor='#2a2e39',
            color='#b2b5be'
        ),
        showlegend=False,
        height=450,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Strateji Metni
    trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
    color = "#2962FF" if trend == "YÜKSELİŞ" else "#D50000"
    
    st.markdown(f"""
    <div style="background-color: #1e222d; border-left: 4px solid {color}; padding: 15px; border-radius: 8px; margin-top: 10px;">
        <h4 style="margin:0; color:#d1d4dc;">🤖 AI Analiz Özeti</h4>
        <p style="color:#9db2bf; margin-top:8px;">
        <b>{user_date.strftime('%d %B')}</b> tarihi için sistem <span style="color:{color}; font-weight:bold;">{trend}</span> sinyali üretmektedir.
        Sabah saat <b>{int(best_buy)}:00</b> sularında alım yapıp, <b>{int(best_sell)}:00</b> civarında pozisyonu kapatmak
        istatistiksel olarak en yüksek başarıyı sunar.
        </p>
    </div>
    """, unsafe_allow_html=True)
