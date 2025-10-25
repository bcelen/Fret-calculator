import streamlit as st
import pandas as pd
import math

st.title("THM Perde Ölçüleri")

# Inputs
ref_freq = st.number_input("Referans frekans (Hz):", value=440.0, step=1.0)
string_length = st.number_input("Tel uzunluğu (mm):", value=740.0, step=1.0)

# Constants
KOMA_PER_SEMITONE = 4.5
KOMA_SIZE = 100 / KOMA_PER_SEMITONE  # ≈22.22 cents

# Fret definitions: note label → cents relative to open (Re = 0)
FRETS = [
    ("mi b", 100),
    ("mi b²", 100 + 2 * KOMA_SIZE),
    ("mi", 200),
    ("fa", 300),
    ("fa♯³", 300 + 3 * KOMA_SIZE),
    ("fa♯", 400),
    ("sol", 500),
    ("la b", 600),
    ("la b²", 600 + 2 * KOMA_SIZE),
    ("la", 700),
    ("si b", 800),
    ("si b²", 800 + 2 * KOMA_SIZE),
    ("si", 900),
    ("do", 1000),
    ("re b", 1100),
    ("re b²", 1100 + 2 * KOMA_SIZE),
    ("re", 1200),
    ("mi b", 1300),
    ("mi", 1400)
]

# Compute frequencies, absolute distances, and spacing
data = []
previous_dist = 0
for label, cents in FRETS:
    freq = ref_freq * (2 ** (cents / 1200))
    dist = string_length * (1 - (2 ** (-cents / 1200)))
    spacing = dist - previous_dist
    previous_dist = dist
    data.append({
        "Perde": label,
        "Cents": round(cents),
        "Frekans (Hz)": round(freq, 2),
        "Uzaklık (mm)": round(dist, 1),
        "Aralık (mm)": round(spacing, 1)
    })

df = pd.DataFrame(data)
st.dataframe(df, hide_index=True, use_container_width=True)

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Tabloyu indir (CSV)", csv, "thm_perde_olculeri.csv", "text/csv", key="download-csv")
