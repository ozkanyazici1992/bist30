import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. SAYFA AYARLARI (MODERN GÖRÜNÜM)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BIST30 AI Trader",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BIST 30 Listesi
BIST_TICKERS = {
    "BIST 30 ENDEKSİ": "XU030.IS",
    "AKBNK - Akbank": "AKBNK.IS",
    "ALARK - Alarko": "ALARK.IS",
    "ARCLK - Arçelik": "ARCLK.IS",
    "ASELS - Aselsan": "ASELS.IS",
    "ASTOR - Astor Enerji": "ASTOR.IS",
    "BIMAS - BİM Mağazalar": "BIMAS.IS",
    "BRSAN - Borusan": "BRSAN.IS",
    "CANTU - Çan2 Termik": "CANTU.IS",
    "EKGYO - Emlak Konut": "EKGYO.IS",
    "ENKAI - Enka İnşaat": "ENKAI.IS",
    "EREGL - Ereğli Demir Çelik": "EREGL.IS",
    "FROTO - Ford Otosan": "FROTO.IS",
    "GARAN - Garanti BBVA": "GARAN.IS",
    "GUBRF - Gübre Fabrikaları": "GUBRF.IS",
    "HEKTS - Hektaş": "HEKTS.IS",
    "ISCTR - İş Bankası (C)": "ISCTR.IS",
    "KCHOL - Koç Holding": "KCHOL.IS",
    "KONTR - Kontrolmatik": "KONTR.IS",
    "KOZAL - Koza Altın": "KOZAL.IS",
    "KRDMD - Kardemir (D)": "KRDMD.IS",
    "ODAS - Odaş Elektrik": "ODAS.IS",
    "OYAKC - Oyak Çimento": "OYAKC.IS",
    "PETKM - Petkim": "PETKM.IS",
    "PGSUS - Pegasus": "PGSUS.IS",
    "SAHOL - Sabancı Holding": "SAHOL.IS",
    "SASA - SASA Polyester": "SASA.IS",
    "SISE - Şişecam": "SISE.IS",
    "TCELL - Turkcell": "TCELL.IS",
    "THYAO - Türk Hava Yolları": "THYAO.IS",
    "TOASO - Tofaş": "TOASO.IS",
    "TUPRS - Tüpraş": "TUPRS.IS",
    "YKBNK - Yapı Kredi": "YKBNK.IS"
}

# -----------------------------------------------------------------------------
# 2. VERİ ÇEKME VE İŞLEME
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_hourly_data(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        # Feature Engineering
        df['Month'] = df['Date'].dt.month
        df['Day'] = df['Date'].dt.day
        df['Hour'] = df['Date'].dt.hour
        df['DateOnly'] = df['Date'].dt.date
        return df
    except Exception:
        return None

def analyze_seasonality(df, target_month, target_day, window=3):
    mask = (
        (df['Month'] == target_month) & 
        (df['Day'] >= target_day - window) & 
        (df['Day'] <= target_day + window)
    )
    subset = df[mask].copy()
    
    if len(subset) < 5: return None, None

    # Normalizasyon: Her günü açılış fiyatına göre %0'dan başlat
    subset['Pct_Change'] = subset.groupby('DateOnly')['Close'].transform(
        lambda x: (x - x.iloc[0]) / x.iloc[0] * 100
    )
    
    # 10:00 - 18:00 arası filtrele
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 10) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats, len(subset['DateOnly'].unique())

# -----------------------------------------------------------------------------
# 3. ARAYÜZ TASARIMI
# -----------------------------------------------------------------------------

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    selected_name = st.selectbox("Hisse Seçimi", list(BIST_TICKERS.keys()))
    
    st.markdown("### 📅 Gelecek Planı")
    
    # --- DEĞİŞİKLİK BURADA: MİNİMUM TARİH 2026 ---
    min_date = datetime(2026, 1, 1)
    user_date = st.date_input(
        "Hedef Tarih", 
        value=min_date,      # Varsayılan değer
        min_value=min_date   # Bundan öncesi seçilemez
    )
    
    st.markdown("---")
    st.caption("⚠️ **Not:** Sadece 2026 ve sonrası için planlama yapılabilir. Sistem, seçtiğiniz tarihin geçmiş yıllardaki izlerini sürer.")

# --- Ana Sayfa ---
st.markdown(f"## 📈 {selected_name}")
st.markdown(f"**Hedeflenen Tarih:** {user_date.strftime('%d %B %Y')}")

# Veri Yükleme
ticker_symbol = BIST_TICKERS[selected_name]
df = get_hourly_data(ticker_symbol)

if df is not None:
    # Yıl ne olursa olsun, Ay ve Gün bilgisini alıp geçmişe bakıyoruz
    stats, days_count = analyze_seasonality(df, user_date.month, user_date.day)
    
    if stats is not None and not stats.empty:
        # Hesaplamalar
        min_val = stats['Pct_Change'].min()
        max_val = stats['Pct_Change'].max()
        best_buy = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
        best_sell = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
        
        # --- BÖLÜM 1: KPI KARTLARI ---
        kpi_cols = st.columns(4)
        
        with kpi_cols[0]:
            st.container(border=True).metric(label="📉 İdeal Alış", value=f"{int(best_buy)}:00")
        with kpi_cols[1]:
            st.container(border=True).metric(label="📈 İdeal Satış", value=f"{int(best_sell)}:00")
        with kpi_cols[2]:
            st.container(border=True).metric(label="💰 Potansiyel Marj", value=f"%{max_val - min_val:.2f}")
        with kpi_cols[3]:
            st.container(border=True).metric(label="📊 Referans Veri", value=f"{days_count} Gün")

        # --- BÖLÜM 2: GRAFİK ---
        st.markdown("### ⏱️ Gün İçi Rota Simülasyonu")
        
        fig = go.Figure()

        # Ana Çizgi
        fig.add_trace(go.Scatter(
            x=stats['Hour'], y=stats['Pct_Change'],
            mode='lines',
            name='Tahmini Hareket',
            line=dict(color='#2962FF', width=4, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(41, 98, 255, 0.1)'
        ))

        # Alım Noktası
        fig.add_trace(go.Scatter(
            x=[best_buy], y=[min_val],
            mode='markers',
            marker=dict(color='#00C853', size=15, line=dict(width=2, color='white')),
            name='Alım Fırsatı'
        ))

        # Satım Noktası
        fig.add_trace(go.Scatter(
            x=[best_sell], y=[max_val],
            mode='markers',
            marker=dict(color='#D50000', size=15, line=dict(width=2, color='white')),
            name='Satış Fırsatı'
        ))

        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                title="Saat (10:00 - 18:00)", 
                showgrid=False, 
                dtick=1,
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
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- BÖLÜM 3: STRATEJİ KARTI ---
        with st.container(border=True):
            st.subheader("🤖 Yapay Zeka Tavsiyesi")
            
            trend = "YÜKSELİŞ" if stats.iloc[-1]['Pct_Change'] > 0 else "DÜŞÜŞ"
            trend_color = "green" if trend == "YÜKSELİŞ" else "red"
            
            st.markdown(f"""
            * **Tahmin:** Geçmiş verilere dayanarak, **{user_date.strftime('%d %B')}** tarihinde bu hissenin günü :{trend_color}[**{trend}**] yönünde kapatması bekleniyor.
            * **Alış Zamanlaması:** Sabah açılışından sonra saat **{int(best_buy)}:00** civarında dip oluşumu gözlemlenmiştir.
            * **Satış Zamanlaması:** Gün içi en yüksek değerlere genellikle **{int(best_sell)}:00** sularında ulaşılmaktadır.
            """)
            
    else:
        st.warning("⚠️ Bu tarih için referans alınabilecek yeterli geçmiş veri bulunamadı. (Hafta sonu etkisi olabilir).")

else:
    st.info("Veriler yükleniyor...")
