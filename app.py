import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CSS & SAYFA YAPILANDIRMASI (PREMIUM DARK TEMA)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS: Arka planı, kartları ve metinleri özelleştiriyoruz
st.markdown("""
    <style>
    /* Ana Arka Plan: Koyu Lacivert/Gri Karışımı (Göz yormaz, Premium durur) */
    .stApp {
        background-color: #1a1e29;
    }
    
    /* Sidebar Rengi */
    [data-testid="stSidebar"] {
        background-color: #13161f;
        border-right: 1px solid #2b303b;
    }
    
    /* Metrik Kartları (Glassmorphism) */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #232836, #1e2230);
        border: 1px solid #363c4e;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Metrik Değerleri Rengi */
    div[data-testid="stMetricValue"] {
        color: #e0e6ed !important;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Metrik Etiketleri */
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
    
    /* Başlıklar */
    h1, h2, h3 {
        color: #f1f5f9 !important;
        font-family: 'Segoe UI', sans-serif;
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
# 2. VERİ MİMARİSİ (HIZLI & TR SAATİ UYUMLU)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_optimized_data(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False, threads=True)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        
        # TIMEZONE FIX (Türkiye Saati Dönüşümü)
        if df['Date'].dt.tz is None:
             df['Date'] = df['Date'].dt.tz_localize('UTC')
        df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul').dt.tz_localize(None)
        
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
    
    if len(subset) < 3: return None

    # Normalizasyon (% Getiri Hesabı)
    start_prices = subset.groupby('DateOnly')['Close'].transform('first')
    subset['Pct_Change'] = ((subset['Close'] - start_prices) / start_prices) * 100
    
    # SAAT FİLTRESİ (09:00 - 18:00 Arası Veriler)
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 9) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats

# -----------------------------------------------------------------------------
# 3. ARAYÜZ ve DASHBOARD
# -----------------------------------------------------------------------------

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 📊 ProTrade AI")
    st.markdown("---")
    
    selected_name = st.selectbox("Hisse / Endeks", list(BIST_TICKERS.keys()))
    
    st.markdown("### 🗓️ Gelecek Planlayıcı")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("İşlem Tarihi", value=min_date, min_value=min_date)
    
    st.markdown("---")
    st.caption("Veriler Borsa İstanbul (TRT) saat dilimine göre analiz edilmektedir.")

# --- Main Page ---
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"<span style='color:#94a3b8'>Analiz Tarihi: {user_date.strftime('%d %B %Y')}</span>", unsafe_allow_html=True)

# Veri Yükleme
ticker_symbol = BIST_TICKERS[selected_name]

# Loading Animasyonu
with st.status("Veriler işleniyor...", expanded=True) as status:
    df = get_optimized_data(ticker_symbol)
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        if stats is not None and not stats.empty:
            status.update(label="Hazır!", state="complete", expanded=False)
        else:
            status.update(label="Veri Yetersiz", state="error")
    else:
        status.update(label="Bağlantı Hatası", state="error")

if df is not None and stats is not None and not stats.empty:
    # İstatistikler
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # KPI Kartları
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="📉 İdeal Alış", value=f"{int(best_buy)}:00", delta="Dip Seviye")
    with col2:
        st.metric(label="🚀 İdeal Satış", value=f"{int(best_sell)}:00", delta="Zirve Seviye")
    with col3:
        st.metric(label="💰 Marj Potansiyeli", value=f"%{potential_profit:.2f}", delta="Fırsat")

    # --- GRAFİK (PREMIUM & FULL EKRAN) ---
    st.markdown("### ⚡ Gün İçi Performans Simülasyonu")
    
    fig = go.Figure()

    # Çizgi (Turkuaz / Cyan - Koyu zeminde çok iyi durur)
    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines',
        name='Trend',
        line=dict(color='#00f2c3', width=4, shape='spline'),
        fill='tozeroy',
        fillcolor='rgba(0, 242, 195, 0.1)' # Hafif parlak dolgu
    ))

    # Alım Noktası (Sarı/Gold)
    fig.add_trace(go.Scatter(
        x=[best_buy], y=[min_val],
        mode='markers',
        marker=dict(color='#FFD700', size=18, line=dict(width=2, color='white')),
        name='AL'
    ))

    # Satım Noktası (Mercan Kırmızısı)
    fig.add_trace(go.Scatter(
        x=[best_sell], y=[max_val],
        mode='markers',
        marker=dict(color='#ff4757', size=18, line=dict(width=2, color='white')),
        name='SAT'
    ))

    # Grafik Düzeni (EKSEN AYARLARI ÇOK ÖNEMLİ)
    fig.update_layout(
        template="plotly_dark", # Koyu tema tabanı
        plot_bgcolor='rgba(0,0,0,0)', # Saydam arka plan
        paper_bgcolor='rgba(0,0,0,0)', # Saydam kağıt
        
        xaxis=dict(
            title="Saat (09:00 - 18:00)",
            tickmode='array',
            # Saatleri elle veriyoruz ki eksik olsa bile eksende görünsün
            tickvals=[10, 11, 12, 13, 14, 15, 16, 17, 18],
            ticktext=['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'],
            range=[9.5, 18.5], # 18:00'in sağına boşluk bırakır, kesilmeyi önler
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title="Değişim (%)",
            gridcolor='#363c4e', # Izgara çizgileri hafif gri
            zeroline=True,
            zerolinecolor='#4b5563'
        ),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        height=450
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Strateji Kutusu
    trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
    border_color = "#00f2c3" if trend == "YÜKSELİŞ" else "#ff4757"
    
    st.markdown(f"""
    <div style="
        background-color: rgba(255, 255, 255, 0.03); 
        border-left: 4px solid {border_color};
        padding: 20px; 
        border-radius: 8px; 
        margin-top: 20px;">
        <h4 style="margin:0; color: #f1f5f9;">🤖 Yapay Zeka Özeti</h4>
        <p style="color:#cbd5e1; margin-top:10px; line-height: 1.6;">
        Sistemin <b>{user_date.strftime('%d %B')}</b> tarihi için teknik simülasyonu 
        <strong style="color:{border_color}">{trend}</strong> yönündedir. <br>
        Gün içi en güvenli giriş saati <b>{int(best_buy)}:00</b> olarak tespit edilmiştir. 
        Kâr realizasyonu için <b>{int(best_sell)}:00</b> suları istatistiksel olarak en uygun zamandır.
        </p>
    </div>
    """, unsafe_allow_html=True)

elif df is None:
    st.error("Veri alınamadı. Lütfen sayfayı yenileyin.")
else:
    st.warning("⚠️ Seçilen tarih için yeterli geçmiş veri bulunamadı.")
