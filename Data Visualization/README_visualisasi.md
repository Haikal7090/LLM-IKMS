# Visualisasi: Workslop on the Rig Floor (IKMS 2026)

Kode untuk membuat ulang Gambar 1–4 pada naskah.

| Berkas keluaran | Gambar di naskah | Sumber data |
|---|---|---|
| `gambar1_alur_penelitian.png` | Gambar 1. Alur penelitian | Diagram (tanpa data) |
| `gambar2_U_per_kondisi.png` | Gambar 2. U per kejadian menurut kondisi dan sumber label | `claims_gated.pkl`, `label_dua_penilai.pkl`, `Diskusi_Klaim_Berbeda_final.xlsx`, `Lembar_Penilai_Utama_KUNCI_TIM_A.csv` |
| `gambar3_jenis_galat.png` | Gambar 3. Jenis galat dan bagian yang dibuang gerbang mutu | Hitungan taksonomi galat pada Subbagian 3.3 |
| `gambar4_tau_dan_roc.png` | Gambar 4. (a) Sapuan τ; (b) Kurva ROC AlignScore dan HHEM | `sensitivitas.json` (Sel 13) dan berkas data Gambar 2 |

## Cara menjalankan

Jalankan di folder kerja notebook `IKMS_2026_Eksperimen.ipynb` setelah Sel 12 dan Sel 13 selesai:

```bash
pip install pandas numpy matplotlib openpyxl
python visualisasi_ikms.py              # semua gambar
python visualisasi_ikms.py --hanya 1 3  # sebagian gambar
```

Gambar 1 dan Gambar 3 dapat dibuat tanpa berkas data. Gambar 4a memakai angka keluaran Sel 13 yang tertanam di skrip apabila `sensitivitas.json` tidak ditemukan.

## Konvensi

- Skala abu-abu agar tetap terbaca bila dicetak hitam-putih.
- Label berbahasa Indonesia dengan desimal koma.
- Resolusi 300 dpi; seed bootstrap 2026, sama dengan analisis utama.
- U dihitung dengan logika yang sama dengan fungsi `analyse()` di `ikms_lib.py`: klaim berlabel S atau T dihitung tidak didukung, dan K3 adalah klaim K2 yang lolos gerbang mutu.
