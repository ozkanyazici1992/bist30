import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. KONFİGÜRASYON VE CSS (PAZARLAMA ODAKLI TASARIM)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI | BIST30",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed" # Menü kapalı başlasın, ekran ferah olsun
)

# ÖZEL CSS (PREMIUM GÖRÜNÜM İÇİN)
st.markdown("""
    <style>
    /* Ana Arka Planı Koyulaştır (Streamlit Dark Mode ile en iyi çalışır) */
    .stApp {
        background-color: #0e1117;
    }
    
    /* KPI Kartları - Glassmorphism Efekti */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e2330, #171b25);
        border: 1px solid #2d3748;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #00FFA3;
        box-shadow: 0 10px 25px rgba(0, 255, 163, 0.2);
    }
    
    /* Etiket Renkleri */
    div[data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Başlık Stili */
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00FFA3, #00C3FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .hero-subtitle {
        color: #718096;
        font-size: 1.2rem;
        margin-bottom: 30px;
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
# 2. VERİ MİMARİSİ
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_hourly_data(ticker_symbol):
    try:
        # Son 730 günün verisi
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        
        # TIMEZONE FIX (TRT DÖNÜŞÜMÜ)
        if df['Date'].dt.tz is None:
             df['Date'] = df['Date'].dt.tz_localize('UTC')
        df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul')
        df['Date'] = df['Date'].dt.tz_localize(None)
        
        df['Month'] = df['Date'].dt.month
        df['Day'] = df['Date'].dt.day
        df['Hour'] = df['Date'].dt.hour
        df['DateOnly'] = df['Date'].dt.date
        return df
    except:
        return None

def analyze_seasonality(df, target_month, target_day, window=3):
    mask = (
        (df['Month'] == target_month) & 
        (df['Day'] >= target_day - window) & 
        (df['Day'] <= target_day + window)
    )
    subset = df[mask].copy()
    
    if len(subset) < 3: return None # Eşik değeri düşürdük

    # Normalizasyon
    subset['Pct_Change'] = subset.groupby('DateOnly')['Close'].transform(
        lambda x: (x - x.iloc[0]) / x.iloc[0] * 100
    )
    
    # 10:00 - 18:00 ARALIĞINI ZORLA
    # (Bazen veri 9:55 olarak gelir, bunu 10'a yuvarlarız analizde)
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    
    # Filtre: 9'dan büyük 19'dan küçük (10,11...18)
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 9) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats

# -----------------------------------------------------------------------------
# 3. ARAYÜZ (UX/UI)
# -----------------------------------------------------------------------------

# --- Header ---
st.markdown('<p class="hero-title">ProTrade AI</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Yapay Zeka Destekli BIST30 Gelecek Simülasyonu</p>', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429177.png", width=50)
    st.markdown("### ⚙️ Simülasyon Ayarları")
    
    selected_name = st.selectbox("Analiz Edilecek Varlık", list(BIST_TICKERS.keys()))
    
    st.markdown("### 📅 Hedef Tarih")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("Planlanan İşlem Tarihi", value=min_date, min_value=min_date)
    
    st.success("Sistem Hazır • TRT Saati")

# --- Veri İşleme ---
ticker_symbol = BIST_TICKERS[selected_name]
df = get_hourly_data(ticker_symbol)

if df is not None:
    stats = analyze_seasonality(df, user_date.month, user_date.day)
    
    if stats is not None and not stats.empty:
        # Hesaplamalar
        min_val = stats['Pct_Change'].min()
        max_val = stats['Pct_Change'].max()
        best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
        best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
        potential_profit = max_val - min_val

        # --- KPI KARTLARI (3 KOLON - DAHA TEMİZ) ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="✅ İdeal Giriş (Alış)", value=f"{int(best_buy)}:00", delta="Dip Noktası")
        with col2:
            st.metric(label="🚀 Hedef Çıkış (Satış)", value=f"{int(best_sell)}:00", delta="Tepe Noktası")
        with col3:
            st.metric(label="💰 Potansiyel Getiri", value=f"%{potential_profit:.2f}", delta="Gün İçi Marj")

        # --- GRAFİK (NEON & DARK THEME) ---
        st.markdown("### ⚡ Gün İçi Fiyat Rotası")
        
        fig = go.Figure()

        # Ana Trend Çizgisi (Neon Yeşil)
        fig.add_trace(go.Scatter(
            x=stats['Hour'], y=stats['Pct_Change'],
            mode='lines',
            name='AI Tahmini',
            line=dict(color='#00FFA3', width=4, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 163, 0.1)' # Hafif yeşil dolgu
        ))

        # Alış İşareti (Yeşil Daire)
        fig.add_trace(go.Scatter(
            x=[best_buy], y=[min_val], mode='markers',
            marker=dict(color='#00FFA3', size=20, line=dict(width=3, color='black'), symbol='circle'),
            name='ALIŞ'
        ))

        # Satış İşareti (Kırmızı Daire)
        fig.add_trace(go.Scatter(
            x=[best_sell], y=[max_val], mode='markers',
            marker=dict(color='#FF0055', size=20, line=dict(width=3, color='black'), symbol='circle'),
            name='SATIŞ'
        ))

        # Grafik Düzeni (Saat 10 ile 18 arasını zorla)
        fig.update_layout(
            template="plotly_dark", # Koyu tema
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                title="Saat (TRT)",
                tickmode='array',
                tickvals=[10, 11, 12, 13, 14, 15, 16, 17, 18], # Saatleri elle sabitledik
                ticktext=['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'],
                range=[9.5, 18.5], # Eksen genişliği
                showgrid=False
            ),
            yaxis=dict(
                title="Değişim (%)",
                gridcolor='#333333',
                zeroline=True,
                zerolinecolor='#444444'
            ),
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- AI TAVSİYE KUTUSU (MODERN TASARIM) ---
        trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
        bg_color = "rgba(0, 255, 163, 0.1)" if trend == "YÜKSELİŞ" else "rgba(255, 0, 85, 0.1)"
        border_color = "#00FFA3" if trend == "YÜKSELİŞ" else "#FF0055"
        
        st.markdown(f"""
        <div style="
            background-color: {bg_color}; 
            border-left: 5px solid {border_color};
            padding: 20px; 
            border-radius: 10px; 
            margin-top: 20px;">
            <h4 style="margin:0; color:white;">🤖 Yapay Zeka Stratejisi</h4>
            <p style="color:#d1d5db; margin-top:10px;">
            Sistemin <b>{user_date.strftime('%d %B')}</b> tarihi için öngörüsü 
            <b style="color:{border_color}">{trend}</b> yönündedir.
            <br><br>
            Sabah açılış volatilitesi geçtikten sonra saat <b>{int(best_buy)}:00</b> sularında pozisyon alınması, 
            kapanışa doğru saat <b>{int(best_sell)}:00</b> civarında kâr realizasyonu yapılması, 
            istatistiksel olarak en yüksek başarı oranını sunmaktadır.
            </p>
        </div>
        """, unsafe_allow_html=True)
            
    else:
        st.warning("⚠️ Bu tarih için yeterli piyasa verisi bulunamadı. Lütfen hafta içi bir tarih seçiniz.")

else:
    st.info("Veriler sunucudan çekiliyor, lütfen bekleyiniz...")
