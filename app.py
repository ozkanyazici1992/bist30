import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# -----------------------------------------------------------------------------
# 1. TASARIM: KURUMSAL AYDINLIK TEMA (CORPORATE LIGHT)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS: Ferah, beyaz ve kurumsal görünüm
st.markdown("""
    <style>
    /* Ana Arka Plan: Çok açık gri (Göz yormayan beyazlık) */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Sidebar Rengi: Tam Beyaz */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Metrik Kartları: Beyaz ve hafif gölgeli (Apple Style) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); /* Çok hafif gölge */
    }
    
    /* Yazı Renkleri (Siyah/Gri) */
    h1, h2, h3, h4, p, span {
        color: #1f2937 !important; /* Koyu antrasit */
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Metrik Değerleri */
    div[data-testid="stMetricValue"] {
        color: #111827 !important; /* Simsiyah */
        font-weight: 700;
    }
    
    /* Etiket Renkleri */
    div[data-testid="stMetricLabel"] {
        color: #6b7280 !important; /* Orta gri */
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Hata almamak için threads=False
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
    st.info("Veriler BIST işlem saatlerine (09:00 - 18:10) göredir.")

# Ana Başlık
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"<span style='color:#6b7280; font-size:1.1rem;'>Hedef Analiz Tarihi: **{user_date.strftime('%d %B %Y')}**</span>", unsafe_allow_html=True)

# Veri İşlemleri
ticker_symbol = BIST_TICKERS[selected_name]

# Yükleme Göstergesi
with st.status("Veriler Borsa İstanbul sunucularından alınıyor...", expanded=True) as status:
    df = get_optimized_data(ticker_symbol)
    
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        if stats is not None and not stats.empty:
            status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
        else:
            status.update(label="Yetersiz Veri", state="error")
    else:
        status.update(label="Sunucu Hatası (Lütfen tekrar deneyin)", state="error")

if df is not None and stats is not None and not stats.empty:
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # KPI Kartları (Beyaz & Temiz)
    col1, col2, col3 = st.columns(3)
    col1.metric("📉 İdeal Alış", f"{int(best_buy)}:00", "Dip Seviye")
    col2.metric("📈 İdeal Satış", f"{int(best_sell)}:00", "Zirve Seviye")
    col3.metric("💰 Marj Potansiyeli", f"%{potential_profit:.2f}", "Fırsat")

    # Grafik Alanı
    st.markdown("### ⚡ Gün İçi Performans Simülasyonu")
    
    fig = go.Figure()

    # Çizgi Rengi: Kurumsal Lacivert/Mavi
    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines', name='Trend',
        line=dict(color='#0f4c81', width=3, shape='spline'),
        fill='tozeroy', fillcolor='rgba(15, 76, 129, 0.1)'
    ))

    # Alış (Yeşil)
    fig.add_trace(go.Scatter(
        x=[best_buy], y=[min_val], mode='markers',
        marker=dict(color='#10b981', size=15, line=dict(width=2, color='white')),
        name='AL'
    ))

    # Satış (Kırmızı)
    fig.add_trace(go.Scatter(
        x=[best_sell], y=[max_val], mode='markers',
        marker=dict(color='#ef4444', size=15, line=dict(width=2, color='white')),
        name='SAT'
    ))

    fig.update_layout(
        template="plotly_white", # BEYAZ TEMA
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Saat (09:00 - 18:00)",
            tickvals=[10, 11, 12, 13, 14, 15, 16, 17, 18],
            range=[9.5, 18.5],
            showgrid=False,
            linecolor='#e5e7eb'
        ),
        yaxis=dict(
            title="Tahmini Değişim (%)",
            gridcolor='#f3f4f6',
            zeroline=True,
            zerolinecolor='#d1d5db'
        ),
        showlegend=False,
        height=450,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Strateji Metni
    trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
    border_color = "#10b981" if trend == "YÜKSELİŞ" else "#ef4444" # Yeşil veya Kırmızı
    
    st.markdown(f"""
    <div style="
        background-color: #ffffff; 
        border-left: 5px solid {border_color};
        padding: 20px; 
        border-radius: 8px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-top: 20px;">
        <h4 style="margin:0; color:#111827;">🤖 Yapay Zeka Özeti</h4>
        <p style="color:#4b5563; margin-top:10px;">
        Seçilen tarih <b>({user_date.strftime('%d %B')})</b> için piyasa eğilimi <strong style="color:{border_color}">{trend}</strong> yönündedir.<br>
        En uygun strateji: Sabah <b>{int(best_buy)}:00</b> civarında pozisyon açıp, <b>{int(best_sell)}:00</b> sularında kârı realize etmektir.
        </p>
    </div>
    """, unsafe_allow_html=True)
