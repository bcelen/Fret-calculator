import streamlit as st
import pandas as pd
import math

st.title("THM Perde Ölçüleri")

# Inputs
colA, colB, colC = st.columns([1.2,1.2,1.2])
with colA:
    ref_freq = st.number_input("Referans frekans (Hz)", value=440.0, step=1.0)
with colB:
    string_length = st.number_input("Tel uzunluğu (mm)", value=740.0, step=1.0)
with colC:
    koma_cents = st.number_input("1 koma (cent cinsinden)", value=22.64, step=0.01, min_value=10.0, max_value=30.0)

# Additional koma definitions
colD, colE = st.columns([1,1])
with colD:
    b2_komas = st.number_input("b² koması", value=2.0, step=0.5, min_value=0.0)
with colE:
    s3_komas = st.number_input("♯³ koması", value=3.0, step=0.5, min_value=0.0)

# Helper for formatting with one decimal always
fmt1 = lambda x: f"{x:.1f}"

# Fret order (starting with open Re)
ORDER = [
    "re",  # open string (0 cents)
    "mi b", "mi b²", "mi",
    "fa", "fa♯³", "fa♯",
    "sol", "la b", "la b²", "la",
    "si b", "si b²", "si",
    "do", "re b", "re b²", "re",
    "mi b", "mi"
]

# Compute cents for each label based on koma size
def cents_of(label: str) -> float:
    l = label.replace(" ", "")
    if l == "re": return 0.0
    if l == "mib": return 100.0
    if l == "mib²": return 200.0 - b2_komas * koma_cents
    if l == "mi": return 200.0
    if l == "fa": return 300.0
    if l == "fa♯³": return 400.0 - s3_komas * koma_cents
    if l == "fa♯": return 400.0
    if l == "sol": return 500.0
    if l == "lab": return 600.0
    if l == "lab²": return 700.0 - b2_komas * koma_cents
    if l == "la": return 700.0
    if l == "sib": return 800.0
    if l == "sib²": return 900.0 - b2_komas * koma_cents
    if l == "si": return 900.0
    if l == "do": return 1000.0
    if l == "reb": return 1100.0
    if l == "reb²": return 1200.0 - b2_komas * koma_cents
    if l == "re" and label != "re": return 1200.0
    if l == "mib" and label.startswith("mi b"): return 1300.0
    if l == "mi" and label == "mi": return 1400.0
    return 0.0

def freq_from_cents(c):
    return ref_freq * (2 ** (c / 1200.0))

def nut_to_fret(c):
    return string_length * (1 - (2 ** (-c / 1200.0)))

rows = []
prev_dist = 0.0
for lab in ORDER:
    c = cents_of(lab)
    f = freq_from_cents(c)
    d = nut_to_fret(c)
    spacing = d - prev_dist
    prev_dist = d
    rows.append({
        "Perde": lab,
        "Cents": int(round(c)),
        "Frekans (Hz)": f"{f:.2f}",
        "Uzaklık (mm)": fmt1(d),
        "Aralık (mm)": fmt1(spacing)
    })

df = pd.DataFrame(rows, columns=["Perde", "Cents", "Frekans (Hz)", "Uzaklık (mm)", "Aralık (mm)"])
st.dataframe(df, hide_index=True, use_container_width=True)

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Tabloyu indir (CSV)", csv, "thm_perde_olculeri.csv", "text/csv", key="download-csv")
