İstediğin proje tam olarak **"Intraday Seasonality Analyzer"** (Gün İçi Mevsimsellik Analizörü) olarak adlandırılır.

Aşağıda, **Streamlit** kullanarak hazırladığım, `yfinance` üzerinden anlık olarak son 730 günün (maksimum izin verilen) saatlik verisini çeken, veriyi işleyen ve sana hem grafik hem de metin olarak tavsiye veren tam kod bulunmaktadır.

Bu kodda **BIST 30 Endeksi (XU030)** ve **BIST 30 Hisseleri** tanımlıdır.

### Nasıl Çalıştırılır?

1. Bilgisayarında `streamlit`, `yfinance`, `plotly` ve `pandas` kütüphanelerinin yüklü olduğundan emin ol.
2. Aşağıdaki kodu `bist30_analiz.py` adıyla kaydet.
3. Terminalden `streamlit run bist30_analiz.py` komutunu çalıştır.

### Python Kodu (bist30_analiz.py)

```python
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. SAYFA AYARLARI VE SABİTLER
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BIST30 Yapay Zeka Zamanlayıcı",
    page_icon="📈",
    layout="wide"
)

# BIST 30 Listesi ve Endeks
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
# 2. VERİ ÇEKME FONKSİYONU (CACHE MEKANİZMALI)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # 1 saatlik önbellek
def get_hourly_data(ticker_symbol):
    """
    Seçilen hissenin son 730 günlük (2 yıl) saatlik verisini çeker.
    """
    try:
        # yfinance ile son 2 yıl, saatlik veri
        df = yf.download(ticker_symbol, period="2y", interval="1h", progress=False)
        
        if df.empty:
            return None

        # Sütun isimlerini düzeltme (MultiIndex sorununa karşı)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        
        # Tarih sütunu standardizasyonu
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df.rename(columns={date_col: 'Date'}, inplace=True)
        
        # Timezone temizliği
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        # Yeni özellikler ekle
        df['Month'] = df['Date'].dt.month
        df['Day'] = df['Date'].dt.day
        df['Hour'] = df['Date'].dt.hour
        df['DateOnly'] = df['Date'].dt.date
        
        return df
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return None

# -----------------------------------------------------------------------------
# 3. ANALİZ MOTORU
# -----------------------------------------------------------------------------
def analyze_intraday_seasonality(df, target_month, target_day, window=5):
    """
    Belirli bir tarih aralığındaki saatlik performansı analiz eder.
    Window: Seçilen günün sağından ve solundan kaç gün bakılacağı (Veri az olduğu için pencereyi geniş tutmak iyidir)
    """
    # 1. Tarih Filtreleme (Güneş Takvimi Paternleri)
    # Yıl farketmeksizin o gün ve çevresindeki günleri al
    
    # Basit filtreleme yerine döngüsel gün kontrolü (Yılbaşı/Yılsonu geçişleri hariç basitleştirilmiş)
    mask = (
        (df['Month'] == target_month) & 
        (df['Day'] >= target_day - window) & 
        (df['Day'] <= target_day + window)
    )
    subset = df[mask].copy()
    
    if len(subset) < 10:  # Yetersiz veri kontrolü
        return None, None

    # 2. Normalizasyon (ÖNEMLİ ADIM)
    # Her günü kendi içinde 0'dan başlatıp yüzdesel değişime bakmalıyız.
    # Yoksa 100 TL'lik fiyat ile 10 TL'lik fiyatın ortalaması yanlış olur.
    
    subset['Pct_Change'] = subset.groupby('DateOnly')['Close'].transform(
        lambda x: (x - x.iloc[0]) / x.iloc[0] * 100
    )
    
    # 3. Saatlik Ortalamaları Al
    hourly_stats = subset.groupby('Hour')['Pct_Change'].mean().reset_index()
    
    # Sadece işlem saatlerini al (10:00 - 18:00 arası, bazen 09:00 gelebilir temizleyelim)
    hourly_stats = hourly_stats[(hourly_stats['Hour'] >= 10) & (hourly_stats['Hour'] <= 18)]
    
    return hourly_stats, len(subset['DateOnly'].unique())

# -----------------------------------------------------------------------------
# 4. ARAYÜZ (SIDEBAR & MAIN)
# -----------------------------------------------------------------------------

# --- SIDEBAR ---
st.sidebar.title("🛠️ Analiz Ayarları")
st.sidebar.markdown("---")

selected_name = st.sidebar.selectbox("Hisse / Endeks Seçin", list(BIST_TICKERS.keys()))
ticker_symbol = BIST_TICKERS[selected_name]

st.sidebar.subheader("📅 Tarih Seçimi")
# Kullanıcıdan sadece gün ve ayı almak için date_input kullanıyoruz ama yılı yoksayacağız
user_date = st.sidebar.date_input("Analiz Tarihi", datetime.now())
target_month = user_date.month
target_day = user_date.day

st.sidebar.info(f"Seçilen Tarih: **{target_day} / {target_month}**\n\nBu sistem, son 2 yıldaki verileri tarayarak, yılın bu dönemlerinde gün içi (saatlik) hareketlerin ortalamasını çıkarır.")

# --- MAIN PAGE ---
st.title(f"📊 {selected_name} - Gün İçi Al/Sat Stratejisi")
st.markdown(f"**Analiz edilen dönem:** Son 2 Yıl | **Hedef Tarih:** {target_day} {datetime(2023, target_month, 1).strftime('%B')}")

# Veriyi Çek
with st.spinner('Veriler Borsa İstanbul sunucularından (Yahoo Finance) çekiliyor...'):
    df = get_hourly_data(ticker_symbol)

if df is not None:
    # Analizi Yap
    stats, days_count = analyze_intraday_seasonality(df, target_month, target_day)
    
    if stats is not None and not stats.empty:
        # En iyi ve en kötü saatleri bul
        min_val = stats['Pct_Change'].min()
        max_val = stats['Pct_Change'].max()
        
        best_buy_hour = stats.loc[stats['Pct_Change'].idxmin()]['Hour']
        best_sell_hour = stats.loc[stats['Pct_Change'].idxmax()]['Hour']
        
        # Fark (Marj)
        margin = max_val - min_val
        
        # KPI KARTLARI
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📉 En İyi Alış Saati", f"{int(best_buy_hour)}:00", delta_color="inverse")
        col2.metric("📈 En İyi Satış Saati", f"{int(best_sell_hour)}:00")
        col3.metric("💰 Ort. Gün İçi Marj", f"%{margin:.2f}")
        col4.metric("📚 Analiz Edilen Gün", f"{days_count} Gün")
        
        # GRAFİK (Plotly)
        fig = go.Figure()
        
        # Çizgi
        fig.add_trace(go.Scatter(
            x=stats['Hour'], 
            y=stats['Pct_Change'], 
            mode='lines+markers',
            name='Ortalama Hareket',
            line=dict(color='#1f77b4', width=3)
        ))
        
        # Alış Noktası İşaretleyici
        fig.add_trace(go.Scatter(
            x=[best_buy_hour], y=[min_val],
            mode='markers+text',
            name='Alış Bölgesi',
            marker=dict(color='green', size=15, symbol='triangle-up'),
            text=["AL"], textposition="bottom center"
        ))

        # Satış Noktası İşaretleyici
        fig.add_trace(go.Scatter(
            x=[best_sell_hour], y=[max_val],
            mode='markers+text',
            name='Satış Bölgesi',
            marker=dict(color='red', size=15, symbol='triangle-down'),
            text=["SAT"], textposition="top center"
        ))

        fig.update_layout(
            title="Saatlik Kümülatif Getiri Eğrisi (Açılışa Göre %)",
            xaxis_title="Saat (10:00 - 18:00)",
            yaxis_title="Gün İçi Değişim (%)",
            hovermode="x unified",
            xaxis=dict(tickmode='linear', tick0=10, dtick=1),
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # TAVSİYE METNİ
        st.subheader("🤖 Yapay Zeka Strateji Özeti")
        
        trend_direction = "Yükseliş" if stats.iloc[-1]['Pct_Change'] > 0 else "Düşüş"
        
        advice_box = f"""
        **Analiz Sonucu:**
        Geçmiş veriler gösteriyor ki, **{selected_name}** bu tarihlerde genellikle günü **{trend_direction}** eğilimiyle kapatıyor.
        
        👉 **Strateji:** Eğer gün içi işlem (trade) yapacaksanız, istatistiksel olarak en uygun alış saati **{int(best_buy_hour)}:00** civarıdır. 
        Sabah açılışındaki volatilitenin geçmesini beklemek mantıklı görünüyor. 
        Pozisyonunuzu kârla kapatmak için en uygun zaman dilimi ise **{int(best_sell_hour)}:00** sularıdır.
        """
        
        if trend_direction == "Yükseliş":
            st.success(advice_box)
        else:
            st.warning(advice_box)
            
    else:
        st.error("⚠️ Seçilen tarih aralığı için yeterli geçmiş veri bulunamadı (Hafta sonuna veya tatillere denk geliyor olabilir). Lütfen tarihi 1-2 gün kaydırarak tekrar deneyin.")

else:
    st.info("Veri bekleniyor... Sol menüden seçim yapın.")


```
