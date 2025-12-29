import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# -----------------------------------------------------------------------------
# 1. TASARIM: SICAK TURUNCU TEMA (WARM AMBER)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS: Turuncu/Krem Tonları
st.markdown("""
    <style>
    /* Ana Arka Plan: Yumuşak Krem/Turuncu (Göz yormaz) */
    .stApp {
        background-color: #fff3e0;
    }
    
    /* Sidebar Rengi: Beyaz (Temiz görünüm için) */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #ffcc80;
    }
    
    /* Metrik Kartları: Beyaz ve Hafif Turuncu Gölgeli */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #ffe0b2;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(255, 167, 38, 0.1);
    }
    
    /* Başlık Renkleri: Koyu Turuncu/Kahve */
    h1, h2, h3, h4 {
        color: #e65100 !important; /* Koyu Turuncu */
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Metrik Değerleri */
    div[data-testid="stMetricValue"] {
        color: #ef6c00 !important;
        font-weight: 800;
    }
    
    /* Etiket Renkleri */
    div[data-testid="stMetricLabel"] {
        color: #fb8c00 !important;
    }
    
    /* Buton ve Seçim Kutuları Vurgusu */
    .stSelectbox, .stDateInput {
        color: #e65100;
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
# 2. VERİ ÇEKME (AYNI GÜVENLİ YAPI)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_optimized_data(ticker_symbol):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False, threads=False)
            if df.empty:
                time.sleep(1)
                continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.reset_index()
            date_col = 'Date' if 'Date' in df.columns else 'Datetime'
            df.rename(columns={date_col: 'Date'}, inplace=True)
            
            if df['Date'].dt.tz is None:
                 df['Date'] = df['Date'].dt.tz_localize('UTC')
            df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul').dt.tz_localize(None)
            
            df['Month'] = df['Date'].dt.month
            df['Day'] = df['Date'].dt.day
            df['Hour'] = df['Date'].dt.hour
            df['DateOnly'] = df['Date'].dt.date
            
            return df
        except Exception:
            time.sleep(2)
            if attempt == max_retries - 1:
                return None
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
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429177.png", width=50)
    st.markdown("## ProTrade AI")
    st.markdown("---")
    
    selected_name = st.selectbox("Hisse / Endeks", list(BIST_TICKERS.keys()))
    
    st.markdown("### 📅 Planlama")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("İşlem Tarihi", value=min_date, min_value=min_date)
    
    st.markdown("---")
    st.warning("Piyasalar 09:00 - 18:10 arası açıktır.")

# Ana Başlık
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"<span style='color:#ef6c00; font-weight:500'>Analiz Hedefi: {user_date.strftime('%d %B %Y')}</span>", unsafe_allow_html=True)

# Veri İşleme
ticker_symbol = BIST_TICKERS[selected_name]

# Yükleme Barı (Turuncu)
with st.status("Veriler işleniyor...", expanded=True) as status:
    df = get_optimized_data(ticker_symbol)
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        if stats is not None and not stats.empty:
            status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
        else:
            status.update(label="Yetersiz Veri", state="error")
    else:
        status.update(label="Hata Oluştu", state="error")

if df is not None and stats is not None and not stats.empty:
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # KPI Kartları
    col1, col2, col3 = st.columns(3)
    col1.metric("📉 İdeal Alış", f"{int(best_buy)}:00", "Dip Noktası")
    col2.metric("📈 İdeal Satış", f"{int(best_sell)}:00", "Zirve Noktası")
    col3.metric("💰 Fırsat Marjı", f"%{potential_profit:.2f}", "Potansiyel")

    # Grafik
    st.markdown("### ⚡ Gün İçi Trend Simülasyonu")
    
    fig = go.Figure()

    # Trend Çizgisi (Canlı Turuncu/Kırmızı)
    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines', name='Trend',
        line=dict(color='#ff6d00', width=4, shape='spline'), # Canlı Turuncu
        fill='tozeroy', fillcolor='rgba(255, 109, 0, 0.1)'
    ))

    # Alış (Yeşil - Kontrast için)
    fig.add_trace(go.Scatter(
        x=[best_buy], y=[min_val], mode='markers',
        marker=dict(color='#2e7d32', size=16, line=dict(width=2, color='white')),
        name='AL'
    ))

    # Satış (Kırmızı - Kontrast için)
    fig.add_trace(go.Scatter(
        x=[best_sell], y=[max_val], mode='markers',
        marker=dict(color='#d32f2f', size=16, line=dict(width=2, color='white')),
        name='SAT'
    ))

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Saat (09:00 - 18:00)",
            tickvals=[10, 11, 12, 13, 14, 15, 16, 17, 18],
            range=[9.5, 18.5],
            showgrid=False,
            linecolor='#ffcc80' # Turuncu Eksen Çizgisi
        ),
        yaxis=dict(
            title="Tahmini Değişim (%)",
            gridcolor='#ffe0b2', # Hafif turuncu ızgara
            zeroline=True,
            zerolinecolor='#ffb74d'
        ),
        showlegend=False,
        height=450
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Strateji Metni
    trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
    border_color = "#2e7d32" if trend == "YÜKSELİŞ" else "#d32f2f"
    
    st.markdown(f"""
    <div style="
        background-color: #ffffff; 
        border-left: 5px solid {border_color};
        padding: 20px; 
        border-radius: 10px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-top: 20px;">
        <h4 style="margin:0; color:#e65100;">🔥 Strateji Özeti</h4>
        <p style="color:#5d4037; margin-top:10px;">
        <b>{user_date.strftime('%d %B')}</b> tarihi için yapay zeka öngörüsü <strong style="color:{border_color}">{trend}</strong> yönündedir.<br>
        Gün içi trade fırsatı: <b>{int(best_buy)}:00</b> sularında alış, <b>{int(best_sell)}:00</b> civarında satış önerilmektedir.
        </p>
    </div>
    """, unsafe_allow_html=True)
