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

# Kustomisasi CSS untuk mempercantik UI & Metric Card
st.markdown("""
    <style>
    [data-testid="stMetricSimplevalue"] {
        font-size: 24px;
        font-weight: bold;
    }
    .main-title {
        font-size: 28px;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 2px;
    }
    .sub-title {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_index=False, unsafe_allow_html=True)

# 2. MEMUAT & MEMPROSES DATA
@st.cache_data
def load_data():
    sheet_id = "1CrupWIBU3NP49ORN3AxC6ave7SD01ds_odu7NVBOIoI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        
        # Konversi Kolom Waktu
        df['RH Start Time'] = pd.to_datetime(df['RH Start Time'], errors='coerce')
        df['RH Stop Time'] = pd.to_datetime(df['RH Stop Time'], errors='coerce')
        
        # Konversi Kolom Angka Hour Meter (RH)
        df['RH Start'] = pd.to_numeric(df['RH Start'], errors='coerce').fillna(0)
        df['RH Stop'] = pd.to_numeric(df['RH Stop'], errors='coerce').fillna(0)
        
        # Perhitungan Durasi & Selisih
        df['Durasi Aktual Waktu (Jam)'] = ((df['RH Stop Time'] - df['RH Start Time']).dt.total_seconds() / 3600).round(2).fillna(0)
        df['Durasi RH Genset (Jam)'] = (df['RH Stop'] - df['RH Start']).round(2).fillna(0)
        df['Selisih Komparasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual Waktu (Jam)']).round(2)
        
        # Tambahkan status kecocokan untuk keperluan filter/analisis
        # Toleransi perbedaan ± 0.1 Jam (6 menit)
        df['Status Validasi'] = df['Selisih Komparasi (Jam)'].apply(
            lambda x: "Sesuai" if abs(x) <= 0.1 else ("Kelebihan RH" if x > 0.1 else "Kekurangan RH")
        )
        
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets: {e}")
        return pd.DataFrame()

# Eksekusi Load Data
df_raw = load_data()

if not df_raw.empty:
    
    # 3. SIDEBAR FILTER (Desain Bersih)
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/generator.png", width=60)
        st.markdown("### **Panel Kontrol Analisis**")
        st.markdown("---")
        
        # Filter 1: Site Name
        site_options = sorted(df_raw["Site Name"].dropna().unique())
        selected_site = st.multiselect(
            "📍 Pilih Area / Site Name:", 
            options=site_options, 
            default=site_options[:3] if len(site_options) > 0 else None
        )
        
        # Filter 2: Status Validasi
        status_options = df_raw["Status Validasi"].unique()
        selected_status = st.multiselect(
            "🔍 Status Validasi:",
            options=status_options,
            default=status_options
        )
        
        st.markdown("---")
        st.caption("Genset Maintenance Analytics Dashboard v2.0 • 2026")

    # Menerapkan Filter ke Dataframe Utama
    df_filtered = df_raw.copy()
    if selected_site:
        df_filtered = df_filtered[df_filtered["Site Name"].isin(selected_site)]
    if selected_status:
        df_filtered = df_filtered[df_filtered["Status Validasi"].isin(selected_status)]

    # 4. HEADER UTAMA
    st.markdown('<p class="main-title">📊 Dashboard Analisis & Komparasi Jam Backup Genset</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Membandingkan durasi riil berdasarkan log waktu kalender terhadap pembacaan mesin Hour Meter (RH).</p>', unsafe_allow_html=True)

    # 5. RINGKASAN KPI UTAMA (Menggunakan Metric UI Baru)
    total_aktual = df_filtered['Durasi Aktual Waktu (Jam)'].sum()
    total_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    total_selisih = df_filtered['Selisih Komparasi (Jam)'].sum()
    total_tiket = len(df_filtered)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric(label="📋 Total Tiket Terfilter", value=f"{total_tiket} Tiket")
    with kpi2:
        st.metric(label="⏱️ Total Waktu Aktual (Kalender)", value=f"{total_aktual:,.2f} Jam")
    with kpi3:
        st.metric(label="⚙️ Total Durasi HM (Mesin)", value=f"{total_rh:,.2f} Jam")
    with kpi4:
        # Menentukan delta visual untuk selisih deviasi
        delta_color = "normal" if abs(total_selisih) < 1.0 else "inverse"
        st.metric(
            label="⚠️ Total Deviasi Selisih", 
            value=f"{total_selisih:,.2f} Jam",
            delta=f"{total_selisih:,.2f} Jam dari target" if total_selisih != 0 else "Sempurna (0.00)",
            delta_color=delta_color,
            help="Nilai ideal mendekati 0. Angka positif artinya durasi mesin mendahului log kalender, angka negatif sebaliknya."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. BAGIAN GRAFIK & VISUALISASI
    col_chart, col_insight = st.columns([2.5, 1])
    
    with col_chart:
        st.subheader("📌 Grafik Batang Komparasi per Tiket")
        
        if not df_filtered.empty:
            # Melt data untuk visualisasi berpasangan
            chart_df = df_filtered.reset_index().melt(
                id_vars=['Ticket Number SWFM', 'Site Name'], 
                value_vars=['Durasi Aktual Waktu (Jam)', 'Durasi RH Genset (Jam)'],
                var_name='Metode Hitung', value_name='Total Jam'
            )
            
            # Pengaturan Grafik Profesional
            fig_compare = px.bar(
                chart_df, 
                x='Ticket Number SWFM', 
                y='Total Jam', 
                color='Metode Hitung', 
                barmode='group',
                color_discrete_map={
                    'Durasi Aktual Waktu (Jam)': '#3B82F6', # Biru Modern
                    'Durasi RH Genset (Jam)': '#F59E0B'     # Amber/Orange hangat
                },
                template="plotly_white"
            )
            
            fig_compare.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Nomor Tiket SWFM",
                yaxis_title="Durasi (Jam)",
                hovermode="x unified"
            )
            st.plotly_chart(fig_compare, use_container_width=True)
        else:
            st.warning("Tidak ada data untuk ditampilkan pada grafik berdasarkan filter Anda.")

    with col_insight:
        st.subheader("💡 Komposisi Validasi")
        # Grafik Donut untuk melihat distribusi status validasi data
        if not df_filtered.empty:
            fig_pie = px.pie(
                df_filtered, 
                names='Status Validasi', 
                hole=0.5,
                color='Status Validasi',
                color_discrete_map={
                    'Sesuai': '#10B981',      # Hijau Emerald
                    'Kelebihan RH': '#EF4444', # Merah
                    'Kekurangan RH': '#3B82F6' # Biru
                },
                template="plotly_white"
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 7. TABEL DETAIL & EKSPOR DATA
    st.subheader("📋 Tabel Detail Komparasi & Validasi Data")
    
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Name', 
        'RH Start Time', 'RH Stop Time', 'Durasi Aktual Waktu (Jam)',
        'RH Start', 'RH Stop', 'Durasi RH Genset (Jam)',
        'Selisih Komparasi (Jam)', 'Status Validasi'
    ]
    
    # Fungsi styling warna background pada dataframe berdasarkan penyimpangan data
    def style_status(val):
        if val == 'Sesuai':
            return 'background-color: #D1FAE5; color: #065F46;' # Hijau Muda
        elif 'Kelebihan' in str(val):
            return 'background-color: #FEE2E2; color: #991B1B;' # Merah Muda
        else:
            return 'background-color: #DBEAFE; color: #1E40AF;' # Biru Muda

    # Menampilkan DataFrame dengan styling interaktif
    if not df_filtered.empty:
        styled_df = df_filtered[kolom_tampilan].style.map(style_status, subset=['Status Validasi'])
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Fitur Tambahan: Tombol Download Excel/CSV
        csv = df_filtered[kolom_tampilan].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Laporan Terfilter (.CSV)",
            data=csv,
            file_name="Laporan_Analisis_RH_Genset.csv",
            mime="text/csv"
        )
    else:
        st.info("Pilih filter pada sidebar untuk memunculkan tabel data.")

else:
    st.info("💡 Menunggu koneksi atau pengecekan struktur Google Sheets Anda. Pastikan nama-nama kolom sudah sesuai.")
