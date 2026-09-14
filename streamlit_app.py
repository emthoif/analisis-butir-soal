import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

st.set_page_config(page_title="Analisis Butir Soal", page_icon="📊", layout="wide")
sns.set_style("whitegrid")

st.title("📊 Analisis Butir Soal Ujian")
st.markdown("""
Aplikasi ini menganalisis **soal pilihan ganda** dengan hasil:
- 📈 Tingkat kesukaran & daya beda
- 🎯 Rekomendasi soal (diterima/direvisi/dibuang)
- 📄 Reliabilitas KR-20
- 💾 Download hasil dalam Excel
""")
st.divider()

st.sidebar.header("⚙️ Pengaturan")
uploaded_file = st.sidebar.file_uploader("Upload file Excel jawaban siswa", type=['xlsx', 'xls', 'csv'])
header_row = st.sidebar.number_input("Nama kolom ada di baris ke- (1 = baris pertama)", min_value=1, max_value=20, value=1) - 1
kolom_nama = st.sidebar.text_input("Nama kolom identitas siswa (opsional)", value="Nama")

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=header_row)
        else:
            df = pd.read_excel(uploaded_file, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Gagal membaca file: {e}")
        st.stop()

    kolom_soal = []
    for c in df.columns:
        c_str = str(c).strip()
        if c_str.isdigit():
            kolom_soal.append(c)
        elif c_str.lower().startswith('soal'):
            kolom_soal.append(c)

    if len(kolom_soal) == 0:
        st.error("❌ Tidak ada kolom soal terdeteksi. Pastikan nama kolom soal = angka (1, 2, 3, ...) atau 'Soal1', 'Soal2', dst.")
        st.stop()

    kolom_soal = [c for c in kolom_soal if df[c].notna().sum() > 0]

    kolom_id = ['No', 'Username', kolom_nama]
    kolom_id = [c for c in kolom_id if c in df.columns]
    df = df[kolom_id + kolom_soal].copy()
    df = df.dropna(subset=[kolom_nama] if kolom_nama in df.columns else None).reset_index(drop=True)

    for c in kolom_soal:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

    df['Skor'] = df[kolom_soal].sum(axis=1)
    df['Persentase'] = (df['Skor'] / len(kolom_soal) * 100).round(2)

    def kategori(s):
        if s >= 80: return 'Sangat Baik'
        elif s >= 70: return 'Baik'
        elif s >= 60: return 'Cukup'
        elif s >= 50: return 'Kurang'
        else: return 'Sangat Kurang'

    df['Kategori'] = df['Persentase'].apply(kategori)
    df = df.sort_values('Skor', ascending=False).reset_index(drop=True)

    st.success(f"✅ File berhasil diproses: **{len(df)} siswa**, **{len(kolom_soal)} soal**")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Statistik", "🔬 Analisis Butir", "📈 Visualisasi", "💾 Download"])

    with tab1:
        st.subheader("Statistik Deskriptif")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jumlah Siswa", len(df))
        col2.metric("Jumlah Soal", len(kolom_soal))
        col3.metric("Rata-rata Skor", f"{df['Skor'].mean():.2f}")
        col4.metric("Std Deviasi", f"{df['Skor'].std():.2f}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Skor Max", int(df['Skor'].max()))
        col2.metric("Skor Min", int(df['Skor'].min()))
        col3.metric("Median", f"{df['Skor'].median():.0f}")
        col4.metric("Modus", ', '.join(map(str, df['Skor'].mode().tolist())))
        st.divider()
        st.subheader("Distribusi Kategori")
        st.dataframe(df['Kategori'].value_counts().reset_index().rename(columns={'index':'Kategori', 'Kategori':'Jumlah'}), use_container_width=True)
        st.divider()
        st.subheader("Daftar Skor Siswa")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Analisis Butir Soal")
        def analisis_butir(df, kolom_soal):
            hasil = []
            n = len(df)
            df_sorted = df.sort_values('Skor', ascending=False).reset_index(drop=True)
            n_grup = max(1, int(0.27 * n))
            atas = df_sorted.head(n_grup)
            bawah = df_sorted.tail(n_grup)
            for soal in kolom_soal:
                jawaban = df[soal].astype(int)
                skor = df['Skor']
                p = jawaban.sum() / n
                D = (atas[soal].sum() - bawah[soal].sum()) / n_grup
                rp = 0 if jawaban.std() == 0 or skor.std() == 0 else np.corrcoef(jawaban, skor)[0, 1]
                kat_p = "Mudah" if p >= 0.70 else "Sedang" if p >= 0.30 else "Sukar"
                kat_d = ("Baik Sekali" if D >= 0.40 else "Baik" if D >= 0.30 else "Cukup" if D >= 0.20 else "Jelek")
                if 0.30 <= p <= 0.70 and D >= 0.30: rekom = "✅ Diterima"
                elif D < 0.20: rekom = "❌ Dibuang"
                else: rekom = "⚠️ Direvisi"
                hasil.append({'Soal': soal, 'Benar': int(jawaban.sum()),
                              'Tingkat Kesukaran (p)': round(p, 3), 'Kategori p': kat_p,
                              'Daya Beda (D)': round(D, 3), 'Kategori D': kat_d,
                              'r-pbis': round(rp, 3), 'Rekomendasi': rekom})
            return pd.DataFrame(hasil)
        hasil_butir = analisis_butir(df, kolom_soal)
        st.dataframe(hasil_butir, use_container_width=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Diterima", (hasil_butir['Rekomendasi'] == '✅ Diterima').sum())
        col2.metric("⚠️ Direvisi", (hasil_butir['Rekomendasi'] == '⚠️ Direvisi').sum())
        col3.metric("❌ Dibuang", (hasil_butir['Rekomendasi'] == '❌ Dibuang').sum())

    with tab3:
        st.subheader("Visualisasi")
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.hist(df['Skor'], bins=range(int(df['Skor'].min()), int(df['Skor'].max()) + 2),
                 color='steelblue', edgecolor='black', alpha=0.8)
        ax1.axvline(df['Skor'].mean(), color='red', linestyle='--', label=f"Mean = {df['Skor'].mean():.2f}")
        ax1.set_title('Distribusi Skor Siswa'); ax1.set_xlabel('Skor'); ax1.set_ylabel('Frekuensi'); ax1.legend()
        st.pyplot(fig1)
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        warna_map = {'✅ Diterima': '#2ecc71', '⚠️ Direvisi': '#f39c12', '❌ Dibuang': '#e74c3c'}
        warna = [warna_map[r] for r in hasil_butir['Rekomendasi']]
        ax2.scatter(hasil_butir['Tingkat Kesukaran (p)'], hasil_butir['Daya Beda (D)'],
                    s=200, c=warna, alpha=0.75, edgecolors='black')
        ax2.axvspan(0.30, 0.70, alpha=0.1, color='green')
        ax2.axhline(0.30, color='gray', linestyle='--'); ax2.axhline(0.0, color='red', linestyle='-', alpha=0.4)
        for _, r in hasil_butir.iterrows():
            ax2.annotate(r['Soal'], (r['Tingkat Kesukaran (p)'], r['Daya Beda (D)']),
                        fontsize=8, fontweight='bold', ha='center', va='center')
        ax2.set_title('Peta Butir Soal'); ax2.set_xlabel('Tingkat Kesukaran (p)'); ax2.set_ylabel('Daya Beda (D)')
        st.pyplot(fig2)

    with tab4:
        st.subheader("Reliabilitas & Download")
        k = len(kolom_soal)
        p_arr = np.array([df[c].mean() for c in kolom_soal])
        q_arr = 1 - p_arr
        var_total = df['Skor'].var(ddof=1)
        kr20 = (k / (k - 1)) * (1 - (p_arr * q_arr).sum() / var_total)
        if kr20 >= 0.80: kat_rel = "Sangat Tinggi"
        elif kr20 >= 0.70: kat_rel = "Tinggi"
        elif kr20 >= 0.60: kat_rel = "Cukup"
        elif kr20 >= 0.50: kat_rel = "Rendah"
        else: kat_rel = "Sangat Rendah"
        col1, col2 = st.columns(2)
        col1.metric("KR-20", f"{kr20:.4f}")
        col2.metric("Kategori", kat_rel)
        st.divider()
        st.subheader("Download Hasil Analisis")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Skor Siswa', index=False)
            hasil_butir.to_excel(writer, sheet_name='Analisis Butir', index=False)
        st.download_button(label="📥 Download Hasil (Excel)", data=output.getvalue(),
                          file_name="hasil_analisis_butir_soal.xlsx",
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("👈 Silakan upload file Excel di sidebar untuk memulai analisis.")
    st.markdown("""
    ### 📋 Format File yang Diharapkan:
    - **1 baris = 1 siswa**
    - Kolom identitas: `No`, `Username`, `Nama` (opsional)
    - Kolom soal: nama kolom = angka (`1`, `2`, `3`, ...) 
    - Isi jawaban: **0 (salah)** atau **1 (benar)**
    """)
