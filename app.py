import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(page_title="Dashboard Genset & MBP", layout="wide")
st.title("📊 Dashboard Analisis & Komparasi RH Genset")
st.markdown("---")

# 2. Memuat Data
@st.cache_data
def load_data():
    df = pd.read_excel("database_mbp.xlsx")
    
    # Konversi kolom waktu ke format datetime
    df['Tanggal Jam Start'] = pd.to_datetime(df['Tanggal Jam Start'], errors='coerce')
    df['Tanggal Jam Stop'] = pd.to_datetime(df['Tanggal Jam Stop'], errors='coerce')
    
    # ─── LOGIKA PERHITUNGAN ───
    # A. Menghitung Durasi Real/Aktual berdasarkan Waktu Kalender (dalam Jam)
    df['Durasi Aktual (Jam)'] = (df['Tanggal Jam Stop'] - df['Tanggal Jam Start']).dt.total_seconds() / 3600
    df['Durasi Aktual (Jam)'] = df['Durasi Aktual (Jam)'].round(2)
    
    # B. Menghitung Durasi berdasarkan Hour Meter (RH) Genset
    df['Durasi RH Genset (Jam)'] = df['Stop RH Genset'] - df['Start RH Genset']
    df['Durasi RH Genset (Jam)'] = df['Durasi RH Genset (Jam)'].round(2)
    
    # C. Komparasi Selisih (Mencari deviasi antara durasi sistem vs durasi riil mesin)
    df['Selisih Durasi (Jam)'] = (df['Durasi RH Genset (Jam)'] - df['Durasi Aktual (Jam)']).round(2)
    
    return df

try:
    df = load_data()

    # 3. Sidebar untuk Filter
    st.sidebar.header("Filter Data")
    site_filter = st.sidebar.multiselect(
        "Pilih Site Name:",
        options=df["Site Name"].unique(),
        default=df["Site Name"].unique()[:5]  # default pilih 5 pertama agar tidak penuh
    )

    # Terapkan Filter
    df_filtered = df[df["Site Name"].isin(site_filter)]

    # 4. KPI Metrics (Ringkasan Total Jam Backup)
    total_jam_aktual = df_filtered['Durasi Aktual (Jam)'].sum()
    total_jam_rh = df_filtered['Durasi RH Genset (Jam)'].sum()
    rata_selisih = df_filtered['Selisih Durasi (Jam)'].mean()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Durasi Aktual (Waktu)", f"{total_jam_aktual:.2f} Jam")
    with col2:
        st.metric("Total Durasi Mesin (RH Genset)", f"{total_jam_rh:.2f} Jam")
    with col3:
        st.metric("Rata-rata Selisih (RH vs Aktual)", f"{rata_selisih:.2f} Jam", 
                  help="Jika minus, artinya durasi di lapangan lebih pendek dari durasi pencatatan waktu kalender.")

    st.markdown("---")

    # 5. Visualisasi Komparasi Berdampingan
    st.subheader("📌 Grafik Komparasi Durasi Aktual vs RH Genset per Transaksi/Tiket")
    
    # Manipulasi data sedikit untuk grafik batang berdampingan
    chart_df = df_filtered.reset_index().melt(
        id_vars=['Ticket Number SWFM', 'Site Name'], 
        value_vars=['Durasi Aktual (Jam)', 'Durasi RH Genset (Jam)'],
        var_name='Metode Hitung', value_name='Total Jam'
    )
    
    fig_compare = px.bar(
        chart_df, 
        x='Ticket Number SWFM', 
        y='Total Jam', 
        color='Metode Hitung', 
        barmode='group',
        title="Perbandingan Jam Backup Waktu Aktual vs Angka Hour Meter Mesin",
        labels={'Ticket Number SWFM': 'Nomor Tiket / ID Event'}
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # 6. Tabel Detail Komparasi (Fokus utama user)
    st.subheader("📋 Tabel Analisis & Komparasi Jam Backup Genset")
    
    # Memilih kolom spesifik untuk ditampilkan agar rapi
    kolom_tampilan = [
        'Ticket Number SWFM', 'Site Name', 
        'Tanggal Jam Start', 'Tanggal Jam Stop', 'Durasi Aktual (Jam)',
        'Start RH Genset', 'Stop RH Genset', 'Durasi RH Genset (Jam)',
        'Selisih Durasi (Jam)'
    ]
    
    st.dataframe(df_filtered[kolom_tampilan], use_container_width=True)

except FileNotFoundError:
    st.error("❌ File 'database_mbp.xlsx' tidak ditemukan.")
except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan atau struktur kolom tidak sesuai: {e}")
