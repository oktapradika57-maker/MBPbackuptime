import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN DASHBOARD
st.set_page_config(
    page_title="Genset RH Analytics", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kustomisasi CSS untuk UI
st.markdown("""
    <style>
    [data-testid="stMetricSimplevalue"] { font-size: 24px; font-weight: bold; }
    .main-title { font-size: 28px; font-weight: 700; color: #1E293B; margin-bottom: 2px; }
    .sub-title { font-size: 14px; color: #64748B; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. MEMUAT & MEMPROSES DATA
@st.cache_data
def load_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        # Membaca data mentah
        df_raw = pd.read_csv(url)
        
        # Jika kolom kurang dari 6, sistem tidak bisa memproses komparasi
        if df_raw.shape[1] < 6:
            st.error(f"❌ Google Sheets Anda hanya memiliki {df_raw.shape[1]} kolom. Dibutuhkan minimal 6 kolom untuk melakukan analisis komparasi.")
            return pd.DataFrame()
            
        # Membuat dataframe baru dengan nama kolom standar berdasarkan posisi urutan (Indeks)
        df = pd.DataFrame()
        df['Ticket Number SWFM'] = df_raw.iloc[:, 0].astype(str) # Kolom ke-1
        df['Site Name'] = df_raw.iloc[:, 1].astype(str)          # Kolom ke-2
        
        # Konversi Kolom Waktu (Kolom ke-3 dan ke-4)
        df['RH Start Time'] = pd.to_datetime(df_raw.iloc[:, 2], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df_raw.iloc[:, 3], errors='coerce')
        
        # Konversi Kolom Angka Hour Meter (Kolom ke-5 dan ke-6)
        df['RH Start'] = pd.to_numeric(df_raw.iloc[:, 4], errors='coerce').fillna(0)
        df['RH Stop'] = pd.to_numeric(df_raw.iloc[:, 5], errors='coerce').fillna(0)
        
        # ─── LOGIKA PERHITUNGAN UTAMA ───
        df['Durasi Aktual Waktu (Jam)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2).fillna(0)
        df['Durasi RH Genset (Jam)'] = (df['RH Stop'] - df['RH Start']).round(2).fillna(0)
        df['Selisih Komparasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
        
        # Status Validasi Berdasarkan Deviasi (Toleransi 0.1 Jam / 6 Menit)
        df['Status Validasi'] = df['Selisih Komparasi (Jam)'].apply(
            lambda x: "Sesuai" if abs(x) <= 0.1 else ("Kelebihan RH" if x > 0.1 else "Kekurangan RH")
        )
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan link sudah publik share. Detail Error: {e}")
        return pd.DataFrame()

# Eksekusi Load Data
df_filtered_master = load_data()

if not df_filtered_master.empty:
    
    # 3. SIDEBAR FILTER
    with st.sidebar:
        st.markdown("### **Panel Kontrol Analisis**")
        st.markdown("---")
        
        site_options = sorted(df_filtered_master["Site Name"].dropna().unique())
        selected_site = st.multiselect(
            "📍 Pilih Area / Site Name:", 
            options=site_options, 
            default=site_options[:3] if len(site_options) > 0 else None
        )
        
        status_options = df_filtered_master["Status Validasi"].unique()
        selected_status = st.multiselect(
            "🔍 Status Validasi:",
            options=status_options,
            default=status_options
        )

    # Menerapkan Filter ke Data
    df_filtered = df_filtered_master.copy()
    if selected_site:
        df_filtered = df_filtered[df_filtered["Site Name"].isin(selected_site)]
    if selected_status:
        df_filtered = df_filtered[df_filtered["Status Validasi"].isin(selected_status)]

    # 4. HEADER UTAMA
    st.markdown('<p class="main-title">📊 Dashboard Analisis & Komparasi Jam Backup Genset</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Membandingkan durasi riil berdasarkan log waktu kalender terhadap pembacaan mesin Hour Meter (RH) secara otomatis berdasarkan urutan kolom.</p>', unsafe_allow_html=True)

    # 5. RINGKASAN KPI UTAMA
    total_aktual = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    total_selisih = df_filtered['Selisih Komparasi (Jam)'].sum()
    total_tiket = len(df_filtered)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(label="📋 Total Tiket Terfilter", value=f"{total_tiket} Tiket")
    with kpi2:
        st.metric(label="⏱️ Waktu Aktual (Kalender)", value=f"{total_aktual:,.2f} Jam")
    with kpi3:
        st.metric(label="⚙️ Durasi HM Mesin (RH)", value=f"{total_rh:,.2f} Jam")
    with kpi4:
        delta_color = "normal" if abs(total_selisih) < 1.0 else "inverse"
        st.metric(label="⚠️ Total Deviasi Selisih", value=f"{total_selisih:,.2f} Jam", delta_color=delta_color)

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. BAGIAN GRAFIK & VISUALISASI
    col_chart, col_insight = st.columns([2.5, 1])
    
    with col_chart:
        st.subheader("📌 Grafik Batang Komparasi per Tiket")
        if not df_filtered.empty:
            chart_df = df_filtered.reset_index().melt(
                id_vars=['Ticket Number SWFM', 'Site Name'], 
                value_vars=['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)'],
                var_name='Metode Hitung', value_name='Total Jam'
            )
            
            fig_compare = px.bar(
                chart_df, x='Ticket Number SWFM', y='Total Jam', 
                color='Metode Hitung', barmode='group',
                color_discrete_map={'Durasi Aktual Waktu (Jam)': '#3B82F6', 'Durasi RH Genset (Jam)': '#F59E0B'},
                template="plotly_white"
            )
            fig_compare.update_layout(margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified")
            st.plotly_chart(fig_compare, use_container_width=True)

    with col_insight:
        st.subheader("💡 Komposisi Data")
        if not df_filtered.empty:
            fig_pie = px.pie(
                df_filtered, names='Status Validasi', hole=0.5,
                color='Status Validasi',
                color_discrete_map={'Sesuai': '#10B981', 'Kelebihan RH': '#EF4444', 'Kekurangan RH': '#3B82F6'},
                template="plotly_white"
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 7. TABEL DETAIL & EKSPOR DATA
    st.subheader("📋 Tabel Detail Komparasi & Validasi Data")
    kolom_tampilan =
