import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. KONFİGÜRASYON VE CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI | BIST30",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS (Aynı Tasarım)
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e2330, #171b25);
        border: 1px solid #2d3748;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] {color: #a0aec0 !important;}
    div[data-testid="stMetricValue"] {color: #ffffff !important;}
    .hero-title {
        font-size: 3rem; font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00FFA3, #00C3FF);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .hero-subtitle {color: #718096; font-size: 1.2rem; margin-bottom: 30px;}
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
# 2. OPTİMİZE EDİLMİŞ VERİ ÇEKME (PERFORMANS İYİLEŞTİRMESİ)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_optimized_data(ticker_symbol):
    """
    Veriyi bir kez çeker ve hafızada tutar.
    threads=True ile indirmeyi hızlandırır.
    """
    try:
        # threads=True parametresi indirmeyi hızlandırır
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False, threads=True)
        
        if df.empty: return None
        
        # MultiIndex Düzeltme (Hızlı Yöntem)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        
        # Sütun adı kontrolü ve düzeltme
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        
        # Tarih İşlemleri (Vectorized - Daha Hızlı)
        if df['Date'].dt.tz is None:
             df['Date'] = df['Date'].dt.tz_localize('UTC')
        df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul').dt.tz_localize(None)
        
        # Feature Engineering (Tek seferde atama)
        df['Month'] = df['Date'].dt.month
        df['Day'] = df['Date'].dt.day
        df['Hour'] = df['Date'].dt.hour
        df['DateOnly'] = df['Date'].dt.date
        
        return df
    except:
        return None

def analyze_seasonality(df, target_month, target_day, window=3):
    # Veri filtreleme işlemlerini hızlandıralım
    mask = (
        (df['Month'] == target_month) & 
        (df['Day'] >= target_day - window) & 
        (df['Day'] <= target_day + window)
    )
    subset = df[mask].copy()
    
    if len(subset) < 3: return None

    # Normalizasyon
    start_prices = subset.groupby('DateOnly')['Close'].transform('first')
    subset['Pct_Change'] = ((subset['Close'] - start_prices) / start_prices) * 100
    
    # Gruplama
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 9) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats

# -----------------------------------------------------------------------------
# 3. ARAYÜZ
# -----------------------------------------------------------------------------

st.markdown('<p class="hero-title">ProTrade AI</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Yapay Zeka Destekli BIST30 Gelecek Simülasyonu</p>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429177.png", width=50)
    st.markdown("### ⚙️ Ayarlar")
    selected_name = st.selectbox("Varlık Seçimi", list(BIST_TICKERS.keys()))
    
    st.markdown("### 📅 Tarih")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("İşlem Tarihi", value=min_date, min_value=min_date)

# Spinner'ı sadece veri yoksa göster
ticker_symbol = BIST_TICKERS[selected_name]

# Yükleniyor mesajını daha modern yapalım
with st.status("Veriler Analiz Ediliyor...", expanded=True) as status:
    st.write("Sunucuya bağlanılıyor...")
    df = get_optimized_data(ticker_symbol)
    st.write("Zaman serileri işleniyor...")
    
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
    else:
        status.update(label="Veri Hatası!", state="error")

if df is not None and stats is not None and not stats.empty:
    # Hesaplamalar
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # KPI KARTLARI
    col1, col2, col3 = st.columns(3)
    with col1: st.metric(label="✅ İdeal Giriş", value=f"{int(best_buy)}:00", delta="Dip")
    with col2: st.metric(label="🚀 Hedef Çıkış", value=f"{int(best_sell)}:00", delta="Tepe")
    with col3: st.metric(label="💰 Potansiyel Marj", value=f"%{potential_profit:.2f}", delta="Fark")

    # GRAFİK
    st.markdown("### ⚡ Gün İçi Fiyat Rotası")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines', name='Tahmin',
        line=dict(color='#00FFA3', width=4, shape='spline'),
        fill='tozeroy', fillcolor='rgba(0, 255, 163, 0.1)'
    ))
    
    # İşaretleyiciler
    fig.add_trace(go.Scatter(x=[best_buy], y=[min_val], mode='markers', marker=dict(color='#00FFA3', size=15), name='AL'))
    fig.add_trace(go.Scatter(x=[best_sell], y=[max_val], mode='markers', marker=dict(color='#FF0055', size=15), name='SAT'))

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickvals=[10,11,12,13,14,15,16,17,18], title="Saat (TRT)", showgrid=False),
        yaxis=dict(title="Değişim (%)", gridcolor='#333333'),
        margin=dict(l=10, r=10, t=10, b=10), showlegend=False, height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # TAVSİYE KUTUSU
    trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
    border = "#00FFA3" if trend == "YÜKSELİŞ" else "#FF0055"
    st.markdown(f"""
    <div style="border-left: 5px solid {border}; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 5px;">
        <h4 style="margin:0; color:white;">🤖 AI Öngörüsü: <span style="color:{border}">{trend}</span></h4>
        <p style="color:#ccc; margin-top:5px; font-size:0.9rem;">
        Sabah <b>{int(best_buy)}:00</b> sularında destek seviyesi, akşam üstü <b>{int(best_sell)}:00</b> civarında direnç testi bekleniyor.
        </p>
    </div>
    """, unsafe_allow_html=True)
elif df is None:
    st.error("Veri alınamadı. Lütfen internet bağlantınızı kontrol edin veya sayfayı yenileyin.")
else:
    st.warning("Bu tarih için yeterli veri yok.")
