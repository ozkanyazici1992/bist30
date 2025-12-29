import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. SAYFA AYARLARI (TEMİZ & KURUMSAL)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BIST30 AI Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# 2. HIZLI VERİ ÇEKME (PERFORMANS ODAKLI)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_optimized_data(ticker_symbol):
    try:
        # threads=True ile çoklu indirme yaparak hızı artırıyoruz
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False, threads=True)
        
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        
        # TRT Saat Dilimi Ayarı
        if df['Date'].dt.tz is None:
             df['Date'] = df['Date'].dt.tz_localize('UTC')
        df['Date'] = df['Date'].dt.tz_convert('Europe/Istanbul').dt.tz_localize(None)
        
        # Feature Engineering
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

    # Normalizasyon (% Değişim)
    start_prices = subset.groupby('DateOnly')['Close'].transform('first')
    subset['Pct_Change'] = ((subset['Close'] - start_prices) / start_prices) * 100
    
    # 09:00 - 18:00 arası saatleri al
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 9) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats

# -----------------------------------------------------------------------------
# 3. ARAYÜZ TASARIMI
# -----------------------------------------------------------------------------

# --- Sidebar (Menü) ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    st.write("Analiz parametrelerini buradan ayarlayabilirsiniz.")
    
    selected_name = st.selectbox("Hisse Seçimi", list(BIST_TICKERS.keys()))
    
    st.markdown("---")
    st.markdown("### 📅 Gelecek Planı")
    
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input(
        "Hedef Tarih", 
        value=min_date, 
        min_value=min_date,
        help="Sadece 2026 ve sonrası seçilebilir."
    )
    
    st.info("💡 **İpucu:** Veriler Türkiye saati ile (09:00 - 18:10) gösterilmektedir.")

# --- Ana Sayfa ---
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"**Hedeflenen Tarih:** {user_date.strftime('%d %B %Y')}")

# Veri İşleme (Optimize Edilmiş Hızlı Yükleme)
ticker_symbol = BIST_TICKERS[selected_name]

# Yükleniyor animasyonunu modernleştirelim
with st.status("Piyasa verileri analiz ediliyor...", expanded=True) as status:
    df = get_optimized_data(ticker_symbol)
    
    if df is not None:
        stats = analyze_seasonality(df, user_date.month, user_date.day)
        if stats is not None and not stats.empty:
            status.update(label="Analiz Başarıyla Tamamlandı!", state="complete", expanded=False)
        else:
            status.update(label="Yetersiz Veri", state="error", expanded=False)
    else:
        status.update(label="Bağlantı Hatası", state="error")

if df is not None and stats is not None and not stats.empty:
    # Hesaplamalar
    min_val = stats['Pct_Change'].min()
    max_val = stats['Pct_Change'].max()
    best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
    best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
    potential_profit = max_val - min_val

    # --- KPI KARTLARI (SADE VE ŞIK) ---
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.container(border=True).metric(label="📉 İdeal Alış Saati", value=f"{int(best_buy)}:00", delta="Dip Seviye")
    with kpi2:
        st.container(border=True).metric(label="📈 İdeal Satış Saati", value=f"{int(best_sell)}:00", delta="Tepe Seviye")
    with kpi3:
        st.container(border=True).metric(label="💰 Potansiyel Marj", value=f"%{potential_profit:.2f}", delta="Fark")

    # --- GRAFİK (AYDINLIK TEMA) ---
    st.markdown("### ⏱️ Gün İçi Performans Simülasyonu")
    
    fig = go.Figure()

    # Ana Çizgi (Profesyonel Mavi)
    fig.add_trace(go.Scatter(
        x=stats['Hour'], y=stats['Pct_Change'],
        mode='lines',
        name='Tahmini Hareket',
        line=dict(color='#2962FF', width=4, shape='spline'), # Spline ile yumuşak geçiş
        fill='tozeroy',
        fillcolor='rgba(41, 98, 255, 0.1)'
    ))

    # Alış Noktası (Yeşil)
    fig.add_trace(go.Scatter(
        x=[best_buy], y=[min_val],
        mode='markers',
        marker=dict(color='#00C853', size=15, line=dict(width=2, color='white')),
        name='Alım Fırsatı'
    ))

    # Satış Noktası (Kırmızı)
    fig.add_trace(go.Scatter(
        x=[best_sell], y=[max_val],
        mode='markers',
        marker=dict(color='#D50000', size=15, line=dict(width=2, color='white')),
        name='Satış Fırsatı'
    ))

    fig.update_layout(
        template="plotly_white", # Temiz beyaz arka plan
        xaxis=dict(
            title="Saat (09:00 - 18:10)", 
            tickmode='array',
            tickvals=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            showgrid=False,
            linecolor='black'
        ),
        yaxis=dict(
            title="Tahmini Değişim (%)", 
            showgrid=True, 
            gridcolor='#f0f0f0',
            zeroline=True, 
            zerolinecolor='#e0e0e0'
        ),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False,
        height=450
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- STRATEJİ KARTI ---
    with st.container(border=True):
        st.subheader("🤖 Yapay Zeka Stratejisi")
        
        trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
        trend_color = "green" if trend == "YÜKSELİŞ" else "red"
        
        st.markdown(f"""
        * **Genel Görünüm:** **{user_date.strftime('%d %B')}** tarihinde hissenin günü :{trend_color}[**{trend}**] ile kapatması bekleniyor.
        * **Alış Zamanı:** Sabah volatilitesi sonrası saat **{int(best_buy)}:00** civarı güvenli bir giriş noktası olabilir.
        * **Satış Zamanı:** Gün içi kârı realize etmek için en uygun zaman dilimi **{int(best_sell)}:00** sularıdır.
        """)

elif df is None:
    st.warning("⚠️ Veri sunucusuna bağlanılamadı. Lütfen internet bağlantınızı kontrol edip sayfayı yenileyin.")
else:
    st.info("👈 Analize başlamak için sol menüden bir hisse ve tarih seçin.")
