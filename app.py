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

st.markdown("""
    <style>
    .stApp { background-color: #fff3e0; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #ffcc80; }
    div[data-testid="stMetric"] {
        background-color: #ffffff; border: 1px solid #ffe0b2;
        border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(255, 167, 38, 0.1);
    }
    h1, h2, h3, h4 { color: #e65100 !important; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stMetricValue"] { color: #ef6c00 !important; font-weight: 800; }
    div[data-testid="stMetricLabel"] { color: #fb8c00 !important; }
    .stSelectbox, .stDateInput { color: #e65100; }
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
# 2. VERİ ÇEKME & FEATURE ENGINEERING (HAFTALIK YAPI)
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
            
            # --- YENİ MANTIK: HAFTA VE GÜN BİLGİSİ ---
            # isocalendar().week -> Yılın kaçıncı haftası olduğu (1-52)
            # dayofweek -> Haftanın hangi günü (0=Pazartesi, 6=Pazar)
            df['WeekOfYear'] = df['Date'].dt.isocalendar().week
            df['DayOfWeek'] = df['Date'].dt.dayofweek 
            
            df['Hour'] = df['Date'].dt.hour
            df['DateOnly'] = df['Date'].dt.date
            
            return df
        except Exception:
            time.sleep(2)
            if attempt == max_retries - 1:
                return None
    return None

def analyze_by_week_cycle(df, target_week, target_day_of_week):
    """
    Eski yöntem: Ay ve Gün (Örn: 15 Haziran)
    Yeni yöntem: Yılın Haftası ve Haftanın Günü (Örn: 24. Haftanın Salı günü)
    """
    
    # Filtre: Geçmiş yıllardaki AYNI HAFTA ve AYNI GÜN'ü bul
    mask = (
        (df['WeekOfYear'] == target_week) & 
        (df['DayOfWeek'] == target_day_of_week)
    )
    subset = df[mask].copy()
    
    # Yeterli veri yoksa (örneğin geçmişte o gün tatilse)
    if len(subset) < 5: return None

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
    
    st.markdown("### 📅 Tarih Seçimi")
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input("İşlem Tarihi", value=min_date, min_value=min_date)
    
    # Seçilen tarihin bilgilerini hesapla
    target_week = user_date.isocalendar().week
    target_day_of_week = user_date.weekday() # 0: Pzt, 4: Cuma, 5: Cmt, 6: Paz
    
    days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    selected_day_name = days_tr[target_day_of_week]
    
    st.markdown("---")
    st.info(f"**Analiz Mantığı:**\nSistem, geçmiş yılların **{target_week}. Haftasının {selected_day_name}** günlerini tarayacaktır.")

# Ana Başlık
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"<span style='color:#ef6c00; font-weight:500'>Hedef: {user_date.year} / {target_week}. Hafta / {selected_day_name}</span>", unsafe_allow_html=True)

# Hafta Sonu Kontrolü
if target_day_of_week > 4: # 5 ve 6 Hafta sonudur
    st.error(f"⚠️ **Piyasa Kapalı:** Seçtiğiniz tarih ({selected_day_name}) hafta sonuna denk geliyor. Borsa İstanbul kapalı olduğu için işlem yapılamaz. Lütfen hafta içi bir tarih seçiniz.")
else:
    # Veri İşleme
    ticker_symbol = BIST_TICKERS[selected_name]

    with st.status("Döngüsel analiz yapılıyor...", expanded=True) as status:
        df = get_optimized_data(ticker_symbol)
        if df is not None:
            # Yeni Fonksiyonu Çağırıyoruz
            stats = analyze_by_week_cycle(df, target_week, target_day_of_week)
            
            if stats is not None and not stats.empty:
                status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
            else:
                status.update(label="Geçmiş Veri Bulunamadı (Resmi Tatil Olabilir)", state="error")
                stats = None
        else:
            status.update(label="Veri Alınamadı", state="error")

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
        st.markdown("### ⚡ Haftalık Döngü Simülasyonu")
        
        fig = go.Figure()

        # Trend Çizgisi
        fig.add_trace(go.Scatter(
            x=stats['Hour'], y=stats['Pct_Change'],
            mode='lines', name='Trend',
            line=dict(color='#ff6d00', width=4, shape='spline'),
            fill='tozeroy', fillcolor='rgba(255, 109, 0, 0.1)'
        ))

        # Alış
        fig.add_trace(go.Scatter(
            x=[best_buy], y=[min_val], mode='markers',
            marker=dict(color='#2e7d32', size=16, line=dict(width=2, color='white')),
            name='AL'
        ))

        # Satış
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
                linecolor='#ffcc80'
            ),
            yaxis=dict(
                title="Tahmini Değişim (%)",
                gridcolor='#ffe0b2',
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
            <h4 style="margin:0; color:#e65100;">🔥 Yapay Zeka Özeti</h4>
            <p style="color:#5d4037; margin-top:10px;">
            Geçmiş yılların <b>{target_week}. Haftasının {selected_day_name}</b> günleri incelendiğinde, 
            piyasa genel eğilimi <strong style="color:{border_color}">{trend}</strong> yönündedir.<br>
            Gün içi strateji: <b>{int(best_buy)}:00</b> sularında destek seviyesinden alım, 
            <b>{int(best_sell)}:00</b> civarında direnç seviyesinden satış.
            </p>
        </div>
        """, unsafe_allow_html=True)
