"""
Kode visualisasi untuk naskah "Workslop on the Rig Floor" (IKMS 2026).

Menghasilkan:
  gambar1_alur_penelitian.png   - Gambar 1: alur penelitian (diagram, tanpa data)
  gambar2_U_per_kondisi.png     - Gambar 2: proporsi klaim tidak didukung per kejadian (U) per kondisi dan sumber label
  gambar3_jenis_galat.png       - Gambar 3: jenis galat klaim K2 dan bagian yang dibuang gerbang mutu
  gambar4_tau_dan_roc.png       - Gambar 4: (a) sapuan tau (R lawan Ret); (b) kurva ROC AlignScore dan HHEM

Cara pakai (Google Colab, di folder kerja notebook IKMS_2026_Eksperimen.ipynb):
  !python visualisasi_ikms.py                # semua gambar
  !python visualisasi_ikms.py --hanya 1 3 4  # sebagian gambar

Berkas data yang dibaca (semuanya dihasilkan notebook):
  claims_gated.pkl                          kolom: event_id, cid, cond, part, unknown, passed, align_score, hhem
  label_dua_penilai.pkl                     kolom: rid, label_1, label_2 (label sebelum diskusi, Sel 11)
  Diskusi_Klaim_Berbeda_final.xlsx          kolom: rid, label_akhir (hasil diskusi 101 klaim)
  Lembar_Penilai_Utama_KUNCI_TIM_A.csv      kolom: rid, event_id, cond, cid (kunci kondisi)
  sensitivitas.json                         keluaran Sel 13 (opsional; bila tidak ada dipakai angka Sel 13 di bawah)

Gambar 3 memakai hitungan taksonomi galat yang dilaporkan pada Subbagian 3.3 naskah (pengodean dari alasan penilai).
Semua gambar memakai skala abu-abu, label berbahasa Indonesia, desimal koma, dan resolusi 300 dpi.
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

FACT_PARTS = ["problem", "cause", "actions", "result"]
SEED = 2026
DPI = 300

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.formatter.use_locale": False, "savefig.dpi": DPI, "savefig.bbox": "tight",
})


def koma(x, d=0):
    """Format angka dengan desimal koma (EYD)."""
    return f"{x:.{d}f}".replace(".", ",")


def formatter_koma(d=0):
    return mticker.FuncFormatter(lambda v, _: koma(v, d))


# --------------------------------------------------------------------------- data
def baca_label(path_merged="label_dua_penilai.pkl", path_diskusi="Diskusi_Klaim_Berbeda_final.xlsx",
               path_kunci="Lembar_Penilai_Utama_KUNCI_TIM_A.csv"):
    """Kembalikan tabel klaim-kondisi dengan label akhir dan label setiap penilai sebelum diskusi."""
    m = pd.read_pickle(path_merged)[["rid", "label_1", "label_2"]]
    d = pd.read_excel(path_diskusi)[["rid", "label_akhir"]].dropna()
    d["label_akhir"] = d.label_akhir.astype(str).str.strip().str.upper()
    m = m.merge(d, on="rid", how="left")
    m["label_akhir"] = np.where(m.label_1 == m.label_2, m.label_1, m.label_akhir)
    kunci = pd.read_csv(path_kunci)[["rid", "event_id", "cond", "cid"]]
    lab = kunci.merge(m, on="rid")
    return lab[lab.label_akhir.isin(["D", "S", "T"])]


def u_per_kejadian(lab, cl, kolom_label):
    """U per kejadian untuk K1, K2, K3 (sama dengan logika analyse() di ikms_lib.py)."""
    k2 = cl[cl.cond == "K2"].set_index(["event_id", "cid"])
    lab = lab.copy()
    lab["passed"] = [k2.passed.get((e, c), np.nan) if cnd == "K2" else np.nan
                     for e, c, cnd in zip(lab.event_id, lab.cid, lab.cond)]
    lab["unsup"] = lab[kolom_label].isin(["S", "T"])
    out = {}
    for cond in ["K1", "K2", "K3"]:
        s = lab[(lab.cond == "K2") & (lab.passed == True)] if cond == "K3" else lab[lab.cond == cond]  # noqa: E712
        out[cond] = s.groupby("event_id").unsup.mean()
    return pd.DataFrame(out)


def ci_bootstrap(v, B=10000, seed=SEED):
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    rng = np.random.default_rng(seed)
    m = rng.choice(v, (B, len(v)), replace=True).mean(1)
    return np.percentile(m, [2.5, 97.5])


def roc(skor, positif):
    """Kurva ROC tanpa sklearn; skor rendah = lebih mungkin tidak didukung (positif)."""
    s = -np.asarray(skor, float)
    y = np.asarray(positif, bool)
    o = np.argsort(-s, kind="mergesort")
    s, y = s[o], y[o]
    batas = np.r_[np.where(np.diff(s))[0], len(s) - 1]
    tp = np.cumsum(y)[batas]
    fp = np.cumsum(~y)[batas]
    tpr = np.r_[0, tp / y.sum()]
    fpr = np.r_[0, fp / (~y).sum()]
    return fpr, tpr, float(np.trapezoid(tpr, fpr) if hasattr(np, "trapezoid") else np.trapz(tpr, fpr))


# --------------------------------------------------------------------------- Gambar 1
def gambar1(out="gambar1_alur_penelitian.png"):
    fig, ax = plt.subplots(figsize=(7.0, 4.7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def kotak(x, y, w, h, judul, isi="", tebal=False, isi_abu=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.5",
                                    fc="#e6e6e6" if isi_abu else "white", ec="black", lw=1.4 if tebal else 0.9))
        ax.text(x + w / 2, y + h - 3.2, judul, ha="center", va="top", fontsize=8.5, fontweight="bold")
        if isi:
            ax.text(x + w / 2, y + h - 8.2, isi, ha="center", va="top", fontsize=7.2, linespacing=1.25)

    def panah(x1, y1, x2, y2, gaya="-|>", putus=False):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=gaya, mutation_scale=9, lw=0.9,
                                     color="black", linestyle=(0, (3, 2)) if putus else "-"))

    kotak(3, 82, 27, 15, "Data Volve", "1.759 DDR · 26 lubang sumur")
    kotak(37, 82, 27, 15, "Kejadian NPT", "1.107 kejadian · 9.626,5 jam")
    kotak(71, 82, 26, 15, "Audit mutu DDR", "P1–P3 · validasi 100 kejadian")
    panah(30.6, 89.5, 36.4, 89.5)
    panah(64.6, 89.5, 70.4, 89.5)

    kotak(18, 63, 64, 12, "Pembagian per keluarga sumur (Tabel 1)",
          "pengembangan 635 · validasi 144 (τ) · uji 328 kejadian")
    panah(50.5, 81.4, 50.5, 75.6)

    kotak(3, 38, 28, 17, "K1: ekstraksi aturan", "kalimat DDR disalin\nmaks. 6 kalimat")
    kotak(36, 38, 28, 17, "K2: LLM bersitasi", "Qwen2.5-7B lokal · JSON\nsitasi kalimat wajib")
    kotak(69, 38, 28, 17, "K3: K2 + gerbang mutu", "cek leksikal + AlignScore ≥ τ\nhanya membuang klaim",
          tebal=True, isi_abu=True)
    for x in (17, 50, 83):
        panah(50.5, 62.4, x, 55.6)
    panah(64.6, 46.5, 68.4, 46.5, putus=True)

    kotak(3, 6, 52, 22, "Evaluasi terpisah dari gerbang (RQ1–RQ2)",
          "fakta kunci terhadap metadata tersembunyi\nHHEM-2.1-Open · penilaian buta dua penilai\n"
          "40 kejadian uji · 413 klaim · U, R, Ret")
    kotak(61, 6, 36, 22, "Penelusuran kasus (RQ3)", "BM25 · 30 kueri narasi mentah\nprecision@5 per kondisi")
    for x in (17, 50, 83):
        panah(x, 37.4, 29 if x < 70 else 79, 28.6)
    fig.savefig(out)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- Gambar 2
def gambar2(out="gambar2_U_per_kondisi.png", path_cl="claims_gated.pkl"):
    cl = pd.read_pickle(path_cl)
    lab = baca_label()
    sumber = [("label_akhir", "Label akhir (utama)", "o", "black"),
              ("label_1", "Penilai 1 (sebelum diskusi)", "s", "white"),
              ("label_2", "Penilai 2 (sebelum diskusi)", "^", "#9a9a9a")]
    U = {k: u_per_kejadian(lab, cl, k) * 100 for k, *_ in sumber}

    fig, ax = plt.subplots(figsize=(4.6, 3.1))
    xs = np.arange(3)
    rng = np.random.default_rng(SEED)
    for j, cond in enumerate(["K1", "K2", "K3"]):
        v = U["label_akhir"][cond].dropna().values
        ax.scatter(j - 0.27 + rng.uniform(-0.05, 0.05, len(v)), v, s=7, facecolor="none", edgecolor="#9a9a9a", lw=0.6)
    for i, (k, nama, mk, fc) in enumerate(sumber):
        off = (i - 1) * 0.16 + 0.05
        for j, cond in enumerate(["K1", "K2", "K3"]):
            v = U[k][cond].dropna().values
            lo, hi = ci_bootstrap(v)
            ax.errorbar(j + off, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt=mk, mfc=fc, mec="black",
                        ecolor="black", ms=5.5, capsize=2.5, lw=0.9, label=nama if j == 0 else None)
    ax.set_xticks(xs, ["K1\n(aturan)", "K2\n(LLM bersitasi)", "K3\n(K2 + gerbang)"])
    ax.set_ylabel("Klaim tidak didukung per kejadian, U (%)")
    ax.set_ylim(-3, 103)
    ax.yaxis.set_major_formatter(formatter_koma(0))
    ax.legend(frameon=False, loc="upper left")
    fig.savefig(out)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- Gambar 3
# Hitungan dari Subbagian 3.3: (jumlah klaim K2 pada jenis tsb., jumlah yang dibuang gerbang mutu)
TAKSONOMI = [("Isi tidak didukung sumber", 23, 19), ("Keluaran rusak atau terpotong", 6, 6),
             ("Pelajaran berasumsi", 41, 19), ("Salah peran (bagian keliru)", 25, 1),
             ('Omisi ("unknown" keliru)', 22, 0), ("Didukung (label D)", 202, 44)]


def gambar3(out="gambar3_jenis_galat.png"):
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    for i, (nama, n, buang) in enumerate(TAKSONOMI[::-1]):
        ax.barh(i, buang, color="#3a3a3a", edgecolor="black", lw=0.6, label="Dibuang gerbang" if i == 0 else None)
        ax.barh(i, n - buang, left=buang, color="white", edgecolor="black", hatch="////", lw=0.6,
                label="Lolos gerbang (tetap di K3)" if i == 0 else None)
        ax.text(n + 2, i, f"{buang} dari {n} dibuang ({koma(100 * buang / n)}%)", va="center", fontsize=8)
    ax.set_yticks(range(len(TAKSONOMI)), [t[0] for t in TAKSONOMI[::-1]])
    ax.set_xlabel("Jumlah klaim K2 pada 40 kejadian uji")
    ax.set_xlim(0, 300)
    ax.legend(frameon=False, loc="upper right")
    fig.savefig(out)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- Gambar 4
# Keluaran Sel 13 (dipakai bila sensitivitas.json tidak ada)
SENSITIVITAS_SEL13 = [
    {"tau": 0.00, "R_%": 5.62, "T_%": 89.43}, {"tau": 0.50, "R_%": 14.53, "T_%": 78.86},
    {"tau": 0.70, "R_%": 14.19, "T_%": 78.05}, {"tau": 0.80, "R_%": 15.96, "T_%": 76.42},
    {"tau": 0.90, "R_%": 19.82, "T_%": 70.73}, {"tau": 0.94, "R_%": 18.82, "T_%": 65.04},
    {"tau": 0.97, "R_%": 21.98, "T_%": 53.66}, {"tau": 0.99, "R_%": 16.69, "T_%": 36.59}]
ORACLE = {"R_%": 100.0, "T_%": 50.0}  # penyaring sempurna, 40 kejadian berlabel (Subbagian 3.3)


def gambar4(out="gambar4_tau_dan_roc.png", path_cl="claims_gated.pkl"):
    if os.path.exists("sensitivitas.json"):
        js = json.load(open("sensitivitas.json"))
        rows = js["sensitivitas"]
    else:
        rows = SENSITIVITAS_SEL13
    sens = pd.DataFrame(rows).sort_values("tau")

    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw={"width_ratios": [1.45, 1]})
    # (a) sapuan tau
    a.add_patch(Rectangle((90, 50), 12, 55, fc="#cfcfcf", ec="none"))
    a.text(96, 88, "daerah\ntarget", ha="center", fontsize=7.5)
    a.axhline(50, ls="--", lw=0.8, color="black")
    a.axvline(90, ls="--", lw=0.8, color="black")
    a.text(31, 52, "target R ≥ 50%", fontsize=7.5)
    a.text(89, 56, "target Ret ≥ 90%", fontsize=7.5, ha="right")
    a.plot(sens["T_%"], sens["R_%"], "-o", color="black", mfc="white", ms=4.5, lw=0.9)
    pakai = sens[np.isclose(sens.tau, 0.94)]
    a.plot(pakai["T_%"], pakai["R_%"], "o", color="black", ms=7)
    tengah = sens[sens.tau.between(0.49, 0.71)]  # titik 0,50 dan 0,70 berimpit: satu label gabungan
    for _, r in sens.iterrows():
        if r.tau in tengah.tau.values:
            continue
        if np.isclose(r.tau, 0.0):
            teks, xy, ha = "τ = 0", (5, -3), "left"
        else:
            teks, ha = ("τ = " if np.isclose(r.tau, 0.94) else "") + koma(r.tau, 2), "center"
            xy = (0, -11) if (np.isclose(r.tau, 0.99) or np.isclose(r.tau, 0.94)) else (0, 6)
        a.annotate(teks, (r["T_%"], r["R_%"]), textcoords="offset points", xytext=xy, ha=ha, fontsize=7,
                   fontweight="bold" if np.isclose(r.tau, 0.94) else "normal")
    if len(tengah):
        a.annotate(f"{koma(tengah.tau.min(), 2)}–{koma(tengah.tau.max(), 2)}",
                   (tengah["T_%"].mean(), tengah["R_%"].min()), textcoords="offset points", xytext=(0, -11),
                   ha="center", fontsize=7)
    a.plot(ORACLE["T_%"], ORACLE["R_%"], marker="*", ms=11, mfc="white", mec="black", ls="none")
    a.text(ORACLE["T_%"], ORACLE["R_%"] - 12, "penyaring sempurna\n(40 kejadian)", ha="center", fontsize=7)
    a.set_xlim(30, 102)
    a.set_ylim(0, 105)
    a.set_xlabel("Retensi, Ret (%)")
    a.set_ylabel("Reduksi klaim tidak didukung, R (%)")
    a.set_title("(a)", loc="left")
    a.xaxis.set_major_formatter(formatter_koma(0))
    a.yaxis.set_major_formatter(formatter_koma(0))

    # (b) ROC: klaim fakta K2 berlabel, bukan "unknown", punya kedua skor
    cl = pd.read_pickle(path_cl)
    lab = baca_label()
    k2 = lab[lab.cond == "K2"].merge(cl[cl.cond == "K2"][["event_id", "cid", "part", "unknown", "align_score", "hhem"]],
                                     on=["event_id", "cid"])
    k2 = k2[k2.part.isin(FACT_PARTS) & ~k2.unknown.astype(bool) & k2.align_score.notna() & k2.hhem.notna()]
    pos = k2.label_akhir.isin(["S", "T"]).values
    for kol, nama, gaya in [("align_score", "AlignScore", "-"), ("hhem", "HHEM", "--")]:
        fpr, tpr, auc = roc(k2[kol].values, pos)
        b.step(fpr, tpr, where="post", ls=gaya, color="black", lw=1.1, label=f"{nama} (AUC = {koma(auc, 2)})")
    b.plot([0, 1], [0, 1], ":", color="#7a7a7a", lw=0.9, label="Acak (AUC = 0,50)")
    b.set_xlabel("1 − spesifisitas")
    b.set_ylabel("Sensitivitas")
    b.set_title("(b)", loc="left")
    b.xaxis.set_major_formatter(formatter_koma(1))
    b.yaxis.set_major_formatter(formatter_koma(1))
    b.legend(frameon=False, loc="lower right", fontsize=7)
    print(f"ROC: n = {len(k2)} klaim fakta, {int(pos.sum())} tidak didukung")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hanya", nargs="*", type=int, default=[1, 2, 3, 4])
    args = ap.parse_args()
    fungsi = {1: gambar1, 2: gambar2, 3: gambar3, 4: gambar4}
    for k in args.hanya:
        print("tersimpan:", fungsi[k]())
